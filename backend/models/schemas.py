from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class OrmModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TimestampedSchema(OrmModel):
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ResumeBase(BaseModel):
    file_name: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=100)
    text_hash: str = Field(min_length=1, max_length=64)
    parsed_text: str | None = None


class ResumeCreate(ResumeBase):
    pass


class ResumeRead(ResumeBase, TimestampedSchema):
    id: uuid.UUID


class ResumeChunkBase(BaseModel):
    resume_id: uuid.UUID
    chunk_index: int = Field(ge=0)
    content: str = Field(min_length=1)
    text_hash: str = Field(min_length=1, max_length=64)


class ResumeChunkCreate(ResumeChunkBase):
    pass


class ResumeChunkRead(ResumeChunkBase, TimestampedSchema):
    id: uuid.UUID


class CandidateProfileBase(BaseModel):
    resume_id: uuid.UUID
    target_roles: list[str] = Field(default_factory=list)
    skills: dict[str, Any] = Field(default_factory=dict)
    experience_years: float | None = Field(default=None, ge=0)
    projects: list[dict[str, Any]] = Field(default_factory=list)
    raw_profile: dict[str, Any] = Field(default_factory=dict)


class CandidateProfileCreate(CandidateProfileBase):
    pass


class CandidateProfileRead(CandidateProfileBase, TimestampedSchema):
    id: uuid.UUID


class CompanyBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    website_url: HttpUrl | None = None
    career_site_url: HttpUrl | None = None
    source_priority: int = Field(default=3, ge=1)


class CompanyCreate(CompanyBase):
    pass


class CompanyRead(CompanyBase, TimestampedSchema):
    id: uuid.UUID


class JobBase(BaseModel):
    company_id: uuid.UUID
    canonical_job_id: uuid.UUID | None = None
    source: str = Field(min_length=1, max_length=80)
    source_job_id: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    remote_type: str | None = Field(default=None, max_length=80)
    posted_at: datetime | None = None
    apply_url: HttpUrl
    description: str = Field(min_length=1)
    raw_payload: dict[str, Any] = Field(default_factory=dict)
    fetched_at: datetime
    status: str = Field(default="new", max_length=50)


class JobCreate(JobBase):
    pass


class JobRead(JobBase, TimestampedSchema):
    id: uuid.UUID


class JobRequirementBase(BaseModel):
    job_id: uuid.UUID
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    min_experience_years: float | None = Field(default=None, ge=0)
    work_authorization: str | None = Field(default=None, max_length=255)
    confidence: float | None = Field(default=None, ge=0, le=1)
    raw_requirements: dict[str, Any] = Field(default_factory=dict)


class JobRequirementCreate(JobRequirementBase):
    pass


class JobRequirementRead(JobRequirementBase, TimestampedSchema):
    id: uuid.UUID


class EmbeddingBase(BaseModel):
    entity_type: str = Field(min_length=1, max_length=80)
    embedding_model: str = Field(min_length=1, max_length=120)
    text_hash: str = Field(min_length=1, max_length=64)
    embedding_vector: list[float] = Field(min_length=1)


class JobEmbeddingCreate(EmbeddingBase):
    job_id: uuid.UUID


class JobEmbeddingRead(JobEmbeddingCreate, TimestampedSchema):
    id: uuid.UUID


class ResumeEmbeddingCreate(EmbeddingBase):
    resume_chunk_id: uuid.UUID


class ResumeEmbeddingRead(ResumeEmbeddingCreate, TimestampedSchema):
    id: uuid.UUID


class JobScoreBase(BaseModel):
    job_id: uuid.UUID
    candidate_profile_id: uuid.UUID
    final_score: int = Field(ge=0, le=100)
    role_match_score: int = Field(default=0, ge=0)
    skill_match_score: int = Field(default=0, ge=0)
    semantic_similarity_score: int = Field(default=0, ge=0)
    experience_fit_score: int = Field(default=0, ge=0)
    freshness_score: int = Field(default=0, ge=0)
    location_fit_score: int = Field(default=0, ge=0)
    source_reliability_score: int = Field(default=0, ge=0)
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    explanation: str = Field(min_length=1)


class JobScoreCreate(JobScoreBase):
    pass


class JobScoreRead(JobScoreBase, TimestampedSchema):
    id: uuid.UUID


class ApplicationBase(BaseModel):
    job_id: uuid.UUID
    status: str = Field(default="saved", max_length=80)
    notes: str | None = None
    applied_at: datetime | None = None
    follow_up_at: datetime | None = None


class ApplicationCreate(ApplicationBase):
    pass


class ApplicationRead(ApplicationBase, TimestampedSchema):
    id: uuid.UUID


class RejectedJobBase(BaseModel):
    job_id: uuid.UUID
    reason: str = Field(min_length=1)
    filter_name: str = Field(min_length=1, max_length=120)
    rejected_at: datetime
    can_restore: bool = True
    restored_at: datetime | None = None


class RejectedJobCreate(RejectedJobBase):
    pass


class RejectedJobRead(RejectedJobBase, TimestampedSchema):
    id: uuid.UUID


class SourceRunBase(BaseModel):
    source_name: str = Field(min_length=1, max_length=80)
    status: str = Field(min_length=1, max_length=80)
    started_at: datetime
    completed_at: datetime | None = None
    jobs_fetched: int = Field(default=0, ge=0)
    jobs_stored: int = Field(default=0, ge=0)
    error_message: str | None = None


class SourceRunCreate(SourceRunBase):
    pass


class SourceRunRead(SourceRunBase, TimestampedSchema):
    id: uuid.UUID


class WorkflowRunBase(BaseModel):
    run_id: str = Field(min_length=1, max_length=120)
    source_name: str | None = Field(default=None, max_length=80)
    status: str = Field(min_length=1, max_length=80)
    started_at: datetime
    completed_at: datetime | None = None
    state: dict[str, Any] = Field(default_factory=dict)
    errors: list[dict[str, Any]] = Field(default_factory=list)


class WorkflowRunCreate(WorkflowRunBase):
    pass


class WorkflowRunRead(WorkflowRunBase, TimestampedSchema):
    id: uuid.UUID


class UserPreferenceBase(BaseModel):
    target_roles: list[str] = Field(default_factory=list)
    preferred_countries: list[str] = Field(
        default_factory=lambda: [
            "India",
            "Germany",
            "Luxembourg",
            "UAE",
            "Saudi Arabia",
            "Qatar",
            "Singapore",
            "Remote",
        ],
    )
    native_country: str = "India"
    preferred_work_modes: list[str] = Field(default_factory=list)
    minimum_fit_score: int = Field(default=70, ge=0, le=100)
    maximum_experience_years: float = Field(default=5, ge=0)
    visa_sponsorship_required: bool = False
    relocation_open: bool = True
    remote_open: bool = True
    excluded_keywords: list[str] = Field(default_factory=list)
    preferred_keywords: list[str] = Field(default_factory=list)


class UserPreferenceCreate(UserPreferenceBase):
    pass


class UserPreferenceRead(UserPreferenceBase, TimestampedSchema):
    id: uuid.UUID
