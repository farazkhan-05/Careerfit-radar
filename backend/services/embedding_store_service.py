from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.config import Settings
from backend.models.db_models import Job, JobEmbedding, ResumeEmbedding


class EmbeddingStoreError(RuntimeError):
    pass


@dataclass(frozen=True)
class StoredEmbedding:
    id: UUID
    owner_id: UUID
    entity_type: str
    embedding_model: str
    text_hash: str
    created: bool


@dataclass(frozen=True)
class SimilaritySearchResult:
    job_id: UUID
    embedding_id: UUID
    score: float
    distance: float
    entity_type: str
    embedding_model: str
    text_hash: str


class EmbeddingStoreService:
    def __init__(
        self,
        session: Session,
        settings: Settings | None = None,
        expected_dimensions: int | None = None,
    ) -> None:
        self._session = session
        self._expected_dimensions = (
            expected_dimensions
            if expected_dimensions is not None
            else settings.embedding_dimensions if settings is not None else None
        )

    def store_resume_embedding(
        self,
        *,
        resume_chunk_id: UUID,
        embedding_model: str,
        text_hash: str,
        embedding_vector: list[float],
        entity_type: str = "resume_chunk",
    ) -> StoredEmbedding:
        self._validate_embedding_vector(embedding_vector)

        existing = self._session.execute(
            select(ResumeEmbedding).where(
                ResumeEmbedding.resume_chunk_id == resume_chunk_id,
                ResumeEmbedding.embedding_model == embedding_model,
                ResumeEmbedding.text_hash == text_hash,
            )
        ).scalar_one_or_none()
        if existing is not None:
            return StoredEmbedding(
                id=existing.id,
                owner_id=existing.resume_chunk_id,
                entity_type=existing.entity_type,
                embedding_model=existing.embedding_model,
                text_hash=existing.text_hash,
                created=False,
            )

        embedding = ResumeEmbedding(
            resume_chunk_id=resume_chunk_id,
            entity_type=entity_type,
            embedding_model=embedding_model,
            text_hash=text_hash,
            embedding_vector=embedding_vector,
        )
        self._session.add(embedding)
        self._session.flush()
        return StoredEmbedding(
            id=embedding.id,
            owner_id=embedding.resume_chunk_id,
            entity_type=embedding.entity_type,
            embedding_model=embedding.embedding_model,
            text_hash=embedding.text_hash,
            created=True,
        )

    def store_job_embedding(
        self,
        *,
        job_id: UUID,
        entity_type: str,
        embedding_model: str,
        text_hash: str,
        embedding_vector: list[float],
    ) -> StoredEmbedding:
        self._validate_embedding_vector(embedding_vector)

        existing = self._session.execute(
            select(JobEmbedding).where(
                JobEmbedding.job_id == job_id,
                JobEmbedding.entity_type == entity_type,
                JobEmbedding.embedding_model == embedding_model,
                JobEmbedding.text_hash == text_hash,
            )
        ).scalar_one_or_none()
        if existing is not None:
            return StoredEmbedding(
                id=existing.id,
                owner_id=existing.job_id,
                entity_type=existing.entity_type,
                embedding_model=existing.embedding_model,
                text_hash=existing.text_hash,
                created=False,
            )

        embedding = JobEmbedding(
            job_id=job_id,
            entity_type=entity_type,
            embedding_model=embedding_model,
            text_hash=text_hash,
            embedding_vector=embedding_vector,
        )
        self._session.add(embedding)
        self._session.flush()
        return StoredEmbedding(
            id=embedding.id,
            owner_id=embedding.job_id,
            entity_type=embedding.entity_type,
            embedding_model=embedding.embedding_model,
            text_hash=embedding.text_hash,
            created=True,
        )

    def search_similar_jobs(
        self,
        *,
        query_vector: list[float],
        embedding_model: str,
        entity_type: str | None = None,
        limit: int = 20,
        minimum_score: float | None = None,
    ) -> tuple[SimilaritySearchResult, ...]:
        if not query_vector or limit <= 0:
            return ()
        self._validate_embedding_vector(query_vector)

        distance = JobEmbedding.embedding_vector.cosine_distance(query_vector)
        statement = (
            select(
                JobEmbedding.job_id,
                JobEmbedding.id,
                JobEmbedding.entity_type,
                JobEmbedding.embedding_model,
                JobEmbedding.text_hash,
                distance.label("distance"),
            )
            .join(Job, Job.id == JobEmbedding.job_id)
            .where(
                JobEmbedding.embedding_model == embedding_model,
                Job.status != "rejected",
                Job.status != "duplicate",
            )
            .order_by(distance)
            .limit(limit)
        )
        if entity_type is not None:
            statement = statement.where(JobEmbedding.entity_type == entity_type)

        try:
            rows = self._session.execute(statement).all()
        except SQLAlchemyError as exc:
            raise EmbeddingStoreError("Similarity search failed.") from exc

        results: list[SimilaritySearchResult] = []
        for row in rows:
            result = _row_to_similarity_result(row)
            if minimum_score is None or result.score >= minimum_score:
                results.append(result)
        return tuple(results)

    def _validate_embedding_vector(self, embedding_vector: list[float]) -> None:
        if not embedding_vector:
            raise EmbeddingStoreError("Embedding vector must not be empty.")
        expected_dimensions = self._expected_dimensions
        if expected_dimensions is not None and len(embedding_vector) != expected_dimensions:
            raise EmbeddingStoreError(
                "Embedding vector dimension mismatch: "
                f"expected {expected_dimensions}, got {len(embedding_vector)}."
            )


def build_similarity_statement(
    *,
    query_vector: list[float],
    embedding_model: str,
    entity_type: str | None = None,
    limit: int = 20,
) -> Select[Any] | None:
    if not query_vector or limit <= 0:
        return None

    distance = JobEmbedding.embedding_vector.cosine_distance(query_vector)
    statement = (
        select(
            JobEmbedding.job_id,
            JobEmbedding.id,
            JobEmbedding.entity_type,
            JobEmbedding.embedding_model,
            JobEmbedding.text_hash,
            distance.label("distance"),
        )
        .join(Job, Job.id == JobEmbedding.job_id)
        .where(
            JobEmbedding.embedding_model == embedding_model,
            Job.status != "rejected",
            Job.status != "duplicate",
        )
        .order_by(distance)
        .limit(limit)
    )
    if entity_type is not None:
        statement = statement.where(JobEmbedding.entity_type == entity_type)
    return statement


def _row_to_similarity_result(row: Any) -> SimilaritySearchResult:
    distance = float(row.distance)
    return SimilaritySearchResult(
        job_id=row.job_id,
        embedding_id=row.id,
        score=round(max(0.0, 1.0 - distance), 6),
        distance=distance,
        entity_type=row.entity_type,
        embedding_model=row.embedding_model,
        text_hash=row.text_hash,
    )
