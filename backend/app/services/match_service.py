import hashlib
import json
from datetime import datetime
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import CandidateProfile, Job, JobAnalysis, JobMatch
from app.models.user import User
from app.schemas.match import MatchExplanationResponse, RelevantProject
from app.services.matching import engine as matching_engine
from app.services.matching.config import MATCH_CATEGORIES, MATCH_VERSION
from app.services.matching.engine import CandidateSnapshot, ExperienceEntrySnapshot, JobAnalysisSnapshot, JobSnapshot, ProjectSnapshot, EducationSnapshot
from app.services.matching.experience_matcher import compute_candidate_years
from app.services.matching.explanation import generate_explanation


class MatchNotFoundError(Exception):
    pass


class ProfileNotFoundError(Exception):
    pass


VALID_MATCH_SORTS = ("match", "match_asc", "newest", "company")
VALID_CATEGORIES = [name for name, _ in MATCH_CATEGORIES]


def _category_bounds(category: str) -> tuple[float, float]:
    ordered = list(MATCH_CATEGORIES)
    for index, (name, floor) in enumerate(ordered):
        if name == category:
            top = ordered[index - 1][1] if index > 0 else 101.0
            return floor, top
    return 0.0, 101.0


def _sha(payload: dict) -> str:
    encoded = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def profile_version(profile: CandidateProfile | None) -> str | None:
    if profile is None:
        return None
    payload = {
        "roles": list(profile.target_roles or []),
        "location": profile.location,
        "summary": profile.professional_summary,
        "years": profile.years_of_experience,
        "skills": sorted((s.skill_name.lower(), s.skill_category or "", s.proficiency or "") for s in profile.skills),
        "experience": sorted((e.company.lower(), e.job_title.lower(), e.is_current, str(e.start_date), str(e.end_date), (e.description or "")[:200]) for e in profile.experience),
        "projects": sorted((p.project_name.lower(), (p.description or "")[:200], tuple(sorted(t.lower() for t in (p.technologies or [])))) for p in profile.projects),
        "education": sorted((e.institution.lower(), (e.degree or "").lower(), (e.field_of_study or "").lower()) for e in profile.education),
        "certifications": sorted((c.name.lower(), (c.issuing_organization or "").lower()) for c in profile.certifications),
        "updated": profile.updated_at.isoformat() if profile.updated_at else None,
    }
    return _sha(payload)


def job_version(job: Job) -> str:
    analysis = job.analysis
    payload = {
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "work_mode": job.work_mode,
        "employment_type": job.employment_type,
        "experience_min": job.experience_min,
        "experience_max": job.experience_max,
        "description": (job.description or "")[:2000],
        "updated": job.updated_at.isoformat() if job.updated_at else None,
        "analysis_updated": analysis.updated_at.isoformat() if analysis and analysis.updated_at else None,
        "analysis": {
            "summary": analysis.summary if analysis else None,
            "required": analysis.required_skills if analysis else [],
            "preferred": analysis.preferred_skills if analysis else [],
            "responsibilities": analysis.responsibilities if analysis else [],
            "qualifications": analysis.qualifications if analysis else [],
            "education": analysis.education_requirements if analysis else [],
            "experience_req": analysis.experience_requirements if analysis else [],
            "tools": analysis.tools_and_technologies if analysis else [],
            "nice": analysis.nice_to_have if analysis else [],
        }
        if analysis else None,
    }
    return _sha(payload)


def build_candidate_snapshot(profile: CandidateProfile) -> CandidateSnapshot:
    entries = [
        ExperienceEntrySnapshot(
            company=e.company,
            job_title=e.job_title,
            description=e.description,
            start_date=e.start_date,
            end_date=e.end_date,
            is_current=e.is_current,
        )
        for e in profile.experience
    ]
    years = compute_candidate_years(profile.years_of_experience, [_entry_dict(e) for e in entries])
    return CandidateSnapshot(
        target_roles=list(profile.target_roles or []),
        skills=[s.skill_name for s in profile.skills],
        years_of_experience=years,
        experience=entries,
        projects=[
            ProjectSnapshot(project_name=p.project_name, description=p.description, technologies=list(p.technologies or []))
            for p in profile.projects
        ],
        education=[
            EducationSnapshot(institution=e.institution, degree=e.degree, field_of_study=e.field_of_study)
            for e in profile.education
        ],
        location=profile.location,
        professional_summary=profile.professional_summary,
    )


def build_job_snapshot(job: Job) -> JobSnapshot:
    analysis = job.analysis
    analysis_snapshot = None
    if analysis is not None:
        analysis_snapshot = JobAnalysisSnapshot(
            summary=analysis.summary,
            required_skills=list(analysis.required_skills or []),
            preferred_skills=list(analysis.preferred_skills or []),
            responsibilities=list(analysis.responsibilities or []),
            qualifications=list(analysis.qualifications or []),
            education_requirements=list(analysis.education_requirements or []),
            experience_requirements=list(analysis.experience_requirements or []),
            tools_and_technologies=list(analysis.tools_and_technologies or []),
            nice_to_have=list(analysis.nice_to_have or []),
        )
    return JobSnapshot(
        title=job.title,
        company=job.company,
        location=job.location,
        work_mode=job.work_mode,
        employment_type=job.employment_type,
        experience_min=job.experience_min,
        experience_max=job.experience_max,
        description=job.description,
        analysis=analysis_snapshot,
    )


def _entry_dict(entry: ExperienceEntrySnapshot) -> dict:
    return {
        "company": entry.company,
        "job_title": entry.job_title,
        "description": entry.description,
        "start_date": entry.start_date,
        "end_date": entry.end_date,
        "is_current": entry.is_current,
    }


class MatchService:
    def __init__(self) -> None:
        self._engine = matching_engine

    # ------------------------------------------------------------- calculate

    def calculate_match(self, db: Session, user: User, job: Job, force: bool = False) -> JobMatch:
        profile = db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user.id))
        if profile is None:
            raise ProfileNotFoundError("Add your resume or update your profile before generating matches.")

        current_profile_version = profile_version(profile)
        current_job_version = job_version(job)
        existing = db.scalar(
            select(JobMatch).where(
                JobMatch.user_id == user.id,
                JobMatch.job_id == job.id,
                JobMatch.candidate_profile_id == profile.id,
                JobMatch.match_version == MATCH_VERSION,
            )
        )

        if existing and not force and not existing.is_stale and existing.candidate_profile_version == current_profile_version and existing.job_analysis_version == current_job_version:
            existing.is_stale = False
            db.flush()
            return existing

        reuse_cached = bool(
            existing is not None
            and not force
            and existing.candidate_profile_version == current_profile_version
            and existing.job_analysis_version == current_job_version
        )

        candidate = build_candidate_snapshot(profile)
        job_snapshot = build_job_snapshot(job)
        semantic_override = existing.semantic_score if reuse_cached else None
        match = self._engine.calculate_match(candidate, job_snapshot, semantic_override=semantic_override)

        if reuse_cached and existing is not None:
            explanation = self._explanation_from_record(existing)
        else:
            explanation = generate_explanation(candidate, job_snapshot, match)

        record = self._upsert(db, user, job, profile, match, explanation, current_profile_version, current_job_version)
        db.flush()
        return record

    # ------------------------------------------------------------ read paths

    def get_match_for_job(self, db: Session, user: User, job_id) -> JobMatch | None:
        record = db.scalar(
            select(JobMatch).where(
                JobMatch.user_id == user.id,
                JobMatch.job_id == job_id,
            ).order_by(JobMatch.created_at.desc()).limit(1)
        )
        if record is None:
            return None
        job = db.get(Job, job_id)
        profile = db.get(CandidateProfile, record.candidate_profile_id)
        self._refresh_staleness(db, record, profile, job)
        return record

    def get_match_by_id(self, db: Session, user: User, match_id) -> JobMatch | None:
        record = db.scalar(select(JobMatch).where(JobMatch.id == match_id, JobMatch.user_id == user.id))
        if record is None:
            return None
        job = db.get(Job, record.job_id)
        profile = db.get(CandidateProfile, record.candidate_profile_id)
        self._refresh_staleness(db, record, profile, job)
        return record

    def list_matches(self, db: Session, user: User, *, page: int = 1, page_size: int = 20, sort: str = "match", category: str | None = None, score_min: float | None = None, score_max: float | None = None, location: str | None = None, role: str | None = None, company: str | None = None, stale: bool | None = None) -> dict:
        query = select(JobMatch).join(Job, JobMatch.job_id == Job.id).where(JobMatch.user_id == user.id)
        count_query = select(func.count(JobMatch.id)).join(Job, JobMatch.job_id == Job.id).where(JobMatch.user_id == user.id)

        if category:
            floor, top = _category_bounds(category)
            query = query.where(JobMatch.overall_score >= floor, JobMatch.overall_score < top)
            count_query = count_query.where(JobMatch.overall_score >= floor, JobMatch.overall_score < top)
        if score_min is not None:
            query = query.where(JobMatch.overall_score >= score_min)
            count_query = count_query.where(JobMatch.overall_score >= score_min)
        if score_max is not None:
            query = query.where(JobMatch.overall_score <= score_max)
            count_query = count_query.where(JobMatch.overall_score <= score_max)
        if location:
            query = query.where(Job.location.ilike(f"%{location}%"))
            count_query = count_query.where(Job.location.ilike(f"%{location}%"))
        if role:
            query = query.where(Job.title.ilike(f"%{role}%"))
            count_query = count_query.where(Job.title.ilike(f"%{role}%"))
        if company:
            query = query.where(Job.company.ilike(f"%{company}%"))
            count_query = count_query.where(Job.company.ilike(f"%{company}%"))
        if stale is not None:
            query = query.where(JobMatch.is_stale.is_(stale))
            count_query = count_query.where(JobMatch.is_stale.is_(stale))

        order_map = {
            "match": JobMatch.overall_score.desc(),
            "match_asc": JobMatch.overall_score.asc(),
            "newest": Job.created_at.desc(),
            "company": Job.company.asc(),
        }
        query = query.order_by(order_map[sort]).offset((page - 1) * page_size).limit(page_size)

        total = db.scalar(count_query) or 0
        records = list(db.scalars(query).all())
        for record in records:
            job = db.get(Job, record.job_id)
            profile = db.get(CandidateProfile, record.candidate_profile_id)
            self._refresh_staleness(db, record, profile, job)

        return {
            "items": records,
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size if total else 0,
        }

    # ----------------------------------------------------------- bulk actions

    def recalculate_all(self, db: Session, user: User) -> list[JobMatch]:
        if db.scalar(select(func.count(CandidateProfile.id)).where(CandidateProfile.user_id == user.id)) == 0:
            raise ProfileNotFoundError("Add your resume or update your profile before generating matches.")
        match_ids = db.scalars(
            select(JobMatch.job_id).where(JobMatch.user_id == user.id).distinct()
        ).all()
        results: list[JobMatch] = []
        for job_id in match_ids:
            job = db.get(Job, job_id)
            if job is None:
                continue
            results.append(self.calculate_match(db, user, job, force=False))
        return results

    def run_all(self, db: Session, user: User) -> list[JobMatch]:
        if db.scalar(select(func.count(CandidateProfile.id)).where(CandidateProfile.user_id == user.id)) == 0:
            raise ProfileNotFoundError("Add your resume or update your profile before generating matches.")

        current_job_ids = set(db.scalars(select(JobMatch.job_id).where(JobMatch.user_id == user.id)).all())
        jobs = list(
            db.scalars(select(Job).where(Job.user_id == user.id, Job.status == "ACTIVE").order_by(Job.created_at.desc())).all()
        )
        results: list[JobMatch] = []
        for job in jobs:
            if job.id in current_job_ids:
                continue
            results.append(self.calculate_match(db, user, job, force=False))
        return results

    # ------------------------------------------------------------------ utils

    def _refresh_staleness(self, db: Session, record: JobMatch, profile: CandidateProfile | None, job: Job | None) -> None:
        if record is None:
            return
        current_profile_version = profile_version(profile)
        current_job_version = job_version(job) if job is not None else None
        stale = (
            record.match_version != MATCH_VERSION
            or (current_profile_version is not None and record.candidate_profile_version != current_profile_version)
            or (current_job_version is not None and record.job_analysis_version != current_job_version)
        )
        if stale and not record.is_stale:
            record.is_stale = True
            db.flush()

    @staticmethod
    def _explanation_from_record(record: JobMatch) -> MatchExplanationResponse:
        return MatchExplanationResponse(
            strengths=list(record.strengths or []),
            gaps=list(record.gaps or []),
            explanation=record.explanation,
            relevant_projects=[RelevantProject(project=p.get("project", ""), reason=p.get("reason", "")) for p in (record.relevant_projects or [])],
        )

    @staticmethod
    def _upsert(db: Session, user: User, job: Job, profile: CandidateProfile, match, explanation: MatchExplanationResponse, current_profile_version: str, current_job_version: str) -> JobMatch:
        record = db.scalar(
            select(JobMatch).where(
                JobMatch.user_id == user.id,
                JobMatch.job_id == job.id,
                JobMatch.candidate_profile_id == profile.id,
                JobMatch.match_version == MATCH_VERSION,
            )
        )
        if record is None:
            record = JobMatch(
                user_id=user.id,
                job_id=job.id,
                candidate_profile_id=profile.id,
                match_version=MATCH_VERSION,
            )
            db.add(record)

        record.overall_score = match.overall_score
        record.skill_score = match.scores.get("skills")
        record.role_score = match.scores.get("role")
        record.experience_score = match.scores.get("experience")
        record.project_score = match.scores.get("project")
        record.education_score = match.scores.get("education")
        record.location_score = match.scores.get("location")
        record.semantic_score = match.scores.get("semantic")
        record.matching_skills = list(match.matching_skills)
        record.matching_preferred_skills = list(match.matching_preferred_skills)
        record.related_required_matches = list(match.related_required_matches)
        record.missing_required_skills = list(match.missing_required_skills)
        record.role_alignment = match.role_alignment
        record.experience_alignment = match.experience_alignment
        record.education_alignment = match.education_alignment
        record.project_alignment = match.project_alignment
        record.location_alignment = match.location_alignment
        record.strengths = list(explanation.strengths)
        record.gaps = list(explanation.gaps)
        record.explanation = explanation.explanation
        record.relevant_projects = [p.model_dump() for p in explanation.relevant_projects]
        record.candidate_profile_version = current_profile_version
        record.job_analysis_version = current_job_version
        record.is_stale = False
        return record