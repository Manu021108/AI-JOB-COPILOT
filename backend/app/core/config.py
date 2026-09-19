from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://job_copilot:change_me@localhost:5432/job_copilot"
    jwt_secret: str = "development-only-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    cors_origins: str = "http://localhost:3000"
    storage_path: str = "./storage"
    max_resume_size_mb: int = 10
    llm_provider: str = "mock"
    llm_api_key: str | None = None
    llm_model: str = "gpt-4o-mini"
    llm_base_url: str | None = None
    job_fetch_connect_timeout: float = 5.0
    job_fetch_timeout: float = 20.0
    job_fetch_max_size: int = 2_000_000
    job_fetch_max_redirects: int = 5
    job_import_rate_limit: int = 20
    job_import_rate_window: int = 60
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

@lru_cache
def get_settings() -> Settings:
    return Settings()
