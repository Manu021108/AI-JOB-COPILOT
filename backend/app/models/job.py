import uuid
from datetime import date, datetime
from sqlalchemy import DateTime, Date, Float, ForeignKey, Integer, String, Text, func, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.user import User


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    source: Mapped[str] = mapped_column(String(40), index=True, nullable=False, server_default="USER_SUBMITTED")
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    source_job_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    normalized_job_key: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)

    title: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    company: Mapped[str] = mapped_column(String(255), index=True, nullable=False, server_default="")
    location: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)

    employment_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    work_mode: Mapped[str | None] = mapped_column(String(40), index=True, nullable=True)

    experience_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    experience_max: Mapped[int | None] = mapped_column(Integer, nullable=True)

    salary_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_currency: Mapped[str | None] = mapped_column(String(10), nullable=True)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    application_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    posted_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), index=True, nullable=False, server_default="ACTIVE")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user: Mapped[User] = relationship(back_populates="jobs")
    analysis: Mapped["JobAnalysis | None"] = relationship(back_populates="job", cascade="all, delete-orphan", uselist=False)
    skills: Mapped[list["JobSkill"]] = relationship(back_populates="job", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_jobs_user_created", "user_id", "created_at"),
        Index("ix_jobs_user_company", "user_id", "company"),
        Index("ix_jobs_user_status", "user_id", "status"),
    )


class JobAnalysis(Base):
    __tablename__ = "job_analysis"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), index=True, nullable=False)

    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    required_skills: Mapped[list | None] = mapped_column(JSONB, nullable=False, server_default="[]")
    preferred_skills: Mapped[list | None] = mapped_column(JSONB, nullable=False, server_default="[]")
    responsibilities: Mapped[list | None] = mapped_column(JSONB, nullable=False, server_default="[]")
    qualifications: Mapped[list | None] = mapped_column(JSONB, nullable=False, server_default="[]")
    education_requirements: Mapped[list | None] = mapped_column(JSONB, nullable=False, server_default="[]")
    experience_requirements: Mapped[list | None] = mapped_column(JSONB, nullable=False, server_default="[]")
    tools_and_technologies: Mapped[list | None] = mapped_column(JSONB, nullable=False, server_default="[]")
    nice_to_have: Mapped[list | None] = mapped_column(JSONB, nullable=False, server_default="[]")
    employment_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    analysis_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    job: Mapped[Job] = relationship(back_populates="analysis")


class JobSkill(Base):
    __tablename__ = "job_skills"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), index=True, nullable=False)
    skill_name: Mapped[str] = mapped_column(String(120), nullable=False)
    skill_category: Mapped[str] = mapped_column(String(60), nullable=False, server_default="Other")
    is_required: Mapped[bool] = mapped_column(index=True, nullable=False, default=False)
    importance: Mapped[str | None] = mapped_column(String(20), nullable=True)

    job: Mapped[Job] = relationship(back_populates="skills")

    __table_args__ = (
        Index("ix_job_skills_job_name", "job_id", "skill_name"),
    )