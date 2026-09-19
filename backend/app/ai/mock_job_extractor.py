"""Deterministic, offline job-description extraction.

Heuristic parser that mirrors the structure of a typical job posting. Used by
the mock LLM provider so development and tests work without API keys. Like the
real analyzer it only extracts what is present in the text - it never invents
facts or follows instructions embedded in the description.
"""
import json
import re

from app.services.job_normalizer import (
    infer_employment_type,
    infer_experience_range,
    infer_salary,
    infer_work_mode,
    normalize_employment_type,
    normalize_text,
    normalize_work_mode,
    parse_posted_date,
)
from app.services.skill_categorizer import SKILL_CATEGORIES, categorize_skill

_INLINE_FIELDS = {
    "title": [r"^(?:job title|position|title|role)\s*[:：]\s*(.+)$"],
    "company": [r"^(?:company|organization|employer|department)\s*[:：]\s*(.+)$"],
    "location": [r"^(?:location|work location|job location|office location)\s*[:：]\s*(.+)$"],
    "application_url": [r"^(?:application url|apply at|apply here|apply link)\s*[:：]\s*(.+)$"],
    "salary_line": [r"^(?:salary|pay|compensation|annual (?:salary|pay)|ctc)\s*[:：]\s*(.+)$"],
    "posted_line": [r"^(?:posted|date posted|posted on)\s*[:：]?\s*(.+)$"],
}

_SECTIONS = {
    "responsibilities": ["responsibilities", "key responsibilities", "duties", "what you'll do", "what you will do", "what you'll be doing", "your day-to-day", "the role", "about the role", "in this role", "your responsibilities"],
    "required": ["requirements", "required skills", "what you need", "what you'll need", "you will need", "you'll need", "must have", "minimum qualifications", "qualifications", "what we're looking for", "what we are looking for", "your background", "about you", "who you are", "ideal candidate", "we are looking for", "job requirements"],
    "preferred": ["preferred", "preferred qualifications", "great to have"],
    "nice": ["nice to have", "nice-to-have", "good to have", "bonus points", "bonus", "plus points"],
    "tools": ["tech stack", "technologies", "tools", "technology stack"],
    "education": ["education", "educational requirements", "educational qualification", "degree"],
    "benefits": ["benefits", "compensation & benefits", "compensation and benefits", "what we offer", "perks"],
    "about": ["about the role", "about this position", "team intro"],
}

_DEGREE_WORDS = [
    "bachelor", "bachelors", "be in", "b.tech", "btech", "b.e.", "master", "masters", "m.tech", "mtech",
    "mba", "phd", "ph.d", "degree", "bsc", "b.sc", "msc", "m.sc", "undergraduate", "graduate degree",
]

_HEADER_RE = re.compile(r"^(?:[-*•\d.)#]+\s*)?(.+?)\s*:?\s*$")
_BULLET_PREFIX_RE = re.compile(r"^(?:[-*•·#]+\s*|\d+[.)]\s*)")
_EDUCATION_RE = re.compile(r"\b(" + "|".join(_DEGREE_WORDS) + r")\b", re.IGNORECASE)

_SKILL_TOKENS: list[str] = []
for _name in sorted({s for skills in SKILL_CATEGORIES.values() for s in skills}, key=len, reverse=True):
    _SKILL_TOKENS.append(re.escape(_name))
_SKILL_RE = re.compile(r"\b(" + "|".join(_SKILL_TOKENS) + r")\b", re.IGNORECASE)
_CANONICAL_BY_LOWER: dict[str, str] = {}
for _category, _skills in SKILL_CATEGORIES.items():
    for _skill in _skills:
        _CANONICAL_BY_LOWER.setdefault(_skill.lower(), _skill)


def extract_from_text(job_text: str) -> str:
    data = extract_job(job_text)
    return json.dumps(data)


def extract_job(job_text: str) -> dict:
    lines = [normalize_text(line) for line in (job_text or "").splitlines() if line.strip()]
    if not lines:
        return _empty()

    inline = {}
    remaining: list[str] = []
    for line in lines:
        consumed = False
        for field, patterns in _INLINE_FIELDS.items():
            for pattern in patterns:
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    inline[field] = match.group(1).strip()
                    consumed = True
                    break
            if consumed:
                break
        if not consumed:
            remaining.append(line)

    title = inline.get("title") or _guess_title(remaining)
    company, location = _guess_meta(remaining, title)
    company = inline.get("company") or company
    location = inline.get("location") or location
    application_url = inline.get("application_url")
    if not application_url:
        application_url = _find_application_url(remaining)

    whole = " ".join(remaining)
    salary_min, salary_max, salary_currency = _salary(inline.get("salary_line"), whole)
    employment_type = normalize_employment_type(inline.get("employment_type") or infer_employment_type(whole))
    work_mode = normalize_work_mode(inline.get("work_mode") or infer_work_mode(whole))
    experience_min, experience_max = infer_experience_range(whole)
    posted_line = inline.get("posted_line") or whole
    posted_at = parse_posted_date(posted_line)

    sections = _split_sections(remaining)
    required_text = _section_text(sections, "required")
    preferred_text = _section_text(sections, "preferred")
    nice_text = _section_text(sections, "nice")
    tools_text = _section_text(sections, "tools")

    required_skills = _dedupe(_find_skills(required_text))[:40]
    preferred_skills = _dedupe([s for s in _find_skills(preferred_text) if s.lower() not in {x.lower() for x in required_skills}])[:30]
    nice_have = _dedupe([s for s in _find_skills(nice_text) if s.lower() not in {x.lower() for x in required_skills + preferred_skills}])[:30]

    tools = _dedupe(_find_skills(tools_text) + _find_skills(whole))
    tools = [t for t in tools if categorize_skill(t) != "Other"][:40]

    responsibilities = _bullets(sections.get("responsibilities", []), max_items=25)
    qual_lines = sections.get("required", []) + sections.get("qualifications", [])
    qualifications = [b for b in _bullets(qual_lines, max_items=15) if not _is_skill_only_line(b, required_skills)]
    education_requirements = _find_degree_lines(whole, qual_lines)
    experience_requirements = [l for l in _bullets(qual_lines, max_items=8) if "year" in l.lower()]
    employment_details = " ".join(sections.get("benefits", [])).strip() or None

    summary = _summary(remaining, sections.get("about", []))

    data = _empty()
    data["title"] = title
    data["company"] = company
    data["location"] = location
    data["summary"] = summary
    data["required_skills"] = required_skills
    data["preferred_skills"] = preferred_skills
    data["responsibilities"] = responsibilities
    data["qualifications"] = qualifications
    data["education_requirements"] = education_requirements
    data["experience_requirements"] = experience_requirements
    data["tools_and_technologies"] = tools
    data["nice_to_have"] = nice_have
    data["employment_details"] = employment_details
    data["employment_type"] = employment_type
    data["work_mode"] = work_mode
    data["experience_min"] = experience_min
    data["experience_max"] = experience_max
    data["salary_min"] = salary_min
    data["salary_max"] = salary_max
    data["salary_currency"] = salary_currency
    data["posted_at"] = posted_at.isoformat() if posted_at else None
    data["application_url"] = application_url
    return data


def _empty() -> dict:
    return {
        "title": None, "company": None, "location": None, "summary": None,
        "required_skills": [], "preferred_skills": [], "responsibilities": [],
        "qualifications": [], "education_requirements": [],
        "experience_requirements": [], "tools_and_technologies": [],
        "nice_to_have": [], "employment_details": None,
        "employment_type": None, "work_mode": None,
        "experience_min": None, "experience_max": None,
        "salary_min": None, "salary_max": None, "salary_currency": None,
        "posted_at": None, "application_url": None,
    }


def _guess_title(lines: list[str]) -> str | None:
    for line in lines[:8]:
        if _is_boilerplate_line(line) or len(line) > 120:
            continue
        header = _header(line)
        if header and _resolve_section(header):
            continue
        if _BULLET_PREFIX_RE.match(line):
            continue
        return line[:120]
    return None


def _guess_meta(lines: list[str], title: str | None) -> tuple[str | None, str | None]:
    company = _guess_company(lines)
    location: str | None = None

    if title:
        title_index = next((i for i, line in enumerate(lines) if line == title), None)
        if title_index is not None:
            block: list[str] = []
            for line in lines[title_index + 1 : title_index + 6]:
                if _is_boilerplate_line(line) or len(line) > 60:
                    break
                if _header(line) and _resolve_section(_header(line)):
                    break
                if len(line.split()) > 12:
                    break
                block.append(line)
            for line in block:
                if company is None and _plausible_company(line):
                    company = line
                elif location is None and _plausible_location(line) and line != company:
                    location = line
                if company and location:
                    break

    if location is None:
        location = _guess_location(lines)
    return company, location


def _guess_company(lines: list[str]) -> str | None:
    for line in lines[:12]:
        match = re.match(r"^(?:at|@)\s*(.+)$", line, re.IGNORECASE)
        if match and len(match.group(1)) <= 120:
            return match.group(1).strip()
    for line in lines[:12]:
        if re.search(r"\bat\b|joins?\s+", line, re.IGNORECASE) and len(line) <= 160:
            match = re.search(r"\bat\s+([A-Z][A-Za-z0-9 .&\-]{2,80})$", line)
            if match:
                return match.group(1).strip()
    return None


def _guess_location(lines: list[str]) -> str | None:
    for line in lines[:12]:
        match = re.match(r"^(?:based in|located in|location|office in|in)\s*[:.-]?\s*(.+)$", line, re.IGNORECASE)
        if match and len(match.group(1)) <= 120:
            return match.group(1).strip()
    return None


_COMPANY_SUFFIXES = (
    "inc", "corp", "corporation", "company", "llc", "ltd", "limited", "labs", "lab",
    "group", "gmbh", "technologies", "technology", "systems", "solutions", "software",
    "services", "consulting", "consultancy", "studios", "analytics", "research",
)


def _plausible_company(line: str) -> bool:
    if not line or len(line) > 60 or line.endswith((".", ",", ";", ":")):
        return False
    if not line[0].isupper() or any(ch.isdigit() for ch in line):
        return False
    words = line.split()
    return len(words) > 1 or line.lower().endswith(_COMPANY_SUFFIXES)


def _plausible_location(line: str) -> bool:
    if not line or len(line) > 60 or line.endswith((".", ",", ";", ":")):
        return False
    if not line[0].isupper() or any(ch.isdigit() for ch in line):
        return False
    return True


def _find_application_url(lines: list[str]) -> str | None:
    for line in lines:
        match = re.match(r"^(?:apply|application|more info)\s*[:：]?\s*(https?://\S+)$", line, re.IGNORECASE)
        if match:
            return match.group(1)
        match = re.match(r"^(https?://\S+)$", line)
        if match and ("apply" in line.lower() or "career" in line.lower() or "job" in line.lower()):
            return match.group(1)
    return None


def _split_sections(lines: list[str]) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in lines:
        header = _header(line)
        section = _resolve_section(header) if header else None
        if section:
            current = section
            sections.setdefault(current, [])
            continue
        if current:
            sections[current].append(line)
        else:
            sections.setdefault("_preamble", []).append(line)
    return sections or {"_preamble": lines}


def _resolve_section(header: str) -> str | None:
    lowered = header.lower().strip()
    for name, keywords in _SECTIONS.items():
        for keyword in keywords:
            if lowered == keyword:
                return name
    if lowered == "qualifications":
        return "required"
    return None


def _header(line: str) -> str | None:
    match = _HEADER_RE.match(line)
    if not match:
        return None
    candidate = match.group(1).strip()
    if not candidate or len(candidate) > 50:
        return None
    return candidate


def _section_text(sections: dict, name: str) -> str:
    return "\n".join(sections.get(name, []))


def _bullets(lines: list[str], max_items: int) -> list[str]:
    result: list[str] = []
    for line in lines:
        clean = _strip_bullet(line)
        if not clean or _is_boilerplate_line(clean):
            continue
        if clean not in result:
            result.append(clean)
        if len(result) >= max_items:
            break
    return result


def _strip_bullet(line: str) -> str:
    return _BULLET_PREFIX_RE.sub("", line).strip()


def _is_skill_only_line(line: str, skills: list[str]) -> bool:
    stripped = _strip_bullet(line).strip()
    lowered = stripped.lower()
    if not stripped:
        return True
    if len(stripped) > 80:
        return False
    # Strip the skills and separators; if nothing meaningful remains, drop it.
    for skill in skills:
        lowered = lowered.replace(skill.lower(), " ")
    leftover = re.sub(r"[^a-z0-9 ]+", " ", lowered)
    words = [w for w in leftover.split() if len(w) > 1]
    return len(words) <= 1


def _find_degree_lines(whole: str, qual_lines: list[str]) -> list[str]:
    result: list[str] = []
    for line in qual_lines:
        clean = _strip_bullet(line).strip()
        if not clean:
            continue
        if _EDUCATION_RE.search(clean) and clean not in result:
            result.append(clean)
    if not result and _EDUCATION_RE.search(whole):
        sentences = re.split(r"(?<=[.!?])\s+|\n", whole)
        for sentence in sentences:
            if _EDUCATION_RE.search(sentence) and len(sentence) > 8:
                result.append(sentence.strip())
                break
    return result[:5]


def _find_skills(text: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    if not text:
        return found
    for match in _SKILL_RE.finditer(text):
        name = match.group(1)
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        found.append(_canonical(name))
    return found[:60]


def _canonical(name: str) -> str:
    from app.services.skill_categorizer import normalize_skill_name

    canonical = normalize_skill_name(name)
    return _CANONICAL_BY_LOWER.get(canonical.lower(), canonical)


def _dedupe(items: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        item = (item or "").strip()
        key = item.lower()
        if item and key not in seen:
            seen.add(key)
            result.append(item)
    return result


def _summary(lines: list[str], about_lines: list[str]) -> str | None:
    candidates = about_lines or lines
    prose: list[str] = []
    for line in candidates:
        if _is_boilerplate_line(line) or _header(line):
            continue
        clean = re.sub(r"^[-*•·\d.)#\s]+", "", line).strip()
        if len(clean.split()) >= 12 and clean not in prose:
            prose.append(clean)
        if len(prose) >= 2:
            break
    if not prose:
        for line in candidates[:12]:
            if len(line.split()) >= 14:
                prose.append(line)
                break
    return " ".join(prose)[:1000] if prose else None


def _salary(line: str | None, whole: str) -> tuple[int | None, int | None, str | None]:
    if not line or len(line) < 4:
        return _salary_from(whole)
    return _salary_from(line)


def _salary_from(text: str) -> tuple[int | None, int | None, str | None]:
    return infer_salary(text)


def _is_boilerplate_line(line: str) -> bool:
    from app.services.job_text_cleaner import _is_boilerplate

    return _is_boilerplate(line)