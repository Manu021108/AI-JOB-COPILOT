import datetime
import uuid
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator


class SkillAnalysis(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    category: str | None = None
    proficiency: str | None = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        return v.strip()


class ExperienceAnalysis(BaseModel):
    company: str | None = None
    job_title: str | None = None
    location: str | None = None
    employment_type: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    description: str | None = None
    is_current: bool = False


class ProjectAnalysis(BaseModel):
    project_name: str | None = None
    description: str | None = None
    technologies: list[str] = Field(default_factory=list)
    project_url: str | None = None
    start_date: str | None = None
    end_date: str | None = None


class EducationAnalysis(BaseModel):
    institution: str | None = None
    degree: str | None = None
    field_of_study: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    grade: str | None = None


class CertificationAnalysis(BaseModel):
    name: str | None = None
    issuing_organization: str | None = None
    issue_date: str | None = None
    expiration_date: str | None = None
    credential_url: str | None = None


class ResumeAnalysis(BaseModel):
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    linkedin_url: str | None = None
    github_url: str | None = None
    portfolio_url: str | None = None
    professional_summary: str | None = None
    target_roles: list[str] = Field(default_factory=list)
    years_of_experience: float | None = None
    skills: list[SkillAnalysis | str] = Field(default_factory=list)
    experience: list[ExperienceAnalysis] = Field(default_factory=list)
    projects: list[ProjectAnalysis] = Field(default_factory=list)
    education: list[EducationAnalysis] = Field(default_factory=list)
    certifications: list[CertificationAnalysis] = Field(default_factory=list)

    @field_validator("email", mode="before")
    @classmethod
    def clean_email(cls, v: Any) -> Any:
        if isinstance(v, str):
            v = v.strip().lower()
            v = v.rstrip(".") if v.endswith(".") else v
        return v or None


class ResumeUploadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    filename: str = Field(validation_alias="original_filename")
    file_type: str
    file_size: int
    version: int
    is_active: bool
    status: Literal["uploaded"] = "uploaded"
    profile_created: bool = False


class ResumeListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    filename: str = Field(validation_alias="original_filename")
    file_type: str
    file_size: int
    version: int
    is_active: bool
    has_profile: bool = False
    created_at: datetime.datetime


class ResumeDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    filename: str = Field(validation_alias="original_filename")
    file_type: str
    file_size: int
    version: int
    is_active: bool
    created_at: datetime.datetime