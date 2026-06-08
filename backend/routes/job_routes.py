from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Body, Depends, Query, Response
from sqlalchemy import delete, select
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
    top_matches: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    # Resolve latest profile for score injection
    latest_profile_id = db.execute(
        select(db_models.CandidateProfile.id).order_by(db_models.CandidateProfile.created_at.desc()).limit(1)
    ).scalar_one_or_none()

    statement = select(db_models.Job)
    if status is not None:
        statement = statement.where(db_models.Job.status == status)
    if source is not None:
        statement = statement.where(db_models.Job.source == source)
    if q is not None:
        statement = statement.where(db_models.Job.title.ilike(f"%{q}%"))
    if top_matches and latest_profile_id is not None:
        statement = statement.where(
            db_models.Job.id.in_(
                select(db_models.JobScore.job_id)
                .where(db_models.JobScore.candidate_profile_id == latest_profile_id)
                .where(db_models.JobScore.final_score >= 50)
            )
        )

    # Sort by score when profile exists, otherwise by fetch date
    if latest_profile_id is not None:
        score_subq = (
            select(db_models.JobScore.job_id, db_models.JobScore.final_score)
            .where(db_models.JobScore.candidate_profile_id == latest_profile_id)
            .subquery()
        )
        statement = (
            statement.outerjoin(score_subq, db_models.Job.id == score_subq.c.job_id)
            .order_by(score_subq.c.final_score.desc().nulls_last(), db_models.Job.fetched_at.desc())
            .add_columns(score_subq.c.final_score)
        )
    else:
        statement = statement.order_by(db_models.Job.fetched_at.desc())

    result = paginate(db, statement, pagination)

    # Inject match_score into each item dict
    if latest_profile_id is not None:
        job_ids = [item["id"] for item in result["items"]]
        if job_ids:
            scores = db.execute(
                select(db_models.JobScore.job_id, db_models.JobScore.final_score, db_models.JobScore.explanation)
                .where(db_models.JobScore.job_id.in_(job_ids))
                .where(db_models.JobScore.candidate_profile_id == latest_profile_id)
            ).all()
            score_map = {str(row.job_id): {"match_score": row.final_score, "match_explanation": row.explanation} for row in scores}
            for item in result["items"]:
                info = score_map.get(str(item["id"]), {})
                item["match_score"] = info.get("match_score")
                item["match_explanation"] = info.get("match_explanation")
    else:
        for item in result["items"]:
            item["match_score"] = None
            item["match_explanation"] = None

    return result


@router.get("/{job_id}", response_model=JobRead)
def get_job(job_id: UUID, db: Session = Depends(get_db)) -> db_models.Job:
    return get_or_404(db, db_models.Job, job_id)


@router.patch("/{job_id}", response_model=JobRead)
def update_job(job_id: UUID, payload: dict[str, object] = Body(...), db: Session = Depends(get_db)) -> db_models.Job:
    return update_entity(db, db_models.Job, job_id, payload)


@router.delete("", status_code=204)
def delete_all_jobs(db: Session = Depends(get_db)):
    # Delete in FK-safe order; job deletion cascades to applications,
    # scores, embeddings, requirements, and rejected_jobs via DB constraints.
    db.execute(delete(db_models.WorkflowRun))
    db.execute(delete(db_models.SourceRun))
    db.execute(delete(db_models.Job))
    db.execute(delete(db_models.Company))
    db.commit()
    return Response(status_code=204)


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
