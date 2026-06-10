from __future__ import annotations

from typing import Any, Mapping

from backend.sources import SourceStatus
from backend.sources.tavily_search_source import TavilySearchSource


class FakeTavilyResponse:
    def __init__(self, status_code: int, payload: dict[str, Any]) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict[str, Any]:
        return self._payload


class FakeTavilySession:
    def __init__(self, response: FakeTavilyResponse) -> None:
        self.response = response
        self.json: Mapping[str, Any] | None = None
        self.headers: Mapping[str, str] | None = None

    def post(
        self,
        url: str,
        *,
        json: Mapping[str, Any],
        headers: Mapping[str, str],
        timeout: int,
    ) -> FakeTavilyResponse:
        self.json = json
        self.headers = headers
        return self.response

    def close(self) -> None:
        pass


def test_tavily_missing_credentials_fails_before_request() -> None:
    session = FakeTavilySession(FakeTavilyResponse(200, {"results": []}))
    source = TavilySearchSource(api_key="", http_session=session)

    result = source.fetch_jobs(query="Software Engineer", location="India")

    assert result.status == SourceStatus.FAILED
    assert "TAVILY_API_KEY" in (result.error_message or "")
    assert session.json is None


def test_tavily_auth_error_is_sanitized() -> None:
    source = TavilySearchSource(
        api_key="secret-key",
        http_session=FakeTavilySession(FakeTavilyResponse(401, {"detail": "Invalid API key"})),
    )

    result = source.fetch_jobs(query="Software Engineer", location="India")

    assert result.status == SourceStatus.FAILED
    assert "authorization failed" in (result.error_message or "")
    assert "secret-key" not in (result.error_message or "")
    assert "api.tavily.com" not in (result.error_message or "")


def test_tavily_returns_normalized_ats_jobs() -> None:
    session = FakeTavilySession(
        FakeTavilyResponse(
            200,
            {
                "results": [
                    {
                        "title": "Software Engineer - Acme",
                        "url": "https://jobs.lever.co/acme/123",
                        "content": "Build React and FastAPI features in India.",
                        "score": 0.91,
                    },
                    {
                        "title": "Aggregator result",
                        "url": "https://example.com/jobs/123",
                        "content": "Should be skipped.",
                    },
                ],
                "response_time": "0.42",
                "usage": {"credits": 1},
                "request_id": "req-1",
            },
        )
    )
    source = TavilySearchSource(api_key="test-key", http_session=session)

    result = source.fetch_jobs(query="Software Engineer", location="India")

    assert result.status == SourceStatus.SUCCESS
    assert len(result.jobs) == 1
    job = result.jobs[0]
    assert job.source == "tavily_search"
    assert job.company_name == "Acme"
    assert str(job.apply_url) == "https://jobs.lever.co/acme/123"
    assert job.location == "India"
    assert result.metadata["skipped_count"] == 1
    assert session.json is not None
    assert "jobs.lever.co" in session.json["include_domains"]
    assert session.headers is not None
    assert session.headers["Authorization"] == "Bearer test-key"
