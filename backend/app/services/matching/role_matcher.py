from __future__ import annotations

import re
from dataclasses import dataclass, field

# Role alias groups: normalized role names that land in the same bucket are
# treated as related (85/100). Extend these groups carefully.
ROLE_GROUPS: list[list[str]] = [
    ["ai engineer", "ai/ml engineer", "ai ml engineer", "ml engineer", "machine learning engineer", "deep learning engineer", "generative ai engineer", "llm engineer"],
    ["data scientist", "data science", "ml scientist", "ai scientist"],
    ["data engineer", "data warehouse engineer", "etl engineer", "big data engineer"],
    ["data analyst", "business intelligence analyst", "bi analyst"],
    ["backend engineer", "backend developer", "software engineer backend", "python developer", "java developer", "go developer"],
    ["frontend engineer", "frontend developer", "ui developer", "react developer", "react engineer", "javascript developer"],
    ["full stack engineer", "full stack developer", "fullstack developer", "mern developer"],
    ["devops engineer", "site reliability engineer", "sre", "platform engineer", "automation engineer", "release engineer"],
    ["cloud engineer", "cloud architect", "aws engineer", "azure engineer", "gcp engineer", "solutions architect"],
    ["qa engineer", "quality assurance engineer", "sdet", "test engineer", "software test engineer"],
    ["security engineer", "cybersecurity engineer", "security analyst", "application security engineer"],
    ["mobile developer", "ios developer", "android developer", "react native developer", "flutter developer"],
    ["software engineer", "software developer", "programmer", "applications engineer"],
    ["product manager", "technical product manager", "product owner"],
    ["project manager", "technical program manager", "program manager"],
    ["engineering manager", "tech lead", "engineering lead", "engineering team lead"],
    ["solutions engineer", "sales engineer", "customer engineer", "presales engineer"],
]

_SENIORITY_WORDS = {
    "intern", "junior", "jr", "i", "ii", "iii", "iv", "v", "mid", "midlevel",
    "mid-level", "associate", "entry", "entrylevel", "entry-level", "senior",
    "sr", "sr.", "lead", "principal", "staff", "distinguished", "architect",
    "manager", "head", "director", "vp",
}

_STOP_WORDS = {
    "engineer", "engineers", "developer", "developers", "software",
    "engineering", "role", "position", "job", "jobs", "hiring", "open",
}

_TOKEN_RE = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class RoleMatchResult:
    score: float
    applicable: bool
    alignment: dict = field(default_factory=dict)


def _full_norm(value: str) -> str:
    text = re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()
    tokens = [t for t in text.split() if t not in _STOP_WORDS and t not in _SENIORITY_WORDS]
    return " ".join(tokens)


def _tokens(value: str) -> set[str]:
    text = re.sub(r"[^a-z0-9]+", " ", (value or "").lower())
    return {t for t in text.split() if t and t not in _STOP_WORDS and t not in _SENIORITY_WORDS}


def _group_variants() -> list[set[str]]:
    """Normalized member aliases per role group (same normalization as roles)."""
    return [{_full_norm(entry) for entry in group if _full_norm(entry)} for group in ROLE_GROUPS]


_GROUP_VARIANTS: list[set[str]] = _group_variants()


def _shared_groups(role_norm: str, title_norm: str) -> set[str]:
    """Indices of role groups that both the role and the title normalize into."""
    if not role_norm or not title_norm:
        return set()
    role_ids = {index for index, variants in enumerate(_GROUP_VARIANTS) if role_norm in variants}
    title_ids = {index for index, variants in enumerate(_GROUP_VARIANTS) if title_norm in variants}
    return role_ids.intersection(title_ids)


def match_role(target_roles: list[str], job_title: str | None) -> RoleMatchResult:
    job_title = (job_title or "").strip()
    target_roles = [r for r in (target_roles or []) if r]

    if not job_title or not target_roles:
        return RoleMatchResult(score=0.0, applicable=False, alignment={"weight": 0.0})

    title_tokens = _tokens(job_title)
    title_full = _full_norm(job_title)

    best_score = 0.0
    best_role: str | None = None
    best_reason = f"No target role found matching “{job_title}”."

    for role in target_roles:
        score, reason = _score_role(role, title_full, title_tokens)
        if score > best_score:
            best_score, best_role, best_reason = score, role, reason

    status = "aligned" if best_score >= 70 else ("partial" if best_score >= 40 else "mismatch")
    return RoleMatchResult(
        score=round(best_score, 1),
        applicable=True,
        alignment={
            "weight": 1.0,
            "status": status,
            "job_title": job_title,
            "target_role": best_role,
            "reason": best_reason,
        },
    )


def _score_role(role: str, title_full: str, title_tokens: set[str]) -> tuple[float, str]:
    role_full = _full_norm(role)
    role_tokens = _tokens(role)

    if role_full and role_full == title_full:
        return 100.0, f"Target role “{role}” matches the job title exactly."
    if role_full and title_full and _shared_groups(role_full, title_full):
        return 85.0, f"Target role “{role}” is closely related to the job title."

    shared = role_tokens.intersection(title_tokens)
    if shared:
        union = role_tokens.union(title_tokens) or {""}
        jaccard = len(shared) / len(union)
        score = 40.0 + jaccard * 40.0
        return score, f"Target role “{role}” shares keywords ({', '.join(sorted(shared))}) with the job."
    return 0.0, f"No target role found matching “{title_full}”."