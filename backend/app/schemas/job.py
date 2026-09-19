import datetime
import uuid
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator


class JobAnalysisSchema(BaseModel):
    """Structured LLM analyzer output. Validated before anything is persisted."""

    title: str | None = None
    company: str | None = None
    location: str | None = None
    summary: str | None = None
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    qualifications: list[str] = Field(default_factory=list)
    education_requirements: list[str] = Field(default_factory=list)
    experience_requirements: list[str] = Field(default_factory=list)
    tools_and_technologies: list[str] = Field(default_factory=list)
    nice_to_have: list[str] = Field(default_factory=list)
    employment_details: str | None = None
    employment_type: str | None = None
    work_mode: str | None = None
    experience_min: int | None = None
    experience_max: int | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    salary_currency: str | None = None
    posted_at: str | None = None
    application_url: str | None = None

    @field_validator("*", mode="before")
    @classmethod
    def strip_values(cls, value):
        if isinstance(value, str):
            return value.strip() or None
        return value

    @field_validator(
        "required_skills", "preferred_skills", "responsibilities", "qualifications",
        "education_requirements", "experience_requirements", "tools_and_technologies",
        "nice_to_have",
        mode="before",
    )
    @classmethod
    def normalize_lists(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value or []

    @field_validator("salary_currency")
    @classmethod
    def upper_currency(cls, value):
        if value is None:
            return None
        return value.strip().upper()[:3] or None


class JobCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    company: str = Field(default="", max_length=255)
    location: str | None = Field(default=None, max_length=255)
    description: str | None = None
    application_url: str | None = Field(default=None, max_length=2048)
    source_url: str | None = Field(default=None, max_length=2048)
    source_job_id: str | None = Field(default=None, max_length=255)
    employment_type: str | None = Field(default=None, max_length=40)
    work_mode: str | None = Field(default=None, max_length=40)
    experience_min: int | None = Field(default=None, ge=0, le=60)
    experience_max: int | None = Field(default=None, ge=0, le=60)
    salary_min: int | None = None
    salary_max: int | None = None
    salary_currency: str | None = Field(default=None, max_length=10)
    status: Literal["ACTIVE", "CLOSED", "EXPIRED", "ARCHIVED"] = "ACTIVE"


class JobDescriptionCreate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    company: str | None = Field(default=None, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    description: str = Field(min_length=10, max_length=100_000)
    application_url: str | None = Field(default=None, max_length=2048)
    source_url: str | None = Field(default=None, max_length=2048)


class JobUrlImport(BaseModel):
    url: str = Field(min_length=4, max_length=2048)


class JobUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    company: str | None = Field(default=None, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    description: str | None = None
    application_url: str | None = Field(default=None, max_length=2048)
    employment_type: str | None = Field(default=None, max_length=40)
    work_mode: str | None = Field(default=None, max_length=40)
    experience_min: int | None = Field(default=None, ge=0, le=60)
    experience_max: int | None = Field(default=None, ge=0, le=60)
    salary_min: int | None = None
    salary_max: int | None = None
    salary_currency: str | None = Field(default=None, max_length=10)
    status: Literal["ACTIVE", "CLOSED", "EXPIRED", "ARCHIVED"] | None = None


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str
    company: str
    location: str | None
    source: str
    source_url: str | None
    source_job_id: str | None
    employment_type: str | None
    work_mode: str | None
    experience_min: int | None
    experience_max: int | None
    salary_min: int | None
    salary_max: int | None
    salary_currency: str | None
    description: str | None
    application_url: str | None
    posted_at: datetime.date | None
    status: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    has_analysis: bool = False


class JobListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str
    company: str
    location: str | None
    source: str
    status: str
    work_mode: str | None
    employment_type: str | None
    created_at: datetime.datetime
    has_analysis: bool = False


class JobAnalysisResponse(BaseModel):
    job_id: uuid.UUID
    summary: str | None
    required_skills: list[str]
    preferred_skills: list[str]
    responsibilities: list[str]
    qualifications: list[str]
    education_requirements: list[str]
    experience_requirements: list[str]
    tools_and_technologies: list[str]
    nice_to_have: list[str]
    employment_details: str | None
    updated_at: datetime.datetime


class PaginatedJobs(BaseModel):
    items: list[JobListItem]
    page: int
    page_size: int
    total: int
    total_pages: int