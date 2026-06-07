from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Body
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import db_models
from backend.models.api_schemas import PageResponse
from backend.models.schemas import CandidateProfileCreate, CandidateProfileRead
from backend.routes.crud import PaginationParams, create_entity, delete_entity, get_or_404, paginate, update_entity

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.post("", response_model=CandidateProfileRead, status_code=201)
def create_profile(payload: CandidateProfileCreate, db: Session = Depends(get_db)) -> db_models.CandidateProfile:
    return create_entity(db, db_models.CandidateProfile, payload)


@router.get("", response_model=PageResponse)
def list_profiles(pagination: PaginationParams = Depends(), db: Session = Depends(get_db)) -> dict[str, object]:
    return paginate(db, select(db_models.CandidateProfile).order_by(db_models.CandidateProfile.created_at.desc()), pagination)


@router.get("/{profile_id}", response_model=CandidateProfileRead)
def get_profile(profile_id: UUID, db: Session = Depends(get_db)) -> db_models.CandidateProfile:
    return get_or_404(db, db_models.CandidateProfile, profile_id)


@router.patch("/{profile_id}", response_model=CandidateProfileRead)
def update_profile(profile_id: UUID, payload: dict[str, object] = Body(...), db: Session = Depends(get_db)) -> db_models.CandidateProfile:
    return update_entity(db, db_models.CandidateProfile, profile_id, payload)


@router.delete("/{profile_id}", status_code=204)
def delete_profile(profile_id: UUID, db: Session = Depends(get_db)):
    return delete_entity(db, db_models.CandidateProfile, profile_id)
