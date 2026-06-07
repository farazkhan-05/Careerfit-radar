from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import db_models
from backend.models.api_schemas import PageResponse, SourceImportResponse
from backend.models.schemas import SourceRunCreate, SourceRunRead
from backend.routes.crud import PaginationParams, create_entity, delete_entity, get_or_404, paginate, update_entity
from backend.sources.arbeitnow_source import ArbeitnowSource
from backend.sources.base_source import NormalizedJob, SourceStatus
from backend.sources.greenhouse_source import GreenhouseSource
from backend.sources.lever_source import LeverSource
from backend.sources.remotive_source import RemotiveSource

router = APIRouter(prefix="/sources", tags=["sources"])


@router.post("/import/greenhouse", response_model=SourceImportResponse)
def import_greenhouse_jobs(
    board_token: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
) -> SourceImportResponse:
    source = GreenhouseSource(board_token=board_token)
    try:
        result = source.fetch_jobs()
    finally:
        source.close()
    return _store_source_result(db, result.source_name, result.status.value, result.jobs, result.error_message)


@router.post("/import/lever", response_model=SourceImportResponse)
def import_lever_jobs(
    company_slug: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
) -> SourceImportResponse:
    source = LeverSource(company_slug=company_slug)
    try:
        result = source.fetch_jobs()
    finally:
        source.close()
    return _store_source_result(db, result.source_name, result.status.value, result.jobs, result.error_message)


@router.post("/import/remotive", response_model=SourceImportResponse)
def import_remotive_jobs(
    search: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> SourceImportResponse:
    source = RemotiveSource(search=search)
    try:
        result = source.fetch_jobs()
    finally:
        source.close()
    return _store_source_result(db, result.source_name, result.status.value, result.jobs, result.error_message)


@router.post("/import/arbeitnow", response_model=SourceImportResponse)
def import_arbeitnow_jobs(db: Session = Depends(get_db)) -> SourceImportResponse:
    source = ArbeitnowSource()
    try:
        result = source.fetch_jobs()
    finally:
        source.close()
    return _store_source_result(db, result.source_name, result.status.value, result.jobs, result.error_message)


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
