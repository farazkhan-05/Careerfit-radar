from __future__ import annotations

import json
import uuid
from typing import Any, Mapping, Protocol

from pydantic import BaseModel, Field, ValidationError, field_validator

from backend.models.schemas import CandidateProfileCreate
from backend.utils.text_utils import normalize_for_match, normalize_text


class ProfileExtractionError(RuntimeError):
    pass


class ProfileLLM(Protocol):
    def generate_profile(self, prompt: str) -> Mapping[str, Any] | str | BaseModel:
        pass


class EvidenceItem(BaseModel):
    value: str = Field(min_length=1, max_length=255)
    evidence: str = Field(min_length=1)

    @field_validator("value", "evidence")
    @classmethod
    def normalize(cls, value: str) -> str:
        return normalize_text(value)


class ProjectExtraction(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    summary: str = Field(min_length=1)
    technologies: list[str] = Field(default_factory=list)
    evidence: str = Field(min_length=1)

    @field_validator("name", "summary", "evidence")
    @classmethod
    def normalize_text_fields(cls, value: str) -> str:
        return normalize_text(value)


class CandidateProfileExtraction(BaseModel):
    target_roles: list[EvidenceItem] = Field(default_factory=list)
    technical_skills: list[EvidenceItem] = Field(default_factory=list)
    tools: list[EvidenceItem] = Field(default_factory=list)
    domains: list[EvidenceItem] = Field(default_factory=list)
    soft_skills: list[EvidenceItem] = Field(default_factory=list)
    experience_years: float | None = Field(default=None, ge=0, le=80)
    experience_evidence: str | None = None
    projects: list[ProjectExtraction] = Field(default_factory=list)


class GeminiProfileClient:
    def __init__(self, *, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    def generate_profile(self, prompt: str) -> Mapping[str, Any] | str:
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:  # pragma: no cover - dependency guard.
            raise ProfileExtractionError("google-genai is not installed.") from exc

        client = genai.Client(api_key=self._api_key)
        response = client.models.generate_content(
            model=self._model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=CandidateProfileExtraction,
            ),
        )
        return response.text or "{}"


class CandidateProfileService:
    def __init__(self, llm_client: ProfileLLM) -> None:
        self._llm_client = llm_client

    def extract_profile(
        self,
        *,
        resume_id: uuid.UUID,
        resume_text: str,
    ) -> CandidateProfileCreate:
        normalized_resume = normalize_text(resume_text)
        if not normalized_resume:
            raise ProfileExtractionError("Resume text is required.")

        raw_response = self._llm_client.generate_profile(_build_prompt(normalized_resume))
        extraction = _coerce_extraction(raw_response)
        supported = _remove_unsupported_claims(extraction, normalized_resume)

        return CandidateProfileCreate(
            resume_id=resume_id,
            target_roles=[item.value for item in supported.target_roles],
            skills={
                "technical": [item.value for item in supported.technical_skills],
                "tools": [item.value for item in supported.tools],
                "domains": [item.value for item in supported.domains],
                "soft": [item.value for item in supported.soft_skills],
            },
            experience_years=supported.experience_years,
            projects=[
                {
                    "name": project.name,
                    "summary": project.summary,
                    "technologies": project.technologies,
                    "evidence": project.evidence,
                }
                for project in supported.projects
            ],
            raw_profile=supported.model_dump(),
        )


def _build_prompt(resume_text: str) -> str:
    return (
        "Extract a candidate profile from the resume text. Return JSON matching the "
        "provided schema. Every role, skill, project, and experience claim must include "
        "a short exact evidence quote copied from the resume. Do not infer unsupported "
        "facts.\n\nResume:\n"
        f"{resume_text}"
    )


def _coerce_extraction(raw_response: Mapping[str, Any] | str | BaseModel) -> CandidateProfileExtraction:
    try:
        if isinstance(raw_response, CandidateProfileExtraction):
            return raw_response
        if isinstance(raw_response, BaseModel):
            return CandidateProfileExtraction.model_validate(raw_response.model_dump())
        if isinstance(raw_response, str):
            return CandidateProfileExtraction.model_validate(json.loads(raw_response))
        return CandidateProfileExtraction.model_validate(raw_response)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise ProfileExtractionError("Candidate profile response failed validation.") from exc


def _remove_unsupported_claims(
    extraction: CandidateProfileExtraction,
    resume_text: str,
) -> CandidateProfileExtraction:
    filtered = extraction.model_copy(deep=True)
    filtered.target_roles = _supported_items(extraction.target_roles, resume_text)
    filtered.technical_skills = _supported_items(extraction.technical_skills, resume_text)
    filtered.tools = _supported_items(extraction.tools, resume_text)
    filtered.domains = _supported_items(extraction.domains, resume_text)
    filtered.soft_skills = _supported_items(extraction.soft_skills, resume_text)
    filtered.projects = [
        project
        for project in extraction.projects
        if _evidence_is_supported(project.evidence, resume_text)
    ]
    if extraction.experience_years is not None and not _evidence_is_supported(
        extraction.experience_evidence or "",
        resume_text,
    ):
        filtered.experience_years = None
        filtered.experience_evidence = None
    return filtered


def _supported_items(items: list[EvidenceItem], resume_text: str) -> list[EvidenceItem]:
    deduped: list[EvidenceItem] = []
    seen: set[str] = set()
    for item in items:
        key = normalize_for_match(item.value)
        if key not in seen and _evidence_is_supported(item.evidence, resume_text):
            seen.add(key)
            deduped.append(item)
    return deduped


def _evidence_is_supported(evidence: str, resume_text: str) -> bool:
    normalized_evidence = normalize_for_match(evidence)
    return bool(normalized_evidence) and normalized_evidence in normalize_for_match(resume_text)
