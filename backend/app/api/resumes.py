import uuid
from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.orm import Session
from app.ai.resume_analyzer import ResumeAnalysisError
from app.core.database import get_db
from app.core.responses import ApiError, ok, raise_api
from app.models import Resume
from app.models.candidate_profile import CandidateProfile
from app.models.user import User
from app.api.users import get_current_user
from app.schemas.resume import ResumeDetail, ResumeListItem, ResumeUploadResponse
from app.services.document_parser import EmptyDocumentError, ScannedPdfError, UnsupportedDocumentError
from app.services.resume_service import ResumeNotFoundError, ResumeService, ResumeUploadError

router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.post("/upload", status_code=status.HTTP_201_CREATED)
def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    content = file.file.read()
    service = ResumeService()
    try:
        resume, _analysis, profile_created = service.upload_resume(
            db, current_user, file.filename or "", file.content_type, content
        )
    except ResumeUploadError as exc:
        code_map = {"FILE_TOO_LARGE": 413}
        raise_api(ApiError(exc.code, exc.message, code_map.get(exc.code, status.HTTP_400_BAD_REQUEST)))
    except UnsupportedDocumentError as exc:
        raise_api(ApiError("CORRUPTED_FILE", str(exc), status.HTTP_400_BAD_REQUEST))
    except EmptyDocumentError as exc:
        raise_api(ApiError("EMPTY_DOCUMENT", str(exc), status.HTTP_422_UNPROCESSABLE_ENTITY))
    except ScannedPdfError as exc:
        raise_api(ApiError("SCANNED_PDF", str(exc), status.HTTP_422_UNPROCESSABLE_ENTITY))
    except ResumeAnalysisError:
        raise_api(ApiError("ANALYSIS_FAILED", "We couldn't analyze this resume. Please try again.", status.HTTP_422_UNPROCESSABLE_ENTITY))
    except Exception:
        raise_api(ApiError("UPLOAD_FAILED", "The resume could not be processed. Please try again.", status.HTTP_500_INTERNAL_SERVER_ERROR))
    return ok(ResumeUploadResponse.model_validate(resume).model_dump() | {"profile_created": profile_created})


@router.get("")
def list_resumes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    service = ResumeService()
    resumes = service.list_resumes(db, current_user)
    profile = db.query(CandidateProfile).filter(CandidateProfile.user_id == current_user.id).first()
    profile_resume_id = profile.resume_id if profile else None
    items = []
    for resume in resumes:
        item = ResumeListItem.model_validate(resume).model_dump()
        item["has_profile"] = resume.id == profile_resume_id
        items.append(item)
    return ok(items)


@router.get("/{resume_id}")
def get_resume(
    resume_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    service = ResumeService()
    try:
        resume = service.get_resume(db, current_user, resume_id)
    except ResumeNotFoundError:
        raise_api(ApiError("RESUME_NOT_FOUND", "Resume not found.", status.HTTP_404_NOT_FOUND))
    return ok(ResumeDetail.model_validate(resume).model_dump())


@router.delete("/{resume_id}")
def delete_resume(
    resume_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    service = ResumeService()
    try:
        deleted = service.delete_resume(db, current_user, resume_id)
    except ResumeNotFoundError:
        raise_api(ApiError("RESUME_NOT_FOUND", "Resume not found.", status.HTTP_404_NOT_FOUND))
    return ok({"id": str(deleted.id)})