from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any, Mapping, Protocol, cast
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

_TAVILY_SEARCH_URL = "https://api.tavily.com/search"
_REQUEST_TIMEOUT = 20
_MAX_RESULTS = 12
_ATS_DOMAINS = (
    "boards.greenhouse.io",
    "job-boards.greenhouse.io",
    "jobs.lever.co",
    "myworkdayjobs.com",
    "jobs.ashbyhq.com",
    "boards.icims.com",
)


class TavilyProviderError(RuntimeError):
    """Sanitized provider error that never includes API keys."""


class TavilyHttpResponse(Protocol):
    status_code: int

    def json(self) -> Any: ...


class TavilyHttpSession(Protocol):
    def post(
        self,
        url: str,
        *,
        json: Mapping[str, Any],
        headers: Mapping[str, str],
        timeout: int,
    ) -> TavilyHttpResponse: ...

    def close(self) -> None: ...


class TavilySearchSource(JobSource):
    source_name = "tavily_search"
    timeout_seconds = 25.0
    default_query = "Software Engineer"
    default_location = "India"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        http_session: TavilyHttpSession | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        settings = get_settings()
        self._api_key = api_key if api_key is not None else settings.tavily_api_key
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
        except TavilyProviderError as exc:
            logger.warning("TavilySearchSource.fetch_jobs failed: %s", exc)
            return SourceFetchResult(
                source_name=self.source_name,
                status=SourceStatus.FAILED,
                started_at=datetime.now(UTC),
                completed_at=datetime.now(UTC),
                error_message=str(exc),
            )
        except (RequestException, RuntimeError, ValueError) as exc:
            logger.exception("TavilySearchSource.fetch_jobs failed")
            return SourceFetchResult(
                source_name=self.source_name,
                status=SourceStatus.FAILED,
                started_at=datetime.now(UTC),
                completed_at=datetime.now(UTC),
                error_message=str(exc),
            )

    def _fetch_jobs(self) -> tuple[list[NormalizedJob], Mapping[str, Any]]:
        if not self._api_key:
            raise TavilyProviderError(
                "Tavily Search is not configured. Set TAVILY_API_KEY in the backend "
                "environment, then restart the API."
            )

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

        search_query = f'{ui_query} jobs "{ui_location}" apply'
        payload: dict[str, Any] = {
            "query": search_query,
            "search_depth": "basic",
            "topic": "general",
            "max_results": _MAX_RESULTS,
            "include_answer": False,
            "include_raw_content": "text",
            "include_images": False,
            "include_domains": list(_ATS_DOMAINS),
            "include_usage": True,
        }
        country = _country_from_location(ui_location)
        if country:
            payload["country"] = country

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        logger.info("TavilySearchSource: querying Tavily - %s", search_query)
        response = self._session.post(
            _TAVILY_SEARCH_URL,
            json=payload,
            headers=headers,
            timeout=_REQUEST_TIMEOUT,
        )
        _raise_for_tavily_error(response)

        data: dict[str, Any] = response.json()
        items = data.get("results") or []

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
                "TavilySearchSource returned 0 jobs for '%s' in '%s'.",
                ui_query,
                ui_location,
            )

        usage_payload = data.get("usage")
        usage = usage_payload if isinstance(usage_payload, dict) else {}
        return jobs, {
            "search_query": search_query,
            "fetched_count": len(jobs),
            "skipped_count": skipped,
            "response_time": data.get("response_time"),
            "request_id": data.get("request_id"),
            "credits": usage.get("credits"),
        }

    def _normalize_job(
        self,
        item: dict[str, Any],
        *,
        ui_query: str = "",
        ui_location: str = "",
    ) -> NormalizedJob | None:
        apply_url = as_text(item.get("url"))
        if not apply_url or not _is_known_ats_url(apply_url):
            return None

        title = as_text(item.get("title")) or "Unknown Title"
        content = as_text(item.get("raw_content")) or as_text(item.get("content")) or title
        company = _extract_company_from_url(apply_url) or "Direct ATS"
        source_job_id = sha256(apply_url.encode()).hexdigest()[:64]

        try:
            return NormalizedJob(
                source=self.source_name,
                source_job_id=source_job_id,
                company_name=company,
                title=title,
                location=ui_location,
                remote_type=infer_remote_type(content, title),
                posted_at=None,
                apply_url=cast(Any, apply_url),
                description=content,
                source_metadata={
                    "search_query": ui_query,
                    "search_location": ui_location,
                    "score": item.get("score"),
                    "provider": "tavily",
                },
                raw_payload=item,
            )
        except ValueError:
            return None


def _raise_for_tavily_error(response: TavilyHttpResponse) -> None:
    if 200 <= response.status_code < 300:
        return

    message = ""
    try:
        payload = response.json()
    except ValueError:
        payload = {}
    if isinstance(payload, dict):
        detail = payload.get("detail") or payload.get("error") or payload.get("message")
        message = as_text(detail)

    if response.status_code in (401, 403):
        detail = message or "Tavily rejected the API key."
        raise TavilyProviderError(
            f"Tavily Search authorization failed. {detail} "
            "Check TAVILY_API_KEY and restart the backend."
        )

    if response.status_code in (429, 432, 433):
        detail = message or "Tavily quota or rate limit was reached."
        raise TavilyProviderError(
            f"Tavily Search quota/rate limit reached. {detail} "
            "Wait for quota reset or upgrade the Tavily plan."
        )

    detail = f" {message}" if message else ""
    raise TavilyProviderError(f"Tavily Search request failed with HTTP {response.status_code}.{detail}")


def _country_from_location(location: str) -> str | None:
    normalized = location.casefold()
    if "india" in normalized:
        return "india"
    if "united states" in normalized or "usa" in normalized:
        return "united states"
    if "united kingdom" in normalized or "uk" in normalized:
        return "united kingdom"
    if "germany" in normalized:
        return "germany"
    if "singapore" in normalized:
        return "singapore"
    if "canada" in normalized:
        return "canada"
    return None


def _is_known_ats_url(url: str) -> bool:
    hostname = urlparse(url).hostname or ""
    return any(hostname == domain or hostname.endswith(f".{domain}") for domain in _ATS_DOMAINS)


def _extract_company_from_url(url: str) -> str | None:
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
