from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

from app.services.embeddings import cosine_similarity, normalize_score
from app.services.embeddings.local import build_embedding_provider
from app.services.matching.config import SEMANTIC_MIN_TEXT_CHARS

CANDIDATE_MAX_CHARS = 8000
JOB_MAX_CHARS = 8000


@dataclass(frozen=True)
class SemanticMatchResult:
    score: float
    applicable: bool
    alignment: dict = field(default_factory=dict)


def build_candidate_text(
    target_roles: list[str],
    skills: list[str],
    professional_summary: str | None,
    experience_descriptions: list[str],
    project_texts: list[str],
) -> str:
    parts: list[str] = []
    if target_roles:
        parts.append("Target roles: " + ", ".join(target_roles))
    if professional_summary:
        parts.append("Summary: " + professional_summary)
    if skills:
        parts.append("Skills: " + ", ".join(skills))
    for description in experience_descriptions:
        if description:
            parts.append("Experience: " + description)
    for project_text in project_texts:
        if project_text:
            parts.append("Project: " + project_text)
    return "\n".join(parts)[:CANDIDATE_MAX_CHARS]


def build_job_text(
    title: str | None,
    summary: str | None,
    required_skills: list[str],
    preferred_skills: list[str],
    responsibilities: list[str],
    qualifications: list[str],
    description: str | None,
) -> str:
    parts: list[str] = []
    if title:
        parts.append("Title: " + title)
    if summary:
        parts.append("Summary: " + summary)
    if required_skills:
        parts.append("Required skills: " + ", ".join(required_skills))
    if preferred_skills:
        parts.append("Preferred skills: " + ", ".join(preferred_skills))
    if responsibilities:
        parts.append("Responsibilities: " + " ".join(responsibilities))
    if qualifications:
        parts.append("Qualifications: " + " ".join(qualifications))
    if description:
        parts.append("Description: " + description)
    return "\n".join(parts)[:JOB_MAX_CHARS]


@lru_cache(maxsize=256)
def _embed(text: str) -> tuple[float, ...]:
    provider = build_embedding_provider()
    return tuple(provider.generate_embedding(text))


def match_semantic(candidate_text: str, job_text: str, override_score: float | None = None) -> SemanticMatchResult:
    candidate_text = (candidate_text or "").strip()
    job_text = (job_text or "").strip()

    if len(candidate_text) < SEMANTIC_MIN_TEXT_CHARS or len(job_text) < SEMANTIC_MIN_TEXT_CHARS:
        return SemanticMatchResult(score=0.0, applicable=False, alignment={"status": "neutral", "reason": "Not enough text to compare semantically."})

    if override_score is not None:
        score = float(override_score)
    else:
        candidate_vector = _embed(candidate_text)
        job_vector = _embed(job_text)
        score = normalize_score(cosine_similarity(candidate_vector, job_vector))

    return SemanticMatchResult(score=round(score, 1), applicable=True, alignment={"status": "aligned"})


def clear_embedding_cache() -> None:
    _embed.cache_clear()