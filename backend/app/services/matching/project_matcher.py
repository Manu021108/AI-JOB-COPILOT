from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.services.matching.config import PROJECT_MAX_SURFACED, PROJECT_MIN_RELEVANCE
from app.services.matching.skill_normalizer import normalize_skill

_KEYWORD_RE = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class ProjectMatchResult:
    score: float
    applicable: bool
    alignment: dict = field(default_factory=dict)
    relevant_projects: list[dict] = field(default_factory=list)


def _keyword_set(text: str) -> set[str]:
    return set(_KEYWORD_RE.findall((text or "").lower()))


def match_projects(projects: list[dict], job_skills: list[str], job_keywords: str) -> ProjectMatchResult:
    job_skill_set = {normalize_skill(s).lower() for s in job_skills if s}
    keyword_set = _keyword_set(job_keywords)

    if not projects:
        if job_skill_set or keyword_set:
            return ProjectMatchResult(
                score=30.0,
                applicable=True,
                alignment={"status": "no_projects", "reason": "No projects identified in the candidate profile."},
            )
        return ProjectMatchResult(score=0.0, applicable=False, alignment={"status": "neutral", "reason": "No project or job requirement data to compare."})

    scored: list[tuple[str, float, str]] = []
    for project in projects:
        name = (project.get("project_name") or "").strip() or "Untitled project"
        description = project.get("description") or ""
        technologies = [normalize_skill(t) for t in (project.get("technologies") or [])]
        tech_set = {t.lower() for t in technologies if t}

        if job_skill_set and tech_set:
            hits = tech_set.intersection(job_skill_set)
            tech_ratio = len(hits) / len(tech_set)
            coverage = len(hits) / len(job_skill_set)
            score = (tech_ratio * 0.6 + coverage * 0.4) * 100.0
            reason = f"Uses matching technologies: {', '.join(sorted(hits)) or 'none'}."
        elif job_skill_set and not tech_set:
            score = 0.0
            reason = "The project does not list technologies."
        elif keyword_set and (description or name):
            project_tokens = _keyword_set(f"{name} {description}")
            if project_tokens:
                hits = project_tokens.intersection(keyword_set)
                score = min(70.0, len(hits) / max(len(keyword_set), 1) * 100.0)
                reason = "Description matches keywords from the job."
            else:
                score = 0.0
                reason = "No keyword overlap with the job."
        else:
            score = 30.0
            reason = "The project could not be compared with the job requirements."
        scored.append((name, round(max(0.0, min(100.0, score)), 1), reason))

    best_score = max((s for _, s, _ in scored), default=0.0)
    relevant = [
        {"project": name, "reason": reason, "score": s}
        for name, s, reason in sorted(scored, key=lambda item: item[1], reverse=True)
        if s >= PROJECT_MIN_RELEVANCE
    ][:PROJECT_MAX_SURFACED]

    best_project = max(scored, key=lambda item: item[1])
    status = "aligned" if best_score >= PROJECT_MIN_RELEVANCE else "limited"
    return ProjectMatchResult(
        score=best_score,
        applicable=True,
        alignment={
            "status": status,
            "reason": f"{len(scored)} project(s) considered; best was “{best_project[0]}”.",
            "relevant_count": len(relevant),
        },
        relevant_projects=relevant,
    )