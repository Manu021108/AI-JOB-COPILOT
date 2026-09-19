import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.responses import ApiError, ok, raise_api
from app.models import JobMatch
from app.models.user import User
from app.api.users import get_current_user
from app.schemas.match import (
    JobMatchListItem,
    MatchResponse,
    MatchScores,
    PaginatedMatches,
    RelevantProject,
)
from app.services.match_service import (
    MatchNotFoundError,
    MatchService,
    ProfileNotFoundError,
    VALID_MATCH_SORTS,
    VALID_CATEGORIES,
)

router = APIRouter(prefix="/matches", tags=["matches"])


def _map_errors(exc: Exception) -> None:
    if isinstance(exc, MatchNotFoundError):
        raise_api(ApiError("MATCH_NOT_FOUND", "No match found.", status.HTTP_404_NOT_FOUND))
    if isinstance(exc, ProfileNotFoundError):
        raise_api(ApiError("PROFILE_NOT_FOUND", str(exc), status.HTTP_422_UNPROCESSABLE_ENTITY))
    raise_api(ApiError("REQUEST_FAILED", "The request could not be completed. Please try again.", status.HTTP_400_BAD_REQUEST))


@router.get("")
def list_matches(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    sort: str = Query("match", max_length=20),
    category: str | None = Query(None, max_length=20),
    score_min: float | None = Query(None, ge=0, le=100),
    score_max: float | None = Query(None, ge=0, le=100),
    location: str | None = Query(None, max_length=255),
    role: str | None = Query(None, max_length=255),
    company: str | None = Query(None, max_length=255),
    stale: bool | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if sort not in VALID_MATCH_SORTS:
        raise_api(ApiError("INVALID_SORT", "Invalid sort value.", status.HTTP_400_BAD_REQUEST))
    if category is not None and category not in VALID_CATEGORIES:
        raise_api(ApiError("INVALID_CATEGORY", "Invalid match category.", status.HTTP_400_BAD_REQUEST))
    if score_min is not None and score_max is not None and score_min > score_max:
        raise_api(ApiError("INVALID_RANGE", "score_min cannot exceed score_max.", status.HTTP_400_BAD_REQUEST))

    service = MatchService()
    result = service.list_matches(
        db, current_user,
        page=page,
        page_size=page_size,
        sort=sort,
        category=category,
        score_min=score_min,
        score_max=score_max,
        location=location,
        role=role,
        company=company,
        stale=stale,
    )
    db.commit()
    items = [_list_item(record) for record in result["items"]]
    return ok(PaginatedMatches(
        items=items,
        page=result["page"],
        page_size=result["page_size"],
        total=result["total"],
        total_pages=result["total_pages"],
    ).model_dump())


@router.get("/{match_id}")
def get_match(
    match_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    service = MatchService()
    record = service.get_match_by_id(db, current_user, match_id)
    db.commit()
    if record is None:
        raise_api(ApiError("MATCH_NOT_FOUND", "No match found.", status.HTTP_404_NOT_FOUND))
    return ok(_match_response(record))


@router.post("/recalculate")
def recalculate_matches(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    service = MatchService()
    try:
        records = service.recalculate_all(db, current_user)
        db.commit()
    except Exception as exc:
        db.rollback()
        _map_errors(exc)
    return ok({"recalculated": len(records), "items": [_list_item(r) for r in records]})


@router.post("/run")
def run_all_matches(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    service = MatchService()
    try:
        records = service.run_all(db, current_user)
        db.commit()
    except Exception as exc:
        db.rollback()
        _map_errors(exc)
    return ok({"generated": len(records), "items": [_list_item(r) for r in records]})


# ---- serializers

def match_response(record: JobMatch) -> dict:
    return MatchResponse(
        id=record.id,
        job_id=record.job_id,
        candidate_profile_id=record.candidate_profile_id,
        overall_score=record.overall_score,
        category=_category(record),
        match_version=record.match_version,
        scores=MatchScores(
            skill=record.skill_score,
            role=record.role_score,
            experience=record.experience_score,
            project=record.project_score,
            education=record.education_score,
            location=record.location_score,
            semantic=record.semantic_score,
        ),
        matching_skills=list(record.matching_skills or []),
        matching_preferred_skills=list(record.matching_preferred_skills or []),
        missing_required_skills=list(record.missing_required_skills or []),
        role_alignment=record.role_alignment or {},
        experience_alignment=record.experience_alignment or {},
        education_alignment=record.education_alignment or {},
        project_alignment=record.project_alignment or {},
        location_alignment=record.location_alignment or {},
        strengths=list(record.strengths or []),
        gaps=list(record.gaps or []),
        explanation=record.explanation,
        relevant_projects=[RelevantProject(project=p.get("project", ""), reason=p.get("reason", "")) for p in (record.relevant_projects or [])],
        is_stale=record.is_stale,
        created_at=record.created_at,
        updated_at=record.updated_at,
    ).model_dump()


_match_response = match_response


def _list_item(record: JobMatch) -> dict:
    job = record.job
    return JobMatchListItem(
        id=record.id,
        job_id=record.job_id,
        job_title=job.title if job else "",
        company=job.company if job else "",
        location=job.location if job else None,
        work_mode=job.work_mode if job else None,
        overall_score=record.overall_score,
        category=_category(record),
        is_stale=record.is_stale,
        matching_skills=list(record.matching_skills or []),
        missing_required_skills=list(record.missing_required_skills or []),
        role_alignment=record.role_alignment or {},
        created_at=record.created_at,
    ).model_dump()


def _category(record: JobMatch) -> str:
    from app.services.matching.config import category_for_score

    return category_for_score(record.overall_score)