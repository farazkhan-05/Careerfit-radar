from __future__ import annotations

from typing import Any, Mapping

from backend.sources.base_source import JobSource, NormalizedJob, as_text, infer_remote_type


class GreenhouseSource(JobSource):
    source_name = "greenhouse"

    def __init__(self, *, board_token: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.board_token = board_token

    def _fetch_jobs(self) -> tuple[list[NormalizedJob], Mapping[str, Any]]:
        url = f"https://boards-api.greenhouse.io/v1/boards/{self.board_token}/jobs"
        response = self._client.get(url, params={"content": "true"})
        response.raise_for_status()
        payload = response.json()
        jobs = [
            self._normalize_job(raw_job)
            for raw_job in payload.get("jobs", [])
            if raw_job.get("id") and raw_job.get("title") and raw_job.get("absolute_url")
        ]
        return jobs, {
            "board_token": self.board_token,
            "fetched_count": len(jobs),
            "provider_url": url,
        }

    def _normalize_job(self, raw_job: dict[str, Any]) -> NormalizedJob:
        offices = raw_job.get("offices") or []
        locations = [
            as_text(office.get("name"))
            for office in offices
            if isinstance(office, dict) and office.get("name")
        ]
        departments = raw_job.get("departments") or []
        department_names = [
            as_text(department.get("name"))
            for department in departments
            if isinstance(department, dict) and department.get("name")
        ]
        location = ", ".join(locations) or None
        return NormalizedJob(
            source=self.source_name,
            source_job_id=str(raw_job["id"]),
            company_name=self.board_token,
            title=as_text(raw_job["title"]),
            location=location,
            remote_type=infer_remote_type(location, raw_job.get("title")),
            posted_at=None,
            apply_url=raw_job["absolute_url"],
            description=as_text(raw_job.get("content") or raw_job.get("title")),
            source_metadata={
                "board_token": self.board_token,
                "department_names": department_names,
                "location_names": locations,
            },
            raw_payload=raw_job,
        )
