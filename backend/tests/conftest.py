import os
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
os.environ["STORAGE_PATH"] = str(TESTS_DIR / ".test_storage")
os.environ["DATABASE_URL"] = "postgresql+psycopg://job_copilot:change_me@localhost:5432/job_copilot"
os.environ.setdefault("JWT_SECRET", "test-only-secret")

from app.core.config import get_settings

get_settings.cache_clear()