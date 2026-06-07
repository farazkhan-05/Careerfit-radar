from __future__ import annotations

from typing import Any, Mapping

from backend.sources.base_source import (
    JobSource,
    NormalizedJob,
    as_text,
    infer_remote_type,
    parse_iso_datetime,
)


class SmartRecruitersSource(JobSource):
    source_name = "smartrecruiters"
    enabled = False

    def __init__(self, *, company_slug: str, enabled: bool = False, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.company_slug = company_slug
        self.enabled = enabled

    def _fetch_jobs(self) -> tuple[list[NormalizedJob], Mapping[str, Any]]:
        url = f"https://api.smartrecruiters.com/v1/companies/{self.company_slug}/postings"
        response = self._client.get(url)
        response.raise_for_status()
        payload = response.json()
        raw_jobs = payload.get("content") or []
        jobs = [
            self._normalize_job(raw_job)
            for raw_job in raw_jobs
            if raw_job.get("id") and raw_job.get("name") and raw_job.get("applyUrl")
        ]
        return jobs, {
            "company_slug": self.company_slug,
            "fetched_count": len(jobs),
            "provider_url": url,
            "enabled": self.enabled,
        }

    def _normalize_job(self, raw_job: dict[str, Any]) -> NormalizedJob:
        location_payload = raw_job.get("location") or {}
        location = as_text(location_payload.get("city") or location_payload.get("country")) or None
        sections = raw_job.get("jobAd", {}).get("sections", {})
        return NormalizedJob(
            source=self.source_name,
            source_job_id=str(raw_job["id"]),
            company_name=self.company_slug,
            title=as_text(raw_job["name"]),
            location=location,
            remote_type=infer_remote_type(location, raw_job.get("name")),
            posted_at=parse_iso_datetime(raw_job.get("releasedDate")),
            apply_url=raw_job["applyUrl"],
            description=as_text(sections.get("jobDescription")) or as_text(raw_job["name"]),
            source_metadata={
                "company_slug": self.company_slug,
                "location": location_payload,
            },
            raw_payload=raw_job,
        )
