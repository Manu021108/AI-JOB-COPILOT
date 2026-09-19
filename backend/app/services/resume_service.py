import re
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.ai.resume_analyzer import ResumeAnalyzer, ResumeAnalysisError
from app.core.config import get_settings
from app.models import Resume
from app.models.user import User
from app.models.candidate_profile import CandidateProfile
from app.schemas.resume import ResumeAnalysis
from app.services.document_parser import (
    EmptyDocumentError,
    ScannedPdfError,
    UnsupportedDocumentError,
    extract_docx_text,
    extract_pdf_text,
)
from app.services.profile_service import apply_analysis
from app.services.storage import ALLOWED_EXTENSIONS, StorageService, is_allowed_extension, max_file_size_bytes, validate_filename
from app.services.text_cleaner import clean_text

MIME_BY_EXTENSION = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
MAGIC_PDF = b"%PDF-"
MAGIC_ZIP = b"PK\x03\x04"


class ResumeUploadError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class ResumeNotFoundError(Exception):
    pass


class ResumeService:
    def __init__(self, storage: StorageService | None = None, analyzer: ResumeAnalyzer | None = None) -> None:
        self.storage = storage or StorageService()
        self.analyzer = analyzer or ResumeAnalyzer()

    def upload_resume(
        self,
        db: Session,
        user: User,
        filename: str,
        content_type: str | None,
        content: bytes,
    ) -> tuple[Resume, ResumeAnalysis, bool]:
        file_type, safe_name = _validate_upload(filename, content_type, content)
        display_name = sanitize_display_name(safe_name)

        storage_path = self.storage.save_file(user.id, file_type, content)
        try:
            text = self._extract_text(storage_path, file_type)
        except Exception:
            self.storage.delete_file(storage_path)
            raise
        raw_text = clean_text(text)

        version = self._next_version(db, user.id)
        resume = Resume(
            user_id=user.id,
            original_filename=display_name,
            file_type=file_type,
            file_size=len(content),
            storage_path=storage_path,
            raw_text=raw_text,
            version=version,
            is_active=True,
        )
        db.add(resume)
        db.flush()

        if version > 1:
            db.execute(Resume.__table__.update().where(Resume.user_id == user.id, Resume.version != version).values(is_active=False))

        profile_existed = db.scalar(select(CandidateProfile.id).where(CandidateProfile.user_id == user.id)) is not None

        analysis = None
        try:
            analysis = self.analyzer.analyze(raw_text)
        except ResumeAnalysisError:
            self.storage.delete_file(storage_path)
            if resume.id:
                db.delete(resume)
            raise
        apply_analysis(db, user, resume, analysis)
        db.commit()
        db.refresh(resume)
        if analysis is None:
            raise ResumeAnalysisError("Resume analysis failed.")
        return resume, analysis, not profile_existed

    def list_resumes(self, db: Session, user: User) -> list[Resume]:
        return list(db.scalars(
            select(Resume)
            .where(Resume.user_id == user.id)
            .order_by(Resume.version.desc())
        ))

    def get_resume(self, db: Session, user: User, resume_id) -> Resume:
        resume = db.get(Resume, resume_id)
        if resume is None or resume.user_id != user.id:
            raise ResumeNotFoundError()
        return resume

    def delete_resume(self, db: Session, user: User, resume_id) -> Resume:
        resume = self.get_resume(db, user, resume_id)
        self.storage.delete_file(resume.storage_path)
        db.delete(resume)
        db.commit()
        return resume

    def _extract_text(self, storage_path: str, file_type: str) -> str:
        full_path = self.storage._resolve(storage_path)
        if file_type == "pdf":
            return extract_pdf_text(full_path)
        return extract_docx_text(full_path)

    def _next_version(self, db: Session, user_id) -> int:
        current = db.scalar(select(func.max(Resume.version)).where(Resume.user_id == user_id))
        return (current or 0) + 1


def _validate_upload(filename: str, content_type: str | None, content: bytes) -> tuple[str, str]:
    if not filename or not is_allowed_extension(filename):
        raise ResumeUploadError("INVALID_FILE_TYPE", "Please upload a PDF or DOCX file.")
    file_type = filename.rsplit(".", 1)[-1].lower()
    if len(content) == 0:
        raise ResumeUploadError("EMPTY_FILE", "The uploaded file is empty.")
    limit = max_file_size_bytes()
    if len(content) > limit:
        size_mb = get_settings().max_resume_size_mb
        raise ResumeUploadError("FILE_TOO_LARGE", f"The file exceeds the {size_mb} MB size limit.")
    if not _content_matches(file_type, content):
        raise ResumeUploadError("CORRUPTED_FILE", f"The file does not appear to be a valid {file_type.upper()} document.")
    if content_type and content_type.lower() not in (
        "application/octet-stream",
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
        "application/zip",
    ):
        if MIME_BY_EXTENSION.get(file_type) and content_type.lower() != MIME_BY_EXTENSION[file_type]:
            pass
    safe_name = _sanitize_internal_name(filename, file_type)
    return file_type, safe_name


def _content_matches(file_type: str, content: bytes) -> bool:
    if file_type == "pdf":
        return content.lstrip()[:5] == MAGIC_PDF or content[:4] == MAGIC_PDF
    return content[:4] == MAGIC_ZIP


def _sanitize_internal_name(filename: str, file_type: str) -> str:
    base = re.sub(r"[^A-Za-z0-9._ -]", "_", filename.rsplit(".", 1)[0]) or "resume"
    return f"{base[:120]}.{file_type}"


def sanitize_display_name(filename: str) -> str:
    try:
        return validate_filename(filename)
    except ValueError:
        return "resume" + (filename.rsplit(".", 1)[-1] if "." in filename else ".pdf")