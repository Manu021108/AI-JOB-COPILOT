from __future__ import annotations

import re
from dataclasses import dataclass, field

_WORD_RE = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class LocationMatchResult:
    score: float
    applicable: bool
    alignment: dict = field(default_factory=dict)


def _city_tokens(location: str | None) -> set[str]:
    if not location:
        return set()
    city = (location or "").split(",")[0]
    return set(_WORD_RE.findall(city.lower()))


def _normalize_work_mode(work_mode: str | None) -> str | None:
    value = ((work_mode or "").strip().lower() or None)
    if value == "on-site":
        return "onsite"
    return value


def match_location(job_location: str | None, job_work_mode: str | None, candidate_location: str | None) -> LocationMatchResult:
    work_mode = _normalize_work_mode(job_work_mode)
    job_location = ((job_location or "").strip() or None)

    if not job_location and not work_mode:
        return LocationMatchResult(score=0.0, applicable=False, alignment={"status": "neutral", "reason": "The job does not specify a location or work mode."})

    if work_mode == "remote":
        return LocationMatchResult(score=100.0, applicable=True, alignment={"status": "aligned", "reason": "Remote role — location compatible."})

    if not candidate_location:
        reason = "Candidate location was not identified; treated neutrally."
        return LocationMatchResult(score=50.0, applicable=True, alignment={"status": "unknown", "reason": reason})

    base_score = _city_match(job_location, candidate_location) if job_location else None

    if work_mode == "hybrid":
        score = max(base_score if base_score is not None else 60.0, 60.0) if base_score is not None else 60.0
    else:
        score = base_score if base_score is not None else 50.0

    if base_score is None:
        status, reason = "unknown", "No job location given."
    else:
        status = "aligned" if base_score >= 70 else ("partial" if base_score >= 40 else "mismatch")
        reason = f"Candidate location “{candidate_location}” vs job location “{job_location}”."

    return LocationMatchResult(score=round(score, 1), applicable=True, alignment={"status": status, "reason": reason})


def _city_match(job_location: str, candidate_location: str) -> float:
    job_tokens = _city_tokens(job_location)
    candidate_tokens = _city_tokens(candidate_location)
    if not job_tokens or not candidate_tokens:
        return 50.0

    # Normalized whole-city equality.
    if job_tokens == candidate_tokens:
        return 100.0

    shared = job_tokens.intersection(candidate_tokens)
    if shared:
        # Same city (possibly with extra region tokens on one side) -> match.
        bigger = max(len(job_tokens), len(candidate_tokens))
        if len(shared) == min(len(job_tokens), len(candidate_tokens)) and len(shared) / bigger >= 0.5:
            return 100.0
        union = job_tokens.union(candidate_tokens) or {""}
        return round(len(shared) / len(union) * 100.0, 1)
    return 0.0