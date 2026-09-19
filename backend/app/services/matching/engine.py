"""Hybrid job matching engine.

Combines a deterministic rule-based matcher with a semantic similarity score.
The final score is always computed in Python from the configured weights; the
LLM is used only for explanation text later in the pipeline and can never
alter the score.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.services.matching.config import MATCH_VERSION, category_for_score, normalized_weights
from app.services.matching.education_matcher import match_education
from app.services.matching.experience_matcher import match_experience
from app.services.matching.location_matcher import match_location
from app.services.matching.project_matcher import match_projects
from app.services.matching.role_matcher import match_role
from app.services.matching.semantic_matcher import (
    SemanticMatchResult,
    build_candidate_text,
    build_job_text,
    match_semantic,
)
from app.services.matching.skill_matcher import match_skills


@dataclass
class ExperienceEntrySnapshot:
    company: str = ""
    job_title: str = ""
    description: str | None = None
    start_date: object | None = None
    end_date: object | None = None
    is_current: bool = False


@dataclass
class ProjectSnapshot:
    project_name: str = ""
    description: str | None = None
    technologies: list[str] = field(default_factory=list)


@dataclass
class EducationSnapshot:
    institution: str = ""
    degree: str | None = None
    field_of_study: str | None = None


@dataclass
class CandidateSnapshot:
    target_roles: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    years_of_experience: float | None = None
    experience: list[ExperienceEntrySnapshot] = field(default_factory=list)
    projects: list[ProjectSnapshot] = field(default_factory=list)
    education: list[EducationSnapshot] = field(default_factory=list)
    location: str | None = None
    professional_summary: str | None = None


@dataclass
class JobAnalysisSnapshot:
    summary: str | None = None
    required_skills: list[str] = field(default_factory=list)
    preferred_skills: list[str] = field(default_factory=list)
    responsibilities: list[str] = field(default_factory=list)
    qualifications: list[str] = field(default_factory=list)
    education_requirements: list[str] = field(default_factory=list)
    experience_requirements: list[str] = field(default_factory=list)
    tools_and_technologies: list[str] = field(default_factory=list)
    nice_to_have: list[str] = field(default_factory=list)


@dataclass
class JobSnapshot:
    title: str = ""
    company: str = ""
    location: str | None = None
    work_mode: str | None = None
    employment_type: str | None = None
    experience_min: int | None = None
    experience_max: int | None = None
    description: str | None = None
    analysis: JobAnalysisSnapshot | None = None


@dataclass
class MatchResult:
    overall_score: float
    category: str
    match_version: str
    scores: dict = field(default_factory=dict)
    matching_skills: list[str] = field(default_factory=list)
    matching_preferred_skills: list[str] = field(default_factory=list)
    related_required_matches: list[str] = field(default_factory=list)
    missing_required_skills: list[str] = field(default_factory=list)
    role_alignment: dict = field(default_factory=dict)
    experience_alignment: dict = field(default_factory=dict)
    education_alignment: dict = field(default_factory=dict)
    project_alignment: dict = field(default_factory=dict)
    location_alignment: dict = field(default_factory=dict)
    relevant_projects: list[dict] = field(default_factory=list)


def calculate_match(
    candidate: CandidateSnapshot,
    job: JobSnapshot,
    semantic_override: float | None = None,
) -> MatchResult:
    """Compute a full match from candidate and job snapshots.

    Deterministic except for the optional semantic score, which is cached and
    can be overridden for reuse. The overall score is always computed here.
    """
    analysis = job.analysis or JobAnalysisSnapshot()

    skill_result = match_skills(candidate.skills, analysis.required_skills, analysis.preferred_skills)
    role_result = match_role(candidate.target_roles, job.title)
    experience_result = match_experience(candidate.years_of_experience, job.experience_min, job.experience_max)
    education_result = match_education(analysis.education_requirements, [_education_dict(e) for e in candidate.education])
    project_result = match_projects(
        [_project_dict(p) for p in candidate.projects],
        analysis.required_skills + analysis.preferred_skills + analysis.tools_and_technologies,
        " ".join(analysis.responsibilities + analysis.qualifications),
    )
    location_result = match_location(job.location, job.work_mode, candidate.location)

    candidate_text = build_candidate_text(
        candidate.target_roles,
        candidate.skills,
        candidate.professional_summary,
        [e.description or "" for e in candidate.experience],
        [f"{p.project_name} {p.description or ''}" for p in candidate.projects],
    )
    job_text = build_job_text(
        job.title,
        analysis.summary,
        analysis.required_skills,
        analysis.preferred_skills,
        analysis.responsibilities,
        analysis.qualifications,
        job.description,
    )
    semantic_result: SemanticMatchResult = match_semantic(candidate_text, job_text, override_score=semantic_override)

    components = {
        "skills": skill_result,
        "role": role_result,
        "experience": experience_result,
        "projects": project_result,
        "education": education_result,
        "location": location_result,
        "semantic": semantic_result,
    }

    weights = normalized_weights()
    total_weight = 0.0
    weighted_sum = 0.0
    scores: dict[str, float | None] = {}
    for name, result in components.items():
        if not getattr(result, "applicable", False):
            scores[name] = None
            continue
        weight = weights.get(name, 0.0)
        total_weight += weight
        weighted_sum += result.score * weight
        scores[name] = result.score

    overall = round(weighted_sum / total_weight, 1) if total_weight else 0.0
    category = category_for_score(overall)

    return MatchResult(
        overall_score=overall,
        category=category,
        match_version=MATCH_VERSION,
        scores={name: (round(value, 1) if value is not None else None) for name, value in scores.items()},
        matching_skills=skill_result.matching_skills,
        matching_preferred_skills=skill_result.matching_preferred_skills,
        related_required_matches=skill_result.related_required_matches,
        missing_required_skills=skill_result.missing_required_skills,
        role_alignment=role_result.alignment,
        experience_alignment=experience_result.alignment,
        education_alignment=education_result.alignment,
        project_alignment=project_result.alignment,
        location_alignment=location_result.alignment,
        relevant_projects=project_result.relevant_projects,
    )


def _education_dict(entry: EducationSnapshot) -> dict:
    return {"degree": entry.degree or "", "field_of_study": entry.field_of_study or ""}


def _project_dict(project: ProjectSnapshot) -> dict:
    return {
        "project_name": project.project_name,
        "description": project.description,
        "technologies": list(project.technologies or []),
    }