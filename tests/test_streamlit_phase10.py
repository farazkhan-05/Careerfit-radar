from __future__ import annotations

from frontend.streamlit_app import ApiClient, compact_job_rows, metric_value, page_items


def test_api_client_builds_stable_urls() -> None:
    client = ApiClient("http://localhost:8000/")

    assert client._url("/jobs") == "http://localhost:8000/jobs"
    assert client._url("health/live") == "http://localhost:8000/health/live"


def test_page_items_filters_non_mapping_values() -> None:
    page = {"items": [{"id": "1"}, "bad", {"id": "2"}]}

    assert page_items(page) == [{"id": "1"}, {"id": "2"}]
    assert page_items(None) == []


def test_metric_value_counts_case_insensitively() -> None:
    applications = [{"status": "Saved"}, {"status": "saved"}, {"status": "applied"}]

    assert metric_value(applications, "status", "saved") == 2


def test_compact_job_rows_keeps_dashboard_columns() -> None:
    rows = compact_job_rows(
        [
            {
                "title": "Backend Engineer",
                "source": "greenhouse",
                "location": "Remote",
                "remote_type": "remote",
                "status": "new",
                "apply_url": "https://example.com",
            }
        ]
    )

    assert rows == [
        {
            "Title": "Backend Engineer",
            "Source": "greenhouse",
            "Location": "Remote",
            "Mode": "remote",
            "Status": "new",
            "Apply": "https://example.com",
        }
    ]
