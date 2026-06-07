from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Body, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import db_models
from backend.models.api_schemas import PageResponse
from backend.models.schemas import JobCreate, JobRead
from backend.routes.crud import PaginationParams, create_entity, delete_entity, get_or_404, paginate, update_entity

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobRead, status_code=201)
def create_job(payload: JobCreate, db: Session = Depends(get_db)) -> db_models.Job:
    return create_entity(db, db_models.Job, payload)


@router.get("", response_model=PageResponse)
def list_jobs(
    pagination: PaginationParams = Depends(),
    status: str | None = Query(default=None),
    source: str | None = Query(default=None),
    q: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    statement = select(db_models.Job).order_by(db_models.Job.fetched_at.desc())
    if status is not None:
        statement = statement.where(db_models.Job.status == status)
    if source is not None:
        statement = statement.where(db_models.Job.source == source)
    if q is not None:
        pattern = f"%{q}%"
        statement = statement.where(db_models.Job.title.ilike(pattern))
    return paginate(db, statement, pagination)


@router.get("/{job_id}", response_model=JobRead)
def get_job(job_id: UUID, db: Session = Depends(get_db)) -> db_models.Job:
    return get_or_404(db, db_models.Job, job_id)


@router.patch("/{job_id}", response_model=JobRead)
def update_job(job_id: UUID, payload: dict[str, object] = Body(...), db: Session = Depends(get_db)) -> db_models.Job:
    return update_entity(db, db_models.Job, job_id, payload)


@router.delete("/{job_id}", status_code=204)
def delete_job(job_id: UUID, db: Session = Depends(get_db)):
    return delete_entity(db, db_models.Job, job_id)
