from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


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


class ManualJobCreate(BaseModel):
    company_name: str = Field(min_length=1, max_length=255)
    source: str = Field(default="manual", min_length=1, max_length=80)
    source_job_id: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    remote_type: str | None = Field(default=None, max_length=80)
    apply_url: str = Field(min_length=1, max_length=1000)
    description: str = Field(min_length=1)


class ApifyImportRequest(BaseModel):
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
