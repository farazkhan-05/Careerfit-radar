from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from backend.services.deduplication_service import DeduplicationService
from backend.services.hard_filter_service import HardFilterConfig, HardFilterService


@dataclass
class FakeJob:
    title: str
    description: str
    company_id: UUID = field(default_factory=uuid4)
    id: UUID = field(default_factory=uuid4)
    canonical_job_id: UUID | None = None
    source: str = "greenhouse"
    source_job_id: str = field(default_factory=lambda: str(uuid4()))
    location: str | None = "Germany"
    remote_type: str | None = "remote"
    apply_url: str = field(
        default_factory=lambda: f"https://jobs.example.com/{uuid4()}"
    )
    status: str = "new"


def test_hard_filter_rejects_excluded_keywords_and_preserves_job_data() -> None:
    job = FakeJob(
        title="Senior Backend Engineer",
        description="Requires blockchain protocol experience.",
    )
    service = HardFilterService(
        HardFilterConfig(excluded_keywords=("blockchain",)),
    )

    result = service.filter_jobs([job])

    assert result.accepted_jobs == ()
    assert len(result.rejected_jobs) == 1
    assert result.rejected_jobs[0].filter_name == "excluded_keyword"
    assert result.rejected_jobs[0].to_schema().job_id == job.id
    assert job.status == "rejected"
    assert job.description == "Requires blockchain protocol experience."


def test_hard_filter_accepts_matching_job() -> None:
    job = FakeJob(
        title="Backend Engineer",
        description="Build APIs with Python. 3 years of experience preferred.",
        location="Germany",
        remote_type="remote",
    )
    service = HardFilterService(
        HardFilterConfig(
            excluded_keywords=("sales",),
            preferred_countries=("Germany",),
            preferred_work_modes=("remote",),
            maximum_experience_years=5,
            relocation_open=False,
            remote_open=True,
        ),
    )

    result = service.filter_jobs([job])

    assert result.accepted_jobs == (job,)
    assert result.rejected_jobs == ()
    assert job.status == "new"


def test_hard_filter_rejects_location_experience_and_visa_rules() -> None:
    location_job = FakeJob(
        title="Backend Engineer",
        description="Build services.",
        location="Canada",
    )
    experience_job = FakeJob(
        title="Backend Engineer",
        description="Minimum 8 years of experience building APIs.",
    )
    visa_job = FakeJob(
        title="Platform Engineer",
        description="Must be authorized to work without sponsorship.",
    )

    location_decision = HardFilterService(
        HardFilterConfig(preferred_countries=("Germany",), relocation_open=False)
    ).evaluate(location_job)
    experience_decision = HardFilterService(
        HardFilterConfig(maximum_experience_years=5)
    ).evaluate(experience_job)
    visa_decision = HardFilterService(
        HardFilterConfig(visa_sponsorship_required=True)
    ).evaluate(visa_job)

    assert location_decision is not None
    assert location_decision.filter_name == "location"
    assert experience_decision is not None
    assert experience_decision.filter_name == "experience"
    assert visa_decision is not None
    assert visa_decision.filter_name == "visa_sponsorship"


def test_deduplication_links_exact_duplicates_to_canonical_record() -> None:
    company_id = uuid4()
    canonical = FakeJob(
        company_id=company_id,
        title="Backend Engineer",
        description="Build Python APIs",
        apply_url="https://jobs.example.com/backend",
        source="greenhouse",
        source_job_id="123",
    )
    duplicate = FakeJob(
        company_id=company_id,
        title="Backend Engineer",
        description="Build Python APIs",
        apply_url="https://jobs.example.com/backend/",
        source="lever",
        source_job_id="456",
    )

    result = DeduplicationService().deduplicate([canonical, duplicate])

    assert result.canonical_jobs == (canonical,)
    assert len(result.duplicates) == 1
    assert result.duplicates[0].canonical_job_id == canonical.id
    assert result.duplicates[0].reason == "exact"
    assert duplicate.canonical_job_id == canonical.id
    assert duplicate.status == "duplicate"


def test_deduplication_links_fuzzy_duplicates_with_same_company() -> None:
    company_id = uuid4()
    canonical = FakeJob(
        company_id=company_id,
        title="Backend Software Engineer",
        description="Build and operate Python APIs for internal users.",
        location="Berlin",
    )
    duplicate = FakeJob(
        company_id=company_id,
        title="Backend Software Engineer",
        description="Build and operate Python API services for internal users.",
        location="Berlin, Germany",
    )

    result = DeduplicationService().deduplicate([canonical, duplicate])

    assert result.canonical_jobs == (canonical,)
    assert result.duplicates[0].reason == "fuzzy"
    assert duplicate.canonical_job_id == canonical.id


def test_deduplication_does_not_merge_different_companies() -> None:
    first = FakeJob(
        company_id=uuid4(),
        title="Backend Engineer",
        description="Build Python APIs",
    )
    second = FakeJob(
        company_id=uuid4(),
        title="Backend Engineer",
        description="Build Python APIs",
    )

    result = DeduplicationService().deduplicate([first, second])

    assert result.canonical_jobs == (first, second)
    assert result.duplicates == ()
    assert second.canonical_job_id is None
