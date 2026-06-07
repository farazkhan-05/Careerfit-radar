from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import db_models
from backend.models.api_schemas import PageResponse
from backend.models.schemas import ApplicationCreate, ApplicationRead
from backend.routes.crud import PaginationParams, create_entity, delete_entity, get_or_404, paginate, update_entity

router = APIRouter(prefix="/applications", tags=["applications"])


@router.post("/jobs/{job_id}/save", response_model=ApplicationRead, status_code=201)
def save_job_application(job_id: UUID, db: Session = Depends(get_db)) -> db_models.Application:
    existing = db.execute(select(db_models.Application).where(db_models.Application.job_id == job_id)).scalar_one_or_none()
    if existing is not None:
        return existing
    application = db_models.Application(job_id=job_id, status="saved")
    db.add(application)
    db.commit()
    db.refresh(application)
    return application


@router.post("", response_model=ApplicationRead, status_code=201)
def create_application(payload: ApplicationCreate, db: Session = Depends(get_db)) -> db_models.Application:
    return create_entity(db, db_models.Application, payload)


@router.get("", response_model=PageResponse)
def list_applications(
    pagination: PaginationParams = Depends(),
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    statement = select(db_models.Application).order_by(db_models.Application.created_at.desc())
    if status is not None:
        statement = statement.where(db_models.Application.status == status)
    return paginate(db, statement, pagination)


@router.get("/{application_id}", response_model=ApplicationRead)
def get_application(application_id: UUID, db: Session = Depends(get_db)) -> db_models.Application:
    return get_or_404(db, db_models.Application, application_id)


@router.patch("/{application_id}", response_model=ApplicationRead)
def update_application(application_id: UUID, payload: dict[str, object] = Body(...), db: Session = Depends(get_db)) -> db_models.Application:
    return update_entity(db, db_models.Application, application_id, payload)


@router.delete("/{application_id}", status_code=204)
def delete_application(application_id: UUID, db: Session = Depends(get_db)):
    return delete_entity(db, db_models.Application, application_id)
