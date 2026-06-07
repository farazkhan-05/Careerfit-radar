from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import db_models
from backend.models.api_schemas import ManualJobCreate, PageResponse
from backend.models.schemas import CompanyCreate, CompanyRead, JobCreate, JobRead
from backend.routes.crud import PaginationParams, create_entity, delete_entity, get_or_404, paginate, update_entity

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/companies", response_model=CompanyRead, status_code=201)
def create_company(payload: CompanyCreate, db: Session = Depends(get_db)) -> db_models.Company:
    existing = db.execute(select(db_models.Company).where(db_models.Company.name == payload.name)).scalar_one_or_none()
    if existing is not None:
        return existing
    return create_entity(db, db_models.Company, payload)


@router.get("/companies", response_model=PageResponse)
def list_companies(
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return paginate(db, select(db_models.Company).order_by(db_models.Company.name), pagination)


@router.post("/manual", response_model=JobRead, status_code=201)
def create_manual_job(payload: ManualJobCreate, db: Session = Depends(get_db)) -> db_models.Job:
    company = _get_or_create_company(db, payload.company_name)
    source_job_id = payload.source_job_id or f"manual-{uuid4()}"
    existing = db.execute(
        select(db_models.Job).where(
            db_models.Job.source == payload.source,
            db_models.Job.source_job_id == source_job_id,
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    job = db_models.Job(
        company_id=company.id,
        source=payload.source,
        source_job_id=source_job_id,
        title=payload.title,
        location=payload.location,
        remote_type=payload.remote_type,
        apply_url=payload.apply_url,
        description=payload.description,
        raw_payload={"created_by": "manual"},
        fetched_at=datetime.now(UTC),
        status="new",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


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


def _get_or_create_company(db: Session, name: str) -> db_models.Company:
    company = db.execute(select(db_models.Company).where(db_models.Company.name == name)).scalar_one_or_none()
    if company is not None:
        return company
    company = db_models.Company(name=name, source_priority=3)
    db.add(company)
    db.flush()
    return company
