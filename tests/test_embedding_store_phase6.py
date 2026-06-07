from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import Session

from backend.models.db_models import JobEmbedding, ResumeEmbedding
from backend.services.embedding_store_service import (
    EmbeddingStoreError,
    EmbeddingStoreService,
    SimilaritySearchResult,
    build_similarity_statement,
)


class ScalarResult:
    def __init__(self, value: Any = None) -> None:
        self._value = value

    def scalar_one_or_none(self) -> Any:
        return self._value

    def all(self) -> list[Any]:
        return []


@dataclass(frozen=True)
class SearchRow:
    job_id: UUID
    id: UUID
    entity_type: str
    embedding_model: str
    text_hash: str
    distance: float


class SearchResult:
    def __init__(self, rows: list[SearchRow]) -> None:
        self._rows = rows

    def all(self) -> list[SearchRow]:
        return self._rows


class FakeSession:
    def __init__(self, *, existing: Any = None, rows: list[SearchRow] | None = None) -> None:
        self.existing = existing
        self.rows = rows
        self.added: list[Any] = []
        self.executed: list[Any] = []

    def execute(self, statement: Any) -> ScalarResult | SearchResult:
        self.executed.append(statement)
        if self.rows is not None:
            return SearchResult(self.rows)
        return ScalarResult(self.existing)

    def add(self, value: Any) -> None:
        self.added.append(value)

    def flush(self) -> None:
        for value in self.added:
            if getattr(value, "id", None) is None:
                value.id = uuid4()


def test_store_resume_embedding_uses_cache_key() -> None:
    resume_chunk_id = uuid4()
    existing = ResumeEmbedding(
        id=uuid4(),
        resume_chunk_id=resume_chunk_id,
        entity_type="resume_chunk",
        embedding_model="gemini-embedding",
        text_hash="resume-hash",
        embedding_vector=[0.1, 0.2],
    )
    session = FakeSession(existing=existing)

    stored = EmbeddingStoreService(cast(Session, session)).store_resume_embedding(
        resume_chunk_id=resume_chunk_id,
        embedding_model="gemini-embedding",
        text_hash="resume-hash",
        embedding_vector=[0.1, 0.2],
    )

    assert stored.created is False
    assert stored.id == existing.id
    assert stored.owner_id == resume_chunk_id
    assert session.added == []


def test_store_job_embedding_creates_metadata_record() -> None:
    job_id = uuid4()
    session = FakeSession()

    stored = EmbeddingStoreService(cast(Session, session)).store_job_embedding(
        job_id=job_id,
        entity_type="job_description",
        embedding_model="gemini-embedding",
        text_hash="job-hash",
        embedding_vector=[0.4, 0.6],
    )

    assert stored.created is True
    assert stored.owner_id == job_id
    assert stored.entity_type == "job_description"
    assert stored.embedding_model == "gemini-embedding"
    assert stored.text_hash == "job-hash"
    assert isinstance(session.added[0], JobEmbedding)


def test_store_embedding_rejects_empty_vectors() -> None:
    service = EmbeddingStoreService(cast(Session, FakeSession()))

    with pytest.raises(EmbeddingStoreError, match="must not be empty"):
        service.store_job_embedding(
            job_id=uuid4(),
            entity_type="job_description",
            embedding_model="gemini-embedding",
            text_hash="job-hash",
            embedding_vector=[],
        )


def test_similarity_search_tolerates_missing_embeddings() -> None:
    service = EmbeddingStoreService(cast(Session, FakeSession(rows=[])))

    assert service.search_similar_jobs(
        query_vector=[],
        embedding_model="gemini-embedding",
    ) == ()
    assert service.search_similar_jobs(
        query_vector=[0.1, 0.2],
        embedding_model="gemini-embedding",
    ) == ()


def test_similarity_search_returns_usable_scores() -> None:
    job_id = uuid4()
    embedding_id = uuid4()
    session = FakeSession(
        rows=[
            SearchRow(
                job_id=job_id,
                id=embedding_id,
                entity_type="job_description",
                embedding_model="gemini-embedding",
                text_hash="job-hash",
                distance=0.18,
            )
        ]
    )

    results = EmbeddingStoreService(cast(Session, session)).search_similar_jobs(
        query_vector=[0.1, 0.2],
        embedding_model="gemini-embedding",
        entity_type="job_description",
        minimum_score=0.8,
    )

    assert results == (
        SimilaritySearchResult(
            job_id=job_id,
            embedding_id=embedding_id,
            score=0.82,
            distance=0.18,
            entity_type="job_description",
            embedding_model="gemini-embedding",
            text_hash="job-hash",
        ),
    )


def test_similarity_statement_is_built_for_pgvector_search() -> None:
    statement = build_similarity_statement(
        query_vector=[0.1, 0.2],
        embedding_model="gemini-embedding",
        entity_type="job_description",
        limit=5,
    )

    assert statement is not None
    compiled = str(statement)
    assert "job_embeddings" in compiled
    assert "jobs" in compiled
    assert "embedding_model" in compiled
    assert "entity_type" in compiled
