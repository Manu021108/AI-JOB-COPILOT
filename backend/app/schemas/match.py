import datetime
import uuid
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field


MatchCategory = Literal["STRONG_MATCH", "GOOD_MATCH", "REVIEW", "LOW_MATCH"]


class MatchScores(BaseModel):
    skill: float | None = None
    role: float | None = None
    experience: float | None = None
    project: float | None = None
    education: float | None = None
    location: float | None = None
    semantic: float | None = None


class RelevantProject(BaseModel):
    project: str
    reason: str


class MatchExplanationResponse(BaseModel):
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    explanation: str = ""
    relevant_projects: list[RelevantProject] = Field(default_factory=list)


class MatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    job_id: uuid.UUID
    candidate_profile_id: uuid.UUID
    overall_score: float
    category: MatchCategory
    match_version: str
    scores: MatchScores
    matching_skills: list[str]
    matching_preferred_skills: list[str]
    missing_required_skills: list[str]
    role_alignment: dict[str, Any]
    experience_alignment: dict[str, Any]
    education_alignment: dict[str, Any]
    project_alignment: dict[str, Any]
    location_alignment: dict[str, Any]
    strengths: list[str]
    gaps: list[str]
    explanation: str | None
    relevant_projects: list[RelevantProject]
    is_stale: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime


class JobMatchListItem(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    job_title: str
    company: str
    location: str | None
    work_mode: str | None
    overall_score: float
    category: MatchCategory
    is_stale: bool
    matching_skills: list[str]
    missing_required_skills: list[str]
    role_alignment: dict[str, Any]
    created_at: datetime.datetime


class PaginatedMatches(BaseModel):
    items: list[JobMatchListItem]
    page: int
    page_size: int
    total: int
    total_pages: int