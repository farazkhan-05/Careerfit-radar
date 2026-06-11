from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import db_models
from backend.routes.crud import rows_to_csv
from backend.security import require_api_auth

router = APIRouter(
    prefix="/exports",
    tags=["exports"],
    dependencies=[Depends(require_api_auth)],
)


@router.get("/jobs.csv")
def export_jobs_csv(db: Session = Depends(get_db)) -> Response:
    jobs = db.execute(select(db_models.Job).order_by(db_models.Job.fetched_at.desc())).scalars().all()
    payload = rows_to_csv(
        (
            {
                "id": str(job.id),
                "source": job.source,
                "source_job_id": job.source_job_id,
                "title": job.title,
                "location": job.location or "",
                "remote_type": job.remote_type or "",
                "status": job.status,
                "apply_url": job.apply_url,
            }
            for job in jobs
        ),
        ["id", "source", "source_job_id", "title", "location", "remote_type", "status", "apply_url"],
    )
    return Response(
        content=payload,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=jobs.csv"},
    )


@router.get("/applications.csv")
def export_applications_csv(db: Session = Depends(get_db)) -> Response:
    applications = (
        db.execute(
            select(db_models.Application).order_by(db_models.Application.created_at.desc())
        )
        .scalars()
        .all()
    )
    payload = rows_to_csv(
        (
            {
                "id": str(application.id),
                "job_id": str(application.job_id),
                "status": application.status,
                "notes": application.notes or "",
                "applied_at": application.applied_at.isoformat() if application.applied_at else "",
                "follow_up_at": application.follow_up_at.isoformat() if application.follow_up_at else "",
            }
            for application in applications
        ),
        ["id", "job_id", "status", "notes", "applied_at", "follow_up_at"],
    )
    return Response(
        content=payload,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=applications.csv"},
    )
