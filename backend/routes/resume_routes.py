from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Body
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import db_models
from backend.models.api_schemas import PageResponse
from backend.models.schemas import ResumeCreate, ResumeRead
from backend.routes.crud import (
    PaginationParams,
    create_entity,
    delete_entity,
    get_or_404,
    paginate,
    update_entity,
)

router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.post("", response_model=ResumeRead, status_code=201)
def create_resume(payload: ResumeCreate, db: Session = Depends(get_db)) -> db_models.Resume:
    return create_entity(db, db_models.Resume, payload)


@router.get("", response_model=PageResponse)
def list_resumes(
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return paginate(db, select(db_models.Resume).order_by(db_models.Resume.created_at.desc()), pagination)


@router.get("/{resume_id}", response_model=ResumeRead)
def get_resume(resume_id: UUID, db: Session = Depends(get_db)) -> db_models.Resume:
    return get_or_404(db, db_models.Resume, resume_id)


@router.patch("/{resume_id}", response_model=ResumeRead)
def update_resume(
    resume_id: UUID,
    payload: dict[str, object] = Body(...),
    db: Session = Depends(get_db),
) -> db_models.Resume:
    return update_entity(db, db_models.Resume, resume_id, payload)


@router.delete("/{resume_id}", status_code=204)
def delete_resume(resume_id: UUID, db: Session = Depends(get_db)):
    return delete_entity(db, db_models.Resume, resume_id)
