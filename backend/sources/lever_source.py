from __future__ import annotations

from typing import Any, Mapping

from backend.sources.base_source import (
    JobSource,
    NormalizedJob,
    as_text,
    infer_remote_type,
    parse_timestamp_millis,
)


class LeverSource(JobSource):
    source_name = "lever"

    def __init__(self, *, company_slug: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.company_slug = company_slug

    def _fetch_jobs(self) -> tuple[list[NormalizedJob], Mapping[str, Any]]:
        url = f"https://api.lever.co/v0/postings/{self.company_slug}"
        response = self._client.get(url, params={"mode": "json"})
        response.raise_for_status()
        payload = response.json()
        jobs = [
            self._normalize_job(raw_job)
            for raw_job in payload
            if raw_job.get("id") and raw_job.get("text") and raw_job.get("hostedUrl")
        ]
        return jobs, {
            "company_slug": self.company_slug,
            "fetched_count": len(jobs),
            "provider_url": url,
        }

    def _normalize_job(self, raw_job: dict[str, Any]) -> NormalizedJob:
        categories = raw_job.get("categories") or {}
        location = as_text(categories.get("location")) or None
        commitment = as_text(categories.get("commitment")) or None
        team = as_text(categories.get("team")) or None
        description = "\n".join(
            section
            for section in [
                as_text(raw_job.get("descriptionPlain") or raw_job.get("description")),
                as_text(raw_job.get("additionalPlain") or raw_job.get("additional")),
            ]
            if section
        )
        return NormalizedJob(
            source=self.source_name,
            source_job_id=str(raw_job["id"]),
            company_name=self.company_slug,
            title=as_text(raw_job["text"]),
            location=location,
            remote_type=infer_remote_type(location, commitment, team),
            posted_at=parse_timestamp_millis(raw_job.get("createdAt")),
            apply_url=raw_job["hostedUrl"],
            description=description or as_text(raw_job["text"]),
            source_metadata={
                "company_slug": self.company_slug,
                "team": team,
                "commitment": commitment,
            },
            raw_payload=raw_job,
        )
