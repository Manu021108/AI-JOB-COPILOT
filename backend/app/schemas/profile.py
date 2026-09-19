import datetime
import uuid
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class SkillPayload(BaseModel):
    id: uuid.UUID | None = None
    skill_name: str = Field(min_length=1, max_length=120)
    skill_category: str = "Other"
    proficiency: str | None = None


class ExperiencePayload(BaseModel):
    id: uuid.UUID | None = None
    company: str
    job_title: str
    location: str | None = None
    employment_type: str | None = None
    start_date: datetime.date | None = None
    end_date: datetime.date | None = None
    description: str | None = None
    is_current: bool = False


class ProjectPayload(BaseModel):
    id: uuid.UUID | None = None
    project_name: str
    description: str | None = None
    technologies: list[str] = Field(default_factory=list)
    project_url: str | None = None
    start_date: datetime.date | None = None
    end_date: datetime.date | None = None


class EducationPayload(BaseModel):
    id: uuid.UUID | None = None
    institution: str
    degree: str | None = None
    field_of_study: str | None = None
    start_date: datetime.date | None = None
    end_date: datetime.date | None = None
    grade: str | None = None


class CertificationPayload(BaseModel):
    id: uuid.UUID | None = None
    name: str
    issuing_organization: str | None = None
    issue_date: datetime.date | None = None
    expiration_date: datetime.date | None = None
    credential_url: str | None = None


class ProfileUpdate(BaseModel):
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    linkedin_url: str | None = None
    github_url: str | None = None
    portfolio_url: str | None = None
    professional_summary: str | None = None
    target_roles: list[str] | None = None
    years_of_experience: float | None = None
    skills: list[SkillPayload] | None = None
    experience: list[ExperiencePayload] | None = None
    projects: list[ProjectPayload] | None = None
    education: list[EducationPayload] | None = None
    certifications: list[CertificationPayload] | None = None


class SkillResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    skill_name: str
    skill_category: str
    proficiency: str | None


class ExperienceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    company: str
    job_title: str
    location: str | None
    employment_type: str | None
    start_date: datetime.date | None
    end_date: datetime.date | None
    description: str | None
    is_current: bool


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    project_name: str
    description: str | None
    technologies: list[str]
    project_url: str | None
    start_date: datetime.date | None
    end_date: datetime.date | None


class EducationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    institution: str
    degree: str | None
    field_of_study: str | None
    start_date: datetime.date | None
    end_date: datetime.date | None
    grade: str | None


class CertificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    issuing_organization: str | None
    issue_date: datetime.date | None
    expiration_date: datetime.date | None
    credential_url: str | None


class CandidateProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    resume_id: uuid.UUID | None
    full_name: str | None
    email: str | None
    phone: str | None
    location: str | None
    linkedin_url: str | None
    github_url: str | None
    portfolio_url: str | None
    professional_summary: str | None
    target_roles: list[Any]
    years_of_experience: float | None
    skills: list[SkillResponse]
    experience: list[ExperienceResponse]
    projects: list[ProjectResponse]
    education: list[EducationResponse]
    certifications: list[CertificationResponse]
    updated_at: datetime.datetime


class CompletenessResponse(BaseModel):
    percentage: int
    missing: list[str]