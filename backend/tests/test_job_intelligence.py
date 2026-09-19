from uuid import uuid4
from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.core.rate_limit import RateLimiter
from app.services.job_sources.http_client import FetchResult, HttpFetchError

client = TestClient(app)

SAMPLE_JOB = """AI/ML Engineer
ABC Technologies
Hyderabad

We are looking for an AI/ML Engineer to join our platform team. You will build and ship machine learning models, design retrieval pipelines, and develop production APIs using Python and FastAPI. This role works across product and data teams.

Responsibilities:
- Build and train machine learning models.
- Design and develop REST APIs with FastAPI.
- Collaborate with product and data teams to ship features.

Requirements:
- 2-5 years of experience in machine learning or software engineering.
- Strong proficiency in Python and SQL.
- Hands-on experience with Machine Learning frameworks.
- Bachelor's degree in Computer Science or equivalent.

Preferred:
- Experience with FastAPI and Docker.
- Familiarity with AWS.

Nice to have:
- Kubernetes and LangChain experience.

Salary: $120,000 - $180,000
Employment Type: Full Time
Work Mode: Hybrid
Application URL: https://careers.abctech.com/apply/123
"""

SAMPLE_JOB_2 = """Data Engineer
Beta Data Systems
New York, NY

We are looking for a Data Engineer to own and scale data pipelines. You will build ETL jobs, model the warehouse, and support analytics with SQL and dbt.

Responsibilities:
- Build and maintain reliable ETL pipelines.
- Model and manage the data warehouse.
- Support analytics teams with SQL.

Requirements:
- 4-8 years of experience in data engineering.
- Advanced SQL and Python skills.
- Experience with dbt and Airflow.

Preferred:
- Experience with AWS and Snowflake.

Employment Type: Full Time
Work Mode: Remote
"""

SAMPLE_FRONTEND = """Frontend Engineer
Nexa Labs
Bengaluru

We are looking for a Frontend Engineer who is passionate about building fast, accessible web applications with React and TypeScript.

Responsibilities:
- Build and maintain React components.
- Improve application performance.

Requirements:
- 3-6 years of experience with React and TypeScript.
- Strong command of CSS and browser debugging.

Nice to have:
- Experience with Next.js and Tailwind CSS.

Work Mode: Onsite
"""

SAMPLE_CLOSED = """DevOps Engineer
OpsWorks
Singapore

We are looking for a DevOps Engineer to run our Kubernetes infrastructure and CI/CD pipelines.

Responsibilities:
- Operate and scale Kubernetes clusters.
- Maintain CI/CD pipelines with GitHub Actions.

Requirements:
- 3-7 years of experience in DevOps.
- Strong Kubernetes and Docker experience.

Work Mode: Hybrid
"""


def unique_email(prefix: str = "jobs") -> str:
    return f"{prefix}-{uuid4()}@example.com"


def register(token_prefix: str = "jobs") -> str:
    from tests.helpers import register_user

    return register_user(client, unique_email(token_prefix))


def auth(token: str) -> dict:
    from tests.helpers import auth_headers

    return auth_headers(token)


# ---------------------------------------------------------------------------- URL fetching

class FakeHttpFetcher:
    """Deterministic fake of HttpFetcher for URL-import tests (no network)."""

    def __init__(self, pages=None, errors=None):
        self.pages = pages or {}
        self.errors = errors or {}

    async def fetch(self, url: str) -> FetchResult:
        if url in self.errors:
            raise self.errors[url]
        if url in self.pages:
            content_type, body = self.pages[url]
            return FetchResult(final_url=url, content_type=content_type, body=body)
        raise HttpFetchError("UNREACHABLE", "Page not found.")


JOB_PAGE_HTML = (
    "<html><head><title>AI/ML Engineer at ABC Technologies</title></head><body>"
    + "".join(f"<p>{line}</p>" for line in SAMPLE_JOB.splitlines())
    + "</body></html>"
).encode("utf-8")


def test_url_import_creates_job(monkeypatch):
    token = register()
    fetcher = FakeHttpFetcher(pages={"https://careers.abctech.com/jobs/abc": ("text/html", JOB_PAGE_HTML)})
    monkeypatch.setattr("app.services.job_service.HttpFetcher", lambda *a, **k: fetcher)

    response = client.post(
        "/api/jobs/import-url",
        headers=auth(token),
        json={"url": "https://careers.abctech.com/jobs/abc"},
    )
    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert data["source"] == "URL"
    assert data["source_url"] == "https://careers.abctech.com/jobs/abc"
    assert data["title"] == "AI/ML Engineer"
    assert data["company"] == "ABC Technologies"
    assert data["has_analysis"] is True
    assert data["experience_min"] == 2
    assert data["experience_max"] == 5


def test_url_import_same_url_is_duplicate(monkeypatch):
    token = register()
    fetcher = FakeHttpFetcher(pages={"https://x.com/j/1": ("text/html", JOB_PAGE_HTML)})
    monkeypatch.setattr("app.services.job_service.HttpFetcher", lambda *a, **k: fetcher)

    url = {"url": "https://x.com/j/1"}
    assert client.post("/api/jobs/import-url", headers=auth(token), json=url).status_code == 201
    second = client.post("/api/jobs/import-url", headers=auth(token), json=url)
    assert second.status_code == 409
    assert second.json()["detail"]["error"]["code"] == "DUPLICATE_JOB"


def test_url_import_rejects_linkedin(monkeypatch):
    token = register()
    response = client.post(
        "/api/jobs/import-url",
        headers=auth(token),
        json={"url": "https://www.linkedin.com/jobs/view/123456"},
    )
    assert response.status_code == 400
    assert response.json()["detail"]["error"]["code"] == "LINKEDIN_MANUAL_INPUT_REQUIRED"


@pytest.mark.parametrize(
    "bad_url",
    [
        "http://localhost:8000/jobs",
        "http://127.0.0.1/job",
        "http://10.0.0.5/job",
        "http://169.254.169.254/latest/meta-data",
        "http://192.168.1.1/job",
        "ftp://example.com/job",
        "file:///etc/passwd",
    ],
)
def test_url_import_rejects_unsafe_urls(monkeypatch, bad_url):
    token = register()
    response = client.post("/api/jobs/import-url", headers=auth(token), json={"url": bad_url})
    assert response.status_code == 400
    assert response.json()["detail"]["error"]["code"] == "URL_NOT_ALLOWED"


def test_url_import_unreachable_page(monkeypatch):
    token = register()
    monkeypatch.setattr(
        "app.services.job_service.HttpFetcher",
        lambda *a, **k: FakeHttpFetcher(),
    )
    response = client.post(
        "/api/jobs/import-url",
        headers=auth(token),
        json={"url": "https://example.org/job/42"},
    )
    assert response.status_code == 502
    assert response.json()["detail"]["error"]["code"] == "UNREACHABLE"


def test_url_import_empty_page(monkeypatch):
    token = register()
    fetcher = FakeHttpFetcher(pages={"https://x.com/empty": ("text/html", b"<html><body><p>Please enable JavaScript to view the job.</p></body></html>")})
    monkeypatch.setattr("app.services.job_service.HttpFetcher", lambda *a, **k: fetcher)
    response = client.post("/api/jobs/import-url", headers=auth(token), json={"url": "https://x.com/empty"})
    assert response.status_code == 422
    assert response.json()["detail"]["error"]["code"] == "EMPTY_URL_CONTENT"


def test_url_import_http_error(monkeypatch):
    token = register()
    fetcher = FakeHttpFetcher(errors={"https://x.com/broken": HttpFetchError("HTTP_ERROR", "The URL returned HTTP 500.")})
    monkeypatch.setattr("app.services.job_service.HttpFetcher", lambda *a, **k: fetcher)
    response = client.post("/api/jobs/import-url", headers=auth(token), json={"url": "https://x.com/broken"})
    assert response.status_code == 502
    assert response.json()["detail"]["error"]["code"] == "HTTP_ERROR"


def test_import_url_requires_auth():
    response = client.post("/api/jobs/import-url", json={"url": "https://example.com/job"})
    assert response.status_code == 401


# ---------------------------------------------------------------------------- manual creation

def test_create_manual_job():
    token = register()
    response = client.post(
        "/api/jobs",
        headers=auth(token),
        json={
            "title": "Senior Backend Engineer",
            "company": "Acme Corp",
            "location": "Remote",
            "employment_type": "Full Time",
            "work_mode": "Remote",
            "status": "ACTIVE",
        },
    )
    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert data["source"] == "USER_SUBMITTED"
    assert data["has_analysis"] is False
    assert data["status"] == "ACTIVE"


def test_create_manual_job_requires_title():
    token = register()
    response = client.post(
        "/api/jobs",
        headers=auth(token),
        json={"title": "   ", "company": "Acme"},
    )
    assert response.status_code == 400
    assert response.json()["detail"]["error"]["code"] == "VALIDATION_ERROR"


def test_create_manual_duplicate():
    token = register()
    payload = {"title": "Full Stack Engineer", "company": "Acme Corp", "location": "Remote"}
    assert client.post("/api/jobs", headers=auth(token), json=payload).status_code == 201
    second = client.post("/api/jobs", headers=auth(token), json=payload)
    assert second.status_code == 409
    assert second.json()["detail"]["error"]["code"] == "DUPLICATE_JOB"


def test_create_manual_duplicate_by_application_url():
    token = register()
    payload = {"title": "iOS Engineer", "company": "MobileCo", "application_url": "https://careers.mobileco.com/42"}
    assert client.post("/api/jobs", headers=auth(token), json=payload).status_code == 201
    second = client.post(
        "/api/jobs",
        headers=auth(token),
        json={"title": "iOS Engineer II", "company": "OtherCo", "application_url": "https://careers.mobileco.com/42"},
    )
    assert second.status_code == 409


# ----------------------------------------------------------------------- from description

def test_create_from_description_runs_analysis():
    token = register()
    response = client.post(
        "/api/jobs/from-description",
        headers=auth(token),
        json={"description": SAMPLE_JOB},
    )
    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert data["title"] == "AI/ML Engineer"
    assert data["company"] == "ABC Technologies"
    assert data["location"] == "Hyderabad"
    assert data["has_analysis"] is True
    assert data["application_url"] == "https://careers.abctech.com/apply/123"

    analysis = client.get(f"/api/jobs/{data['id']}/analysis", headers=auth(token))
    assert analysis.status_code == 200
    body = analysis.json()["data"]
    assert "Python" in body["required_skills"]
    assert "Kubernetes" in body["nice_to_have"]
    assert data["id"] == body["job_id"]


def test_create_from_description_respects_overrides():
    token = register()
    response = client.post(
        "/api/jobs/from-description",
        headers=auth(token),
        json={"description": SAMPLE_JOB, "title": "My Custom Title", "company": "Override Co"},
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["title"] == "My Custom Title"
    assert data["company"] == "Override Co"


def test_create_from_description_duplicate():
    token = register()
    payload = {"description": SAMPLE_JOB_2}
    assert client.post("/api/jobs/from-description", headers=auth(token), json=payload).status_code == 201
    second = client.post("/api/jobs/from-description", headers=auth(token), json=payload)
    assert second.status_code == 409
    assert second.json()["detail"]["error"]["code"] == "DUPLICATE_JOB"


def test_create_from_description_requires_description():
    token = register()
    response = client.post("/api/jobs/from-description", headers=auth(token), json={"description": "  "})
    assert response.status_code in (400, 422)


# ------------------------------------------------------------------------------ listing

def _make_many(token):
    jobs = []
    for description in (SAMPLE_JOB, SAMPLE_JOB_2, SAMPLE_FRONTEND, SAMPLE_CLOSED):
        response = client.post("/api/jobs/from-description", headers=auth(token), json={"description": description})
        assert response.status_code == 201, response.text
        jobs.append(response.json()["data"])
    return jobs


def test_list_jobs_pagination():
    token = register()
    _make_many(token)
    response = client.get("/api/jobs", headers=auth(token), params={"page": 1, "page_size": 2})
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["total"] == 4
    assert body["total_pages"] == 2
    assert len(body["items"]) == 2


def test_list_jobs_search():
    token = register()
    _make_many(token)
    response = client.get("/api/jobs", headers=auth(token), params={"search": "GitHub Actions"})
    assert response.status_code == 200
    titles = [item["title"] for item in response.json()["data"]["items"]]
    assert titles == ["DevOps Engineer"]


def test_list_jobs_filter_by_status():
    token = register()
    listed = _make_many(token)
    job_id = listed[0]["id"]
    updated = client.put(
        f"/api/jobs/{job_id}",
        headers=auth(token),
        json={"status": "CLOSED"},
    )
    assert updated.status_code == 200

    response = client.get("/api/jobs", headers=auth(token), params={"status": "CLOSED"})
    items = response.json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["id"] == job_id


def test_list_jobs_filter_company_and_location():
    token = register()
    _make_many(token)
    response = client.get("/api/jobs", headers=auth(token), params={"company": "Beta Data Systems"})
    assert [i["title"] for i in response.json()["data"]["items"]] == ["Data Engineer"]

    response = client.get("/api/jobs", headers=auth(token), params={"location": "Bengaluru"})
    assert [i["title"] for i in response.json()["data"]["items"]] == ["Frontend Engineer"]


def test_list_jobs_filter_work_mode_and_source():
    token = register()
    _make_many(token)
    response = client.get("/api/jobs", headers=auth(token), params={"work_mode": "Hybrid"})
    assert sorted(i["title"] for i in response.json()["data"]["items"]) == ["AI/ML Engineer", "DevOps Engineer"]

    response = client.get("/api/jobs", headers=auth(token), params={"source": "URL"})
    assert response.json()["data"]["total"] == 0


def test_list_jobs_sort_by_title():
    token = register()
    _make_many(token)
    response = client.get("/api/jobs", headers=auth(token), params={"sort": "title"})
    titles = [item["title"] for item in response.json()["data"]["items"]]
    assert titles == sorted(titles)


def test_list_jobs_invalid_sort():
    token = register()
    response = client.get("/api/jobs", headers=auth(token), params={"sort": "bogus"})
    assert response.status_code == 400
    assert response.json()["detail"]["error"]["code"] == "INVALID_SORT"


def test_list_empty():
    token = register()
    response = client.get("/api/jobs", headers=auth(token))
    assert response.status_code == 200
    assert response.json()["data"]["items"] == []
    assert response.json()["data"]["total"] == 0


# ----------------------------------------------------------------- dynamic operations

def test_get_update_delete_job():
    token = register()
    created = client.post(
        "/api/jobs",
        headers=auth(token),
        json={"title": "QA Engineer", "company": "TestCo", "location": "Remote", "salary_min": 60000, "salary_max": 90000},
    ).json()["data"]
    job_id = created["id"]

    detail = client.get(f"/api/jobs/{job_id}", headers=auth(token))
    assert detail.status_code == 200
    assert detail.json()["data"]["salary_max"] == 90000

    updated = client.put(
        f"/api/jobs/{job_id}",
        headers=auth(token),
        json={"status": "EXPIRED", "salary_max": 95000, "work_mode": "Hybrid"},
    )
    assert updated.status_code == 200
    data = updated.json()["data"]
    assert data["status"] == "EXPIRED"
    assert data["salary_max"] == 95000
    assert data["work_mode"] == "Hybrid"
    assert data["title"] == "QA Engineer"

    deleted = client.delete(f"/api/jobs/{job_id}", headers=auth(token))
    assert deleted.status_code == 200

    missing = client.get(f"/api/jobs/{job_id}", headers=auth(token))
    assert missing.status_code == 404
    assert missing.json()["detail"]["error"]["code"] == "JOB_NOT_FOUND"


def test_analyze_manual_job_with_description():
    token = register()
    created = client.post(
        "/api/jobs",
        headers=auth(token),
        json={"title": "Manual ML Role", "company": "MLCo", "description": SAMPLE_JOB},
    ).json()["data"]
    job_id = created["id"]
    assert created["has_analysis"] is False

    response = client.post(f"/api/jobs/{job_id}/analyze", headers=auth(token))
    assert response.status_code == 200, response.text
    assert "required_skills" in response.json()["data"]

    detail = client.get(f"/api/jobs/{job_id}", headers=auth(token)).json()["data"]
    assert detail["has_analysis"] is True
    assert detail["title"] == "Manual ML Role"


def test_analyze_requires_description():
    token = register()
    created = client.post(
        "/api/jobs",
        headers=auth(token),
        json={"title": "No Description Role", "company": "EmptyCo"},
    ).json()["data"]
    response = client.post(f"/api/jobs/{created['id']}/analyze", headers=auth(token))
    assert response.status_code == 422
    assert response.json()["detail"]["error"]["code"] == "ANALYSIS_FAILED"


def test_re_analyze_replaces_analysis():
    token = register()
    created = client.post(
        "/api/jobs/from-description",
        headers=auth(token),
        json={"description": SAMPLE_FRONTEND},
    ).json()["data"]
    job_id = created["id"]
    first = client.get(f"/api/jobs/{job_id}/analysis", headers=auth(token)).json()["data"]
    assert "React" in first["required_skills"]

    client.put(f"/api/jobs/{job_id}", headers=auth(token), json={"description": SAMPLE_JOB_2})
    client.post(f"/api/jobs/{job_id}/analyze", headers=auth(token))
    second = client.get(f"/api/jobs/{job_id}/analysis", headers=auth(token)).json()["data"]
    assert "Python" in second["required_skills"]
    assert "React" not in second["required_skills"]


def test_analysis_not_found():
    token = register()
    created = client.post(
        "/api/jobs",
        headers=auth(token),
        json={"title": "TBD Role", "company": "ACo"},
    ).json()["data"]
    response = client.get(f"/api/jobs/{created['id']}/analysis", headers=auth(token))
    assert response.status_code == 404
    assert response.json()["detail"]["error"]["code"] == "ANALYSIS_NOT_FOUND"


# --------------------------------------------------------------------- user isolation

def test_jobs_are_isolated_between_users():
    token_a = register("aaa")
    token_b = register("bbb")

    created = client.post(
        "/api/jobs",
        headers=auth(token_a),
        json={"title": "Secret Role", "company": "AlphaCo"},
    ).json()["data"]

    listing = client.get("/api/jobs", headers=auth(token_b))
    assert listing.json()["data"]["items"] == []

    job_id = created["id"]
    assert client.get(f"/api/jobs/{job_id}", headers=auth(token_b)).status_code == 404
    assert client.put(f"/api/jobs/{job_id}", headers=auth(token_b), json={"title": "Hijack"}).status_code == 404
    assert client.delete(f"/api/jobs/{job_id}", headers=auth(token_b)).status_code == 404
    assert client.post(f"/api/jobs/{job_id}/analyze", headers=auth(token_b)).status_code == 404


def test_job_operations_require_auth():
    assert client.get("/api/jobs").status_code == 401
    assert client.post("/api/jobs", json={"title": "x"}).status_code == 401
    assert client.post("/api/jobs/from-description", json={"description": SAMPLE_JOB}).status_code == 401


# --------------------------------------------------------------------------- rate limit

def test_rate_limiter_sliding_window():
    limiter = RateLimiter(window_seconds=60, max_requests=3)
    assert limiter.allow("k") is True
    assert limiter.allow("k") is True
    assert limiter.allow("k") is True
    assert limiter.allow("k") is False