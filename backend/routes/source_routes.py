from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Body, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import db_models
from backend.models.api_schemas import PageResponse
from backend.models.schemas import SourceRunCreate, SourceRunRead
from backend.routes.crud import PaginationParams, create_entity, delete_entity, get_or_404, paginate, update_entity

router = APIRouter(prefix="/sources", tags=["sources"])


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
