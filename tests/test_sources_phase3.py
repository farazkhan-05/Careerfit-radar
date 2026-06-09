from __future__ import annotations

from typing import Any, Mapping

from backend.sources import ApifySource, SmartRecruitersSource, SourceStatus


class FakeActorClient:
    def __init__(self, dataset_id: str, run_id: str = "run-1") -> None:
        self.dataset_id = dataset_id
        self.run_id = run_id
        self.actor_id: str | None = None
        self.run_input: Mapping[str, Any] | None = None
        self.call_kwargs: dict[str, Any] = {}

    def call(self, *, run_input: Mapping[str, Any], **kwargs: Any) -> dict[str, str]:
        self.run_input = run_input
        self.call_kwargs = kwargs
        return {"id": self.run_id, "defaultDatasetId": self.dataset_id}


class FakeDatasetClient:
    def __init__(self, items: list[dict[str, Any]]) -> None:
        self.items = items
        self.iterate_kwargs: dict[str, Any] = {}

    def iterate_items(self, **kwargs: Any) -> list[dict[str, Any]]:
        self.iterate_kwargs = kwargs
        return self.items


class FakeApifyClient:
    def __init__(self, items: list[dict[str, Any]]) -> None:
        self.actor_client = FakeActorClient("dataset-1")
        self.dataset_client = FakeDatasetClient(items)

    def actor(self, actor_id: str) -> FakeActorClient:
        self.actor_client.actor_id = actor_id
        return self.actor_client

    def dataset(self, dataset_id: str) -> FakeDatasetClient:
        return self.dataset_client


def test_apify_returns_normalized_jobs_from_realistic_payload() -> None:
    source = ApifySource(
        api_token="test-token",
        apify_client=FakeApifyClient(
            [
                {
                    "id": "linkedin-1",
                    "site": "linkedin",
                    "title": "Associate Software Engineer",
                    "companyName": "Acme India",
                    "location": "Lucknow, Uttar Pradesh, India",
                    "applyUrl": "https://example.com/jobs/linkedin-1",
                    "descriptionText": "Build frontend and API features with React.",
                    "postedAt": "2026-01-01T12:00:00Z",
                    "job_type": "fulltime",
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
    assert job.source_job_id == "linkedin-1"
    assert job.company_name == "Acme India"
    assert job.title == "Associate Software Engineer"
    assert job.location == "Lucknow, Uttar Pradesh, India"
    assert str(job.apply_url) == "https://example.com/jobs/linkedin-1"
    assert job.description == "Build frontend and API features with React."
    assert job.posted_at is not None
    assert job.source_metadata["platform"] == "linkedin"
    assert result.metadata["actor_id"] == "valig/linkedin-jobs-scraper"
    assert result.metadata["dataset_id"] == "dataset-1"
    assert result.metadata["run_id"] == "run-1"


def test_apify_normalize_job_maps_required_schema_fields_without_fetching() -> None:
    source = ApifySource(api_token="test-token", apify_client=FakeApifyClient([]))

    job = source._normalize_job(
        {
            "jobId": "linkedin-frontend-1",
            "site": "linkedin",
            "title": "Front End Developer",
            "companyName": "Example Labs",
            "city": "Lucknow",
            "state": "Uttar Pradesh",
            "country": "India",
            "applyUrl": "https://example.com/apply/frontend",
            "descriptionText": "Build accessible product screens.",
            "postedAt": "2026-01-02T09:30:00Z",
            "remoteType": "Hybrid",
            "search_query": "Front End Developer",
        }
    )

    assert job is not None
    assert job.source == "apify"
    assert job.source_job_id == "linkedin-frontend-1"
    assert job.company_name == "Example Labs"
    assert job.title == "Front End Developer"
    assert job.location == "Lucknow, Uttar Pradesh, India"
    assert job.remote_type == "hybrid"
    assert str(job.apply_url) == "https://example.com/apply/frontend"
    assert job.description == "Build accessible product screens."
    assert job.posted_at is not None
    assert job.source_metadata["platform"] == "linkedin"
    assert job.raw_payload["jobId"] == "linkedin-frontend-1"


def test_apify_builds_india_full_time_search_payload() -> None:
    fake_client = FakeApifyClient([])
    source = ApifySource(api_token="test-token", apify_client=fake_client)

    result = source.fetch_jobs()

    assert result.status == SourceStatus.SUCCESS
    run_input = fake_client.actor_client.run_input
    assert run_input is not None
    assert run_input["title"] == "Software Engineer"
    assert run_input["location"] == "India"
    assert run_input["datePosted"] == "r604800"
    assert run_input["experienceLevel"] == ["1", "2"]
    assert run_input["limit"] == 50
    assert fake_client.actor_client.actor_id == "valig/linkedin-jobs-scraper"
    assert fake_client.actor_client.call_kwargs["wait_duration"].total_seconds() == 120
    assert fake_client.dataset_client.iterate_kwargs["clean"] is True
    assert fake_client.dataset_client.iterate_kwargs["limit"] == 50


def test_apify_accepts_dynamic_search_payload() -> None:
    fake_client = FakeApifyClient([])
    source = ApifySource(api_token="test-token", apify_client=fake_client)

    result = source.fetch_jobs(query="React Engineer", location="Bengaluru, India")

    assert result.status == SourceStatus.SUCCESS
    run_input = fake_client.actor_client.run_input
    assert run_input is not None
    assert run_input["title"] == "React Engineer"
    assert run_input["location"] == "Bengaluru, India"


def test_apify_accepts_workflow_state_search_payload() -> None:
    fake_client = FakeApifyClient([])
    source = ApifySource(api_token="test-token", apify_client=fake_client)

    result = source.fetch_jobs(state={"search": {"query": "Data Analyst", "location": "Pune, India"}})

    assert result.status == SourceStatus.SUCCESS
    run_input = fake_client.actor_client.run_input
    assert run_input is not None
    assert run_input["title"] == "Data Analyst"
    assert run_input["location"] == "Pune, India"


def test_apify_normalize_job_uses_valig_fallback_fields() -> None:
    source = ApifySource(api_token="test-token", apify_client=FakeApifyClient([]))

    job = source._normalize_job(
        {
            "id": "linkedin-fallback-1",
            "company": "Fallback Co",
            "link": "https://www.linkedin.com/jobs/view/linkedin-fallback-1",
            "descriptionHtml": "<p>Fallback description</p>",
            "date": "2026-01-03T08:00:00Z",
        }
    )

    assert job is not None
    assert job.title == "Unknown Title"
    assert job.company_name == "Fallback Co"
    assert str(job.apply_url) == "https://www.linkedin.com/jobs/view/linkedin-fallback-1"
    assert job.description == "<p>Fallback description</p>"
    assert job.posted_at is not None


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
