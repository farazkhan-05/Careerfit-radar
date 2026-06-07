from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.database import get_db
from backend.models import db_models
from backend.models.api_schemas import PageResponse, ResumeUploadResponse
from backend.models.schemas import ResumeCreate, ResumeRead
from backend.routes.crud import (
    PaginationParams,
    create_entity,
    delete_entity,
    get_or_404,
    paginate,
    update_entity,
)
from backend.services.candidate_profile_service import (
    CandidateProfileService,
    GeminiProfileClient,
    ProfileExtractionError,
)
from backend.services.resume_parser import ResumeParseError, parse_resume_bytes

router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.post("/upload", response_model=ResumeUploadResponse, status_code=201)
async def upload_resume(
    file: UploadFile = File(...),
    extract_profile: bool = Form(default=False),
    db: Session = Depends(get_db),
) -> ResumeUploadResponse:
    payload = await file.read()
    try:
        parsed = parse_resume_bytes(
            file_name=file.filename or "resume",
            content_type=file.content_type or "",
            payload=payload,
        )
    except ResumeParseError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    resume = db.execute(
        select(db_models.Resume).where(db_models.Resume.text_hash == parsed.text_hash)
    ).scalar_one_or_none()
    if resume is None:
        resume = db_models.Resume(
            file_name=parsed.file_name,
            content_type=parsed.content_type,
            text_hash=parsed.text_hash,
            parsed_text=parsed.parsed_text,
        )
        db.add(resume)
        db.flush()
        for chunk in parsed.chunks:
            db.add(
                db_models.ResumeChunk(
                    resume_id=resume.id,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    text_hash=chunk.text_hash,
                )
            )
    profile_id = None
    profile_error = None
    if extract_profile:
        existing_profile = db.execute(
            select(db_models.CandidateProfile).where(db_models.CandidateProfile.resume_id == resume.id)
        ).scalar_one_or_none()
        if existing_profile is not None:
            profile_id = existing_profile.id
        else:
            try:
                settings = get_settings()
                profile_payload = CandidateProfileService(
                    GeminiProfileClient(
                        api_key=settings.gemini_api_key,
                        model=settings.gemini_llm_model,
                    )
                ).extract_profile(resume_id=resume.id, resume_text=parsed.parsed_text)
                profile = db_models.CandidateProfile(**profile_payload.model_dump(mode="json"))
                db.add(profile)
                db.flush()
                profile_id = profile.id
            except ProfileExtractionError as exc:
                profile_error = str(exc)

    db.commit()
    return ResumeUploadResponse(
        resume_id=resume.id,
        chunk_count=len(parsed.chunks),
        profile_id=profile_id,
        profile_error=profile_error,
    )


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
