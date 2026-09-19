from pathlib import Path
from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app
from app.services.matching.experience_matcher import match_experience
from app.services.matching.education_matcher import match_education
from app.services.matching.engine import (
    CandidateSnapshot,
    EducationSnapshot,
    ExperienceEntrySnapshot,
    JobAnalysisSnapshot,
    JobSnapshot,
    ProjectSnapshot,
    calculate_match,
)
from app.services.matching.location_matcher import match_location
from app.services.matching.project_matcher import match_projects
from app.services.matching.role_matcher import match_role
from app.services.matching.semantic_matcher import match_semantic, clear_embedding_cache
from app.services.matching.skill_matcher import match_skills
from app.services.matching.skill_normalizer import normalize_skill
from app.services.matching.skill_relationships import related_skills
from app.services.matching.config import MATCH_VERSION, category_for_score
from tests.conftest import TESTS_DIR
from tests.helpers import auth_headers, make_pdf_resume, register_user, upload_pdf

client = TestClient(app)
SAMPLE_DIR = Path(__file__).resolve().parent / ".samples"

CATEGORIES = {"STRONG_MATCH", "GOOD_MATCH", "REVIEW", "LOW_MATCH"}


def unique_email(prefix: str = "match") -> str:
    return f"{prefix}-{uuid4()}@example.com"


def setup_module():
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)


def setup_function(_module):
    clear_embedding_cache()


# --------------------------------------------------------------------------- #
# Unit: skill normalization & relationships
# --------------------------------------------------------------------------- #


def test_normalize_skill_aliases():
    assert normalize_skill("JavaScript") == "JavaScript"
    assert normalize_skill("JS") == "JavaScript"
    assert normalize_skill("Postgres") == "PostgreSQL"
    assert normalize_skill("ReactJS") == "React"
    assert normalize_skill("pandas").lower() == "pandas"


def test_related_skills_symmetric():
    for name in {"PostgreSQL", "Python", "RAG", "Deep Learning"}:
        for related in related_skills(name):
            assert name.lower() in related_skills(related), f"relationship {name}->{related} is not symmetric"


# --------------------------------------------------------------------------- #
# Unit: skill matcher
# --------------------------------------------------------------------------- #


def test_skill_matcher_exact_and_missing():
    result = match_skills(
        required_skills=["Python", "SQL", "AWS"],
        preferred_skills=["FastAPI", "Docker"],
        candidate_names=["Python", "PostgreSQL", "React", "Git"],
    )
    assert result.applicable is True
    assert "Python" in result.matching_skills
    assert "SQL" in result.related_required_matches
    assert "AWS" in result.missing_required_skills
    assert 40 < result.score < 60


def test_skill_matcher_preferred_bonus_lost_without_preferred():
    with_pref = match_skills(
        required_skills=["Python"],
        preferred_skills=["AWS"],
        candidate_names=["Python", "AWS"],
    )
    without = match_skills(
        required_skills=["Python"],
        preferred_skills=["AWS"],
        candidate_names=["Python"],
    )
    assert with_pref.score == 100.0
    assert without.score == 90.0


def test_skill_matcher_no_requirements_not_applicable():
    result = match_skills(
        required_skills=[],
        preferred_skills=[],
        candidate_names=["Python"],
    )
    assert result.applicable is False
    assert result.score == 0


def test_skill_matcher_related_skill_partial_credit():
    result = match_skills(
        required_skills=["PostgreSQL"],
        preferred_skills=[],
        candidate_names=["SQL"],
    )
    assert result.applicable is True
    assert result.score < 100
    assert result.score > 0
    assert result.matching_skills == []
    assert result.related_required_matches == ["PostgreSQL"]


# --------------------------------------------------------------------------- #
# Unit: role, experience, education, projects, location
# --------------------------------------------------------------------------- #


def test_role_exact_and_group_and_none():
    exact = match_role(["AI/ML Engineer"], "AI/ML Engineer")
    assert exact.score == 100 and exact.applicable
    group = match_role(["Python Developer"], "Backend Engineer")
    assert group.applicable and group.score == 85
    partial = match_role(["AI Engineer"], "Python AI Engineer")
    assert partial.applicable and 40 <= partial.score < 100
    none = match_role(["Frontend Engineer"], "Backend Engineer")
    assert none.score == 0
    napp = match_role([], "Backend Engineer")
    assert napp.applicable is False


def test_experience_scoring_and_not_applicable():
    aligned = match_experience(4.0, 2, 5)
    assert aligned.score == 100 and aligned.applicable
    below = match_experience(2.0, 5, 10)
    assert below.score == 40
    over = match_experience(12.0, 2, 5)
    assert over.score < 100
    unknown = match_experience(5.0, None, None)
    assert unknown.applicable is False
    no_candidate = match_experience(None, 2, 5)
    assert no_candidate.score == 50


def test_education_levels_and_cs_field():
    high = match_education(["Bachelor's degree in Computer Science or equivalent"], [
        {"degree": "M.Tech Computer Science", "field_of_study": None, "institution": "IIT"},
    ])
    assert high.score >= 80 and high.applicable
    low = match_education(["Master's or PhD in Computer Science"], [
        {"degree": "Bachelor of Science in Statistics", "field_of_study": None, "institution": "U"},
    ])
    assert low.score < 60
    none = match_education([], [{"degree": "Bachelor of Science"}])
    assert none.applicable is False


def test_project_tech_overlap():
    projects = [{"project_name": "API Gateway", "description": "Built REST APIs", "technologies": ["Python", "FastAPI"]}]
    result = match_projects(projects, ["Python", "FastAPI", "PostgreSQL"], "REST APIs and microservices")
    assert result.applicable
    assert result.score > 0
    assert result.alignment["relevant_count"] == 1
    none = match_projects(
        [{"project_name": "Web", "description": "HTML site", "technologies": []}],
        ["Java", "Spring"],
        "JVM microservices",
    )
    assert none.score < 70


def test_location_remote_city_and_hybrid():
    remote = match_location("Bengaluru, IN", "Remote", None)
    assert remote.score == 100
    same = match_location("San Francisco, CA", "Onsite", "San Francisco, CA")
    assert same.score == 100
    diff = match_location("Austin, TX", "Onsite", "Bangalore, India")
    assert diff.score == 0
    hybrid = match_location("Austin, TX", "Hybrid", "Bangalore, India")
    assert hybrid.score == 60
    napp = match_location(None, "Onsite", "Austin, TX")
    assert napp.applicable is True and napp.score == 50


def test_semantic_identical_and_cache():
    first = match_semantic("Build REST APIs with Python.", "Build REST APIs with Python.")
    second = match_semantic("Build REST APIs with Python.", "Build REST APIs with Python.")
    third = match_semantic("Build REST APIs with Python.", "Manage a fleet of delivery trucks.")
    assert first.score == 100.0
    assert second.score == first.score
    assert third.score < first.score
    assert first.score <= 100 and first.score >= 0
    clear_embedding_cache()


# --------------------------------------------------------------------------- #
# Unit: engine composition & categories
# --------------------------------------------------------------------------- #


def _candidate(overrides=None):
    base = dict(
        target_roles=["AI/ML Engineer"],
        skills=["Python", "FastAPI", "PostgreSQL", "Docker", "Machine Learning", "Git"],
        years_of_experience=4.0,
        experience=[
            ExperienceEntrySnapshot(company="Acme", job_title="ML Engineer", description="Built ML models", is_current=True)
        ],
        projects=[ProjectSnapshot(project_name="Reco Engine", description="LLM RAG pipeline", technologies=["Python", "FastAPI", "LLM"])],
        education=[EducationSnapshot(institution="IIT", degree="M.Tech Computer Science")],
        location="San Francisco, CA",
        professional_summary="Backend and ML engineer with 4 years of experience.",
    )
    base.update(overrides or {})
    return CandidateSnapshot(**base)


def _job(overrides=None):
    base = dict(
        title="AI/ML Engineer",
        company="Nebula Labs",
        location="San Francisco, CA",
        work_mode="Hybrid",
        experience_min=2,
        experience_max=5,
        description="Build ML models and REST APIs with Python and FastAPI at scale.",
        analysis=JobAnalysisSnapshot(
            summary="AI/ML Engineer to build ML models and REST APIs",
            required_skills=["Python", "Machine Learning", "SQL"],
            preferred_skills=["FastAPI", "Docker"],
            responsibilities=["Build ML models", "Build REST APIs"],
            qualifications=["2-5 years of experience", "Bachelor's degree in Computer Science"],
            education_requirements=["Bachelor's degree in Computer Science or equivalent"],
            experience_requirements=["2-5 years"],
            tools_and_technologies=["AWS"],
        ),
    )
    base.update(overrides or {})
    return JobSnapshot(**base)


def test_engine_weights_and_strong_match():
    match = calculate_match(_candidate(), _job())
    for key in ("skills", "role", "experience", "education", "location", "semantic", "projects"):
        assert 0 <= match.scores[key] <= 100
    assert 0 <= match.overall_score <= 100
    assert match.match_version == "v1"
    assert match.category in CATEGORIES


def test_engine_weak_match_for_mismatched_candidate():
    weak = _candidate(
        dict(
            skills=["React", "TypeScript"],
            target_roles=["Frontend Engineer"],
            years_of_experience=0.5,
            location="Austin, TX",
            education=[EducationSnapshot(institution="U", degree="Associate of Arts")],
        )
    )
    match = calculate_match(weak, _job())
    assert match.overall_score < 60
    assert match.missing_required_skills


def test_engine_rated_without_analysis():
    match = calculate_match(_candidate(), _job(dict(analysis=None)))
    assert 0 <= match.overall_score <= 100
    assert match.category in CATEGORIES


def test_category_boundaries():
    assert category_for_score(85) == "STRONG_MATCH"
    assert category_for_score(84.9) == "GOOD_MATCH"
    assert category_for_score(70) == "GOOD_MATCH"
    assert category_for_score(69.9) == "REVIEW"
    assert category_for_score(55) == "REVIEW"
    assert category_for_score(0) == "LOW_MATCH"


# --------------------------------------------------------------------------- #
# Integration: match lifecycle
# --------------------------------------------------------------------------- #


def _setup_user_with_profile_and_job(prefix: str = "match"):
    email = unique_email(prefix)
    token = register_user(client, email)
    pdf = make_pdf_resume(SAMPLE_DIR / "sample_p.pdf")
    response = upload_pdf(client, token, pdf)
    assert response.status_code == 201, response.text
    job = client.post(
        "/api/jobs/from-description",
        headers=auth_headers(token),
        json={
            "title": "AI/ML Engineer",
            "company": "Nebula Labs",
            "location": "San Francisco, CA",
            "description": (
                "We are looking for an AI/ML Engineer to build ML models and REST APIs. "
                "You need experience with Python, SQL and Machine Learning. "
                "Preferred skills are FastAPI and Docker. 2-5 years of experience required. "
                "Bachelor's degree in Computer Science required. Hybrid work from San Francisco."
            ),
        },
    )
    assert job.status_code == 201, job.text
    return token, job.json()["data"]["id"]


def test_calculate_and_get_job_match():
    token, job_id = _setup_user_with_profile_and_job()
    created = client.post(f"/api/jobs/{job_id}/match", headers=auth_headers(token))
    assert created.status_code == 201, created.text
    body = created.json()["data"]
    assert body["match_version"] == MATCH_VERSION
    assert 0 <= body["overall_score"] <= 100
    assert body["category"] in CATEGORIES
    assert body["scores"]["skill"] is None or isinstance(body["scores"]["skill"], (int, float))
    assert isinstance(body["matching_skills"], list)
    assert body["explanation"]
    fetched = client.get(f"/api/jobs/{job_id}/match", headers=auth_headers(token))
    assert fetched.status_code == 200
    assert fetched.json()["data"]["id"] == body["id"]


def test_get_match_not_found_before_calculation():
    token, job_id = _setup_user_with_profile_and_job()
    fetched = client.get(f"/api/jobs/{job_id}/match", headers=auth_headers(token))
    assert fetched.status_code == 404
    assert fetched.json()["detail"]["error"]["code"] == "MATCH_NOT_FOUND"


def test_match_requires_profile():
    email = unique_email("noprof")
    token = register_user(client, email)
    job = client.post(
        "/api/jobs/from-description",
        headers=auth_headers(token),
        json={
            "title": "Backend Engineer",
            "description": "Build REST APIs with Python and FastAPI. PostgreSQL and Docker experience required.",
        },
    )
    assert job.status_code == 201, job.text
    created = client.post(f"/api/jobs/{job.json()['data']['id']}/match", headers=auth_headers(token))
    assert created.status_code == 422
    assert created.json()["detail"]["error"]["code"] == "PROFILE_NOT_FOUND"


def test_match_reuses_cache_when_unchanged():
    token, job_id = _setup_user_with_profile_and_job()
    first = client.post(f"/api/jobs/{job_id}/match", headers=auth_headers(token))
    second = client.post(f"/api/jobs/{job_id}/match", headers=auth_headers(token))
    assert first.status_code == 201 and second.status_code == 201
    assert first.json()["data"]["id"] == second.json()["data"]["id"]


def test_match_weak_for_unrelated_job():
    email = unique_email("mismatch")
    token = register_user(client, email)
    upload_pdf(client, token, make_pdf_resume(SAMPLE_DIR / "sample_q.pdf"))
    job = client.post(
        "/api/jobs/from-description",
        headers=auth_headers(token),
        json={
            "title": "Frontend UX Designer",
            "location": "Bangalore, IN",
            "description": (
                "Design delightful user interfaces with Figma and Adobe XD. "
                "Strong visual design portfolio required. Onsite in Bangalore."
            ),
        },
    )
    assert job.status_code == 201, job.text
    created = client.post(f"/api/jobs/{job.json()['data']['id']}/match", headers=auth_headers(token))
    assert created.status_code == 201
    assert created.json()["data"]["overall_score"] < 85


def test_job_without_analysis_still_matches():
    email = unique_email("noanl")
    token = register_user(client, email)
    upload_pdf(client, token, make_pdf_resume(SAMPLE_DIR / "sample_r.pdf"))
    job = client.post(
        "/api/jobs",
        headers=auth_headers(token),
        json={"title": "AI/ML Engineer", "company": "Nebula Labs", "location": "San Francisco, CA", "work_mode": "Remote"},
    )
    assert job.status_code == 201, job.text
    created = client.post(f"/api/jobs/{job.json()['data']['id']}/match", headers=auth_headers(token))
    assert created.status_code == 201, created.text
    assert 0 <= created.json()["data"]["overall_score"] <= 100


def test_local_candidate_full_location_score():
    token, job_id = _setup_user_with_profile_and_job("localfull")
    assert token
    match = client.post(f"/api/jobs/{job_id}/match", headers=auth_headers(token))
    assert match.status_code == 201
    assert match.json()["data"]["scores"]["location"] == 100.0


# --------------------------------------------------------------------------- #
# Integration: /api/matches collection
# --------------------------------------------------------------------------- #


def test_run_all_then_list_with_sort_and_filters():
    token, job_id = _setup_user_with_profile_and_job("runall")
    listing = client.get("/api/matches", headers=auth_headers(token))
    assert listing.status_code == 200
    assert listing.json()["data"]["items"] == []

    ran = client.post("/api/matches/run", headers=auth_headers(token))
    assert ran.status_code == 200
    assert ran.json()["data"]["generated"] >= 1

    listing = client.get("/api/matches?sort=match", headers=auth_headers(token))
    assert listing.status_code == 200
    items = listing.json()["data"]["items"]
    assert len(items) >= 1
    assert items[0]["job_id"] == job_id

    filtered = client.get(f"/api/matches?category={items[0]['category']}", headers=auth_headers(token))
    assert filtered.status_code == 200
    assert all(i["category"] == items[0]["category"] for i in filtered.json()["data"]["items"])

    company = filtered.json()["data"]["items"][0]["company"]
    by_company = client.get(f"/api/matches?company={company}", headers=auth_headers(token))
    assert by_company.status_code == 200
    assert all(i["company"] == company for i in by_company.json()["data"]["items"])


def test_list_matches_invalid_params():
    token, _job_id = _setup_user_with_profile_and_job()
    bad_sort = client.get("/api/matches?sort=bogus", headers=auth_headers(token))
    assert bad_sort.status_code == 400
    assert bad_sort.json()["detail"]["error"]["code"] == "INVALID_SORT"
    bad_cat = client.get("/api/matches?category=bogus", headers=auth_headers(token))
    assert bad_cat.status_code == 400
    assert bad_cat.json()["detail"]["error"]["code"] == "INVALID_CATEGORY"


def test_match_user_isolation():
    token_a, job_id = _setup_user_with_profile_and_job("iso-a")
    created = client.post(f"/api/jobs/{job_id}/match", headers=auth_headers(token_a))
    match_id = created.json()["data"]["id"]

    token_b = register_user(client, unique_email("iso-b"))
    listing = client.get("/api/matches", headers=auth_headers(token_b))
    assert listing.json()["data"]["items"] == []
    direct = client.get(f"/api/matches/{match_id}", headers=auth_headers(token_b))
    assert direct.status_code == 404


def test_recalculate_all():
    token, _job_id = _setup_user_with_profile_and_job("recalc")
    client.post("/api/matches/run", headers=auth_headers(token))
    recalculated = client.post("/api/matches/recalculate", headers=auth_headers(token))
    assert recalculated.status_code == 200
    assert recalculated.json()["data"]["recalculated"] >= 1


def test_match_stale_after_profile_update():
    token, job_id = _setup_user_with_profile_and_job("stale")
    client.post(f"/api/jobs/{job_id}/match", headers=auth_headers(token))
    updated = client.put("/api/profile", headers=auth_headers(token), json={"target_roles": ["Principal ML Engineer"]})
    assert updated.status_code == 200, updated.text
    fetched = client.get(f"/api/jobs/{job_id}/match", headers=auth_headers(token))
    assert fetched.status_code == 200
    assert fetched.json()["data"]["is_stale"] is True