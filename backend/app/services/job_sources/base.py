from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Protocol


@dataclass
class JobContent:
    """Standardized, source-agnostic job record produced by a job source."""

    source: str = "USER_SUBMITTED"
    source_url: str | None = None
    source_job_id: str | None = None
    title: str | None = None
    company: str | None = None
    location: str | None = None
    description: str | None = None
    application_url: str | None = None
    employment_type: str | None = None
    work_mode: str | None = None
    posted_at: date | None = None
    extra: dict = field(default_factory=dict)
    analyzed: bool = False


class JobSourceError(Exception):
    """Base class for job source failures."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class JobSource(Protocol):
    async def fetch(self, payload: dict) -> JobContent: ...