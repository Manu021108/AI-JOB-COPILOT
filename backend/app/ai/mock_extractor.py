import json
import re

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"\+?\(?\d{2,4}\)?[\s.\-]?\d{3,4}[\s.\-]?\d{3,4}")
URL_RE = re.compile(r"https?://\S+")
BARE_LINKEDIN_RE = re.compile(r"(?:https?://)?(?:www\.)?linkedin\.com/in/[\w%.-]+")
BARE_GITHUB_RE = re.compile(r"(?:https?://)?(?:www\.)?github\.com/[\w.-]+")
DATE_RANGE_RE = re.compile(
    r"(?P<start>(?:[A-Za-z]{3,9}\.? ?)?\d{4})\s*[-–—to\s]+\s*(?P<end>present|now|(?:[A-Za-z]{3,9}\.? ?)?\d{4})",
    re.IGNORECASE,
)
SINGLE_DATE_RE = re.compile(r"^((?:[A-Za-z]{3,9}\.?\s?)?\d{4})$", re.IGNORECASE)

SECTION_HEADERS = {
    "skills": ["skills", "technical skills", "skills & competencies", "skill highlights", "core competencies", "technologies"],
    "experience": ["experience", "work experience", "professional experience", "employment history", "career history"],
    "projects": ["projects", "project experience", "key projects", "major projects", "notable projects"],
    "education": ["education", "academic background", "academic qualifications"],
    "certifications": ["certifications", "certificates", "licenses", "certifications & licenses"],
    "summary": ["professional summary", "summary", "objective", "career objective", "profile", "about me", "about"],
    "roles": ["target role", "target roles", "desired role", "open to"],
}

_CONTACT_WORDS = {"email", "phone", "mobile", "linkedin", "github", "location", "address", "portfolio", "website", "www"}


def extract_from_text(text: str) -> str:
    sections = _split_sections(text)
    lines = sections["_top"]
    full_text = "\n".join(line for section_lines in sections.values() for line in section_lines).strip()
    raw = "\n".join(lines).strip()

    emails = _dedupe(EMAIL_RE.findall(full_text))
    phones = _dedupe(re.sub(r"[^\d()+\-\s.]", "", m) for m in PHONE_RE.findall(full_text))
    all_urls = [*URL_RE.findall(full_text), *BARE_LINKEDIN_RE.findall(full_text), *BARE_GITHUB_RE.findall(full_text)]
    urls = _dedupe(all_urls)
    linkedin = _find_url(urls, "linkedin.com")
    github = _find_url(urls, "github.com")
    portfolio = _find_url(urls, ("portfolio", "bitbucket", "gitlab", "dev.to")) or (
        (urls[0] if urls and not linkedin and not github else None)
    )

    data = {
        "full_name": _guess_name(lines),
        "email": emails[0] if emails else None,
        "phone": phones[0] if phones else None,
        "location": _guess_location(lines),
        "linkedin_url": linkedin,
        "github_url": github,
        "portfolio_url": portfolio,
        "professional_summary": "\n".join(sections["summary"]).strip() or None,
        "target_roles": _guess_roles(sections["roles"], lines),
        "years_of_experience": _guess_years(full_text),
        "skills": _guess_skills(sections["skills"]),
        "experience": _guess_experience(sections["experience"]),
        "projects": _guess_projects(sections["projects"]),
        "education": _guess_education(sections["education"]),
        "certifications": _guess_certifications(sections["certifications"]),
    }
    return json.dumps(data)


def _split_sections(text: str) -> dict[str, list[str]]:
    header_re = re.compile(
        r"^\s*(?:==+\s*)?(?P<h>[A-Za-z &/.,-]{3,40})\s*(?:==+)?\s*:?\s*$"
    )
    inline_header_re = re.compile(r"^\s*(?P<h>[A-Za-z &/.,-]{3,40})\s*[:-]\s*(?P<rest>.+)$")
    sections: dict[str, list[str]] = {k: [] for k in SECTION_HEADERS}
    sections["_top"] = []
    current = "_top"
    for raw_line in text.splitlines():
        line = raw_line.strip()
        m = header_re.match(line)
        matched = None
        if m:
            header_text = (m.group("h") or "").lower().strip().rstrip(":.")
            matched = _match_header(header_text)
            if matched:
                current = matched
                continue
        else:
            inline = inline_header_re.match(line)
            if inline:
                header_text = (inline.group("h") or "").lower().strip().rstrip(":.")
                matched = _match_header(header_text)
                if matched:
                    current = matched
                    rest = (inline.group("rest") or "").strip()
                    if rest:
                        sections[current].append(rest)
                    continue
        sections[current].append(line)
    return sections


def _match_header(header_text: str) -> str | None:
    for section, headers in SECTION_HEADERS.items():
        if header_text in headers:
            return section
    return None


def _guess_name(lines: list[str]) -> str | None:
    skip = _CONTACT_WORDS | {"curriculum", "vitae", "resume", "cv"}
    for line in lines:
        if not line or len(line) > 80:
            continue
        low = line.lower()
        if any(skip_word in low for skip_word in _CONTACT_WORDS):
            continue
        if EMAIL_RE.search(line) or URL_RE.search(line):
            continue
        if low.endswith("resume") or low.endswith("curriculum vitae"):
            continue
        tokens = line.split()
        if 1 <= len(tokens) <= 4:
            return " ".join(tokens[:4])
    return None


def _guess_location(lines: list[str]) -> str | None:
    for line in lines:
        low = line.lower()
        if low.startswith("location:") or low.startswith("address:"):
            return line.split(":", 1)[1].strip()
    city_state = re.compile(r"^[A-Za-z][A-Za-z .'-]+,?\s+[A-Z]{2,3}(?:\s+\d{5})?$")
    for line in lines:
        if city_state.match(line.strip()) and " " in line.strip():
            return line.strip()
    return None


def _guess_roles(role_lines: list[str], lines: list[str]) -> list[str]:
    candidates: list[str] = []
    for line in [*role_lines, *lines]:
        low = line.lower()
        if ":" not in line:
            continue
        if any(k in low for k in ("target role", "desired role", "open to")):
            value = line.split(":", 1)[1].strip()
            if value:
                candidates.append(value)
    flattened: list[str] = []
    for value in candidates:
        for part in re.split(r"[,;/|]+", value):
            part = part.strip()
            if part and not EMAIL_RE.search(part) and not URL_RE.search(part):
                flattened.append(part)
    return _dedupe(flattened)[:3]


def _guess_years(raw: str) -> float | None:
    for match in re.finditer(r"(\d+(?:\.\d+)?)\s*(?:\+)?\s*years?", raw, re.IGNORECASE):
        return float(match.group(1))
    return None


def _guess_skills(skill_lines: list[str]) -> list[str]:
    skills: list[str] = []
    for line in skill_lines:
        line = re.sub(r"[•▪●◦‣–—・·|]", " | ", line)
        parts = re.split(r"[|,;/]+", line)
        for part in parts:
            part = part.strip().strip(":").strip()
            if not part:
                continue
            if len(part) > 60 or EMAIL_RE.search(part) or URL_RE.search(part):
                continue
            if re.search(r"\d{4}", part):
                continue
            if part.lower() in ("skills", "technical skills", "technologies"):
                continue
            skills.append(part)
    return _dedupe(skills)


def _guess_experience(exp_lines: list[str]) -> list[dict]:
    blocks = _split_blocks(exp_lines)
    entries: list[dict] = []
    for block in blocks:
        if not block:
            continue
        title = block[0]
        patch = _patch_experience_block(block)
        company = _guess_experience_company(block)
        if company is None:
            comma = re.match(r"^(.*?)\s*,\s*([A-Z][A-Za-z .&'-]+)$", title)
            if comma and title.count(",") <= 1:
                company = comma.group(2).strip()
                title = comma.group(1).strip()
        entries.append({
            "job_title": title,
            "company": company,
            "location": patch.get("location"),
            "employment_type": None,
            "start_date": patch.get("start_date"),
            "end_date": patch.get("end_date"),
            "is_current": patch.get("is_current", False),
            "description": _join_brief(patch.get("description_lines", [])),
        })
    return entries


def _patch_experience_block(block: list[str]) -> dict:
    start, end, is_current = _date_range(block)
    description_started = False
    location = None
    description_lines: list[str] = []
    for line in block[1:]:
        if DATE_RANGE_RE.search(line):
            if "|" in line and " " in line and not location:
                possible_location = line.split("|")[-1].strip()
                if not DATE_RANGE_RE.search(possible_location):
                    location = possible_location
            continue
        if _looks_like_bullet(line):
            description_started = True
            description_lines.append(re.sub(r"^[\s\-•▪●◦‣–—·]+", "", line).strip())
            continue
        if description_started or _looks_like_description(line):
            description_lines.append(line)
    return {"start_date": start, "end_date": end, "is_current": is_current, "location": location, "description_lines": description_lines}


def _guess_experience_company(block: list[str]) -> str | None:
    for line in block[1:]:
        pipe = re.match(r"^(.+?)\s*[|]\s*(.+)$", line)
        if pipe:
            left, right = pipe.group(1).strip(), pipe.group(2).strip()
            if DATE_RANGE_RE.search(right):
                return left[:80]
            if not DATE_RANGE_RE.search(left) and len(left) <= 60 and not _looks_like_description(left):
                return left[:80]
        if _looks_like_bullet(line):
            continue
        if DATE_RANGE_RE.search(line):
            continue
        comma = re.match(r"^(.*?)\s*,\s*([A-Z][A-Za-z .&'-]+)$", line)
        if comma:
            left = comma.group(1).strip()
            return left[:80]
        if len(line) <= 60 and not SINGLE_DATE_RE.match(line) and not _looks_like_description(line):
            return line.strip()[:80]
    return None


def _looks_like_bullet(line: str) -> bool:
    return bool(re.match(r"^\s*[-•▪●◦‣–—·›>]+\s+", line)) or (line.startswith("- ") and len(line) > 20)


def _looks_like_description(line: str) -> bool:
    return len(line) > 60 or any(line.lower().startswith(word) for word in ("responsible", "built", "developed", "led", "managed", "designed", "created", "improved", "implemented", "maintained", "collaborated"))


def _guess_projects(proj_lines: list[str]) -> list[dict]:
    blocks = _split_blocks(proj_lines)
    projects: list[dict] = []
    for block in blocks:
        if not block:
            continue
        name_line, rest = block[0], block[1:]
        start, end, _is_current = _date_range(block)
        technologies: list[str] = []
        remaining: list[str] = []
        for line in rest:
            if line.lower().startswith("technolog"):
                technologies = [t.strip() for t in re.split(r"[,;/|•]", line.split(":", 1)[1]) if t.strip()]
            else:
                remaining.append(line)
        projects.append({
            "project_name": name_line,
            "description": _join_brief(remaining),
            "technologies": technologies,
            "project_url": _first_url(rest),
            "start_date": start,
            "end_date": end,
        })
    return projects


def _guess_education(edu_lines: list[str]) -> list[dict]:
    blocks = _split_blocks(edu_lines)
    educations: list[dict] = []
    for block in blocks:
        if not block:
            continue
        start, end, _is_current = _date_range(block)
        degree = None
        institution = block[0]
        grade = None
        for line in block[0:]:
            low = line.lower()
            if any(k in low for k in ("gpa", "grade", "cgpa")):
                grade = line.split(":", 1)[1].strip() if ":" in line else line
        comma = re.match(r"^(.*?)\s*,\s*([A-Z][A-Za-z .&'-]+)$", block[0])
        if comma:
            degree, institution = comma.group(1).strip(), comma.group(2).strip()
        elif len(block) > 1:
            degree = block[1].strip() if _looks_like_degree(block[1]) else None
            if degree and len(block) > 2 and not _looks_like_degree(block[2]):
                institution = block[2]
        educations.append({
            "institution": institution,
            "degree": degree,
            "field_of_study": None,
            "start_date": start,
            "end_date": end,
            "grade": grade,
        })
    return educations


def _guess_certifications(cert_lines: list[str]) -> list[dict]:
    certs: list[dict] = []
    for line in cert_lines:
        if not line or EMAIL_RE.search(line) or URL_RE.search(line) and not line.lower().startswith(("www", "http")):
            if not line:
                continue
        name = line.split(" - ")[0].split(" – ")[0].split(":")[0].strip()
        org = None
        for sep in (" - ", " – ", " | ", ", "):
            if sep in line:
                org = line.split(sep, 1)[1].strip()
                break
        certs.append({
            "name": name,
            "issuing_organization": org,
            "issue_date": None,
            "expiration_date": None,
            "credential_url": _first_url([line]),
        })
    return certs


def _split_blocks(lines: list[str]) -> list[list[str]]:
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        if not line:
            if current:
                blocks.append(current)
                current = []
            continue
        current.append(line)
    if current:
        blocks.append(current)
    return [b for b in blocks if b]


def _date_range(lines: list[str]) -> tuple[str | None, str | None, bool]:
    for line in lines:
        m = DATE_RANGE_RE.search(line)
        if m:
            end = (m.group("end") or "").lower()
            if end in ("present", "now"):
                return m.group("start"), None, True
            return m.group("start"), m.group("end"), False
    return None, None, False


def _join_brief(lines: list[str], limit: int = 4) -> str | None:
    kept = [l.rstrip(" .,-") for l in lines if l]
    if not kept:
        return None
    return "\n".join(kept[:limit])


def _find_url(urls: list[str], needle: str | tuple[str, ...]) -> str | None:
    for url in urls:
        low = url.lower()
        if isinstance(needle, tuple):
            if any(n in low for n in needle):
                return url
        elif needle in low:
            return url
    return None


def _first_url(lines: list[str]) -> str | None:
    for line in lines:
        m = URL_RE.search(line)
        if m:
            return m.group(0)
    return None


def _looks_like_degree(line: str) -> bool:
    return any(k in line.lower() for k in ("b.sc", "b.tech", "b.e", "m.sc", "m.tech", "ph.d", "mba", "bachelor", "master", "diploma", "b.a", "m.a", "high school"))


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        key = item.strip().lower()
        if item and key not in seen:
            seen.add(key)
            result.append(item.strip())
    return result