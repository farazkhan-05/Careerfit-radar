from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping
from uuid import UUID, uuid4

from pydantic import BaseModel

from backend.config import Settings
from backend.services.gemini_embedding_service import (
    EmbeddingStatus,
    GeminiEmbeddingError,
    GeminiEmbeddingService,
)
from backend.services.gemini_llm_service import (
    ExtractionStatus,
    JobRequirementExtractionService,
)


@dataclass
class FakeJob:
    id: UUID
    title: str
    description: str


class FakeRequirementLLM:
    model_name = "test-llm"

    def __init__(self, response: object) -> None:
        self.response = response

    def generate_json(
        self,
        *,
        prompt: str,
        response_schema: type[BaseModel],
    ) -> Mapping[str, Any] | str | BaseModel:
        assert "Extract structured job requirements" in prompt
        assert response_schema.__name__ == "JobRequirementExtraction"
        if isinstance(self.response, BaseModel | str):
            return self.response
        return self.response  # type: ignore[return-value]


class FakeEmbeddingProvider:
    model_name = "test-embedding"

    def __init__(self, vectors: list[list[float]] | None = None) -> None:
        self.vectors = vectors or [[1.0, 0.0], [0.5, 0.5]]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return self.vectors[: len(texts)]


class FailingEmbeddingProvider:
    model_name = "test-embedding"

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        raise GeminiEmbeddingError("embedding failed")


def test_job_requirement_extraction_validates_structured_output() -> None:
    job = FakeJob(
        id=uuid4(),
        title="Backend Engineer",
        description="Build FastAPI services. Requires Python and PostgreSQL. 3 years of experience.",
    )
    service = JobRequirementExtractionService(
        FakeRequirementLLM(
            {
                "required_skills": ["Python", "PostgreSQL", "Python"],
                "preferred_skills": ["FastAPI"],
                "responsibilities": ["Build FastAPI services"],
                "min_experience_years": 3,
                "work_authorization": "Authorized to work",
                "confidence": 0.91,
            }
        )
    )

    attempt = service.extract(job)

    assert attempt.status == ExtractionStatus.SUCCESS
    assert attempt.requirements is not None
    assert attempt.requirements.job_id == job.id
    assert attempt.requirements.required_skills == ["Python", "PostgreSQL"]
    assert attempt.requirements.confidence == 0.91
    assert attempt.requirements.raw_requirements["model_name"] == "test-llm"


def test_job_requirement_extraction_tracks_failed_outputs() -> None:
    job = FakeJob(id=uuid4(), title="Backend Engineer", description="Build APIs.")
    service = JobRequirementExtractionService(
        FakeRequirementLLM({"confidence": 4.2})
    )

    attempt = service.extract(job)

    assert attempt.status == ExtractionStatus.FAILED
    assert attempt.requirements is None
    assert attempt.error_message


def test_gemini_models_are_configurable_from_environment_settings() -> None:
    settings = Settings(
        DATABASE_URL="postgresql://user:pass@example.com:5432/careerfit",
        GEMINI_API_KEY="test-key",
        GEMINI_LLM_MODEL="custom-llm",
        GEMINI_EMBEDDING_MODEL="custom-embedding",
    )

    requirement_service = JobRequirementExtractionService.from_settings(settings)
    embedding_service = GeminiEmbeddingService.from_settings(settings)

    assert requirement_service._llm_client.model_name == "custom-llm"
    assert embedding_service._provider.model_name == "custom-embedding"


def test_embedding_service_returns_hashes_and_vectors() -> None:
    service = GeminiEmbeddingService(FakeEmbeddingProvider())

    result = service.embed_texts([" Python API ", "PostgreSQL"])

    assert result.status == EmbeddingStatus.SUCCESS
    assert len(result.embeddings) == 2
    assert result.embeddings[0].text == "Python API"
    assert result.embeddings[0].model_name == "test-embedding"
    assert result.embeddings[0].vector == (1.0, 0.0)


def test_embedding_service_tracks_failures() -> None:
    service = GeminiEmbeddingService(FailingEmbeddingProvider())

    result = service.embed_texts(["Python API"])

    assert result.status == EmbeddingStatus.FAILED
    assert result.embeddings == ()
    assert result.error_message == "embedding failed"
