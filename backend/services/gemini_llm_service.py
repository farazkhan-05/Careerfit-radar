from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Protocol
from uuid import UUID

from pydantic import BaseModel, Field, ValidationError, field_validator

from backend.config import Settings, get_settings
from backend.models.schemas import JobRequirementCreate
from backend.utils.text_utils import normalize_text


class GeminiServiceError(RuntimeError):
    pass


class ExtractionStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"


class RequirementLLM(Protocol):
    model_name: str

    def generate_json(
        self,
        *,
        prompt: str,
        response_schema: type[BaseModel],
    ) -> Mapping[str, Any] | str | BaseModel:
        pass


class ExtractableJob(Protocol):
    id: UUID
    title: str
    description: str


class JobRequirementExtraction(BaseModel):
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    min_experience_years: float | None = Field(default=None, ge=0, le=80)
    work_authorization: str | None = Field(default=None, max_length=255)
    confidence: float = Field(default=0.0, ge=0, le=1)

    @field_validator("required_skills", "preferred_skills", "responsibilities")
    @classmethod
    def normalize_list(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for item in value:
            cleaned = normalize_text(item)
            key = cleaned.casefold()
            if cleaned and key not in seen:
                seen.add(key)
                normalized.append(cleaned)
        return normalized

    @field_validator("work_authorization")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = normalize_text(value)
        return cleaned or None


@dataclass(frozen=True)
class JobRequirementExtractionAttempt:
    job_id: UUID
    status: ExtractionStatus
    model_name: str
    requirements: JobRequirementCreate | None = None
    raw_response: dict[str, Any] | None = None
    error_message: str | None = None


class GoogleGeminiLLMClient:
    def __init__(self, *, api_key: str, model_name: str) -> None:
        self._api_key = api_key
        self.model_name = model_name

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> GoogleGeminiLLMClient:
        resolved = settings or get_settings()
        return cls(
            api_key=resolved.gemini_api_key,
            model_name=resolved.gemini_llm_model,
        )

    def generate_json(
        self,
        *,
        prompt: str,
        response_schema: type[BaseModel],
    ) -> Mapping[str, Any] | str:
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:  # pragma: no cover - dependency guard.
            raise GeminiServiceError("google-genai is not installed.") from exc

        client = genai.Client(api_key=self._api_key)
        response = client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=response_schema,
            ),
        )
        if not response.text:
            raise GeminiServiceError("Gemini returned an empty response.")
        return response.text


class JobRequirementExtractionService:
    def __init__(self, llm_client: RequirementLLM) -> None:
        self._llm_client = llm_client

    @classmethod
    def from_settings(
        cls,
        settings: Settings | None = None,
    ) -> JobRequirementExtractionService:
        return cls(GoogleGeminiLLMClient.from_settings(settings))

    def extract(self, job: ExtractableJob) -> JobRequirementExtractionAttempt:
        try:
            raw_response = self._llm_client.generate_json(
                prompt=_build_job_requirement_prompt(job.title, job.description),
                response_schema=JobRequirementExtraction,
            )
            parsed = _coerce_requirement_extraction(raw_response)
            raw_dump = parsed.model_dump()
            return JobRequirementExtractionAttempt(
                job_id=job.id,
                status=ExtractionStatus.SUCCESS,
                model_name=self._llm_client.model_name,
                requirements=JobRequirementCreate(
                    job_id=job.id,
                    required_skills=parsed.required_skills,
                    preferred_skills=parsed.preferred_skills,
                    responsibilities=parsed.responsibilities,
                    min_experience_years=parsed.min_experience_years,
                    work_authorization=parsed.work_authorization,
                    confidence=parsed.confidence,
                    raw_requirements={
                        **raw_dump,
                        "model_name": self._llm_client.model_name,
                    },
                ),
                raw_response=raw_dump,
            )
        except (GeminiServiceError, ValidationError, json.JSONDecodeError) as exc:
            return JobRequirementExtractionAttempt(
                job_id=job.id,
                status=ExtractionStatus.FAILED,
                model_name=self._llm_client.model_name,
                error_message=str(exc),
            )


def _build_job_requirement_prompt(title: str, description: str) -> str:
    return (
        "Extract structured job requirements from the posting. Use only the provided "
        "job text. Return concise JSON that matches the schema. Do not add skills, "
        "experience, authorization, or responsibilities that are not supported by the "
        "posting.\n\n"
        f"Title:\n{normalize_text(title)}\n\n"
        f"Description:\n{normalize_text(description)}"
    )


def _coerce_requirement_extraction(
    raw_response: Mapping[str, Any] | str | BaseModel,
) -> JobRequirementExtraction:
    if isinstance(raw_response, JobRequirementExtraction):
        return raw_response
    if isinstance(raw_response, BaseModel):
        return JobRequirementExtraction.model_validate(raw_response.model_dump())
    if isinstance(raw_response, str):
        return JobRequirementExtraction.model_validate(json.loads(raw_response))
    return JobRequirementExtraction.model_validate(raw_response)
