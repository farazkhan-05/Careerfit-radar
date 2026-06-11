from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, Response
from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session, selectinload

from backend.database import get_db
from backend.models import db_models
from backend.models.api_schemas import ApplicationStatus, ApplicationUpdate, PageResponse
from backend.models.schemas import ApplicationCreate, ApplicationRead
from backend.routes.crud import PaginationParams, get_or_404, serialize_entity
from backend.security import require_api_auth, require_bulk_delete_confirmation

_APPLICATION_STATUSES = (
    "saved",
    "applied",
    "follow_up",
    "interview",
    "offer",
    "rejected",
    "ignored",
)

router = APIRouter(
    prefix="/applications",
    tags=["applications"],
    dependencies=[Depends(require_api_auth)],
)


@router.post("/jobs/{job_id}/save", response_model=ApplicationRead, status_code=201)
def save_job_application(job_id: UUID, db: Session = Depends(get_db)) -> db_models.Application:
    job = get_or_404(db, db_models.Job, job_id)
    existing = db.execute(
        select(db_models.Application).where(db_models.Application.job_id == job_id)
    ).scalar_one_or_none()
    if existing is not None:
        if job.status != existing.status:
            job.status = existing.status
            db.commit()
        return existing
    application = db_models.Application(job_id=job_id, status="saved")
    job.status = "saved"
    db.add(application)
    db.commit()
    db.refresh(application)
    return application


@router.post("", response_model=ApplicationRead, status_code=201)
def create_application(payload: ApplicationCreate, db: Session = Depends(get_db)) -> db_models.Application:
    job = get_or_404(db, db_models.Job, payload.job_id)
    existing = db.execute(
        select(db_models.Application).where(db_models.Application.job_id == payload.job_id)
    ).scalar_one_or_none()
    if existing is not None:
        job.status = existing.status
        db.commit()
        return existing
    application = db_models.Application(**payload.model_dump())
    job.status = application.status
    db.add(application)
    db.commit()
    db.refresh(application)
    return application


@router.get("", response_model=PageResponse)
def list_applications(
    pagination: PaginationParams = Depends(),
    status: ApplicationStatus | None = Query(default=None),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    statement = (
        select(db_models.Application)
        .options(selectinload(db_models.Application.job).selectinload(db_models.Job.company))
        .order_by(db_models.Application.created_at.desc())
    )
    if status is not None:
        statement = statement.where(db_models.Application.status == status)
    total_statement = select(func.count()).select_from(db_models.Application)
    if status is not None:
        total_statement = total_statement.where(db_models.Application.status == status)
    total = int(db.execute(total_statement).scalar_one())
    applications = (
        db.execute(statement.limit(pagination.limit).offset(pagination.offset))
        .scalars()
        .all()
    )
    return {
        "items": [_serialize_application(application) for application in applications],
        "total": total,
        "limit": pagination.limit,
        "offset": pagination.offset,
    }


@router.get("/{application_id}", response_model=ApplicationRead)
def get_application(application_id: UUID, db: Session = Depends(get_db)) -> db_models.Application:
    return get_or_404(db, db_models.Application, application_id)


@router.patch("/{application_id}", response_model=ApplicationRead)
def update_application(
    application_id: UUID,
    payload: ApplicationUpdate = Body(...),
    db: Session = Depends(get_db),
) -> db_models.Application:
    application = get_or_404(db, db_models.Application, application_id)
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(application, key, value)
    if "status" in changes and application.job is not None:
        application.job.status = application.status
    db.commit()
    db.refresh(application)
    return application


@router.delete(
    "",
    status_code=204,
    dependencies=[Depends(require_bulk_delete_confirmation)],
)
def delete_all_applications(db: Session = Depends(get_db)):
    db.execute(delete(db_models.Application))
    db.execute(
        update(db_models.Job)
        .where(db_models.Job.status.in_(_APPLICATION_STATUSES))
        .values(status="new")
    )
    db.commit()
    return Response(status_code=204)


@router.delete("/{application_id}", status_code=204)
def delete_application(application_id: UUID, db: Session = Depends(get_db)):
    application = get_or_404(db, db_models.Application, application_id)
    job = application.job
    db.delete(application)
    if job is not None and job.status in _APPLICATION_STATUSES:
        job.status = "new"
    db.commit()
    return Response(status_code=204)


def _serialize_application(application: db_models.Application) -> dict[str, object]:
    item = serialize_entity(application)
    job = application.job
    if job is not None:
        item["job"] = {
            "id": job.id,
            "title": job.title,
            "company_name": job.company.name if job.company is not None else None,
            "source": job.source,
            "location": job.location,
            "remote_type": job.remote_type,
            "apply_url": job.apply_url,
            "status": job.status,
        }
    else:
        item["job"] = None
    return item
