"""Extract readable text from an HTML job page.

Simple, best-effort extraction: remove non-content elements (scripts, styles,
navigation, footer, ads, forms) and return the remaining text. This is not a
crawler - job pages are parsed on demand for a single URL import.
"""
from bs4 import BeautifulSoup

_IGNORE_TAGS = ["script", "style", "noscript", "iframe", "svg", "canvas", "template", "form", "button", "title", "meta"]
_REMOVE_SECTIONS = ["nav", "footer", "header", "aside"]


def extract_text_from_html(html: bytes | str) -> str:
    if isinstance(html, bytes):
        html = html.decode("utf-8", errors="replace")
    soup = BeautifulSoup(html, "html.parser")

    for tag_name in _IGNORE_TAGS:
        for tag in soup.find_all(tag_name):
            tag.decompose()
    for section in _REMOVE_SECTIONS:
        for tag in soup.find_all(section):
            tag.decompose()

    for tag in soup.find_all(True):
        if _is_hidden(tag):
            tag.decompose()

    text = soup.get_text("\n")
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _is_hidden(tag) -> bool:
    style = (tag.get("style") or "").lower().replace(" ", "")
    hidden = tag.get("hidden") is not None
    if hidden:
        return True
    return "display:none" in style or "visibility:hidden" in style