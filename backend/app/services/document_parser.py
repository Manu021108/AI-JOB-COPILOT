from pathlib import Path
import fitz
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph


class UnsupportedDocumentError(Exception):
    pass


class EmptyDocumentError(Exception):
    pass


class ScannedPdfError(Exception):
    pass


def extract_pdf_text(file_path: str | Path) -> str:
    try:
        doc = fitz.open(file_path)
    except Exception as exc:
        raise UnsupportedDocumentError("Could not open this PDF. The file may be damaged.") from exc

    if doc.page_count == 0:
        raise EmptyDocumentError("This PDF contains no pages.")

    pages: list[str] = []
    try:
        for page in doc:
            pages.append((page.get_text() or "").strip())
    finally:
        doc.close()

    text = "\n\n".join(page for page in pages if page)
    if len(text.strip()) < 20:
        raise ScannedPdfError(
            "This PDF appears to contain scanned images. Text extraction was unsuccessful. "
            "Image-only (scanned) PDFs are not supported yet."
        )
    return text


def extract_docx_text(file_path: str | Path) -> str:
    try:
        document = Document(file_path)
    except Exception as exc:
        raise UnsupportedDocumentError("Could not open this DOCX file. The file may be damaged.") from exc

    parts: list[str] = []
    for child in document.element.body.iterchildren():
        tag = child.tag.split("}")[-1]
        if tag == "p":
            paragraph = Paragraph(child, document)
            text = paragraph.text.strip()
            if text:
                parts.append(text)
        elif tag == "tbl":
            table = Table(child, document)
            rows: list[str] = []
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells]
                rows.append(" | ".join(c for c in cells if c))
            if rows:
                parts.append("\n".join(rows))

    text = "\n".join(parts)
    if not text.strip():
        raise EmptyDocumentError("This DOCX file contains no readable text.")
    return text