from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any, Mapping
from urllib.parse import urlparse

import requests
from requests.exceptions import RequestException

from backend.config import get_settings
from backend.sources.base_source import (
    JobSource,
    NormalizedJob,
    SourceFetchResult,
    SourceStatus,
    as_text,
    infer_remote_type,
)

logger = logging.getLogger(__name__)

_ATS_DOMAINS = (
    "site:boards.greenhouse.io OR site:jobs.lever.co OR site:myworkdayjobs.com"
    " OR site:jobs.ashbyhq.com OR site:boards.icims.com"
)
_GOOGLE_CSE_URL = "https://www.googleapis.com/customsearch/v1"
_REQUEST_TIMEOUT = 10
_MAX_RESULTS = 10


class GoogleSearchSource(JobSource):
    source_name = "google_search"
    timeout_seconds = 15.0
    default_query = "Software Engineer"
    default_location = "India"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        engine_id: str | None = None,
        http_session: requests.Session | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        settings = get_settings()
        self._api_key = api_key if api_key is not None else settings.google_search_api_key
        self._engine_id = engine_id if engine_id is not None else settings.google_search_engine_id
        self._session = http_session or requests.Session()
        self._external_session = http_session is not None
        self._workflow_state: Mapping[str, Any] = {}

    def close(self) -> None:
        super().close()
        if not self._external_session:
            self._session.close()

    def fetch_jobs(
        self,
        *,
        query: str | None = None,
        location: str | None = None,
        state: Mapping[str, Any] | None = None,
    ) -> SourceFetchResult:
        self._workflow_state = _state_from_values(query=query, location=location, state=state)
        try:
            return super().fetch_jobs()
        except (RequestException, RuntimeError, ValueError) as exc:
            logger.exception("GoogleSearchSource.fetch_jobs failed")
            return SourceFetchResult(
                source_name=self.source_name,
                status=SourceStatus.FAILED,
                started_at=datetime.now(UTC),
                completed_at=datetime.now(UTC),
                error_message=str(exc),
            )

    def _fetch_jobs(self) -> tuple[list[NormalizedJob], Mapping[str, Any]]:
        state = self._workflow_state
        search = state.get("search", {})
        if not isinstance(search, Mapping):
            search = {}

        raw_query = search.get("query")
        raw_location = search.get("location")
        ui_query = _normalize_text(
            raw_query if isinstance(raw_query, str) else None,
            self.default_query,
        )
        ui_location = _normalize_text(
            raw_location if isinstance(raw_location, str) else None,
            self.default_location,
        )

        search_query = f'({_ATS_DOMAINS}) "{ui_query}" "{ui_location}"'
        params: dict[str, Any] = {
            "key": self._api_key,
            "cx": self._engine_id,
            "q": search_query,
            "dateRestrict": "d7",
            "num": _MAX_RESULTS,
        }

        logger.info("GoogleSearchSource: querying CSE — %s", search_query)
        response = self._session.get(_GOOGLE_CSE_URL, params=params, timeout=_REQUEST_TIMEOUT)
        response.raise_for_status()

        data: dict[str, Any] = response.json()
        items = data.get("items") or []

        jobs: list[NormalizedJob] = []
        skipped = 0
        for item in items:
            if not isinstance(item, dict):
                skipped += 1
                continue
            normalized = self._normalize_job(item, ui_query=ui_query, ui_location=ui_location)
            if normalized is None:
                skipped += 1
                continue
            jobs.append(normalized)

        if not jobs:
            logger.warning(
                "GoogleSearchSource returned 0 jobs for '%s' in '%s'.",
                ui_query,
                ui_location,
            )

        return jobs, {
            "search_query": search_query,
            "total_results": (data.get("searchInformation") or {}).get("totalResults"),
            "fetched_count": len(jobs),
            "skipped_count": skipped,
        }

    def _normalize_job(
        self,
        item: dict[str, Any],
        *,
        ui_query: str = "",
        ui_location: str = "",
    ) -> NormalizedJob | None:
        apply_url = as_text(item.get("link"))
        if not apply_url:
            return None

        title = as_text(item.get("title")) or "Unknown Title"
        # snippet is the primary content — Gemini will score from this
        snippet = as_text(item.get("snippet")) or title
        company = (
            _extract_company_from_pagemap(item)
            or _extract_company_from_url(apply_url)
            or "Direct ATS"
        )
        source_job_id = sha256(apply_url.encode()).hexdigest()[:64]

        try:
            return NormalizedJob(
                source=self.source_name,
                source_job_id=source_job_id,
                company_name=company,
                title=title,
                location=None,
                remote_type=infer_remote_type(snippet),
                posted_at=None,
                apply_url=apply_url,
                description=snippet,
                source_metadata={
                    "display_link": item.get("displayLink", ""),
                    "search_query": ui_query,
                    "search_location": ui_location,
                },
                raw_payload=item,
            )
        except ValueError:
            return None


def _extract_company_from_pagemap(item: dict[str, Any]) -> str | None:
    pagemap = item.get("pagemap")
    if not isinstance(pagemap, dict):
        return None
    for org in pagemap.get("organization") or []:
        if isinstance(org, dict):
            name = org.get("name") or org.get("legalname")
            if name:
                return as_text(name)
    for meta in pagemap.get("metatags") or []:
        if not isinstance(meta, dict):
            continue
        for key in ("og:site_name", "application-name", "twitter:site"):
            name = meta.get(key)
            if name:
                return as_text(name)
    return None


def _extract_company_from_url(url: str) -> str | None:
    """Parse the company slug from known ATS URL structures."""
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        path_parts = [p for p in parsed.path.split("/") if p]

        if hostname in ("boards.greenhouse.io", "job-boards.greenhouse.io"):
            return _slug_to_name(path_parts[0]) if path_parts else None
        if hostname == "jobs.lever.co":
            return _slug_to_name(path_parts[0]) if path_parts else None
        if hostname == "jobs.ashbyhq.com":
            return _slug_to_name(path_parts[0]) if path_parts else None
        if "myworkdayjobs.com" in hostname:
            return _slug_to_name(hostname.split(".")[0])
        if "icims.com" in hostname:
            return _slug_to_name(hostname.split(".")[0])
    except Exception:  # noqa: BLE001
        pass
    return None


def _slug_to_name(slug: str) -> str:
    return re.sub(r"[-_]+", " ", slug).title()


def _normalize_text(value: str | None, default: str) -> str:
    if value is None:
        return default
    stripped = value.strip()
    return stripped or default


def _state_from_values(
    *,
    query: str | None,
    location: str | None,
    state: Mapping[str, Any] | None,
) -> Mapping[str, Any]:
    if state is not None:
        return state
    return {"search": {"query": query, "location": location}}
