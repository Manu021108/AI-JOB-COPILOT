import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.ai.job_analyzer import JobAnalysisError
from app.core.database import get_db
from app.core.rate_limit import url_import_limiter
from app.core.responses import ApiError, ok, raise_api
from app.models import Job, JobAnalysis
from app.models.user import User
from app.api.users import get_current_user
from app.schemas.job import (
    JobAnalysisResponse,
    JobCreate,
    JobDescriptionCreate,
    JobListItem,
    JobResponse,
    JobUpdate,
    JobUrlImport,
    PaginatedJobs,
)
from app.services.job_service import DuplicateJobError, JobNotFoundError, JobService, VALID_SORTS
from app.services.job_sources import JobSourceError

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _map_service_errors(exc: Exception) -> None:
    if isinstance(exc, JobNotFoundError):
        raise_api(ApiError("JOB_NOT_FOUND", "Job not found.", status.HTTP_404_NOT_FOUND))
    if isinstance(exc, DuplicateJobError):
        raise_api(ApiError("DUPLICATE_JOB", str(exc), status.HTTP_409_CONFLICT))
    if isinstance(exc, JobSourceError):
        code = exc.code
        if code in {"HTTP_ERROR", "UNREACHABLE", "FETCH_TIMEOUT", "TOO_MANY_REDIRECTS"}:
            raise_api(ApiError(code, exc.message, status.HTTP_502_BAD_GATEWAY))
        if code in {"URL_NOT_ALLOWED", "VALIDATION_ERROR", "LINKEDIN_MANUAL_INPUT_REQUIRED"}:
            raise_api(ApiError(code, exc.message, status.HTTP_400_BAD_REQUEST))
        raise_api(ApiError(code, exc.message, status.HTTP_422_UNPROCESSABLE_ENTITY))
    if isinstance(exc, JobAnalysisError):
        raise_api(ApiError("ANALYSIS_FAILED", str(exc), status.HTTP_422_UNPROCESSABLE_ENTITY))
    if isinstance(exc, ValueError):
        raise_api(ApiError("VALIDATION_ERROR", str(exc), status.HTTP_400_BAD_REQUEST))
    raise_api(ApiError("REQUEST_FAILED", "The request could not be completed. Please try again.", status.HTTP_400_BAD_REQUEST))


@router.post("", status_code=status.HTTP_201_CREATED)
def create_job(
    payload: JobCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    service = JobService()
    try:
        job = service.create_manual(db, current_user, payload)
    except Exception as exc:
        _map_service_errors(exc)
    return ok(_job_response(job))


@router.post("/import-url", status_code=status.HTTP_201_CREATED)
async def import_job_from_url(
    payload: JobUrlImport,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if not url_import_limiter.allow(f"url_import:{current_user.id}"):
        raise_api(ApiError("TOO_MANY_REQUESTS", "Too many URL imports. Please try again later.", status.HTTP_429_TOO_MANY_REQUESTS))
    service = JobService()
    try:
        job = await service.import_from_url(db, current_user, payload.url)
    except Exception as exc:
        _map_service_errors(exc)
    return ok(_job_response(job))


@router.post("/from-description", status_code=status.HTTP_201_CREATED)
def create_job_from_description(
    payload: JobDescriptionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    service = JobService()
    try:
        job = service.create_from_description(db, current_user, payload)
    except Exception as exc:
        _map_service_errors(exc)
    return ok(_job_response(job))


@router.get("")
def list_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    search: str | None = Query(None, max_length=200),
    company: str | None = Query(None, max_length=255),
    location: str | None = Query(None, max_length=255),
    source: str | None = Query(None, max_length=40),
    status_filter: str | None = Query(None, alias="status", max_length=20),
    work_mode: str | None = Query(None, max_length=40),
    sort: str = Query("newest", max_length=20),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if sort not in VALID_SORTS:
        raise_api(ApiError("INVALID_SORT", "Invalid sort value.", status.HTTP_400_BAD_REQUEST))
    service = JobService()
    result = service.list_jobs(
        db, current_user,
        page=page,
        page_size=page_size,
        search=search,
        company=company,
        location=location,
        source=source,
        status=status_filter,
        work_mode=work_mode,
        sort=sort,
    )
    items = [_list_item(job) for job in result["items"]]
    return ok(PaginatedJobs(
        items=items,
        page=result["page"],
        page_size=result["page_size"],
        total=result["total"],
        total_pages=result["total_pages"],
    ).model_dump())


@router.get("/{job_id}")
def get_job(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    service = JobService()
    try:
        job = service.get_job(db, current_user, job_id)
    except Exception as exc:
        _map_service_errors(exc)
    return ok(_job_response(job))


@router.put("/{job_id}")
def update_job(
    job_id: uuid.UUID,
    payload: JobUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    service = JobService()
    try:
        job = service.update_job(db, current_user, job_id, payload)
    except Exception as exc:
        _map_service_errors(exc)
    return ok(_job_response(job))


@router.delete("/{job_id}")
def delete_job(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    service = JobService()
    try:
        deleted = service.delete_job(db, current_user, job_id)
    except Exception as exc:
        _map_service_errors(exc)
    return ok({"id": str(deleted.id)})


@router.post("/{job_id}/analyze")
def analyze_job(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    service = JobService()
    try:
        analysis_record = service.analyze_job(db, current_user, job_id)
    except Exception as exc:
        _map_service_errors(exc)
    return ok(_analysis_response(current_user.id, job_id, analysis_record))


@router.get("/{job_id}/analysis")
def get_job_analysis(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    service = JobService()
    try:
        record = service.get_analysis(db, current_user, job_id)
    except Exception as exc:
        _map_service_errors(exc)
    if record is None:
        raise_api(ApiError("ANALYSIS_NOT_FOUND", "No analysis exists for this job yet.", status.HTTP_404_NOT_FOUND))
    return ok(_analysis_response(current_user.id, job_id, record))


def _job_response(job: Job) -> dict:
    data = JobResponse.model_validate(job).model_dump()
    data["has_analysis"] = job.analysis is not None
    return data


def _list_item(job: Job) -> dict:
    data = JobListItem.model_validate(job).model_dump()
    data["has_analysis"] = job.analysis is not None
    return data


def _analysis_response(user_id: uuid.UUID, job_id: uuid.UUID, record: JobAnalysis | None) -> dict:
    if record is None:
        return {"job_id": str(job_id), "has_analysis": False}
    return JobAnalysisResponse(
        job_id=job_id,
        summary=record.summary,
        required_skills=record.required_skills or [],
        preferred_skills=record.preferred_skills or [],
        responsibilities=record.responsibilities or [],
        qualifications=record.qualifications or [],
        education_requirements=record.education_requirements or [],
        experience_requirements=record.experience_requirements or [],
        tools_and_technologies=record.tools_and_technologies or [],
        nice_to_have=record.nice_to_have or [],
        employment_details=record.employment_details,
        updated_at=record.updated_at,
    ).model_dump()