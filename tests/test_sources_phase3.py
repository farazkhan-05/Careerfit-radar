from __future__ import annotations

from typing import Any, Mapping

from backend.sources import ApifySource, SmartRecruitersSource, SourceStatus


class FakeActorClient:
    def __init__(self, dataset_id: str) -> None:
        self.dataset_id = dataset_id
        self.run_input: Mapping[str, Any] | None = None

    def call(self, *, run_input: Mapping[str, Any], **kwargs: Any) -> dict[str, str]:
        self.run_input = run_input
        return {"id": "run-1", "defaultDatasetId": self.dataset_id}


class FakeDatasetClient:
    def __init__(self, items: list[dict[str, Any]]) -> None:
        self.items = items

    def iterate_items(self, **kwargs: Any) -> list[dict[str, Any]]:
        return self.items


class FakeApifyClient:
    def __init__(self, items: list[dict[str, Any]]) -> None:
        self.actor_client = FakeActorClient("dataset-1")
        self.dataset_client = FakeDatasetClient(items)

    def actor(self, actor_id: str) -> FakeActorClient:
        return self.actor_client

    def dataset(self, dataset_id: str) -> FakeDatasetClient:
        return self.dataset_client


def test_apify_returns_normalized_jobs() -> None:
    source = ApifySource(
        api_token="test-token",
        apify_client=FakeApifyClient(
            [
                {
                    "id": "indeed-1",
                    "title": "Associate Software Engineer",
                    "companyName": "Acme",
                    "location": "Lucknow, Uttar Pradesh",
                    "jobUrl": "https://example.com/jobs/indeed-1",
                    "description": "Build frontend and API features.",
                    "datePosted": "2026-01-01T12:00:00Z",
                    "jobType": "Full-time",
                    "platform": "indeed",
                    "searchQuery": "Associate Software Engineer",
                    "searchLocation": "Lucknow, Uttar Pradesh",
                }
            ]
        ),
    )

    result = source.fetch_jobs()

    assert result.status == SourceStatus.SUCCESS
    assert len(result.jobs) == 1
    job = result.jobs[0]
    assert job.source == "apify"
    assert job.source_job_id == "indeed-1"
    assert job.company_name == "Acme"
    assert job.title == "Associate Software Engineer"
    assert job.location == "Lucknow, Uttar Pradesh"
    assert job.posted_at is not None
    assert job.source_metadata["platform"] == "indeed"
    assert result.metadata["actor_id"] == "openclawai/job-board-scraper"


def test_apify_builds_india_full_time_search_payload() -> None:
    fake_client = FakeApifyClient([])
    source = ApifySource(api_token="test-token", apify_client=fake_client)

    result = source.fetch_jobs()

    assert result.status == SourceStatus.SUCCESS
    run_input = fake_client.actor_client.run_input
    assert run_input is not None
    searches = run_input["searchTerms"]
    assert {"Associate Software Engineer", "Front End Developer"} == {
        search for search in searches
    }
    assert run_input["sites"] == ["linkedin", "indeed"]
    assert run_input["location"] == "Lucknow, Uttar Pradesh, India"
    assert run_input["countryIndeed"] == "india"
    assert run_input["jobType"] == "fulltime"
    assert run_input["distance"] == 50


def test_apify_missing_token_is_handled_safely() -> None:
    source = ApifySource(api_token="")

    result = source.fetch_jobs()

    assert result.status == SourceStatus.FAILED
    assert result.jobs == ()
    assert "APIFY_API_TOKEN" in (result.error_message or "")


def test_apify_skips_incomplete_items() -> None:
    source = ApifySource(
        api_token="test-token",
        apify_client=FakeApifyClient(
            [
                {"title": "Missing URL", "companyName": "Acme"},
                {
                    "title": "Front End Developer",
                    "companyName": "Acme",
                    "url": "https://example.com/jobs/frontend",
                },
            ]
        ),
    )

    result = source.fetch_jobs()

    assert result.status == SourceStatus.SUCCESS
    assert len(result.jobs) == 1
    assert result.metadata["skipped_count"] == 1


def test_smartrecruiters_is_disabled_by_default() -> None:
    source = SmartRecruitersSource(company_slug="acme")

    result = source.fetch_jobs()

    assert result.status == SourceStatus.DISABLED
    assert result.jobs == ()
    assert result.metadata["enabled"] is False
