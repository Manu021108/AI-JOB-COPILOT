from __future__ import annotations

from dataclasses import dataclass, field

from app.services.matching.config import (
    PREFERRED_BONUS_SPAN,
    PREFERRED_RELATED_CREDIT,
    REQUIRED_RELATED_CREDIT,
)
from app.services.matching.skill_normalizer import normalize_skill
from app.services.matching.skill_relationships import related_skills


@dataclass(frozen=True)
class SkillMatchResult:
    score: float
    applicable: bool
    matching_skills: list[str] = field(default_factory=list)
    matching_preferred_skills: list[str] = field(default_factory=list)
    related_required_matches: list[str] = field(default_factory=list)
    missing_required_skills: list[str] = field(default_factory=list)
    detail: str = ""


def match_skills(
    candidate_names: list[str],
    required_skills: list[str],
    preferred_skills: list[str],
) -> SkillMatchResult:
    """Compares candidate skills against the job's required and preferred sets.

    Exact matches score full credit; explicit related-skill matches score
    partial credit (see config). Missing required skills hurt more than a lack
    of nice-to-have ones. Returns a 0..100 score when at least one requirement
    exists, otherwise the component is marked not applicable (neutral).
    """
    required_skills = [s for s in (required_skills or []) if s]
    preferred_skills = [s for s in (preferred_skills or []) if s]

    if not required_skills and not preferred_skills:
        return SkillMatchResult(score=0.0, applicable=False, detail="The job lists no skill requirements.")

    candidate_normalized = {normalize_skill(name).lower() for name in candidate_names if name}
    candidate_normalized.discard("")

    def _hits(names: list[str]) -> tuple[list[str], list[str], list[str]]:
        exact: list[str] = []
        related: list[str] = []
        missing: list[str] = []
        for raw in names:
            name = normalize_skill(raw)
            key = name.lower()
            if not key:
                continue
            if key in candidate_normalized:
                exact.append(name)
                continue
            related_set = {relation.lower() for relation in related_skills(name)}
            if related_set and related_set.intersection(candidate_normalized):
                related.append(name)
                continue
            missing.append(name)
        return exact, related, missing

    req_exact, req_related, req_missing = _hits(required_skills)
    pref_exact, pref_related, _pref_missing = _hits(preferred_skills)

    req_credit = len(req_exact) + len(req_related) * REQUIRED_RELATED_CREDIT
    pref_credit = len(pref_exact) + len(pref_related) * PREFERRED_RELATED_CREDIT

    req_ratio = req_credit / len(required_skills) if required_skills else None
    pref_ratio = pref_credit / len(preferred_skills) if preferred_skills else None

    if req_ratio is not None:
        score = req_ratio * 100.0
        if pref_ratio is not None:
            # Preferred skills tune the score by at most +/-10 around the base.
            score += (pref_ratio - 0.5) * PREFERRED_BONUS_SPAN
    elif pref_ratio is not None:
        # Only "preferred" skills were listed, so treat them as soft requirements.
        score = 50.0 + (pref_ratio - 0.5) * 100.0
    else:
        score = 0.0

    score = max(0.0, min(100.0, score))
    score = round(score, 1)

    detail = _detail(required_skills, req_exact, req_missing)
    return SkillMatchResult(
        score=score,
        applicable=True,
        matching_skills=req_exact,
        matching_preferred_skills=pref_exact,
        related_required_matches=req_related,
        missing_required_skills=req_missing,
        detail=detail,
    )


def _detail(required_skills: list[str], exact: list[str], missing: list[str]) -> str:
    if required_skills:
        base = f"Matched {len(exact)} of {len(required_skills)} required skills"
        if missing:
            base += f"; missing {', '.join(missing[:4])}"
        return base
    return "Matched preferred skills (no hard requirements listed)."