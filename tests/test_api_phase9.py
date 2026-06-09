from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient
from starlette.routing import Route

from backend.config import Settings, get_settings
from backend.database import get_db
from backend.main import app
from backend.models import db_models
from backend.routes import profile_routes, source_routes
from backend.sources.base_source import SourceFetchResult, SourceStatus


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

    def scalar_one_or_none(self) -> Any:
        return self._values[0] if self._values else None

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

    def flush(self) -> None:
        pass

    def delete(self, entity: Any) -> None:
        self.deleted.append(entity)
        self.entities.get(type(entity), {}).pop(entity.id, None)

    def get(self, model: type[Any], entity_id: Any) -> Any:
        return self.entities.get(model, {}).get(entity_id)

    def execute(self, statement: Any) -> FakeResult:
        statement_text = str(statement)
        if "source_runs" in statement_text:
            values = list(self.entities.get(db_models.SourceRun, {}).values())
        elif "job_scores" in statement_text:
            values = list(self.entities.get(db_models.JobScore, {}).values())
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


class FakeSessionContext:
    def __init__(self, session: FakeSession) -> None:
        self._session = session

    def __enter__(self) -> FakeSession:
        return self._session

    def __exit__(self, *_args: Any) -> None:
        pass


class FakeSessionFactory:
    def __init__(self, session: FakeSession) -> None:
        self._session = session

    def __call__(self) -> FakeSessionContext:
        return FakeSessionContext(self._session)


class FakeScoreSession(FakeSession):
    def __init__(self, *, profile_id: Any, jobs: list[Any]) -> None:
        super().__init__()
        self.profile = SimpleNamespace(
            id=profile_id,
            created_at=datetime.now(UTC),
            skills={"languages": ["Python"], "frontend": ["React"]},
        )
        self.jobs = jobs

    def execute(self, statement: Any) -> FakeResult:
        statement_text = str(statement)
        scored_job_ids = {
            score.job_id
            for score in self.entities.get(db_models.JobScore, {}).values()
        }
        unscored_jobs = [job for job in self.jobs if job.id not in scored_job_ids]

        if "candidate_profiles" in statement_text:
            return FakeResult([self.profile])
        if "count" in statement_text.lower() and "job_scores" in statement_text and "jobs" in statement_text:
            return FakeResult([], scalar=len(unscored_jobs))
        if "count" in statement_text.lower() and "job_scores" in statement_text:
            return FakeResult([], scalar=len(scored_job_ids))
        if "jobs" in statement_text:
            return FakeResult(unscored_jobs[:2])
        return FakeResult([])


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
    assert "/sources/import/apify" in paths
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


def test_apify_import_route_queues_background_workflow(monkeypatch: Any) -> None:
    session = FakeSession()
    client = _client_with_session(session)
    captured: dict[str, Any] = {}

    class FakeApifySource:
        source_name = "apify"

        def fetch_jobs(self, *, query: str | None = None, location: str | None = None) -> SourceFetchResult:
            captured["query"] = query
            captured["location"] = location
            return SourceFetchResult(
                source_name=self.source_name,
                status=SourceStatus.SUCCESS,
                started_at=datetime.now(UTC),
                completed_at=datetime.now(UTC),
                jobs=[],
            )

        def close(self) -> None:
            captured["closed"] = True

    monkeypatch.setattr(source_routes, "ApifySource", FakeApifySource)
    monkeypatch.setattr(source_routes, "SessionLocal", lambda: FakeSessionFactory(session))

    response = client.post(
        "/sources/import/apify",
        json={"query": "React Engineer", "location": "Bengaluru, India"},
    )

    assert response.status_code == 202
    assert response.json()["status"] == "running"
    assert response.json()["run_id"].startswith("apify-")
    assert captured == {
        "query": "React Engineer",
        "location": "Bengaluru, India",
        "closed": True,
    }
    workflow_run = next(iter(session.entities[db_models.WorkflowRun].values()))
    assert workflow_run.run_id == response.json()["run_id"]
    assert workflow_run.status == "completed"
    assert workflow_run.state["source_results"][0]["jobs_fetched"] == 0


def test_workflow_run_can_be_read_by_run_id() -> None:
    session = FakeSession()
    workflow_run = db_models.WorkflowRun(
        run_id="apify-test-run",
        source_name="apify",
        status="running",
        started_at=datetime.now(UTC),
        state={"run_id": "apify-test-run", "status": "running"},
        errors=[],
    )
    session.add(workflow_run)
    client = _client_with_session(session)

    response = client.get("/workflows/apify-test-run")

    assert response.status_code == 200
    assert response.json()["run_id"] == "apify-test-run"


def test_score_jobs_respects_batch_limit_and_returns_remaining_count(monkeypatch: Any) -> None:
    profile_id = uuid4()
    jobs = [
        SimpleNamespace(id=uuid4(), title=f"Job {index}", description="Python and React")
        for index in range(3)
    ]
    session = FakeScoreSession(profile_id=profile_id, jobs=jobs)

    class FakeScore:
        def __init__(self, job_id: Any) -> None:
            self._job_id = job_id

        def model_dump(self, *, mode: str) -> dict[str, Any]:
            return {
                "job_id": self._job_id,
                "candidate_profile_id": profile_id,
                "final_score": 80,
                "role_match_score": 10,
                "skill_match_score": 20,
                "semantic_similarity_score": 0,
                "experience_fit_score": 10,
                "freshness_score": 10,
                "location_fit_score": 10,
                "source_reliability_score": 20,
                "matched_skills": ["Python"],
                "missing_skills": [],
                "risk_flags": [],
                "explanation": "Good fit.",
            }

    class FakeFitScoringService:
        def score_job(self, *, job: Any, candidate_profile: Any, requirements: Any) -> Any:
            return SimpleNamespace(score=FakeScore(job.id))

    monkeypatch.setattr(profile_routes, "FitScoringService", FakeFitScoringService)

    response = profile_routes.score_jobs(limit=2, db=session)

    assert response["scored_count"] == 2
    assert response["scored"] == 2
    assert response["remaining_unscored_count"] == 1
    assert response["total_scored"] == 2
    assert len(session.entities[db_models.JobScore]) == 2


def test_score_jobs_prefers_database_requirements(monkeypatch: Any) -> None:
    profile_id = uuid4()
    stored_requirements = SimpleNamespace(
        required_skills=["Gemini Skill"],
        preferred_skills=["Stored Preferred"],
        min_experience_years=2.0,
    )
    jobs = [
        SimpleNamespace(
            id=uuid4(),
            title="AI Engineer",
            description="This text would trigger the regex fallback.",
            requirements=stored_requirements,
        )
    ]
    session = FakeScoreSession(profile_id=profile_id, jobs=jobs)
    captured: dict[str, Any] = {}

    class FakeScore:
        def model_dump(self, *, mode: str) -> dict[str, Any]:
            return {
                "job_id": jobs[0].id,
                "candidate_profile_id": profile_id,
                "final_score": 80,
                "role_match_score": 10,
                "skill_match_score": 20,
                "semantic_similarity_score": 0,
                "experience_fit_score": 10,
                "freshness_score": 10,
                "location_fit_score": 10,
                "source_reliability_score": 20,
                "matched_skills": [],
                "missing_skills": [],
                "risk_flags": [],
                "explanation": "Good fit.",
            }

    class FakeFitScoringService:
        def score_job(self, *, job: Any, candidate_profile: Any, requirements: Any) -> Any:
            captured["requirements"] = requirements
            return SimpleNamespace(score=FakeScore())

    def fail_infer_requirements(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("Regex fallback should not run when database requirements exist.")

    monkeypatch.setattr(profile_routes, "FitScoringService", FakeFitScoringService)
    monkeypatch.setattr(profile_routes, "_infer_requirements", fail_infer_requirements)

    response = profile_routes.score_jobs(limit=1, db=session)

    requirements = captured["requirements"]
    assert response["scored_count"] == 1
    assert requirements.required_skills == ["Gemini Skill"]
    assert requirements.preferred_skills == ["Stored Preferred"]
    assert requirements.min_experience_years == 2.0


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
