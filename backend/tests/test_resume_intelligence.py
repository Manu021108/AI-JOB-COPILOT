from pathlib import Path
from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app
from app.services.document_parser import extract_docx_text, extract_pdf_text, ScannedPdfError, UnsupportedDocumentError
from app.services.skill_categorizer import categorize_skill, categorize_skills
from tests.conftest import TESTS_DIR
from tests.helpers import auth_headers, make_blank_pdf, make_docx_resume, make_pdf_resume, register_user, upload_docx, upload_pdf

client = TestClient(app)
SAMPLE_DIR = Path(__file__).resolve().parent / ".samples"


def unique_email(prefix: str = "resume") -> str:
    return f"{prefix}-{uuid4()}@example.com"


def setup_module():
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)


def test_upload_valid_pdf_creates_resume_and_profile():
    email = unique_email()
    token = register_user(client, email)
    pdf = make_pdf_resume(SAMPLE_DIR / "sample_a.pdf")

    response = upload_pdf(client, token, pdf)
    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert data["file_type"] == "pdf"
    assert data["version"] == 1
    assert data["is_active"] is True
    assert data["status"] == "uploaded"
    assert data["profile_created"] is True
    resume_id = data["id"]

    listing = client.get("/api/resumes", headers=auth_headers(token))
    assert listing.status_code == 200
    assert len(listing.json()["data"]) == 1
    assert listing.json()["data"][0]["has_profile"] is True

    detail = client.get(f"/api/resumes/{resume_id}", headers=auth_headers(token))
    assert detail.status_code == 200
    assert detail.json()["data"]["filename"].endswith(".pdf")

    profile = client.get("/api/profile", headers=auth_headers(token))
    assert profile.status_code == 200
    body = profile.json()["data"]
    assert body["full_name"] == "Alice Johnson"
    assert body["email"] == "alice.johnson@example.com"
    assert body["years_of_experience"] == 5.0
    assert any(s["skill_name"] == "Python" for s in body["skills"])


def test_upload_valid_docx():
    email = unique_email("docx")
    token = register_user(client, email)
    docx = make_docx_resume(SAMPLE_DIR / "sample_a.docx")

    response = upload_docx(client, token, docx)
    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert data["file_type"] == "docx"
    assert data["version"] == 1

    profile = client.get("/api/profile", headers=auth_headers(token)).json()["data"]
    assert profile["full_name"] == "Alice Johnson"


def test_reject_unsupported_file():
    email = unique_email("unsupported")
    token = register_user(client, email)
    response = client.post(
        "/api/resumes/upload",
        headers=auth_headers(token),
        files={"file": ("malware.exe", b"MZ\x90\x00", "application/octet-stream")},
    )
    assert response.status_code == 400
    assert response.json()["detail"]["error"]["code"] == "INVALID_FILE_TYPE"


def test_reject_oversized_file():
    email = unique_email("oversize")
    token = register_user(client, email)
    big = b"0" * (11 * 1024 * 1024)
    response = client.post(
        "/api/resumes/upload",
        headers=auth_headers(token),
        files={"file": ("huge.pdf", big, "application/pdf")},
    )
    assert response.status_code == 413
    assert response.json()["detail"]["error"]["code"] == "FILE_TOO_LARGE"


def test_reject_empty_file():
    email = unique_email("emptyfile")
    token = register_user(client, email)
    response = client.post(
        "/api/resumes/upload",
        headers=auth_headers(token),
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )
    assert response.status_code == 400
    assert response.json()["detail"]["error"]["code"] == "EMPTY_FILE"


def test_reject_corrupted_pdf():
    email = unique_email("corrupt")
    token = register_user(client, email)
    response = client.post(
        "/api/resumes/upload",
        headers=auth_headers(token),
        files={"file": ("fake.pdf", b"This is not a real pdf at all" * 40, "application/pdf")},
    )
    assert response.status_code == 400
    assert response.json()["detail"]["error"]["code"] == "CORRUPTED_FILE"


def test_reject_scanned_pdf():
    email = unique_email("scanned")
    token = register_user(client, email)
    blank = make_blank_pdf(SAMPLE_DIR / "blank.pdf")
    response = upload_pdf(client, token, blank)
    assert response.status_code == 422
    assert response.json()["detail"]["error"]["code"] == "SCANNED_PDF"


def test_extract_pdf_text_unit():
    pdf = make_pdf_resume(SAMPLE_DIR / "extract.pdf")
    text = extract_pdf_text(pdf)
    assert "Alice Johnson" in text
    assert "5 years" in text
    assert "Pg" not in text


def test_extract_docx_text_unit():
    docx = make_docx_resume(SAMPLE_DIR / "extract.docx")
    text = extract_docx_text(docx)
    assert "Alice Johnson" in text
    assert "Acme Corp" in text


def test_document_parser_errors():
    try:
        extract_pdf_text(SAMPLE_DIR / "missing.pdf")
    except (ScannedPdfError, UnsupportedDocumentError):
        pass


def test_resume_versioning():
    email = unique_email("version")
    token = register_user(client, email)
    pdf = make_pdf_resume(SAMPLE_DIR / "a.pdf")
    docx = make_docx_resume(SAMPLE_DIR / "b.docx")

    assert upload_pdf(client, token, pdf).status_code == 201
    second = upload_docx(client, token, docx)
    assert second.status_code == 201
    assert second.json()["data"]["version"] == 2

    listing = client.get("/api/resumes", headers=auth_headers(token)).json()["data"]
    assert len(listing) == 2
    active = [item for item in listing if item["is_active"]]
    assert len(active) == 1
    assert active[0]["version"] == 2
    assert {item["version"] for item in listing} == {1, 2}


def test_profile_update_and_sections():
    email = unique_email("update")
    token = register_user(client, email)
    make_pdf_resume(SAMPLE_DIR / "c.pdf")
    response = upload_pdf(client, token, SAMPLE_DIR / "c.pdf")
    resume_id = response.json()["data"]["id"]

    profile = client.get("/api/profile", headers=auth_headers(token)).json()["data"]
    payload = {
        "full_name": profile["full_name"],
        "email": profile["email"],
        "phone": profile["phone"],
        "location": profile["location"],
        "target_roles": ["Python Developer", "AI/ML Engineer"],
        "skills": [{"skill_name": "Python", "skill_category": "Programming", "proficiency": "Advanced"}],
    }
    response = client.put("/api/profile", headers=auth_headers(token), json=payload)
    assert response.status_code == 200, response.text
    updated = response.json()["data"]
    assert updated["target_roles"] == ["Python Developer", "AI/ML Engineer"]
    assert len(updated["skills"]) == 1
    assert updated["skills"][0]["proficiency"] == "Advanced"
    assert updated["resume_id"] == resume_id

    skills = client.get("/api/profile/skills", headers=auth_headers(token)).json()["data"]
    assert len(skills) == 1 and skills[0]["skill_name"] == "Python"
    assert client.get("/api/profile/experience", headers=auth_headers(token)).status_code == 200
    assert client.get("/api/profile/projects", headers=auth_headers(token)).status_code == 200
    assert client.get("/api/profile/education", headers=auth_headers(token)).status_code == 200
    assert client.get("/api/profile/certifications", headers=auth_headers(token)).status_code == 200


def test_profile_completeness():
    email = unique_email("completeness")
    token = register_user(client, email)
    make_pdf_resume(SAMPLE_DIR / "d.pdf")
    upload_pdf(client, token, SAMPLE_DIR / "d.pdf")

    completeness = client.get("/api/profile/completeness", headers=auth_headers(token))
    assert completeness.status_code == 200
    data = completeness.json()["data"]
    assert isinstance(data["percentage"], int)
    assert 0 <= data["percentage"] <= 100
    assert isinstance(data["missing"], list)


def test_unauthorized_access():
    response = client.get("/api/profile")
    assert response.status_code == 401
    response = client.post("/api/resumes/upload", files={"file": ("a.pdf", b"%PDF-1.4 test", "application/pdf")})
    assert response.status_code == 401
    response = client.get("/api/resumes")
    assert response.status_code == 401


def test_user_isolation():
    email_a = unique_email("isoA")
    email_b = unique_email("isoB")
    token_a = register_user(client, email_a)
    token_b = register_user(client, email_b)

    make_pdf_resume(SAMPLE_DIR / "iso.pdf")
    upload = upload_pdf(client, token_a, SAMPLE_DIR / "iso.pdf")
    resume_id = upload.json()["data"]["id"]

    profile_a = client.get("/api/profile", headers=auth_headers(token_a))
    assert profile_a.status_code == 200

    assert client.get("/api/resumes", headers=auth_headers(token_b)).json()["data"] == []
    assert client.get(f"/api/resumes/{resume_id}", headers=auth_headers(token_b)).status_code == 404
    assert client.delete(f"/api/resumes/{resume_id}", headers=auth_headers(token_b)).status_code == 404
    assert client.get("/api/profile", headers=auth_headers(token_b)).status_code == 404
    assert client.get("/api/profile/skills", headers=auth_headers(token_b)).status_code == 404


def test_delete_resume_cascades_profile():
    email = unique_email("delete")
    token = register_user(client, email)
    make_pdf_resume(SAMPLE_DIR / "del.pdf")
    upload = upload_pdf(client, token, SAMPLE_DIR / "del.pdf")
    resume_id = upload.json()["data"]["id"]

    response = client.delete(f"/api/resumes/{resume_id}", headers=auth_headers(token))
    assert response.status_code == 200
    assert client.get("/api/resumes", headers=auth_headers(token)).json()["data"] == []
    assert client.get("/api/profile", headers=auth_headers(token)).status_code == 404


def test_skill_categorizer():
    assert categorize_skill("Python") == "Programming"
    assert categorize_skill("FastAPI") == "Backend"
    assert categorize_skill("React") == "Frontend"
    assert categorize_skill("PostgreSQL") == "Database"
    assert categorize_skill("RAG") == "AI/ML"
    assert categorize_skill("Docker") == "DevOps"
    assert categorize_skill("UnknownSkillXYZ") == "Other"

    categorized = categorize_skills(["Python", "python", "PYTHON", "Java", "RAG", "RAG"])
    assert categorized == [("Programming", "Python"), ("Programming", "Java"), ("AI/ML", "RAG")]
