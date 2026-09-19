from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.responses import ApiError, ok, raise_api
from app.models.user import User
from app.api.users import get_current_user
from app.schemas.profile import (
    CandidateProfileResponse,
    CertificationResponse,
    CompletenessResponse,
    EducationResponse,
    ExperienceResponse,
    ProfileUpdate,
    ProjectResponse,
    SkillResponse,
)
from app.services.profile_service import (
    compute_completeness,
    get_user_profile,
    update_profile,
)

router = APIRouter(prefix="/profile", tags=["profile"])


def _get_profile_for(db: Session, user: User):
    profile = get_user_profile(db, user)
    if profile is None:
        raise_api(ApiError("PROFILE_NOT_FOUND", "No candidate profile yet. Upload a resume to get started.", status.HTTP_404_NOT_FOUND))
    return profile


@router.get("")
def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    profile = _get_profile_for(db, current_user)
    return ok(CandidateProfileResponse.model_validate(profile).model_dump())


@router.put("")
def put_profile(
    payload: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    profile = _get_profile_for(db, current_user)
    try:
        profile = update_profile(db, current_user, payload)
    except ValueError:
        raise_api(ApiError("PROFILE_NOT_FOUND", "No candidate profile yet. Upload a resume to get started.", status.HTTP_404_NOT_FOUND))
    db.commit()
    db.refresh(profile)
    return ok(CandidateProfileResponse.model_validate(profile).model_dump())


@router.get("/completeness")
def profile_completeness(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    profile = _get_profile_for(db, current_user)
    return ok(CompletenessResponse(**compute_completeness(profile)).model_dump())


@router.get("/skills")
def profile_skills(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    profile = _get_profile_for(db, current_user)
    return ok([SkillResponse.model_validate(item).model_dump() for item in profile.skills])


@router.get("/experience")
def profile_experience(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    profile = _get_profile_for(db, current_user)
    return ok([ExperienceResponse.model_validate(item).model_dump() for item in profile.experience])


@router.get("/projects")
def profile_projects(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    profile = _get_profile_for(db, current_user)
    return ok([ProjectResponse.model_validate(item).model_dump() for item in profile.projects])


@router.get("/education")
def profile_education(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    profile = _get_profile_for(db, current_user)
    return ok([EducationResponse.model_validate(item).model_dump() for item in profile.education])


@router.get("/certifications")
def profile_certifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    profile = _get_profile_for(db, current_user)
    return ok([CertificationResponse.model_validate(item).model_dump() for item in profile.certifications])