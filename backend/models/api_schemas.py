from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PageResponse(BaseModel):
    items: list[Any]
    total: int
    limit: int
    offset: int


class HealthResponse(BaseModel):
    status: str
    checks: dict[str, str] = Field(default_factory=dict)


class ResumeUploadResponse(BaseModel):
    resume_id: UUID
    chunk_count: int
    profile_id: UUID | None = None
    profile_error: str | None = None


class ManualJobCreate(StrictBaseModel):
    company_name: str = Field(min_length=1, max_length=255)
    source: str = Field(default="manual", min_length=1, max_length=80)
    source_job_id: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    remote_type: str | None = Field(default=None, max_length=80)
    apply_url: HttpUrl
    description: str = Field(min_length=1)


class WebSearchImportRequest(StrictBaseModel):
    query: str = Field(default="Front End Developer", min_length=1, max_length=255)
    location: str = Field(default="Lucknow, India", min_length=1, max_length=255)

    @field_validator("query", "location")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Value must not be blank.")
        return normalized


class SourceImportResponse(BaseModel):
    source_name: str
    status: str
    jobs_fetched: int
    jobs_stored: int
    error_message: str | None = None


class WorkflowTriggerResponse(BaseModel):
    run_id: str
    status: str
    workflow_id: UUID | None = None


JobStatus = Literal[
    "new",
    "saved",
    "applied",
    "follow_up",
    "interview",
    "offer",
    "rejected",
    "ignored",
    "duplicate",
]
ApplicationStatus = Literal[
    "saved",
    "applied",
    "follow_up",
    "interview",
    "offer",
    "rejected",
    "ignored",
]
RunStatus = Literal[
    "pending",
    "running",
    "success",
    "failed",
    "disabled",
    "completed",
    "completed_with_errors",
]


class ResumeUpdate(StrictBaseModel):
    file_name: str | None = Field(default=None, min_length=1, max_length=255)
    content_type: str | None = Field(default=None, min_length=1, max_length=100)
    parsed_text: str | None = None


class CandidateProfileUpdate(StrictBaseModel):
    target_roles: list[str] | None = None
    skills: dict[str, Any] | None = None
    experience_years: float | None = Field(default=None, ge=0)
    projects: list[dict[str, Any]] | None = None
    raw_profile: dict[str, Any] | None = None


class JobUpdate(StrictBaseModel):
    canonical_job_id: UUID | None = None
    title: str | None = Field(default=None, min_length=1, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    remote_type: str | None = Field(default=None, max_length=80)
    posted_at: datetime | None = None
    apply_url: HttpUrl | None = None
    description: str | None = Field(default=None, min_length=1)
    raw_payload: dict[str, Any] | None = None
    status: JobStatus | None = None


class ApplicationUpdate(StrictBaseModel):
    status: ApplicationStatus | None = None
    notes: str | None = None
    applied_at: datetime | None = None
    follow_up_at: datetime | None = None


class SourceRunUpdate(StrictBaseModel):
    status: RunStatus | None = None
    completed_at: datetime | None = None
    jobs_fetched: int | None = Field(default=None, ge=0)
    jobs_stored: int | None = Field(default=None, ge=0)
    error_message: str | None = None


class WorkflowRunUpdate(StrictBaseModel):
    status: RunStatus | None = None
    completed_at: datetime | None = None
    state: dict[str, Any] | None = None
    errors: list[dict[str, Any]] | None = None
