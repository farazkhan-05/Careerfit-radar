from __future__ import annotations

from typing import Any, Mapping
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Body, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import SessionLocal, get_db
from backend.models import db_models
from backend.models.api_schemas import ApifyImportRequest, PageResponse, SourceImportResponse, WorkflowTriggerResponse
from backend.models.schemas import SourceRunCreate, SourceRunRead
from backend.routes.crud import PaginationParams, create_entity, delete_entity, get_or_404, paginate, update_entity
from backend.sources.apify_source import ApifySource
from backend.sources.base_source import NormalizedJob, SourceStatus
from backend.workflows.job_discovery_graph import (
    JobDiscoveryWorkflow,
    JobDiscoveryWorkflowDependencies,
    WorkflowRunRepository,
    create_initial_state,
)

router = APIRouter(prefix="/sources", tags=["sources"])


@router.post("/import/apify", response_model=WorkflowTriggerResponse, status_code=status.HTTP_202_ACCEPTED)
def import_apify_jobs(
    background_tasks: BackgroundTasks,
    payload: ApifyImportRequest | None = Body(default=None),
    db: Session = Depends(get_db),
) -> WorkflowTriggerResponse:
    search = payload or ApifyImportRequest()
    run_id = f"apify-{uuid4()}"
    repository = WorkflowRunRepository(db)
    persisted = repository.save_state(
        create_initial_state(
            {
                "run_id": run_id,
                "source_name": "apify",
                "status": "running",
                "search": {"query": search.query, "location": search.location},
            }
        )
    )
    db.commit()
    background_tasks.add_task(_run_apify_import_workflow, run_id, search.query, search.location)
    return WorkflowTriggerResponse(run_id=run_id, status="running", workflow_id=persisted.id)


def _run_apify_import_workflow(run_id: str, query: str, location: str) -> None:
    session_factory = SessionLocal()
    with session_factory() as db:
        repository = WorkflowRunRepository(db)
        dependencies = JobDiscoveryWorkflowDependencies(
            fetch_sources=lambda state: [_fetch_and_store_apify_jobs(db, state)]
        )
        workflow = JobDiscoveryWorkflow(dependencies=dependencies, repository=repository)
        try:
            workflow.run(
                {
                    "run_id": run_id,
                    "source_name": "apify",
                    "search": {"query": query, "location": location},
                }
            )
            db.commit()
        except Exception as exc:
            _mark_workflow_failed(db, repository, run_id, exc)


def _fetch_and_store_apify_jobs(db: Session, state: Mapping[str, Any]) -> dict[str, object]:
    source = ApifySource()
    try:
        result = source.fetch_jobs(state=state)
    finally:
        source.close()
    response = _store_source_result(db, result.source_name, result.status.value, result.jobs, result.error_message)
    return response.model_dump(mode="json")


def _mark_workflow_failed(
    db: Session,
    repository: WorkflowRunRepository,
    run_id: str,
    exc: Exception,
) -> None:
    existing = repository.get_run(run_id)
    state = dict(existing.state) if existing is not None and isinstance(existing.state, dict) else create_initial_state(
        {"run_id": run_id, "source_name": "apify"}
    )
    errors = list(state.get("errors", []))
    errors.append(
        {
            "node": "background_task",
            "message": str(exc),
            "timestamp": datetime_now().isoformat(),
        }
    )
    repository.save_state(
        {
            **state,
            "status": "failed",
            "completed_at": datetime_now().isoformat(),
            "errors": errors,
        }
    )
    db.commit()


@router.post("/runs", response_model=SourceRunRead, status_code=201)
def create_source_run(payload: SourceRunCreate, db: Session = Depends(get_db)) -> db_models.SourceRun:
    return create_entity(db, db_models.SourceRun, payload)


@router.get("/runs", response_model=PageResponse)
def list_source_runs(
    pagination: PaginationParams = Depends(),
    source_name: str | None = Query(default=None),
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    statement = select(db_models.SourceRun).order_by(db_models.SourceRun.started_at.desc())
    if source_name is not None:
        statement = statement.where(db_models.SourceRun.source_name == source_name)
    if status is not None:
        statement = statement.where(db_models.SourceRun.status == status)
    return paginate(db, statement, pagination)


@router.get("/runs/{source_run_id}", response_model=SourceRunRead)
def get_source_run(source_run_id: UUID, db: Session = Depends(get_db)) -> db_models.SourceRun:
    return get_or_404(db, db_models.SourceRun, source_run_id)


@router.patch("/runs/{source_run_id}", response_model=SourceRunRead)
def update_source_run(source_run_id: UUID, payload: dict[str, object] = Body(...), db: Session = Depends(get_db)) -> db_models.SourceRun:
    return update_entity(db, db_models.SourceRun, source_run_id, payload)


@router.delete("/runs/{source_run_id}", status_code=204)
def delete_source_run(source_run_id: UUID, db: Session = Depends(get_db)):
    return delete_entity(db, db_models.SourceRun, source_run_id)


def _store_source_result(
    db: Session,
    source_name: str,
    status: str,
    jobs: tuple[NormalizedJob, ...],
    error_message: str | None,
) -> SourceImportResponse:
    started_at = datetime_now()
    stored = 0
    if status == SourceStatus.SUCCESS.value:
        for normalized in jobs:
            company = _get_or_create_company(db, normalized.company_name)
            existing = db.execute(
                select(db_models.Job).where(
                    db_models.Job.source == normalized.source,
                    db_models.Job.source_job_id == normalized.source_job_id,
                )
            ).scalar_one_or_none()
            if existing is not None:
                continue
            db.add(
                db_models.Job(
                    company_id=company.id,
                    source=normalized.source,
                    source_job_id=normalized.source_job_id,
                    title=normalized.title,
                    location=normalized.location,
                    remote_type=normalized.remote_type,
                    posted_at=normalized.posted_at,
                    apply_url=str(normalized.apply_url),
                    description=normalized.description,
                    raw_payload=normalized.raw_payload,
                    fetched_at=normalized.fetched_at,
                    status="new",
                )
            )
            stored += 1
    source_run = db_models.SourceRun(
        source_name=source_name,
        status=status,
        started_at=started_at,
        completed_at=datetime_now(),
        jobs_fetched=len(jobs),
        jobs_stored=stored,
        error_message=error_message,
    )
    db.add(source_run)
    db.commit()
    return SourceImportResponse(
        source_name=source_name,
        status=status,
        jobs_fetched=len(jobs),
        jobs_stored=stored,
        error_message=error_message,
    )


def _get_or_create_company(db: Session, name: str) -> db_models.Company:
    company = db.execute(select(db_models.Company).where(db_models.Company.name == name)).scalar_one_or_none()
    if company is not None:
        return company
    company = db_models.Company(name=name, source_priority=3)
    db.add(company)
    db.flush()
    return company


def datetime_now():
    from datetime import UTC, datetime

    return datetime.now(UTC)
