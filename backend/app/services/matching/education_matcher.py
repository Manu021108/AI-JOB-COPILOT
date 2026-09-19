from __future__ import annotations

import re
from dataclasses import dataclass, field

_KEYWORD_LEVELS: dict[str, int] = {
    "phd": 5, "ph.d": 5, "doctorate": 5, "doctoral": 5,
    "master": 4, "masters": 4, "m.tech": 4, "mtech": 4, "msc": 4, "m.sc": 4,
    "ms in": 4, "mba": 4, "m.e.": 4, "m.e": 4,
    "bachelor": 3, "bachelors": 3, "b.tech": 3, "btech": 3, "b.e.": 3, "b.e": 3,
    "bsc": 3, "b.sc": 3, "bs in": 3, "undergraduate": 3,
    "diploma": 2, "associate": 2, "a.a.s.": 2,
    "high school": 1, "higher secondary": 1, "12th": 1, "secondary": 1,
}

_LEVEL_LABELS = {5: "Doctorate", 4: "Master's", 3: "Bachelor's", 2: "Diploma/Associate", 1: "High school"}

_CS_FIELDS = {
    "computer science", "computer science and engineering", "computer engineering",
    "cse", "software engineering", "information technology", "information science",
    "computer applications", "computers", "data science", "artificial intelligence",
    "machine learning", "electronics and communication", "ece", "it",
}

_TOKEN_RE = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class EducationMatchResult:
    score: float
    applicable: bool
    alignment: dict = field(default_factory=dict)


def _level(text: str) -> int | None:
    lowered = (text or "").lower()
    best: int | None = None
    for keyword, level in _KEYWORD_LEVELS.items():
        if keyword in lowered:
            best = level if best is None else max(best, level)
    return best


def _wants_cs(requirements: list[str]) -> bool:
    for requirement in requirements:
        lowered = (requirement or "").lower()
        if any(field in lowered for field in _CS_FIELDS):
            return True
        if "bachelor" in lowered or "master" in lowered or "degree" in lowered:
            if "related field" in lowered:
                return True
    return False


def _candidate_profile(entries: list[dict]) -> tuple[int | None, bool]:
    """Highest degree level present and whether any CS-related field appears."""
    max_level: int | None = None
    cs = False
    for entry in entries or []:
        degree = (entry.get("degree") or "") + " " + (entry.get("field_of_study") or "")
        level = _level(degree)
        if level is not None:
            max_level = level if max_level is None else max(max_level, level)
        field_text = ((entry.get("field_of_study") or "") + " " + (entry.get("degree") or "")).lower()
        if any(f in field_text for f in _CS_FIELDS):
            cs = True
    return max_level, cs


def match_education(requirements: list[str], candidate_entries: list[dict]) -> EducationMatchResult:
    requirements = [r for r in (requirements or []) if r]
    if not requirements:
        return EducationMatchResult(score=0.0, applicable=False, alignment={"status": "neutral", "reason": "The job does not list an education requirement."})

    required_level: int | None = None
    for requirement in requirements:
        level = _level(requirement)
        if level is not None and (required_level is None or level > required_level):
            required_level = level
    job_wants_cs = _wants_cs(requirements)

    cand_level, cand_cs = _candidate_profile(candidate_entries)

    if cand_level is None:
        if not candidate_entries:
            alignment = {"status": "unknown", "reason": "No education identified in the candidate profile.", "required": f"{_LEVEL_LABELS.get(required_level, 'degree')}"}
            return EducationMatchResult(score=50.0, applicable=True, alignment=alignment)
        alignment = {"status": "unknown", "reason": "Education present, but a degree level could not be determined.", "required": f"{_LEVEL_LABELS.get(required_level, '')}"}
        return EducationMatchResult(score=50.0, applicable=True, alignment=alignment)

    if required_level is not None:
        if cand_level < required_level:
            score = max(10.0, round(cand_level / required_level * 100.0, 1))
        elif cand_level == required_level:
            score = 90.0
        else:
            score = 85.0
    elif job_wants_cs:
        score = 90.0 if cand_cs else 70.0
    else:
        score = 75.0

    if job_wants_cs and not cand_cs:
        score = max(5.0, score - 20.0)

    required_label = _LEVEL_LABELS.get(required_level, "")
    cand_label = _LEVEL_LABELS.get(cand_level, "")
    status = "aligned" if score >= 70 else "below_required"
    reason = f"Candidate education: {cand_label}{' (CS)' if cand_cs else ''}; job requires {required_label or 'a degree'}{' in a related field' if job_wants_cs else ''}."
    return EducationMatchResult(
        score=round(score, 1),
        applicable=True,
        alignment={"status": status, "reason": reason, "required": required_label or None, "candidate_degree_level": cand_label},
    )