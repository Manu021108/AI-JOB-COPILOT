import re
import uuid
from pathlib import Path
from app.core.config import get_settings

ALLOWED_EXTENSIONS = {"pdf", "docx"}


def _storage_root() -> Path:
    root = Path(get_settings().storage_path).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def max_file_size_bytes() -> int:
    return get_settings().max_resume_size_mb * 1024 * 1024


def is_allowed_extension(filename: str) -> bool:
    return filename.rsplit(".", 1)[-1].lower() in ALLOWED_EXTENSIONS if "." in filename else False


class StorageService:
    """Local disk storage abstraction.

    The interface is intentionally provider-agnostic so it can be swapped for
    S3/MinIO/object storage later without touching the resume API.
    """

    def save_file(self, user_id: str | uuid.UUID, file_type: str, content: bytes) -> str:
        user_dir = _storage_root() / "resumes" / str(user_id)
        user_dir.mkdir(parents=True, exist_ok=True)
        rel_path = f"resumes/{user_id}/{uuid.uuid4()}.{file_type}"
        full_path = _storage_root() / rel_path
        full_path.write_bytes(content)
        return rel_path

    def get_file(self, storage_path: str) -> bytes:
        full_path = self._resolve(storage_path)
        return full_path.read_bytes()

    def delete_file(self, storage_path: str) -> None:
        full_path = self._resolve(storage_path)
        try:
            full_path.unlink(missing_ok=True)
            parent = full_path.parent
            if parent.is_dir() and not any(parent.iterdir()):
                parent.rmdir()
        except OSError:
            pass

    def _resolve(self, storage_path: str) -> Path:
        root = _storage_root()
        candidate = (root / storage_path).resolve()
        if not candidate.is_relative_to(root):
            raise ValueError("Invalid storage path")
        return candidate


def validate_filename(filename: str) -> str:
    """Sanitize an uploaded filename to a safe display name."""
    name = Path(filename.replace("\\", "/")).name
    name = re.sub(r"[^A-Za-z0-9._() -]", "_", name).strip()
    if not name or name in {".", ".."}:
        raise ValueError("Invalid filename")
    return name[:255]