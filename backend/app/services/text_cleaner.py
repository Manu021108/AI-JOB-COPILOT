import re


def clean_text(text: str) -> str:
    """Normalize whitespace and extraction artifacts without rewriting content."""
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\x00", "")
    text = text.replace("\f", "\n")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    result: list[str] = []
    blank = 0
    for line in lines:
        if not line:
            blank += 1
            if blank <= 1:
                result.append("")
            continue
        blank = 0
        result.append(line)
    return "\n".join(result).strip()