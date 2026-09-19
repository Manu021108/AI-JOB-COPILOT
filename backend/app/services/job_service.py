from datetime import date
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.exc import IntegrityError

from app.ai.job_analyzer import JobAnalysisError, JobAnalyzer
from app.models import Job, JobAnalysis, JobSkill
from app.models.user import User
from app.schemas.job import (
    JobAnalysisSchema,
    JobCreate,
    JobDescriptionCreate,
    JobUpdate,
)
from app.services.job_normalizer import (
    make_job_key,
    normalize_employment_type,
    normalize_text,
    normalize_work_mode,
    parse_posted_date,
)
from app.services.job_text_cleaner import clean_job_text
from app.services.job_sources import JobContent, JobSourceError, UrlJobSource
from app.services.job_sources.http_client import HttpFetcher
from app.services.job_sources.url_source import RobotsTxtPolicy
from app.services.skill_categorizer import categorize_skill, normalize_skill_name
from app.services.url_security import assert_safe_url

VALID_SORTS = {"newest", "oldest", "company", "title"}


class DuplicateJobError(Exception):
    def __init__(self, message: str = "This job already exists in your job list.") -> None:
        super().__init__(message)


class JobNotFoundError(Exception):
    pass


class JobService:
    def __init__(self, analyzer: JobAnalyzer | None = None, url_source: UrlJobSource | None = None) -> None:
        self.analyzer = analyzer or JobAnalyzer()
        if url_source is not None:
            self.url_source = url_source
        else:
            fetcher = HttpFetcher()
            self.url_source = UrlJobSource(fetcher=fetcher, validator=assert_safe_url, robots=RobotsTxtPolicy(fetcher))

    # ------------------------------------------------------------------ create
    def create_manual(self, db: Session, user: User, payload: JobCreate) -> Job:
        title = (payload.title or "").strip()
        if not title:
            raise ValueError("Job title is required.")
        company = (payload.company or "").strip()
        location = normalize_text(payload.location)
        description = clean_job_text(payload.description)

        duplicate = self._find_duplicate(
            db, user,
            title=title, company=company, location=location,
            source_url=payload.source_url,
            application_url=payload.application_url,
            source_job_id=payload.source_job_id,
        )
        if duplicate is not None:
            raise DuplicateJobError()

        job = Job(
            user_id=user.id,
            source="USER_SUBMITTED",
            source_url=payload.source_url,
            source_job_id=payload.source_job_id,
            normalized_job_key=make_job_key(title, company, location),
            title=title,
            company=company,
            location=location,
            employment_type=normalize_employment_type(payload.employment_type),
            work_mode=normalize_work_mode(payload.work_mode),
            experience_min=payload.experience_min,
            experience_max=payload.experience_max,
            salary_min=payload.salary_min,
            salary_max=payload.salary_max,
            salary_currency=payload.salary_currency,
            description=description,
            application_url=payload.application_url,
            status=payload.status,
        )
        db.add(job)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise DuplicateJobError()
        db.refresh(job)
        return job

    def create_from_description(self, db: Session, user: User, payload: JobDescriptionCreate) -> Job:
        description = clean_job_text(payload.description)
        if not description:
            raise ValueError("A job description is required.")

        analysis = self._analyze(description)
        title = normalize_text(payload.title) or normalize_text(analysis.title) or "Untitled Job"
        company = normalize_text(payload.company) or normalize_text(analysis.company) or ""
        location = normalize_text(payload.location) or normalize_text(analysis.location)
        application_url = payload.application_url or analysis.application_url

        duplicate = self._find_duplicate(
            db, user,
            title=title, company=company, location=location,
            source_url=payload.source_url,
            application_url=application_url,
        )
        if duplicate is not None:
            raise DuplicateJobError()

        content = JobContent(
            source="USER_SUBMITTED",
            source_url=payload.source_url,
            title=title,
            company=company,
            location=location,
            description=description,
            application_url=application_url,
            employment_type=analysis.employment_type,
            work_mode=analysis.work_mode,
            posted_at=_parse_date(analysis.posted_at),
        )
        job = self._build_job(user, content, analysis)
        db.add(job)
        self._apply_analysis(db, job, analysis)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise DuplicateJobError()
        db.refresh(job)
        return job

    async def import_from_url(self, db: Session, user: User, url: str) -> Job:
        content = await self.url_source.fetch({"url": url})
        analysis = self._analyze(content.description or "")
        title = normalize_text(content.title or analysis.title) or "Untitled Job"
        company = normalize_text(content.company) or normalize_text(analysis.company) or ""
        location = normalize_text(content.location or analysis.location)
        duplicate = self._find_duplicate(
            db, user,
            title=title, company=company, location=location,
            source_url=content.source_url,
            application_url=content.application_url or analysis.application_url,
            source_job_id=content.source_job_id,
        )
        if duplicate is not None:
            raise DuplicateJobError()

        job = self._build_job(user, content, analysis)
        db.add(job)
        self._apply_analysis(db, job, analysis)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise DuplicateJobError()
        db.refresh(job)
        return job

    # ------------------------------------------------------------------ read
    def list_jobs(
        self,
        db: Session,
        user: User,
        *,
        page: int,
        page_size: int,
        search: str | None,
        company: str | None,
        location: str | None,
        source: str | None,
        status: str | None,
        work_mode: str | None,
        sort: str,
    ) -> dict:
        filters = [Job.user_id == user.id]
        if search:
            term = f"%{search}%"
            filters.append(
                or_(
                    Job.title.ilike(term),
                    Job.company.ilike(term),
                    Job.location.ilike(term),
                    Job.description.ilike(term),
                )
            )
        if company:
            filters.append(Job.company.ilike(f"%{company}%"))
        if location:
            filters.append(Job.location.ilike(f"%{location}%"))
        if source:
            filters.append(Job.source == source)
        if status:
            filters.append(Job.status == status)
        if work_mode:
            filters.append(Job.work_mode == work_mode)

        total = db.scalar(select(func.count(Job.id)).where(*filters)) or 0
        order = _sort_order(sort)
        items = list(
            db.scalars(
                select(Job)
                .options(selectinload(Job.analysis))
                .where(*filters)
                .order_by(order, Job.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        return {
            "items": items,
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size if total else 0,
        }

    def get_job(self, db: Session, user: User, job_id) -> Job:
        job = db.scalar(select(Job).options(selectinload(Job.analysis)).where(Job.id == job_id, Job.user_id == user.id))
        if job is None:
            raise JobNotFoundError()
        return job

    # ----------------------------------------------------------------- update
    def update_job(self, db: Session, user: User, job_id, payload: JobUpdate) -> Job:
        job = self.get_job(db, user, job_id)
        if payload.title is not None:
            job.title = payload.title.strip() or job.title
        if payload.company is not None:
            job.company = payload.company.strip()
        if payload.location is not None:
            job.location = normalize_text(payload.location)
        if payload.description is not None:
            job.description = clean_job_text(payload.description)
        if payload.application_url is not None:
            job.application_url = payload.application_url or None
        if payload.employment_type is not None:
            job.employment_type = normalize_employment_type(payload.employment_type)
        if payload.work_mode is not None:
            job.work_mode = normalize_work_mode(payload.work_mode)
        if payload.experience_min is not None:
            job.experience_min = payload.experience_min
        if payload.experience_max is not None:
            job.experience_max = payload.experience_max
        if payload.salary_min is not None:
            job.salary_min = payload.salary_min
        if payload.salary_max is not None:
            job.salary_max = payload.salary_max
        if payload.salary_currency is not None:
            job.salary_currency = payload.salary_currency or None
        if payload.status is not None:
            job.status = payload.status
        job.normalized_job_key = make_job_key(job.title, job.company, job.location)
        db.commit()
        db.refresh(job)
        return job

    def delete_job(self, db: Session, user: User, job_id) -> Job:
        job = self.get_job(db, user, job_id)
        db.delete(job)
        db.commit()
        return job

    # -------------------------------------------------------------- analysis
    def analyze_job(self, db: Session, user: User, job_id) -> JobAnalysis:
        job = self.get_job(db, user, job_id)
        description = job.description
        if not description or not description.strip():
            raise JobAnalysisError("This job has no description to analyze.")
        analysis = self._analyze(description)
        self._apply_analysis(db, job, analysis)
        db.commit()
        db.refresh(job)
        return job.analysis

    def get_analysis(self, db: Session, user: User, job_id) -> JobAnalysis | None:
        job = self.get_job(db, user, job_id)
        return job.analysis

    # -------------------------------------------------------------- helpers
    def _analyze(self, description: str) -> JobAnalysisSchema:
        return self.analyzer.analyze(description)

    def _build_job(self, user: User, content: JobContent, analysis: JobAnalysisSchema | None = None) -> Job:
        title = content.title
        if analysis is not None and content.title is None:
            title = normalize_text(analysis.title)
        title = normalize_text(title) or "Untitled Job"
        company = content.company or (normalize_text(analysis.company) if analysis else None) or ""
        location = content.location or (normalize_text(analysis.location) if analysis else None)
        application_url = content.application_url or (analysis.application_url if analysis else None)
        posted_at = content.posted_at or (_parse_date(analysis.posted_at) if analysis else None)
        employment_type = content.employment_type or (normalize_employment_type(analysis.employment_type) if analysis else None)
        work_mode = content.work_mode or (normalize_work_mode(analysis.work_mode) if analysis else None)
        experience_min = analysis.experience_min if analysis else None
        experience_max = analysis.experience_max if analysis else None
        salary_min = analysis.salary_min if analysis else None
        salary_max = analysis.salary_max if analysis else None
        salary_currency = analysis.salary_currency if analysis else None
        if content.source_url and application_url is None:
            application_url = content.source_url
        return Job(
            user_id=user.id,
            source=content.source,
            source_url=content.source_url,
            source_job_id=content.source_job_id,
            normalized_job_key=make_job_key(title, company, location),
            title=title,
            company=company,
            location=location,
            employment_type=employment_type,
            work_mode=work_mode,
            experience_min=experience_min,
            experience_max=experience_max,
            salary_min=salary_min,
            salary_max=salary_max,
            salary_currency=salary_currency,
            description=content.description,
            application_url=application_url,
            posted_at=posted_at,
        )

    def _apply_analysis(self, db: Session, job: Job, analysis: JobAnalysisSchema) -> None:
        record = job.analysis if job.analysis is not None else JobAnalysis(job_id=job.id)
        record.summary = analysis.summary
        record.required_skills = list(analysis.required_skills)
        record.preferred_skills = list(analysis.preferred_skills)
        record.responsibilities = list(analysis.responsibilities)
        record.qualifications = list(analysis.qualifications)
        record.education_requirements = list(analysis.education_requirements)
        record.experience_requirements = list(analysis.experience_requirements)
        record.tools_and_technologies = list(analysis.tools_and_technologies)
        record.nice_to_have = list(analysis.nice_to_have)
        record.employment_details = analysis.employment_details
        record.analysis_json = analysis.model_dump(mode="json")
        if record.id is None:
            db.add(record)
            job.analysis = record

        for skill in list(job.skills):
            db.delete(skill)
        for name, importance in _skill_rows(analysis):
            if name:
                job.skills.append(JobSkill(
                    skill_name=name,
                    skill_category=categorize_skill(name),
                    is_required=importance == "high",
                    importance=importance,
                ))

        if job.employment_type is None and analysis.employment_type:
            job.employment_type = normalize_employment_type(analysis.employment_type)
        if job.work_mode is None and analysis.work_mode:
            job.work_mode = normalize_work_mode(analysis.work_mode)
        if job.experience_min is None and analysis.experience_min is not None:
            job.experience_min = analysis.experience_min
        if job.experience_max is None and analysis.experience_max is not None:
            job.experience_max = analysis.experience_max
        if job.salary_min is None and analysis.salary_min is not None:
            job.salary_min = analysis.salary_min
        if job.salary_max is None and analysis.salary_max is not None:
            job.salary_max = analysis.salary_max
        if job.salary_currency is None and analysis.salary_currency:
            job.salary_currency = analysis.salary_currency
        if job.posted_at is None and analysis.posted_at:
            job.posted_at = _parse_date(analysis.posted_at)
        if job.application_url is None and analysis.application_url:
            job.application_url = analysis.application_url
        db.flush()

    def _find_duplicate(
        self,
        db: Session,
        user: User,
        *,
        title: str | None,
        company: str | None,
        location: str | None,
        source_url: str | None = None,
        application_url: str | None = None,
        source_job_id: str | None = None,
    ) -> Job | None:
        if source_url:
            existing = db.scalar(select(Job).where(Job.user_id == user.id, Job.source_url == source_url))
            if existing is not None:
                return existing
        if source_job_id:
            existing = db.scalar(select(Job).where(Job.user_id == user.id, Job.source_job_id == source_job_id))
            if existing is not None:
                return existing
        if application_url:
            existing = db.scalar(select(Job).where(Job.user_id == user.id, Job.application_url == application_url))
            if existing is not None:
                return existing
        key = make_job_key(title, company, location)
        existing = db.scalar(select(Job).where(Job.user_id == user.id, Job.normalized_job_key == key))
        return existing


def _sort_order(sort: str):
    if sort == "oldest":
        return Job.created_at.asc()
    if sort == "company":
        return func.lower(Job.company).asc()
    if sort == "title":
        return func.lower(Job.title).asc()
    return Job.created_at.desc()


def _skill_rows(analysis: JobAnalysisSchema) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    seen: set[str] = set()
    for group, importance in (
        (analysis.required_skills, "high"),
        (analysis.preferred_skills, "medium"),
        (analysis.nice_to_have, "low"),
        (analysis.tools_and_technologies, "medium"),
    ):
        for item in group:
            name = normalize_skill_name(item or "")
            key = name.lower()
            if not name or key in seen:
                continue
            seen.add(key)
            rows.append((name, importance))
    return rows


def _parse_date(value: str | None) -> date | None:
    return parse_posted_date(value)