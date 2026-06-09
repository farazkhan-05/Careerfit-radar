from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Any, Mapping, Protocol

from apify_client import ApifyClient
from apify_client.errors import ApifyApiError, ApifyClientError

from backend.config import get_settings
from backend.sources.base_source import (
    JobSource,
    NormalizedJob,
    SourceFetchResult,
    SourceStatus,
    as_text,
    infer_remote_type,
    parse_iso_datetime,
)


logger = logging.getLogger(__name__)


class _ActorClient(Protocol):
    def call(self, *, run_input: Mapping[str, Any], **kwargs: Any) -> Any:
        pass


class _DatasetClient(Protocol):
    def iterate_items(self, **kwargs: Any) -> Any:
        pass


class _ApifyClient(Protocol):
    def actor(self, actor_id: str) -> _ActorClient:
        pass

    def dataset(self, dataset_id: str) -> _DatasetClient:
        pass


@dataclass(frozen=True)
class ApifyActorConfig:
    actor_id: str = "valig/linkedin-jobs-scraper"
    max_items: int = 50
    wait_secs: int = 120


class ApifySource(JobSource):
    source_name = "apify"
    timeout_seconds = 120.0
    default_query = "Software Engineer"
    default_location = "India"

    def __init__(
        self,
        *,
        api_token: str | None = None,
        apify_client: _ApifyClient | None = None,
        actor_config: ApifyActorConfig | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._actor_config = actor_config or ApifyActorConfig()
        self._search_query = self.default_query
        self._search_location = self.default_location
        self._workflow_state: Mapping[str, Any] = {}
        self._configuration_error: str | None = None

        token = api_token if api_token is not None else get_settings().apify_api_token
        if apify_client is not None:
            self._apify_client = apify_client
            return
        if not token or not token.strip():
            self._configuration_error = "APIFY_API_TOKEN is not configured."
            self._apify_client = None
            return
        self._apify_client = ApifyClient(token.strip())

    def fetch_jobs(
        self,
        *,
        query: str | None = None,
        location: str | None = None,
        state: Mapping[str, Any] | None = None,
    ) -> SourceFetchResult:
        self._workflow_state = _search_state_from_values(query=query, location=location, state=state)
        if self._configuration_error is not None:
            started_at = datetime.now(UTC)
            return SourceFetchResult(
                source_name=self.source_name,
                status=SourceStatus.FAILED,
                started_at=started_at,
                completed_at=datetime.now(UTC),
                metadata={"actor_id": self._actor_config.actor_id, "enabled": self.enabled},
                error_message=self._configuration_error,
            )
        try:
            return super().fetch_jobs()
        except (ApifyApiError, ApifyClientError, RuntimeError, ValueError) as exc:
            started_at = datetime.now(UTC)
            return SourceFetchResult(
                source_name=self.source_name,
                status=SourceStatus.FAILED,
                started_at=started_at,
                completed_at=datetime.now(UTC),
                metadata={"actor_id": self._actor_config.actor_id, "enabled": self.enabled},
                error_message=str(exc),
            )

    def _fetch_jobs(self) -> tuple[list[NormalizedJob], Mapping[str, Any]]:
        if self._apify_client is None:
            raise RuntimeError("APIFY_API_TOKEN is not configured.")

        state = self._workflow_state
        search = state.get("search", {})
        if not isinstance(search, Mapping):
            search = {}
        raw_query = search.get("query")
        raw_location = search.get("location")
        ui_query = _normalize_search_text(raw_query if isinstance(raw_query, str) else None, self.default_query)
        ui_location = _normalize_search_text(
            raw_location if isinstance(raw_location, str) else None,
            self.default_location,
        )
        self._search_query = ui_query
        self._search_location = ui_location

        run_input = {
            "title": ui_query,
            "location": ui_location,
            "limit": 15,
        }
        run = self._apify_client.actor(self._actor_config.actor_id).call(
            run_input=run_input,
            wait_duration=timedelta(seconds=self._actor_config.wait_secs),
        )
        dataset_id = _get_value(run, "defaultDatasetId", "default_dataset_id")
        if not dataset_id:
            raise RuntimeError("Apify run completed without a default dataset.")

        raw_jobs = list(
            self._apify_client.dataset(str(dataset_id)).iterate_items(
                clean=True,
                limit=self._actor_config.max_items,
            )
        )
        if not raw_jobs:
            logger.warning(
                f"Apify fetched 0 jobs for '{ui_query}' in '{ui_location}'. Verify search volume on LinkedIn manually or check Apify Actor logs."
            )
        jobs = []
        skipped = 0
        for raw_job in raw_jobs:
            if not isinstance(raw_job, dict):
                skipped += 1
                continue
            try:
                normalized = self._normalize_job(raw_job)
            except ValueError:
                normalized = None
            if normalized is None:
                skipped += 1
                continue
            jobs.append(normalized)

        return jobs, {
            "actor_id": self._actor_config.actor_id,
            "run_id": _get_value(run, "id"),
            "dataset_id": str(dataset_id),
            "requested_count": self._actor_config.max_items,
            "fetched_count": len(jobs),
            "skipped_count": skipped,
            "search_payload": run_input,
        }

    def _build_run_input(self, *, ui_query: str | None = None, ui_location: str | None = None) -> dict[str, Any]:
        search_query = _normalize_search_text(ui_query or self._search_query, self.default_query)
        search_location = _normalize_search_text(ui_location or self._search_location, self.default_location)
        return {
            "title": search_query,
            "location": search_location,
            "datePosted": "r604800",
            "experienceLevel": ["1", "2"],
            "limit": self._actor_config.max_items,
        }

    def _normalize_job(self, raw_job: dict[str, Any]) -> NormalizedJob | None:
        title = as_text(raw_job.get("title", "Unknown Title")) or "Unknown Title"
        company_name = as_text(raw_job.get("companyName", raw_job.get("company", "Unknown Company"))) or "Unknown Company"
        apply_url = as_text(raw_job.get("applyUrl", raw_job.get("link", raw_job.get("url", ""))))
        description = as_text(
            raw_job.get(
                "descriptionText",
                raw_job.get("descriptionHtml", raw_job.get("description", "")),
            )
        )

        if not apply_url:
            return None

        location = _location(raw_job)
        description = description or title
        try:
            return NormalizedJob(
                source=self.source_name,
                source_job_id=_source_job_id(raw_job, apply_url, title, company_name),
                company_name=company_name,
                title=title,
                location=location,
                remote_type=infer_remote_type(
                    location,
                    _first_text(
                        raw_job,
                        "remote",
                        "remoteType",
                        "workplaceType",
                        "jobType",
                        "employmentType",
                        "workType",
                    ),
                ),
                posted_at=_posted_at(raw_job),
                apply_url=apply_url,
                description=description,
                source_metadata={
                    "actor_id": self._actor_config.actor_id,
                    "platform": _first_text(raw_job, "platform", "source", "site") or "linkedin",
                    "search_query": _first_text(raw_job, "query", "searchQuery", "search_query"),
                    "search_location": _first_text(raw_job, "searchLocation", "search_location"),
                },
                raw_payload=raw_job,
            )
        except ValueError:
            return None


def _get_value(payload: Any, *keys: str) -> Any:
    for key in keys:
        if isinstance(payload, Mapping) and key in payload:
            return payload[key]
        if hasattr(payload, key):
            return getattr(payload, key)
    return None


def _first_text(payload: Mapping[str, Any], *keys: str) -> str:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, Mapping):
            value = value.get("text") or value.get("name") or value.get("label")
        if isinstance(value, list):
            value = ", ".join(as_text(item) for item in value if as_text(item))
        text = as_text(value)
        if text:
            return text
    return ""


def _location(payload: Mapping[str, Any]) -> str | None:
    location = _first_text(payload, "location", "jobLocation", "formattedLocation")
    if location:
        return location
    parts = [
        _first_text(payload, "city"),
        _first_text(payload, "state", "region"),
        _first_text(payload, "country"),
    ]
    joined = ", ".join(part for part in parts if part)
    return joined or None


def _posted_at(payload: Mapping[str, Any]) -> datetime | None:
    raw_value = _get_value(
        payload,
        "publishedAt",
        "published_at",
        "postedAt",
        "posted_at",
        "date_posted",
        "datePosted",
        "postedDate",
        "date",
        "createdAt",
        "listedAt",
    )
    if isinstance(raw_value, (int, float)):
        from backend.sources.base_source import parse_timestamp_millis

        return parse_timestamp_millis(raw_value)
    return parse_iso_datetime(raw_value)


def _source_job_id(payload: Mapping[str, Any], apply_url: str, title: str, company_name: str) -> str:
    raw_id = _get_value(payload, "id", "jobId", "job_id", "jobKey", "jobkey", "urn")
    if raw_id:
        return as_text(raw_id)[:255]
    digest = sha256(f"{apply_url}|{title}|{company_name}".encode("utf-8")).hexdigest()
    return digest[:64]


def _normalize_search_text(value: str | None, default: str) -> str:
    if value is None:
        return default
    normalized = value.strip()
    return normalized or default


def _search_state_from_values(
    *,
    query: str | None,
    location: str | None,
    state: Mapping[str, Any] | None,
) -> Mapping[str, Any]:
    if state is not None:
        return state
    return {"search": {"query": query, "location": location}}
