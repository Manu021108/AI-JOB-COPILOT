"""Builds the compact context passed to the match explainer and orchestrates
explanation generation with a deterministic fallback."""
from __future__ import annotations

from typing import Any

from app.ai.match_explainer import MatchExplainer
from app.schemas.match import MatchExplanationResponse


def build_explainer_context(candidate, job, match: Any) -> dict:
    """Concise, controlled context for the LLM: only necessary facts."""
    candidate_skills = [s.lower() if isinstance(s, str) else s for s in candidate.skills]

    return {
        "candidate": {
            "target_roles": list(candidate.target_roles or []),
            "skills": candidate_skills,
            "location": candidate.location,
            "experience_years": candidate.years_of_experience,
            "professional_summary": (candidate.professional_summary or "")[:500] or None,
        },
        "job": {
            "title": job.title,
            "required_skills": list((job.analysis.required_skills if job.analysis else []) or []),
            "preferred_skills": list((job.analysis.preferred_skills if job.analysis else []) or []),
            "nice_to_have": list((job.analysis.nice_to_have if job.analysis else []) or []),
        },
        "components": {
            "skills": {
                "score": match.scores.get("skills"),
                "matching_skills": match.matching_skills,
                "missing_required_skills": match.missing_required_skills,
                "detail": _detail_text_for(match),
            },
            "role": _component(match.role_alignment, match.scores.get("role")),
            "experience": {
                "score": match.scores.get("experience"),
                "status": match.experience_alignment.get("status"),
                "required": match.experience_alignment.get("required"),
                "candidate_years": match.experience_alignment.get("candidate_years"),
            },
            "education": {
                "score": match.scores.get("education"),
                "status": match.education_alignment.get("status"),
                "reason": match.education_alignment.get("reason"),
            },
            "location": {
                "score": match.scores.get("location"),
                "status": match.location_alignment.get("status"),
                "reason": match.location_alignment.get("reason"),
            },
            "projects": {
                "score": match.scores.get("project"),
                "status": match.project_alignment.get("status"),
                "relevant_projects": [
                    {"project": p["project"], "reason": p["reason"], "score": p.get("score")}
                    for p in match.relevant_projects
                ],
            },
        },
        "matching_skills": match.matching_skills,
        "related_required_matches": match.related_required_matches,
        "missing_required_skills": match.missing_required_skills,
        "overall_score": match.overall_score,
        "category": match.category,
        "match_version": match.match_version,
    }


def generate_explanation(candidate, job, match: Any, explainer: MatchExplainer | None = None) -> MatchExplanationResponse:
    explainer = explainer or MatchExplainer()
    context = build_explainer_context(candidate, job, match)
    return explainer.explain(context)


def _component(alignment: dict, score) -> dict:
    return {"score": score, "status": alignment.get("status"), "detail": alignment.get("reason")}


def _detail_text_for(match: Any) -> str:
    if match.matching_skills or match.missing_required_skills:
        total = len(match.matching_skills) + len(match.related_required_matches) + len(match.missing_required_skills)
        if total:
            return f"Matched {len(match.matching_skills)} of {total} required skills"
    return match.role_alignment.get("reason", "")