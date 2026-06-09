from __future__ import annotations

import re
from dataclasses import dataclass, field
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Response
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from backend.database import get_db
from backend.models import db_models
from backend.models.api_schemas import PageResponse
from backend.models.schemas import CandidateProfileCreate, CandidateProfileRead
from backend.routes.crud import PaginationParams, create_entity, delete_entity, get_or_404, paginate, update_entity
from backend.services.scoring_service import FitScoringService
from backend.utils.text_utils import normalize_for_match

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


@router.post("/score-jobs", status_code=200)
def score_jobs(
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
) -> dict:
    profile = db.execute(
        select(db_models.CandidateProfile).order_by(db_models.CandidateProfile.created_at.desc())
    ).scalar_one_or_none()
    if profile is None:
        raise HTTPException(status_code=422, detail="No candidate profile found. Upload a resume with AI extraction enabled first.")

    scored_job_ids = select(db_models.JobScore.job_id).where(
        db_models.JobScore.candidate_profile_id == profile.id
    )
    unscored_jobs = select(db_models.Job).where(db_models.Job.id.not_in(scored_job_ids))
    remaining_before = db.execute(
        select(func.count()).select_from(unscored_jobs.subquery())
    ).scalar_one()

    jobs = db.execute(
        unscored_jobs
        .options(selectinload(db_models.Job.requirements))
        .order_by(db_models.Job.fetched_at.desc(), db_models.Job.id)
        .limit(limit)
    ).scalars().all()

    if not jobs:
        total_scored = _count_scored_jobs(db, profile.id)
        return {
            "scored": 0,
            "scored_count": 0,
            "remaining_unscored_count": 0,
            "total_scored": total_scored,
            "profile_id": str(profile.id),
            "message": "All jobs already scored.",
        }

    candidate_skills = _extract_all_skills(profile)
    service = FitScoringService()

    for job in jobs:
        req = _requirements_for_scoring(job, candidate_skills)
        result = service.score_job(job=job, candidate_profile=profile, requirements=req)
        db.add(db_models.JobScore(**result.score.model_dump(mode="json")))

    db.commit()
    scored_count = len(jobs)
    remaining_unscored_count = max(int(remaining_before) - scored_count, 0)
    total_scored = _count_scored_jobs(db, profile.id)
    return {
        "scored": scored_count,
        "scored_count": scored_count,
        "remaining_unscored_count": remaining_unscored_count,
        "total_scored": total_scored,
        "profile_id": str(profile.id),
    }


def _count_scored_jobs(db: Session, profile_id: UUID) -> int:
    return int(
        db.execute(
            select(func.count()).select_from(db_models.JobScore).where(
                db_models.JobScore.candidate_profile_id == profile_id
            )
        ).scalar_one()
    )


@dataclass
class _InferredReq:
    required_skills: list[str] = field(default_factory=list)
    preferred_skills: list[str] = field(default_factory=list)
    min_experience_years: float | None = None


@dataclass(frozen=True)
class _StoredReq:
    required_skills: list[str] = field(default_factory=list)
    preferred_skills: list[str] = field(default_factory=list)
    min_experience_years: float | None = None


_EXP_PATTERNS = (
    re.compile(r"(\d+(?:\.\d+)?)\+?\s*(?:years|yrs)\s+(?:of\s+)?experience", re.I),
    re.compile(r"experience\s+(?:of\s+)?(\d+(?:\.\d+)?)\+?\s*(?:years|yrs)", re.I),
    re.compile(r"minimum\s+(\d+(?:\.\d+)?)\+?\s*(?:years|yrs)", re.I),
)


def _extract_all_skills(profile: db_models.CandidateProfile) -> list[str]:
    skills: list[str] = []
    for value in profile.skills.values():
        if isinstance(value, list):
            skills.extend(str(s) for s in value if s)
    return skills


def _requirements_for_scoring(job: db_models.Job, candidate_skills: list[str]) -> _StoredReq | _InferredReq:
    stored = getattr(job, "requirements", None)
    if stored is not None:
        return _StoredReq(
            required_skills=_clean_requirement_list(stored.required_skills),
            preferred_skills=_clean_requirement_list(stored.preferred_skills),
            min_experience_years=stored.min_experience_years,
        )
    return _infer_requirements(job.description, candidate_skills)


def _clean_requirement_list(values: list[str] | None) -> list[str]:
    if not values:
        return []
    return [str(value) for value in values if value]


def _infer_requirements(description: str, candidate_skills: list[str]) -> _InferredReq:
    desc_norm = normalize_for_match(description)
    found = [s for s in candidate_skills if normalize_for_match(s) in desc_norm]
    exp: float | None = None
    matches: list[float] = []
    for pattern in _EXP_PATTERNS:
        matches.extend(float(m) for m in pattern.findall(description))
    if matches:
        exp = max(matches)
    return _InferredReq(preferred_skills=found, min_experience_years=exp)


@router.delete("", status_code=204)
def delete_all_profiles(db: Session = Depends(get_db)):
    db.execute(delete(db_models.CandidateProfile))
    db.commit()
    return Response(status_code=204)


@router.delete("/{profile_id}", status_code=204)
def delete_profile(profile_id: UUID, db: Session = Depends(get_db)):
    return delete_entity(db, db_models.CandidateProfile, profile_id)
