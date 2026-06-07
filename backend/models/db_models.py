from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector  # type: ignore[import-untyped]
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base

VectorColumn: Any = Vector


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Resume(TimestampMixin, Base):
    __tablename__ = "resumes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    text_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    parsed_text: Mapped[str | None] = mapped_column(Text)

    chunks: Mapped[list[ResumeChunk]] = relationship(
        back_populates="resume",
        cascade="all, delete-orphan",
    )
    candidate_profile: Mapped[CandidateProfile | None] = relationship(
        back_populates="resume",
        cascade="all, delete-orphan",
    )


class ResumeChunk(TimestampMixin, Base):
    __tablename__ = "resume_chunks"
    __table_args__ = (
        UniqueConstraint("resume_id", "chunk_index", name="uq_resume_chunks_order"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    resume_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"),
        nullable=False,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    text_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    resume: Mapped[Resume] = relationship(back_populates="chunks")
    embeddings: Mapped[list[ResumeEmbedding]] = relationship(
        back_populates="resume_chunk",
        cascade="all, delete-orphan",
    )


class CandidateProfile(TimestampMixin, Base):
    __tablename__ = "candidate_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    resume_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    target_roles: Mapped[list[str]] = mapped_column(
        ARRAY(String(120)),
        nullable=False,
        default=list,
    )
    skills: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    experience_years: Mapped[float | None] = mapped_column(Float)
    projects: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    raw_profile: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    resume: Mapped[Resume] = relationship(back_populates="candidate_profile")
    job_scores: Mapped[list[JobScore]] = relationship(
        back_populates="candidate_profile"
    )


class Company(TimestampMixin, Base):
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    website_url: Mapped[str | None] = mapped_column(String(500))
    career_site_url: Mapped[str | None] = mapped_column(String(500))
    source_priority: Mapped[int] = mapped_column(Integer, nullable=False, default=3)

    jobs: Mapped[list[Job]] = relationship(back_populates="company")


class Job(TimestampMixin, Base):
    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint("source", "source_job_id", name="uq_jobs_source_job_id"),
        Index("ix_jobs_company_title", "company_id", "title"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="RESTRICT"),
        nullable=False,
    )
    canonical_job_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("jobs.id", ondelete="SET NULL"),
    )
    source: Mapped[str] = mapped_column(String(80), nullable=False)
    source_job_id: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str | None] = mapped_column(String(255))
    remote_type: Mapped[str | None] = mapped_column(String(80))
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    apply_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="new")

    company: Mapped[Company] = relationship(back_populates="jobs")
    canonical_job: Mapped[Job | None] = relationship(remote_side=[id])
    requirements: Mapped[JobRequirement | None] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
    )
    embeddings: Mapped[list[JobEmbedding]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
    )
    score: Mapped[JobScore | None] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
    )
    application: Mapped[Application | None] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
    )
    rejection: Mapped[RejectedJob | None] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
    )


class JobRequirement(TimestampMixin, Base):
    __tablename__ = "job_requirements"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    required_skills: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    preferred_skills: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    responsibilities: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    min_experience_years: Mapped[float | None] = mapped_column(Float)
    work_authorization: Mapped[str | None] = mapped_column(String(255))
    confidence: Mapped[float | None] = mapped_column(Float)
    raw_requirements: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    job: Mapped[Job] = relationship(back_populates="requirements")


class JobEmbedding(TimestampMixin, Base):
    __tablename__ = "job_embeddings"
    __table_args__ = (
        UniqueConstraint(
            "job_id",
            "entity_type",
            "embedding_model",
            "text_hash",
            name="uq_job_embeddings_cache_key",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(120), nullable=False)
    text_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding_vector: Mapped[list[float]] = mapped_column(VectorColumn, nullable=False)

    job: Mapped[Job] = relationship(back_populates="embeddings")


class ResumeEmbedding(TimestampMixin, Base):
    __tablename__ = "resume_embeddings"
    __table_args__ = (
        UniqueConstraint(
            "resume_chunk_id",
            "embedding_model",
            "text_hash",
            name="uq_resume_embeddings_cache_key",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    resume_chunk_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("resume_chunks.id", ondelete="CASCADE"),
        nullable=False,
    )
    entity_type: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
        default="resume_chunk",
    )
    embedding_model: Mapped[str] = mapped_column(String(120), nullable=False)
    text_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding_vector: Mapped[list[float]] = mapped_column(VectorColumn, nullable=False)

    resume_chunk: Mapped[ResumeChunk] = relationship(back_populates="embeddings")


class JobScore(TimestampMixin, Base):
    __tablename__ = "job_scores"
    __table_args__ = (
        UniqueConstraint(
            "job_id", "candidate_profile_id", name="uq_job_scores_profile"
        ),
        CheckConstraint(
            "final_score >= 0 AND final_score <= 100", name="ck_final_score"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    final_score: Mapped[int] = mapped_column(Integer, nullable=False)
    role_match_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skill_match_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    semantic_similarity_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    experience_fit_score: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    freshness_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    location_fit_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source_reliability_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    matched_skills: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    missing_skills: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    risk_flags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)

    job: Mapped[Job] = relationship(back_populates="score")
    candidate_profile: Mapped[CandidateProfile] = relationship(
        back_populates="job_scores",
    )


class Application(TimestampMixin, Base):
    __tablename__ = "applications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    status: Mapped[str] = mapped_column(String(80), nullable=False, default="saved")
    notes: Mapped[str | None] = mapped_column(Text)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    follow_up_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    job: Mapped[Job] = relationship(back_populates="application")


class RejectedJob(TimestampMixin, Base):
    __tablename__ = "rejected_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    filter_name: Mapped[str] = mapped_column(String(120), nullable=False)
    rejected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    can_restore: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    restored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    job: Mapped[Job] = relationship(back_populates="rejection")


class SourceRun(TimestampMixin, Base):
    __tablename__ = "source_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    source_name: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(80), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    jobs_fetched: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    jobs_stored: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)


class WorkflowRun(TimestampMixin, Base):
    __tablename__ = "workflow_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    run_id: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    source_name: Mapped[str | None] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(80), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    state: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    errors: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )


class UserPreference(TimestampMixin, Base):
    __tablename__ = "user_preferences"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    target_roles: Mapped[list[str]] = mapped_column(
        ARRAY(String(120)),
        nullable=False,
        default=list,
    )
    preferred_countries: Mapped[list[str]] = mapped_column(
        ARRAY(String(120)),
        nullable=False,
        default=lambda: [
            "India",
            "Germany",
            "Luxembourg",
            "UAE",
            "Saudi Arabia",
            "Qatar",
            "Singapore",
            "Remote",
        ],
    )
    native_country: Mapped[str] = mapped_column(
        String(120), nullable=False, default="India"
    )
    preferred_work_modes: Mapped[list[str]] = mapped_column(
        ARRAY(String(80)),
        nullable=False,
        default=list,
    )
    minimum_fit_score: Mapped[int] = mapped_column(Integer, nullable=False, default=70)
    maximum_experience_years: Mapped[float] = mapped_column(
        Float, nullable=False, default=5
    )
    visa_sponsorship_required: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    relocation_open: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    remote_open: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    excluded_keywords: Mapped[list[str]] = mapped_column(
        ARRAY(String(120)),
        nullable=False,
        default=list,
    )
    preferred_keywords: Mapped[list[str]] = mapped_column(
        ARRAY(String(120)),
        nullable=False,
        default=list,
    )
