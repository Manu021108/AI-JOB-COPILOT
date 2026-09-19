"""Deterministic, offline match explanation generator.

Used by the mock LLM provider and as a fallback when the real provider errors.
Reads the same structured context that the real LLM sees and produces a
plausible strengths/gaps/explanation summary. It never invents data.
"""
from __future__ import annotations

import json

from app.schemas.match import MatchExplanationResponse


def explain_from_prompt(context_text: str) -> str:
    try:
        context = json.loads(context_text)
    except (json.JSONDecodeError, TypeError):
        context = {}
    response = build_explanation(context)
    return json.dumps(response.model_dump(), ensure_ascii=False)


def build_explanation(context: dict) -> MatchExplanationResponse:
    components = context.get("components", {}) or {}
    job = context.get("job", {}) or {}
    required_skills = job.get("required_skills", []) or []
    overall = context.get("overall_score")
    category = context.get("category") or "LOW_MATCH"
    matching = context.get("matching_skills", []) or []
    missing = context.get("missing_required_skills", []) or []
    related = context.get("related_required_matches", []) or []
    candidate = context.get("candidate", {}) or {}

    strengths: list[str] = []
    if required_skills:
        strengths.append(f"Matches {len(matching)} of {len(required_skills)} required skills")
    elif matching:
        strengths.append(f"Matches {len(matching)} relevant technologies from the role")

    if related:
        strengths.append(f"Related coverage for: {', '.join(related[:3])}")

    role_comp = components.get("role", {}) or {}
    if role_comp.get("score") is not None and role_comp["score"] >= 70:
        role_reason = (role_comp.get("detail") or "").strip()
        strengths.append(role_reason or "Target role aligns with the job title")

    exp_comp = components.get("experience", {}) or {}
    if exp_comp.get("score") is not None and exp_comp["score"] >= 100:
        try:
            strengths.append(f"Experience matches the job requirement ({exp_comp.get('required', '')})")
        except Exception:
            strengths.append("Experience matches the job requirement")

    project_comp = components.get("projects", {}) or {}
    relevant_projects = [p for p in (project_comp.get("relevant_projects", []) or [])][:4]

    gaps: list[str] = []
    if missing:
        gaps.append(f"Missing required skills: {', '.join(missing[:4])}")
    if exp_comp.get("score") is not None and exp_comp["score"] < 55 and exp_comp.get("status") == "below_required":
        gaps.append("Experience is below the job's stated requirement")
    if exp_comp.get("score") is not None and exp_comp.get("status") == "unknown":
        gaps.append("Experience not identified in the candidate profile")
    if (components.get("education", {}) or {}).get("status") == "below_required":
        gaps.append("Education does not meet the job's requirement")
    if (components.get("location", {}) or {}).get("status") == "mismatch":
        gaps.append("Candidate location does not match the job location")
    if not strengths and not gaps:
        strengths.append("Profile and role requirements overlap in multiple dimensions")

    if overall is None:
        explanation = "Match details have been computed for this role."
    else:
        explanation = (
            f"Overall alignment is {category.replace('_', ' ').title()} with a score of "
            f"{overall:.1f} against the configured matching criteria. "
        )
        if required_skills:
            explanation += f"The profile covers {len(matching)} of {len(required_skills)} required skills"
            if missing:
                explanation += f" but is missing {', '.join(missing[:3])}"
            explanation += "."
        elif missing:
            explanation += f"Missing required skills: {', '.join(missing[:3])}."

    response = MatchExplanationResponse(
        strengths=strengths[:4],
        gaps=gaps[:4],
        explanation=explanation,
        relevant_projects=[{"project": p.get("project", ""), "reason": p.get("reason", "")} for p in relevant_projects],
    )

    # Candidate fact safety: never claim things that are not in the profile.
    if not candidate.get("skills"):
        response.strengths = [s for s in response.strengths if "skills" not in s.lower()]

    return response