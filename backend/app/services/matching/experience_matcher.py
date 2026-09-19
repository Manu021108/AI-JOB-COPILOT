from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from app.services.job_normalizer import infer_experience_range
from app.services.matching.config import EXPERIENCE_ONLY_MAX_PENALTY, EXPERIENCE_OVER_QUALIFICATION_PENALTY

MONTHS_PER_YEAR = 12.0
DAYS_PER_MONTH = 30.44


@dataclass(frozen=True)
class ExperienceMatchResult:
    score: float
    applicable: bool
    alignment: dict = field(default_factory=dict)


def compute_candidate_years(years_of_experience: float | None, entries: list[dict]) -> float | None:
    """Total candidate experience in years, from explicit years or work entries."""
    if isinstance(years_of_experience, (int, float)) and not isinstance(years_of_experience, bool):
        value = float(years_of_experience)
        if value >= 0:
            return round(value, 1)

    total_months = 0.0
    today = date.today()
    for entry in entries or []:
        start = entry.get("start_date")
        end = entry.get("end_date")
        is_current = bool(entry.get("is_current"))
        if start is None:
            continue
        if end is not None and end < start:
            continue
        if (end is None and not is_current):
            continue
        effective_end = end or today
        total_months += max(0, (effective_end - start).days) / DAYS_PER_MONTH
    if total_months <= 0:
        return None
    return round(total_months / MONTHS_PER_YEAR, 1)


def job_requirement(experience_min: int | None, experience_max: int | None, analysis_requirements: list[str]) -> tuple[int | None, int | None]:
    """Job experience requirement in (min, max) years. Uses parsed analysis first."""
    if experience_min is not None or experience_max is not None:
        return experience_min, experience_max
    text = " ".join(analysis_requirements or [])
    if text.strip():
        low, high = infer_experience_range(text)
        return low, high
    return None, None


def match_experience(candidate_years: float | None, job_min: int | None, job_max: int | None) -> ExperienceMatchResult:
    if job_min is None and job_max is None:
        return ExperienceMatchResult(score=0.0, applicable=False, alignment={"status": "neutral", "reason": "The job does not specify an experience requirement."})

    required = _range_text(job_min, job_max)
    if candidate_years is None:
        return ExperienceMatchResult(
            score=50.0,
            applicable=True,
            alignment={"status": "unknown", "reason": "Experience was not identified in the candidate profile.", "required": required},
        )

    score = _score(candidate_years, job_min, job_max)
    status = _status(score, candidate_years, job_min, job_max)
    reason = f"Candidate has ~{candidate_years} years; job requires {required}."
    return ExperienceMatchResult(
        score=round(score, 1),
        applicable=True,
        alignment={"status": status, "reason": reason, "required": required, "candidate_years": candidate_years},
    )


def _score(candidate: float, job_min: int | None, job_max: int | None) -> float:
    if job_min is not None and job_max is not None:
        if job_min <= candidate <= job_max:
            return 100.0
        if candidate < job_min:
            return max(0.0, candidate / max(job_min, 1) * 100.0)
        return max(50.0, 100.0 - (candidate - job_max) * EXPERIENCE_OVER_QUALIFICATION_PENALTY)
    if job_min is not None:
        if candidate >= job_min:
            return 100.0
        return max(0.0, candidate / max(job_min, 1) * 100.0)
    if job_max is not None:
        if candidate <= job_max:
            return 100.0
        return max(30.0, 100.0 - (candidate - job_max) * EXPERIENCE_ONLY_MAX_PENALTY)
    return 50.0


def _status(score, candidate, job_min, job_max) -> str:
    if job_min is not None and candidate < job_min:
        return "below_required"
    if score >= 100:
        return "aligned"
    return "partial"


def _range_text(job_min: int | None, job_max: int | None) -> str:
    if job_min is not None and job_max is not None:
        return f"{job_min}–{job_max} years"
    if job_min is not None:
        return f"{job_min}+ years"
    if job_max is not None:
        return f"up to {job_max} years"
    return "unspecified"