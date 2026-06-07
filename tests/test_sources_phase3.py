from __future__ import annotations

import httpx

from backend.sources import (
    ArbeitnowSource,
    GreenhouseSource,
    LeverSource,
    RemotiveSource,
    SmartRecruitersSource,
    SourceStatus,
)


def _client(response_payload: object, status_code: int = 200) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json=response_payload, request=request)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_greenhouse_returns_normalized_jobs() -> None:
    source = GreenhouseSource(
        board_token="acme",
        client=_client(
            {
                "jobs": [
                    {
                        "id": 123,
                        "title": "Backend Engineer",
                        "absolute_url": "https://boards.greenhouse.io/acme/jobs/123",
                        "content": "<p>Build APIs</p>",
                        "offices": [{"name": "Remote"}],
                        "departments": [{"name": "Engineering"}],
                    }
                ]
            }
        ),
    )

    result = source.fetch_jobs()

    assert result.status == SourceStatus.SUCCESS
    assert len(result.jobs) == 1
    job = result.jobs[0]
    assert job.source == "greenhouse"
    assert job.source_job_id == "123"
    assert job.company_name == "acme"
    assert job.remote_type == "remote"
    assert job.source_metadata["department_names"] == ["Engineering"]


def test_lever_returns_normalized_jobs() -> None:
    source = LeverSource(
        company_slug="acme",
        client=_client(
            [
                {
                    "id": "abc",
                    "text": "Data Engineer",
                    "hostedUrl": "https://jobs.lever.co/acme/abc",
                    "descriptionPlain": "Own data pipelines",
                    "createdAt": 1767225600000,
                    "categories": {
                        "location": "Berlin",
                        "team": "Engineering",
                        "commitment": "Full-time",
                    },
                }
            ]
        ),
    )

    result = source.fetch_jobs()

    assert result.status == SourceStatus.SUCCESS
    assert result.jobs[0].source == "lever"
    assert result.jobs[0].posted_at is not None
    assert result.jobs[0].location == "Berlin"


def test_remotive_returns_normalized_jobs() -> None:
    source = RemotiveSource(
        search="python",
        client=_client(
            {
                "jobs": [
                    {
                        "id": 99,
                        "title": "Python Developer",
                        "url": "https://remotive.com/remote-jobs/software-dev/python-developer-99",
                        "company_name": "Acme",
                        "candidate_required_location": "Worldwide",
                        "publication_date": "2026-01-01T12:00:00Z",
                        "description": "Build services",
                        "tags": ["python"],
                    }
                ]
            }
        ),
    )

    result = source.fetch_jobs()

    assert result.status == SourceStatus.SUCCESS
    assert result.jobs[0].source == "remotive"
    assert result.jobs[0].remote_type == "remote"
    assert result.metadata["search"] == "python"


def test_arbeitnow_returns_normalized_jobs() -> None:
    source = ArbeitnowSource(
        client=_client(
            {
                "data": [
                    {
                        "slug": "backend-engineer-acme",
                        "title": "Backend Engineer",
                        "url": "https://www.arbeitnow.com/jobs/companies/acme/backend-engineer",
                        "company_name": "Acme",
                        "location": "Germany",
                        "created_at": "2026-01-01T12:00:00Z",
                        "description": "Build APIs",
                        "tags": ["remote"],
                        "job_types": ["full-time"],
                    }
                ],
                "links": {},
                "meta": {},
            }
        ),
    )

    result = source.fetch_jobs()

    assert result.status == SourceStatus.SUCCESS
    assert result.jobs[0].source == "arbeitnow"
    assert result.jobs[0].remote_type == "remote"
    assert result.jobs[0].source_metadata["job_types"] == ["full-time"]


def test_network_failures_are_handled_safely() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection failed", request=request)

    source = RemotiveSource(client=httpx.Client(transport=httpx.MockTransport(handler)))

    result = source.fetch_jobs()

    assert result.status == SourceStatus.FAILED
    assert result.jobs == ()
    assert "connection failed" in (result.error_message or "")


def test_smartrecruiters_is_disabled_by_default() -> None:
    source = SmartRecruitersSource(company_slug="acme", client=_client({}))

    result = source.fetch_jobs()

    assert result.status == SourceStatus.DISABLED
    assert result.jobs == ()
    assert result.metadata["enabled"] is False
