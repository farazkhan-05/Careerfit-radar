from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Body, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import db_models
from backend.models.api_schemas import PageResponse
from backend.models.schemas import WorkflowRunCreate, WorkflowRunRead
from backend.routes.crud import PaginationParams, create_entity, delete_entity, get_or_404, paginate, update_entity

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.post("", response_model=WorkflowRunRead, status_code=201)
def create_workflow_run(payload: WorkflowRunCreate, db: Session = Depends(get_db)) -> db_models.WorkflowRun:
    return create_entity(db, db_models.WorkflowRun, payload)


@router.get("", response_model=PageResponse)
def list_workflow_runs(
    pagination: PaginationParams = Depends(),
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    statement = select(db_models.WorkflowRun).order_by(db_models.WorkflowRun.started_at.desc())
    if status is not None:
        statement = statement.where(db_models.WorkflowRun.status == status)
    return paginate(db, statement, pagination)


@router.get("/{workflow_id}", response_model=WorkflowRunRead)
def get_workflow_run(workflow_id: UUID, db: Session = Depends(get_db)) -> db_models.WorkflowRun:
    return get_or_404(db, db_models.WorkflowRun, workflow_id)


@router.patch("/{workflow_id}", response_model=WorkflowRunRead)
def update_workflow_run(workflow_id: UUID, payload: dict[str, object] = Body(...), db: Session = Depends(get_db)) -> db_models.WorkflowRun:
    return update_entity(db, db_models.WorkflowRun, workflow_id, payload)


@router.delete("/{workflow_id}", status_code=204)
def delete_workflow_run(workflow_id: UUID, db: Session = Depends(get_db)):
    return delete_entity(db, db_models.WorkflowRun, workflow_id)
