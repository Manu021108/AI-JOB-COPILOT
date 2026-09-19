"""Normalization helpers for job records."""
import hashlib
import re
from datetime import date, datetime, timedelta

_EMPLOYMENT_TYPES = {
    "fulltime": "Full Time",
    "full-time": "Full Time",
    "full time": "Full Time",
    "ft": "Full Time",
    "permanent": "Full Time",
    "parttime": "Part Time",
    "part-time": "Part Time",
    "part time": "Part Time",
    "pt": "Part Time",
    "contract": "Contract",
    "contractor": "Contract",
    "fixed term": "Contract",
    "internship": "Internship",
    "intern": "Internship",
    "temporary": "Temporary",
    "temp": "Temporary",
}

_WORK_MODES = {
    "remote": "Remote",
    "fully remote": "Remote",
    "100% remote": "Remote",
    "work from home": "Remote",
    "wfh": "Remote",
    "hybrid": "Hybrid",
    "hybrid remote": "Hybrid",
    "on-site": "On-site",
    "on site": "On-site",
    "onsite": "On-site",
    "in office": "On-site",
    "in-office": "On-site",
    "from office": "On-site",
}

_EMPLOYMENT_TYPE_RE = re.compile(
    r"\b(full[- ]?time|part[- ]?time|contract|internship|intern|temporary|temp|permanent)\b",
    re.IGNORECASE,
)
_WORK_MODE_RE = re.compile(
    r"\b(remote|work from home|wfh|hybrid|on[- ]?site|in[- ]?office)\b",
    re.IGNORECASE,
)
_EXPERIENCE_RE = re.compile(r"(\d+)\s*(?:to|[-–])\s*(\d+)\s*(?:\+)?\s*years?", re.IGNORECASE)
_EXPERIENCE_PLUS_RE = re.compile(r"(\d+)\s*\+?\s*years?", re.IGNORECASE)


def normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = re.sub(r"\s+", " ", str(value)).strip()
    return cleaned or None


def normalize_employment_type(value: str | None) -> str | None:
    if value is None:
        return None
    key = re.sub(r"\s+", " ", value.strip().lower())
    if key in _EMPLOYMENT_TYPES:
        return _EMPLOYMENT_TYPES[key]
    return _title(value)


def normalize_work_mode(value: str | None) -> str | None:
    if value is None:
        return None
    key = re.sub(r"\s+", " ", value.strip().lower())
    if key in _WORK_MODES:
        return _WORK_MODES[key]
    return _title(value)


def infer_employment_type(text: str | None) -> str | None:
    if not text:
        return None
    match = _EMPLOYMENT_TYPE_RE.search(text)
    if not match:
        return None
    return normalize_employment_type(match.group(1))


def infer_work_mode(text: str | None) -> str | None:
    if not text:
        return None
    match = _WORK_MODE_RE.search(text)
    if not match:
        return None
    return normalize_work_mode(match.group(1))


def infer_experience_range(text: str | None) -> tuple[int | None, int | None]:
    if not text:
        return None, None
    match = _EXPERIENCE_RE.search(text)
    if match:
        return int(match.group(1)), int(match.group(2))
    plus = _EXPERIENCE_PLUS_RE.search(text)
    if plus:
        return int(plus.group(1)), None
    return None, None


def infer_salary(text: str | None) -> tuple[int | None, int | None, str | None]:
    """Best-effort salary parse. Returns (min, max, currency) or (None, None, None)."""
    if not text:
        return None, None, None
    currency = "USD"
    for code, glyph in (("USD", "$"), ("EUR", "€"), ("GBP", "£"), ("INR", "₹")):
        if glyph in text or code.lower() in text.lower():
            currency = code
            break
    pattern = re.compile(
        r"(\d[\d,]*(?:\.\d+)?[kKmM]?)\s*(?:-|–|to)\s*(?:[$€£₹])?\s*(\d[\d,]*(?:\.\d+)?[kKmM]?)",
        re.IGNORECASE,
    )
    match = pattern.search(text)
    if not match:
        return None, None, None
    return _salary_num(match.group(1)), _salary_num(match.group(2)), currency


def _salary_num(raw: str) -> int:
    value = raw.strip()
    multiplier = 1
    if value[-1:] in {"k", "K"}:
        multiplier = 1000
        value = value[:-1]
    elif value[-1:] in {"m", "M"}:
        multiplier = 1_000_000
        value = value[:-1]
    return int(float(value.replace(",", "")) * multiplier)


def make_job_key(title: str | None, company: str | None, location: str | None) -> str:
    parts = "|".join(
        (
            (normalize_text(company) or "").lower(),
            (normalize_text(title) or "").lower(),
            (normalize_text(location) or "").lower(),
        )
    )
    return hashlib.sha256(parts.encode("utf-8")).hexdigest()


_MONTHS = {"jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"}
_DATE_RE = re.compile(
    r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(\d{1,2})(?:st|nd|rd|th)?[,]?\s+(\d{4})\b",
    re.IGNORECASE,
)
_ISO_DATE_RE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_DAYS_AGO_RE = re.compile(r"\bposted\s+(\d{1,3})\s*(?:day|days)?\s*ago\b", re.IGNORECASE)


def parse_posted_date(text: str | None, today: date | None = None) -> date | None:
    if not text:
        return None
    today = today or date.today()
    match = _ISO_DATE_RE.search(text)
    if match:
        try:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            pass
    match = _DATE_RE.search(text)
    if match:
        month = list(_MONTHS).index(match.group(1).lower()[:3]) + 1
        try:
            return date(int(match.group(3)), month, int(match.group(2)))
        except ValueError:
            pass
    match = _DAYS_AGO_RE.search(text)
    if match:
        try:
            return today - timedelta(days=int(match.group(1)))
        except ValueError:
            pass
    return None


def _title(value: str) -> str:
    lowered = value.strip().lower()
    return lowered[:1].upper() + lowered[1:] if lowered else value.strip()