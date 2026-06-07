from __future__ import annotations

from typing import Any, Mapping

from backend.sources.base_source import (
    JobSource,
    NormalizedJob,
    as_text,
    infer_remote_type,
    parse_iso_datetime,
)


class RemotiveSource(JobSource):
    source_name = "remotive"

    def __init__(self, *, search: str | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search = search

    def _fetch_jobs(self) -> tuple[list[NormalizedJob], Mapping[str, Any]]:
        url = "https://remotive.com/api/remote-jobs"
        params = {"search": self.search} if self.search else None
        response = self._client.get(url, params=params)
        response.raise_for_status()
        payload = response.json()
        jobs = [
            self._normalize_job(raw_job)
            for raw_job in payload.get("jobs", [])
            if raw_job.get("id") and raw_job.get("title") and raw_job.get("url")
        ]
        return jobs, {
            "search": self.search,
            "fetched_count": len(jobs),
            "provider_url": url,
        }

    def _normalize_job(self, raw_job: dict[str, Any]) -> NormalizedJob:
        location = as_text(raw_job.get("candidate_required_location")) or "Remote"
        return NormalizedJob(
            source=self.source_name,
            source_job_id=str(raw_job["id"]),
            company_name=as_text(raw_job.get("company_name")) or "Unknown",
            title=as_text(raw_job["title"]),
            location=location,
            remote_type=infer_remote_type(location, "remote"),
            posted_at=parse_iso_datetime(raw_job.get("publication_date")),
            apply_url=raw_job["url"],
            description=as_text(raw_job.get("description") or raw_job["title"]),
            source_metadata={
                "category": as_text(raw_job.get("category")) or None,
                "salary": as_text(raw_job.get("salary")) or None,
                "tags": raw_job.get("tags") or [],
            },
            raw_payload=raw_job,
        )
