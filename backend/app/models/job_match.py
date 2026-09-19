import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.user import User


class JobMatch(Base):
    __tablename__ = "job_matches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), index=True, nullable=False)
    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True, nullable=False)

    overall_score: Mapped[float] = mapped_column(Float, index=True, nullable=False)
    match_version: Mapped[str] = mapped_column(String(20), nullable=False, server_default="v1")

    skill_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    role_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    experience_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    project_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    education_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    semantic_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    matching_skills: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    matching_preferred_skills: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    related_required_matches: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    missing_required_skills: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")

    role_alignment: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    experience_alignment: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    education_alignment: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    project_alignment: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    location_alignment: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    strengths: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    gaps: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    relevant_projects: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")

    candidate_profile_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    job_analysis_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    is_stale: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user: Mapped[User] = relationship()
    job: Mapped["Job"] = relationship()
    candidate_profile: Mapped["CandidateProfile"] = relationship()

    __table_args__ = (
        UniqueConstraint("user_id", "job_id", "candidate_profile_id", "match_version", name="uq_job_matches_user_job_profile_version"),
        Index("ix_job_matches_user_score", "user_id", "overall_score"),
        Index("ix_job_matches_user_job", "user_id", "job_id"),
    )