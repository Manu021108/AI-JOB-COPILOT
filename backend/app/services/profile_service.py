import re
from datetime import date
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import (
    Resume,
    CandidateProfile,
    CandidateSkill,
    CandidateExperience,
    CandidateProject,
    CandidateEducation,
    CandidateCertification,
)
from app.models.user import User
from app.schemas.profile import ProfileUpdate
from app.schemas.resume import ResumeAnalysis

COMPLETENESS_WEIGHTS = {
    "full_name": 10,
    "email": 10,
    "phone": 5,
    "target_roles": 10,
    "skills": 20,
    "experience": 20,
    "projects": 15,
    "education": 10,
    "summary": 10,
}
COMPLETENESS_WEIGHTS = {k: v for k, v in COMPLETENESS_WEIGHTS.items() if v}


def get_user_profile(db: Session, user: User) -> CandidateProfile | None:
    return db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user.id))


def apply_analysis(db: Session, user: User, resume: Resume, analysis: ResumeAnalysis) -> CandidateProfile:
    profile = get_user_profile(db, user)
    if profile is None:
        profile = CandidateProfile(user_id=user.id)
        db.add(profile)
        db.flush()

    profile.resume_id = resume.id
    profile.full_name = _or_none(analysis.full_name)
    profile.email = _or_none(analysis.email)
    profile.phone = _or_none(analysis.phone)
    profile.location = _or_none(analysis.location)
    profile.linkedin_url = _or_none(analysis.linkedin_url)
    profile.github_url = _or_none(analysis.github_url)
    profile.portfolio_url = _or_none(analysis.portfolio_url)
    profile.professional_summary = _or_none(analysis.professional_summary)
    profile.target_roles = list(analysis.target_roles or [])
    profile.years_of_experience = analysis.years_of_experience

    _replace_skills(db, profile, analysis)
    _replace_experience(db, profile, analysis)
    _replace_projects(db, profile, analysis)
    _replace_education(db, profile, analysis)
    _replace_certifications(db, profile, analysis)
    return profile


def _replace_skills(db: Session, profile: CandidateProfile, analysis: ResumeAnalysis) -> None:
    for skill in list(profile.skills):
        db.delete(skill)
    for item in analysis.skills:
        name = item.name if hasattr(item, "name") else item
        category = getattr(item, "category", None) or "Other"
        proficiency = getattr(item, "proficiency", None)
        if name:
            profile.skills.append(CandidateSkill(skill_name=str(name), skill_category=str(category), proficiency=proficiency))
    db.flush()


def _replace_experience(db: Session, profile: CandidateProfile, analysis: ResumeAnalysis) -> None:
    for item in list(profile.experience):
        db.delete(item)
    for item in analysis.experience:
        if not item.company and not item.job_title:
            continue
        profile.experience.append(CandidateExperience(
            company=item.company or "Unknown",
            job_title=item.job_title or "Unknown",
            location=_or_none(item.location),
            employment_type=_or_none(item.employment_type),
            start_date=_parse_date(item.start_date),
            end_date=_parse_date(item.end_date),
            description=_or_none(item.description),
            is_current=bool(item.is_current),
        ))
    db.flush()


def _replace_projects(db: Session, profile: CandidateProfile, analysis: ResumeAnalysis) -> None:
    for item in list(profile.projects):
        db.delete(item)
    for item in analysis.projects:
        if not item.project_name:
            continue
        profile.projects.append(CandidateProject(
            project_name=item.project_name,
            description=_or_none(item.description),
            technologies=list(item.technologies or []),
            project_url=_or_none(item.project_url),
            start_date=_parse_date(item.start_date),
            end_date=_parse_date(item.end_date),
        ))
    db.flush()


def _replace_education(db: Session, profile: CandidateProfile, analysis: ResumeAnalysis) -> None:
    for item in list(profile.education):
        db.delete(item)
    for item in analysis.education:
        if not item.institution:
            continue
        profile.education.append(CandidateEducation(
            institution=item.institution,
            degree=_or_none(item.degree),
            field_of_study=_or_none(item.field_of_study),
            start_date=_parse_date(item.start_date),
            end_date=_parse_date(item.end_date),
            grade=_or_none(item.grade),
        ))
    db.flush()


def _replace_certifications(db: Session, profile: CandidateProfile, analysis: ResumeAnalysis) -> None:
    for item in list(profile.certifications):
        db.delete(item)
    for item in analysis.certifications:
        if not item.name:
            continue
        profile.certifications.append(CandidateCertification(
            name=item.name,
            issuing_organization=_or_none(item.issuing_organization),
            issue_date=_parse_date(item.issue_date),
            expiration_date=_parse_date(item.expiration_date),
            credential_url=_or_none(item.credential_url),
        ))
    db.flush()


def update_profile(db: Session, user: User, payload: ProfileUpdate) -> CandidateProfile:
    profile = get_user_profile(db, user)
    if profile is None:
        raise ValueError("No candidate profile exists yet.")

    fields = {
        "full_name": payload.full_name,
        "email": payload.email,
        "phone": payload.phone,
        "location": payload.location,
        "linkedin_url": payload.linkedin_url,
        "github_url": payload.github_url,
        "portfolio_url": payload.portfolio_url,
        "professional_summary": payload.professional_summary,
        "years_of_experience": payload.years_of_experience,
    }
    for field, value in fields.items():
        if value is not None:
            setattr(profile, field, value)
    if payload.target_roles is not None:
        profile.target_roles = [r.strip() for r in payload.target_roles if r.strip()]

    _apply_section_updates(db, profile, payload)
    return profile


def _apply_section_updates(db: Session, profile: CandidateProfile, payload: ProfileUpdate) -> None:
    if payload.skills is not None:
        for row in list(profile.skills):
            db.delete(row)
        for item in payload.skills:
            if item.skill_name.strip():
                profile.skills.append(CandidateSkill(
                    skill_name=item.skill_name.strip(),
                    skill_category=item.skill_category or "Other",
                    proficiency=item.proficiency,
                ))
        db.flush()
    if payload.experience is not None:
        for row in list(profile.experience):
            db.delete(row)
        for item in payload.experience:
            if item.company.strip() or item.job_title.strip():
                profile.experience.append(CandidateExperience(
                    company=item.company.strip(),
                    job_title=item.job_title.strip(),
                    location=_or_none(item.location),
                    employment_type=_or_none(item.employment_type),
                    start_date=item.start_date,
                    end_date=item.end_date,
                    description=_or_none(item.description),
                    is_current=item.is_current,
                ))
        db.flush()
    if payload.projects is not None:
        for row in list(profile.projects):
            db.delete(row)
        for item in payload.projects:
            if item.project_name.strip():
                profile.projects.append(CandidateProject(
                    project_name=item.project_name.strip(),
                    description=_or_none(item.description),
                    technologies=list(item.technologies or []),
                    project_url=_or_none(item.project_url),
                    start_date=item.start_date,
                    end_date=item.end_date,
                ))
        db.flush()
    if payload.education is not None:
        for row in list(profile.education):
            db.delete(row)
        for item in payload.education:
            if item.institution.strip():
                profile.education.append(CandidateEducation(
                    institution=item.institution.strip(),
                    degree=_or_none(item.degree),
                    field_of_study=_or_none(item.field_of_study),
                    start_date=item.start_date,
                    end_date=item.end_date,
                    grade=_or_none(item.grade),
                ))
        db.flush()
    if payload.certifications is not None:
        for row in list(profile.certifications):
            db.delete(row)
        for item in payload.certifications:
            if item.name.strip():
                profile.certifications.append(CandidateCertification(
                    name=item.name.strip(),
                    issuing_organization=_or_none(item.issuing_organization),
                    issue_date=item.issue_date,
                    expiration_date=item.expiration_date,
                    credential_url=_or_none(item.credential_url),
                ))
        db.flush()


def compute_completeness(profile: CandidateProfile) -> dict:
    missing: list[str] = []
    earned = 0.0
    total = sum(COMPLETENESS_WEIGHTS.values())

    def check(key: str, label: str, blank: bool) -> int:
        weight = COMPLETENESS_WEIGHTS.get(key, 0)
        if blank:
            missing.append(label)
            return 0
        return weight

    earned += check("full_name", "Full name", not profile.full_name)
    earned += check("email", "Email address", not profile.email)
    earned += check("phone", "Phone number", not profile.phone)
    earned += check("target_roles", "Target roles", not (profile.target_roles or []))
    earned += check("skills", "Skills", not (profile.skills or []))
    earned += check("experience", "Work experience", not (profile.experience or []))
    earned += check("projects", "Projects", not (profile.projects or []))
    earned += check("education", "Education", not (profile.education or []))
    earned += check("summary", "Professional summary", not profile.professional_summary)

    percentage = int(round(earned / total * 100)) if total else 0
    return {"percentage": min(percentage, 100), "missing": missing}


def _or_none(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"n/a", "none", "null"}:
        return None
    return text[:1000]


_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _parse_date(value) -> date | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"present", "now", "current"}:
        return None
    match = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", text)
    if match:
        try:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            return None
    match = re.fullmatch(r"(\d{4})-(\d{2})", text)
    if match:
        try:
            return date(int(match.group(1)), int(match.group(2)), 1)
        except ValueError:
            return None
    match = re.fullmatch(r"(\d{4})", text)
    if match:
        return date(int(match.group(1)), 1, 1)
    match = re.fullmatch(r"([A-Za-z]{3,9})\.?\s+(\d{4})", text, re.IGNORECASE)
    if match:
        month = _MONTHS.get(match.group(1).lower()[:3])
        if month:
            return date(int(match.group(2)), month, 1)
    return None