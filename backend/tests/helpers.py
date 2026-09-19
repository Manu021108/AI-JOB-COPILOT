from pathlib import Path
import fitz
from docx import Document

SAMPLE_RESUME = """Alice Johnson
alice.johnson@example.com | +1 555-123-4567
San Francisco, CA
linkedin.com/in/alicejohnson | https://github.com/alicejohnson

Summary: Backend engineer with 5 years of experience building scalable APIs.

Skills
Python, FastAPI, PostgreSQL, Docker, Machine Learning, React, Git

Experience
Senior Python Developer, Acme Corp
Jan 2021 - Present
- Built REST APIs serving 2M requests/day.
- Reduced average API latency by 40%.

Backend Engineer
Beta Labs | 2018 - 2020
- Maintained Django applications and PostgreSQL databases.

Projects
AI Placement Assistant
Built an LLM RAG pipeline to match candidates.
Technologies: Python, FastAPI, LLM, RAG

Education
M.Tech Computer Science, IIT Delhi
2016-2018
GPA: 8.5

Certifications
AWS Certified Solutions Architect - Amazon
"""


def make_pdf_resume(destination: str | Path, text: str = SAMPLE_RESUME) -> Path:
    dest = Path(destination)
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_textbox(fitz.Rect(72, 72, 523, 770), text, fontsize=10, fontname="helv")
    doc.save(dest)
    doc.close()
    return dest


def make_blank_pdf(destination: str | Path) -> Path:
    dest = Path(destination)
    doc = fitz.open()
    doc.new_page(width=595, height=842)
    doc.save(dest)
    doc.close()
    return dest


def make_docx_resume(destination: str | Path, text: str = SAMPLE_RESUME) -> Path:
    dest = Path(destination)
    document = Document()
    for line in text.splitlines():
        document.add_paragraph(line)
    document.save(dest)
    return dest


def register_user(client, email: str, name: str = "Test User") -> str:
    response = client.post(
        "/api/auth/register",
        json={"name": name, "email": email, "password": "password123"},
    )
    assert response.status_code == 201, response.text
    login = client.post("/api/auth/login", json={"email": email, "password": "password123"})
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def upload_pdf(client, token: str, path: Path) -> dict:
    response = client.post(
        "/api/resumes/upload",
        headers=auth_headers(token),
        files={"file": (path.name, path.read_bytes(), "application/pdf")},
    )
    return response


def upload_docx(client, token: str, path: Path) -> dict:
    response = client.post(
        "/api/resumes/upload",
        headers=auth_headers(token),
        files={"file": (path.name, path.read_bytes(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    return response