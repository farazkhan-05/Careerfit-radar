from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Mapping

import httpx
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from backend.utils.text_utils import normalize_text


class SourceStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    DISABLED = "disabled"


class NormalizedJob(BaseModel):
    source: str = Field(min_length=1, max_length=80)
    source_job_id: str = Field(min_length=1, max_length=255)
    company_name: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    remote_type: str | None = Field(default=None, max_length=80)
    posted_at: datetime | None = None
    apply_url: HttpUrl
    description: str = Field(min_length=1)
    source_metadata: dict[str, Any] = Field(default_factory=dict)
    raw_payload: dict[str, Any] = Field(default_factory=dict)
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = ConfigDict(extra="forbid")

    @field_validator("company_name", "title", "description")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        return normalize_text(value)

    @field_validator("location", "remote_type")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = normalize_text(value)
        return normalized or None


@dataclass(frozen=True)
class SourceFetchResult:
    source_name: str
    status: SourceStatus
    jobs: tuple[NormalizedJob, ...] = ()
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    error_message: str | None = None


class JobSource(ABC):
    source_name: str
    enabled: bool = True
    timeout_seconds: float = 20.0

    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self._external_client = client is not None
        self._client = client or httpx.Client(timeout=timeout_seconds or self.timeout_seconds)
        if timeout_seconds is not None:
            self.timeout_seconds = timeout_seconds

    def close(self) -> None:
        if not self._external_client:
            self._client.close()

    def fetch_jobs(self) -> SourceFetchResult:
        started_at = datetime.now(UTC)
        if not self.enabled:
            return SourceFetchResult(
                source_name=self.source_name,
                status=SourceStatus.DISABLED,
                started_at=started_at,
                completed_at=datetime.now(UTC),
                metadata={"enabled": False},
                error_message="Source is disabled.",
            )

        try:
            jobs, metadata = self._fetch_jobs()
        except httpx.HTTPError as exc:
            return SourceFetchResult(
                source_name=self.source_name,
                status=SourceStatus.FAILED,
                started_at=started_at,
                completed_at=datetime.now(UTC),
                metadata={"enabled": True},
                error_message=str(exc),
            )

        return SourceFetchResult(
            source_name=self.source_name,
            status=SourceStatus.SUCCESS,
            jobs=tuple(jobs),
            started_at=started_at,
            completed_at=datetime.now(UTC),
            metadata=metadata,
        )

    @abstractmethod
    def _fetch_jobs(self) -> tuple[list[NormalizedJob], Mapping[str, Any]]:
        pass


def as_text(value: Any) -> str:
    if value is None:
        return ""
    return normalize_text(str(value))


def parse_timestamp_millis(value: Any) -> datetime | None:
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(float(value) / 1000, UTC)
    except (TypeError, ValueError, OSError):
        return None


def parse_iso_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        raw = str(value).replace("Z", "+00:00")
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def infer_remote_type(*values: str | None) -> str | None:
    searchable = " ".join(value or "" for value in values).casefold()
    if "hybrid" in searchable:
        return "hybrid"
    if "remote" in searchable or "work from home" in searchable:
        return "remote"
    if "onsite" in searchable or "on-site" in searchable:
        return "onsite"
    return None
