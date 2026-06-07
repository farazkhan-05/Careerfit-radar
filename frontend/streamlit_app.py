from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx
import streamlit as st

DEFAULT_API_URL = "http://localhost:8000"
PAGE_SIZE = 25


@dataclass(frozen=True)
class ApiResult:
    ok: bool
    data: Any
    error: str | None = None


class ApiClient:
    def __init__(self, base_url: str, *, timeout_seconds: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def get(self, path: str, params: dict[str, Any] | None = None) -> ApiResult:
        try:
            response = httpx.get(
                self._url(path),
                params={key: value for key, value in (params or {}).items() if value not in (None, "")},
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            return ApiResult(ok=False, data=None, error=str(exc))
        if response.headers.get("content-type", "").startswith("text/csv"):
            return ApiResult(ok=True, data=response.text)
        return ApiResult(ok=True, data=response.json())

    def _url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"


def get_default_api_url() -> str:
    return os.getenv("CAREERFIT_API_URL", DEFAULT_API_URL).rstrip("/")


def page_items(page: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not page:
        return []
    items = page.get("items", [])
    return [item for item in items if isinstance(item, dict)]


def metric_value(items: list[dict[str, Any]], key: str, value: str) -> int:
    return sum(1 for item in items if str(item.get(key, "")).casefold() == value.casefold())


def compact_job_rows(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "Title": job.get("title", ""),
            "Source": job.get("source", ""),
            "Location": job.get("location", ""),
            "Mode": job.get("remote_type", ""),
            "Status": job.get("status", ""),
            "Apply": job.get("apply_url", ""),
        }
        for job in jobs
    ]


def render_page_header(title: str) -> None:
    st.markdown(f"### {title}")


def render_error(result: ApiResult) -> None:
    if not result.ok:
        st.error(result.error or "Request failed.")


def fetch_page(client: ApiClient, path: str, params: dict[str, Any] | None = None) -> ApiResult:
    merged = {"limit": PAGE_SIZE, "offset": 0, **(params or {})}
    return client.get(path, merged)


def render_dashboard(client: ApiClient) -> None:
    render_page_header("Dashboard")
    jobs_result = fetch_page(client, "/jobs")
    workflows_result = fetch_page(client, "/workflows")
    applications_result = fetch_page(client, "/applications")
    for result in (jobs_result, workflows_result, applications_result):
        render_error(result)

    jobs = page_items(jobs_result.data if jobs_result.ok else None)
    workflows = page_items(workflows_result.data if workflows_result.ok else None)
    applications = page_items(applications_result.data if applications_result.ok else None)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Jobs", len(jobs))
    col2.metric("Saved", metric_value(applications, "status", "saved"))
    col3.metric("Applied", metric_value(applications, "status", "applied"))
    col4.metric("Workflow Runs", len(workflows))

    st.divider()
    st.markdown("#### Recent Jobs")
    st.dataframe(compact_job_rows(jobs), use_container_width=True, hide_index=True)

    st.markdown("#### Recent Workflows")
    st.dataframe(
        [
            {
                "Run": workflow.get("run_id", ""),
                "Status": workflow.get("status", ""),
                "Started": workflow.get("started_at", ""),
                "Completed": workflow.get("completed_at", ""),
            }
            for workflow in workflows
        ],
        use_container_width=True,
        hide_index=True,
    )


def render_job_detail(client: ApiClient) -> None:
    render_page_header("Job Detail")
    status = st.selectbox("Status", ["", "new", "duplicate", "rejected", "saved"], index=0)
    source = st.text_input("Source")
    query = st.text_input("Search")
    result = fetch_page(client, "/jobs", {"status": status, "source": source, "q": query})
    render_error(result)
    jobs = page_items(result.data if result.ok else None)
    st.dataframe(compact_job_rows(jobs), use_container_width=True, hide_index=True)

    selected = st.selectbox(
        "Selected Job",
        [job.get("id", "") for job in jobs],
        format_func=lambda job_id: next((job.get("title", job_id) for job in jobs if job.get("id") == job_id), job_id),
    ) if jobs else None
    if selected:
        job_result = client.get(f"/jobs/{selected}")
        render_error(job_result)
        if job_result.ok:
            job = job_result.data
            st.markdown(f"#### {job.get('title', '')}")
            st.write(job.get("description", ""))
            st.link_button("Open Apply Link", job.get("apply_url", DEFAULT_API_URL))


def render_resume_profile(client: ApiClient) -> None:
    render_page_header("Resume Profile")
    resumes_result = fetch_page(client, "/resumes")
    profiles_result = fetch_page(client, "/profiles")
    render_error(resumes_result)
    render_error(profiles_result)

    resumes = page_items(resumes_result.data if resumes_result.ok else None)
    profiles = page_items(profiles_result.data if profiles_result.ok else None)
    left, right = st.columns(2)
    with left:
        st.markdown("#### Resumes")
        st.dataframe(
            [
                {
                    "File": resume.get("file_name", ""),
                    "Type": resume.get("content_type", ""),
                    "Hash": resume.get("text_hash", ""),
                }
                for resume in resumes
            ],
            use_container_width=True,
            hide_index=True,
        )
    with right:
        st.markdown("#### Profiles")
        st.dataframe(
            [
                {
                    "Roles": ", ".join(profile.get("target_roles", [])),
                    "Experience": profile.get("experience_years", ""),
                    "Resume": profile.get("resume_id", ""),
                }
                for profile in profiles
            ],
            use_container_width=True,
            hide_index=True,
        )


def render_application_tracker(client: ApiClient) -> None:
    render_page_header("Application Tracker")
    status = st.selectbox("Application Status", ["", "saved", "applied", "interview", "offer", "rejected"], index=0)
    result = fetch_page(client, "/applications", {"status": status})
    render_error(result)
    applications = page_items(result.data if result.ok else None)
    st.dataframe(
        [
            {
                "Job": application.get("job_id", ""),
                "Status": application.get("status", ""),
                "Applied": application.get("applied_at", ""),
                "Follow Up": application.get("follow_up_at", ""),
                "Notes": application.get("notes", ""),
            }
            for application in applications
        ],
        use_container_width=True,
        hide_index=True,
    )


def render_source_health(client: ApiClient) -> None:
    render_page_header("Source Health")
    source_name = st.text_input("Source Name")
    status = st.selectbox("Run Status", ["", "success", "failed", "disabled"], index=0)
    result = fetch_page(client, "/sources/runs", {"source_name": source_name, "status": status})
    render_error(result)
    runs = page_items(result.data if result.ok else None)
    st.dataframe(
        [
            {
                "Source": run.get("source_name", ""),
                "Status": run.get("status", ""),
                "Fetched": run.get("jobs_fetched", 0),
                "Stored": run.get("jobs_stored", 0),
                "Started": run.get("started_at", ""),
                "Completed": run.get("completed_at", ""),
                "Error": run.get("error_message", ""),
            }
            for run in runs
        ],
        use_container_width=True,
        hide_index=True,
    )


def render_settings(client: ApiClient) -> None:
    render_page_header("Settings")
    ready = client.get("/health/ready")
    live = client.get("/health/live")
    render_error(ready)
    render_error(live)

    col1, col2 = st.columns(2)
    col1.metric("API", "Online" if live.ok else "Unavailable")
    readiness = ready.data.get("status", "unknown") if ready.ok and isinstance(ready.data, dict) else "unknown"
    col2.metric("Readiness", readiness)

    if ready.ok:
        st.json(ready.data)

    jobs_csv = client.get("/exports/jobs.csv")
    applications_csv = client.get("/exports/applications.csv")
    if jobs_csv.ok:
        st.download_button("Download Jobs CSV", jobs_csv.data, "jobs.csv", "text/csv")
    if applications_csv.ok:
        st.download_button("Download Applications CSV", applications_csv.data, "applications.csv", "text/csv")


def main() -> None:
    st.set_page_config(page_title="CareerFit Radar", layout="wide")
    st.title("CareerFit Radar")

    with st.sidebar:
        api_url = st.text_input("API Endpoint", value=get_default_api_url())
        page = st.radio(
            "Navigation",
            [
                "Dashboard",
                "Job Detail",
                "Resume Profile",
                "Application Tracker",
                "Source Health",
                "Settings",
            ],
        )

    client = ApiClient(api_url)
    if page == "Dashboard":
        render_dashboard(client)
    elif page == "Job Detail":
        render_job_detail(client)
    elif page == "Resume Profile":
        render_resume_profile(client)
    elif page == "Application Tracker":
        render_application_tracker(client)
    elif page == "Source Health":
        render_source_health(client)
    else:
        render_settings(client)


if __name__ == "__main__":
    main()
