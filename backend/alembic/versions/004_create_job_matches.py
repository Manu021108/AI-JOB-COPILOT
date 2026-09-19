"""create job matches table"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "004_create_job_matches"
down_revision = "003_create_job_intelligence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("job_matches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("candidate_profile_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("overall_score", sa.Float(), nullable=False),
        sa.Column("match_version", sa.String(length=20), nullable=False, server_default=sa.text("'v1'")),
        sa.Column("skill_score", sa.Float(), nullable=True),
        sa.Column("role_score", sa.Float(), nullable=True),
        sa.Column("experience_score", sa.Float(), nullable=True),
        sa.Column("project_score", sa.Float(), nullable=True),
        sa.Column("education_score", sa.Float(), nullable=True),
        sa.Column("location_score", sa.Float(), nullable=True),
        sa.Column("semantic_score", sa.Float(), nullable=True),
        sa.Column("matching_skills", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("matching_preferred_skills", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("related_required_matches", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("missing_required_skills", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("role_alignment", postgresql.JSONB(), nullable=True),
        sa.Column("experience_alignment", postgresql.JSONB(), nullable=True),
        sa.Column("education_alignment", postgresql.JSONB(), nullable=True),
        sa.Column("project_alignment", postgresql.JSONB(), nullable=True),
        sa.Column("location_alignment", postgresql.JSONB(), nullable=True),
        sa.Column("strengths", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("gaps", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("relevant_projects", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("candidate_profile_version", sa.String(length=40), nullable=True),
        sa.Column("job_analysis_version", sa.String(length=40), nullable=True),
        sa.Column("is_stale", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("user_id", "job_id", "candidate_profile_id", "match_version", name="uq_job_matches_user_job_profile_version"))

    op.create_index("ix_job_matches_user_id", "job_matches", ["user_id"])
    op.create_index("ix_job_matches_job_id", "job_matches", ["job_id"])
    op.create_index("ix_job_matches_candidate_profile_id", "job_matches", ["candidate_profile_id"])
    op.create_index("ix_job_matches_overall_score", "job_matches", ["overall_score"])
    op.create_index("ix_job_matches_created_at", "job_matches", ["created_at"])
    op.create_index("ix_job_matches_user_score", "job_matches", ["user_id", "overall_score"])
    op.create_index("ix_job_matches_user_job", "job_matches", ["user_id", "job_id"])


def downgrade() -> None:
    op.drop_table("job_matches")