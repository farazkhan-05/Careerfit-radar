from __future__ import annotations

from typing import Any, Mapping

from backend.sources.base_source import (
    JobSource,
    NormalizedJob,
    as_text,
    infer_remote_type,
    parse_iso_datetime,
)


class ArbeitnowSource(JobSource):
    source_name = "arbeitnow"

    def _fetch_jobs(self) -> tuple[list[NormalizedJob], Mapping[str, Any]]:
        url = "https://www.arbeitnow.com/api/job-board-api"
        response = self._client.get(url)
        response.raise_for_status()
        payload = response.json()
        jobs = [
            self._normalize_job(raw_job)
            for raw_job in payload.get("data", [])
            if raw_job.get("slug") and raw_job.get("title") and raw_job.get("url")
        ]
        return jobs, {
            "fetched_count": len(jobs),
            "provider_url": url,
            "links": payload.get("links") or {},
            "meta": payload.get("meta") or {},
        }

    def _normalize_job(self, raw_job: dict[str, Any]) -> NormalizedJob:
        location = as_text(raw_job.get("location")) or None
        tags = raw_job.get("tags") or []
        return NormalizedJob(
            source=self.source_name,
            source_job_id=str(raw_job["slug"]),
            company_name=as_text(raw_job.get("company_name")) or "Unknown",
            title=as_text(raw_job["title"]),
            location=location,
            remote_type=infer_remote_type(location, " ".join(str(tag) for tag in tags)),
            posted_at=parse_iso_datetime(raw_job.get("created_at")),
            apply_url=raw_job["url"],
            description=as_text(raw_job.get("description") or raw_job["title"]),
            source_metadata={
                "tags": tags,
                "job_types": raw_job.get("job_types") or [],
            },
            raw_payload=raw_job,
        )
