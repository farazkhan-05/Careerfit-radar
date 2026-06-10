from __future__ import annotations

from typing import Any, Mapping

from backend.sources import SourceStatus
from backend.sources.google_search_source import GoogleSearchSource


class FakeGoogleResponse:
    def __init__(self, status_code: int, payload: dict[str, Any]) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict[str, Any]:
        return self._payload


class FakeGoogleSession:
    def __init__(self, response: FakeGoogleResponse) -> None:
        self.response = response
        self.params: Mapping[str, Any] | None = None

    def get(self, url: str, *, params: Mapping[str, Any], timeout: int) -> FakeGoogleResponse:
        self.params = params
        return self.response

    def close(self) -> None:
        pass


def test_google_search_missing_credentials_fails_before_request() -> None:
    session = FakeGoogleSession(FakeGoogleResponse(200, {"items": []}))
    source = GoogleSearchSource(api_key="", engine_id="", http_session=session)

    result = source.fetch_jobs(query="Software Engineer", location="India")

    assert result.status == SourceStatus.FAILED
    assert "GOOGLE_SEARCH_API_KEY" in (result.error_message or "")
    assert session.params is None


def test_google_search_forbidden_error_is_sanitized() -> None:
    source = GoogleSearchSource(
        api_key="secret-key",
        engine_id="engine-id",
        http_session=FakeGoogleSession(
            FakeGoogleResponse(
                403,
                {
                    "error": {
                        "status": "PERMISSION_DENIED",
                        "message": "This project does not have the access to Custom Search JSON API.",
                        "errors": [{"reason": "forbidden"}],
                    }
                },
            )
        ),
    )

    result = source.fetch_jobs(query="Software Engineer", location="India")

    assert result.status == SourceStatus.FAILED
    assert "Custom Search JSON API" in (result.error_message or "")
    assert "secret-key" not in (result.error_message or "")
    assert "googleapis.com" not in (result.error_message or "")
