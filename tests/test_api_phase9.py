from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient
from starlette.routing import Route

from backend.config import Settings, get_settings
from backend.database import get_db
from backend.main import app
from backend.models import db_models


class FakeScalarResult:
    def __init__(self, values: list[Any]) -> None:
        self._values = values

    def all(self) -> list[Any]:
        return self._values


class FakeResult:
    def __init__(self, values: list[Any], *, scalar: int | None = None) -> None:
        self._values = values
        self._scalar = scalar

    def scalar_one(self) -> int:
        return self._scalar if self._scalar is not None else len(self._values)

    def scalars(self) -> FakeScalarResult:
        return FakeScalarResult(self._values)


class FakeSession:
    def __init__(self) -> None:
        self.entities: dict[type[Any], dict[Any, Any]] = {}
        self.deleted: list[Any] = []

    def add(self, entity: Any) -> None:
        self._ensure_identity(entity)
        self.entities.setdefault(type(entity), {})[entity.id] = entity

    def commit(self) -> None:
        pass

    def refresh(self, entity: Any) -> None:
        self._ensure_identity(entity)

    def delete(self, entity: Any) -> None:
        self.deleted.append(entity)
        self.entities.get(type(entity), {}).pop(entity.id, None)

    def get(self, model: type[Any], entity_id: Any) -> Any:
        return self.entities.get(model, {}).get(entity_id)

    def execute(self, statement: Any) -> FakeResult:
        statement_text = str(statement)
        if "source_runs" in statement_text:
            values = list(self.entities.get(db_models.SourceRun, {}).values())
        elif "applications" in statement_text:
            values = list(self.entities.get(db_models.Application, {}).values())
        elif "workflow_runs" in statement_text:
            values = list(self.entities.get(db_models.WorkflowRun, {}).values())
        elif "jobs" in statement_text:
            values = list(self.entities.get(db_models.Job, {}).values())
        elif "candidate_profiles" in statement_text:
            values = list(self.entities.get(db_models.CandidateProfile, {}).values())
        else:
            values = list(self.entities.get(db_models.Resume, {}).values())
        if "count" in statement_text.lower():
            return FakeResult([], scalar=len(values))
        return FakeResult(values)

    @staticmethod
    def _ensure_identity(entity: Any) -> None:
        if getattr(entity, "id", None) is None:
            entity.id = uuid4()
        now = datetime.now(UTC)
        if getattr(entity, "created_at", None) is None:
            entity.created_at = now
        if getattr(entity, "updated_at", None) is None:
            entity.updated_at = now


def _client_with_session(session: FakeSession) -> TestClient:
    def override_db() -> Any:
        yield session

    app.dependency_overrides[get_db] = override_db
    return TestClient(app)


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_phase9_routers_are_registered() -> None:
    paths = {route.path for route in app.routes if isinstance(route, Route)}

    assert "/resumes" in paths
    assert "/profiles" in paths
    assert "/jobs" in paths
    assert "/workflows" in paths
    assert "/applications" in paths
    assert "/sources/runs" in paths
    assert "/sources/import/greenhouse" in paths
    assert "/sources/import/lever" in paths
    assert "/sources/import/remotive" in paths
    assert "/sources/import/arbeitnow" in paths
    assert "/exports/jobs.csv" in paths
    assert "/health/ready" in paths


def test_resume_crud_routes_function_with_pagination() -> None:
    session = FakeSession()
    client = _client_with_session(session)

    create_response = client.post(
        "/resumes",
        json={
            "file_name": "resume.pdf",
            "content_type": "application/pdf",
            "text_hash": "abc123",
            "parsed_text": "Python developer",
        },
    )
    assert create_response.status_code == 201
    resume_id = create_response.json()["id"]

    list_response = client.get("/resumes?limit=10&offset=0")
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1
    assert list_response.json()["items"][0]["id"] == resume_id

    patch_response = client.patch(f"/resumes/{resume_id}", json={"parsed_text": "Updated"})
    assert patch_response.status_code == 200
    assert patch_response.json()["parsed_text"] == "Updated"

    delete_response = client.delete(f"/resumes/{resume_id}")
    assert delete_response.status_code == 204
    assert session.deleted


def test_missing_resource_returns_404() -> None:
    client = _client_with_session(FakeSession())

    response = client.get(f"/resumes/{uuid4()}")

    assert response.status_code == 404


def test_csv_export_returns_jobs_csv() -> None:
    session = FakeSession()
    job = db_models.Job(
        id=uuid4(),
        company_id=uuid4(),
        source="greenhouse",
        source_job_id="job-1",
        title="Backend Engineer",
        location="Remote",
        remote_type="remote",
        apply_url="https://example.com/apply",
        description="Build APIs",
        raw_payload={},
        fetched_at=datetime.now(UTC),
        status="new",
    )
    session.add(job)
    client = _client_with_session(session)

    response = client.get("/exports/jobs.csv")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "Backend Engineer" in response.text


def test_health_readiness_checks_database_and_gemini_config() -> None:
    session = FakeSession()

    def override_settings() -> Settings:
        return Settings(
            DATABASE_URL="postgresql://user:pass@example.com:5432/careerfit",
            GEMINI_API_KEY="test-key",
        )

    client = _client_with_session(session)
    app.dependency_overrides[get_settings] = override_settings

    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["checks"]["database"] == "ok"
    assert response.json()["checks"]["gemini"] == "configured"
