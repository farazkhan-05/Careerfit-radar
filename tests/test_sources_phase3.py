from __future__ import annotations

from typing import Any, Mapping

from backend.sources import SmartRecruitersSource, SourceStatus, TavilySearchSource


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


def test_tavily_returns_normalized_jobs_from_approved_ats_domains() -> None:
    session = FakeTavilySession(
        FakeTavilyResponse(
            200,
            {
                "results": [
                    {
                        "title": "Frontend Engineer - Acme",
                        "url": "https://jobs.lever.co/acme/123",
                        "content": "Build React features in Bengaluru.",
                        "score": 0.92,
                    },
                    {
                        "title": "Aggregator result",
                        "url": "https://example.com/jobs/123",
                        "content": "Should be skipped.",
                    },
                ],
                "usage": {"credits": 1},
                "request_id": "req-1",
            },
        )
    )
    source = TavilySearchSource(api_key="test-token", http_session=session)

    result = source.fetch_jobs(query="Frontend Engineer", location="Bengaluru, India")

    assert result.status == SourceStatus.SUCCESS
    assert len(result.jobs) == 1
    job = result.jobs[0]
    assert job.source == "tavily_search"
    assert job.company_name == "Acme"
    assert job.title == "Frontend Engineer - Acme"
    assert str(job.apply_url) == "https://jobs.lever.co/acme/123"
    assert job.location == "Bengaluru, India"
    assert result.metadata["skipped_count"] == 1
    assert session.json is not None
    assert "jobs.lever.co" in session.json["include_domains"]


def test_tavily_missing_token_is_handled_safely() -> None:
    source = TavilySearchSource(api_key="")

    result = source.fetch_jobs(query="Software Engineer", location="India")

    assert result.status == SourceStatus.FAILED
    assert result.jobs == ()
    assert "TAVILY_API_KEY" in (result.error_message or "")


def test_smartrecruiters_is_disabled_by_default() -> None:
    source = SmartRecruitersSource(company_slug="acme")

    result = source.fetch_jobs()

    assert result.status == SourceStatus.DISABLED
    assert result.jobs == ()
    assert result.metadata["enabled"] is False
