"""Normalize fetched job page text into a clean job description.

The goal is to remove extraction/navigation noise without rewriting the
semantic content of the job description itself.
"""
import re

BOILERPLATE_PATTERNS = [
    r"cookie",
    r"privacy policy",
    r"terms of s(ervice|use)",
    r"all rights reserved",
    r"©",
    r"rushrecurit",
    r"sign ?in",
    r"log ?in",
    r"subscribe",
    r"newsletter",
    r"follow us",
    r"share this",
    r"job alerts",
    r"create.*profile",
    r"upload.*resume",
    r"apply (now|here|online)",
    r"easy apply",
    r"recommended jobs",
    r"similar jobs",
    r"related jobs",
    r"^jobs? at ",
    r"^loading",
    r"^menu$",
]

_BOILERPLATE_RE = [re.compile(pattern, re.IGNORECASE) for pattern in BOILERPLATE_PATTERNS]


def clean_job_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\ufeff", "").replace("\u200b", "").replace("\xa0", " ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\x00", "")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    result: list[str] = []
    seen_previous = ""
    blank = 0
    for line in lines:
        if not line:
            blank += 1
            if blank <= 1:
                result.append("")
            continue
        blank = 0
        if _is_boilerplate(line):
            continue
        if line == seen_previous:
            continue
        seen_previous = line
        result.append(line)
    cleaned = "\n".join(result).strip()
    return re.sub(r"\n{3,}", "\n\n", cleaned)


def _is_boilerplate(line: str) -> bool:
    lowered = line.lower()
    if len(line) < 3:
        return False
    for pattern in _BOILERPLATE_RE:
        if pattern.search(lowered):
            return True
    return False