"""Manual job source: accepts user-provided job information directly."""
from __future__ import annotations

import re
from datetime import datetime

from app.services.job_normalizer import (
    infer_employment_type,
    infer_experience_range,
    infer_salary,
    infer_work_mode,
    normalize_employment_type,
    normalize_text,
    normalize_work_mode,
    parse_posted_date,
)
from app.services.job_sources.base import JobContent, JobSourceError

_SALARY_PATTERN = re.compile(r"^(\d[\d,]*)\s*-\s*(\d[\d,]*)\s*([A-Za-z$€£₹]{1,5})$", re.IGNORECASE)


class ManualJobSource:
    """Build a JobContent from hand-entered job fields (no analysis implied)."""

    name = "USER_SUBMITTED"

    async def fetch(self, payload: dict) -> JobContent:
        title = normalize_text(payload.get("title"))
        if not title:
            raise JobSourceError("VALIDATION_ERROR", "Job title is required.")
        company = normalize_text(payload.get("company")) or ""
        location = normalize_text(payload.get("location"))
        description = normalize_text(payload.get("description") or "")

        employment_type = normalize_employment_type(payload.get("employment_type")) or infer_employment_type(description)
        work_mode = normalize_work_mode(payload.get("work_mode")) or infer_work_mode(description)
        experience_min, experience_max = _experience(payload, description)
        salary_min, salary_max, currency = _salary(payload, description)
        posted_at = parse_posted_date(description)

        application_url = normalize_text(payload.get("application_url") or payload.get("source_url"))
        source_url = normalize_text(payload.get("source_url"))

        return JobContent(
            source=self.name,
            source_url=source_url,
            source_job_id=normalize_text(payload.get("source_job_id")),
            title=title,
            company=company,
            location=location,
            description=description,
            application_url=application_url,
            employment_type=employment_type,
            work_mode=work_mode,
            posted_at=posted_at,
            extra={
                "experience_min": experience_min,
                "experience_max": experience_max,
                "salary_min": salary_min,
                "salary_max": salary_max,
                "salary_currency": currency,
            },
            analyzed=False,
        )


def _experience(payload: dict, description: str) -> tuple[int | None, int | None]:
    explicit_min = payload.get("experience_min")
    explicit_max = payload.get("experience_max")
    if explicit_min is not None or explicit_max is not None:
        low = int(explicit_min) if explicit_min not in (None, "") else None
        high = int(explicit_max) if explicit_max not in (None, "") else None
        return low, high
    return infer_experience_range(description)


def _salary(payload: dict, description: str) -> tuple[int | None, int | None, str | None]:
    if payload.get("salary_min") is not None or payload.get("salary_max") is not None:
        low = payload.get("salary_min")
        high = payload.get("salary_max")
        return (_to_int(low), _to_int(high), (payload.get("salary_currency") or "USD").strip().upper() or None)
    return infer_salary(description)


def _to_int(value) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(str(value).replace(",", "")))
    except (TypeError, ValueError):
        return None