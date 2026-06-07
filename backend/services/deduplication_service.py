from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Protocol
from uuid import UUID

from backend.utils.hash_utils import sha256_text
from backend.utils.text_utils import normalize_for_match


class DeduplicatableJob(Protocol):
    id: UUID
    company_id: UUID
    canonical_job_id: UUID | None
    source: str
    source_job_id: str
    title: str
    location: str | None
    apply_url: str
    description: str
    status: str


@dataclass(frozen=True)
class DuplicateDecision:
    duplicate_job_id: UUID
    canonical_job_id: UUID
    reason: str
    confidence: float


@dataclass(frozen=True)
class DeduplicationResult:
    canonical_jobs: tuple[DeduplicatableJob, ...]
    duplicates: tuple[DuplicateDecision, ...]


@dataclass(frozen=True)
class DeduplicationConfig:
    fuzzy_threshold: float = 0.92
    description_prefix_chars: int = 1200


class DeduplicationService:
    def __init__(self, config: DeduplicationConfig | None = None) -> None:
        self._config = config or DeduplicationConfig()

    def deduplicate(self, jobs: list[DeduplicatableJob]) -> DeduplicationResult:
        canonical_jobs: list[DeduplicatableJob] = []
        duplicates: list[DuplicateDecision] = []
        exact_index: dict[str, DeduplicatableJob] = {}

        for job in jobs:
            canonical = self._find_exact_duplicate(job, exact_index)
            reason = "exact"
            confidence = 1.0

            if canonical is None:
                fuzzy = self._find_fuzzy_duplicate(job, canonical_jobs)
                if fuzzy is not None:
                    canonical, confidence = fuzzy
                    reason = "fuzzy"

            if canonical is None:
                canonical_jobs.append(job)
                for key in self._exact_keys(job):
                    exact_index.setdefault(key, job)
                continue

            job.canonical_job_id = canonical.id
            job.status = "duplicate"
            duplicates.append(
                DuplicateDecision(
                    duplicate_job_id=job.id,
                    canonical_job_id=canonical.id,
                    reason=reason,
                    confidence=round(confidence, 4),
                )
            )

        return DeduplicationResult(
            canonical_jobs=tuple(canonical_jobs),
            duplicates=tuple(duplicates),
        )

    def _find_exact_duplicate(
        self,
        job: DeduplicatableJob,
        exact_index: dict[str, DeduplicatableJob],
    ) -> DeduplicatableJob | None:
        for key in self._exact_keys(job):
            existing = exact_index.get(key)
            if existing is not None:
                return existing
        return None

    def _find_fuzzy_duplicate(
        self,
        job: DeduplicatableJob,
        canonical_jobs: list[DeduplicatableJob],
    ) -> tuple[DeduplicatableJob, float] | None:
        best_job: DeduplicatableJob | None = None
        best_score = 0.0
        for candidate in canonical_jobs:
            if candidate.company_id != job.company_id:
                continue
            score = self._similarity_score(candidate, job)
            if score > best_score:
                best_job = candidate
                best_score = score

        if best_job is None or best_score < self._config.fuzzy_threshold:
            return None
        return best_job, best_score

    def _exact_keys(self, job: DeduplicatableJob) -> tuple[str, ...]:
        source_key = f"source:{job.source}:{job.source_job_id}"
        apply_url = normalize_for_match(job.apply_url).rstrip("/")
        url_key = f"url:{apply_url}" if apply_url else ""
        fingerprint = _job_fingerprint(
            title=job.title,
            company_id=job.company_id,
            location=job.location,
            description=job.description,
            prefix_chars=self._config.description_prefix_chars,
        )
        return tuple(key for key in (source_key, url_key, f"fingerprint:{fingerprint}") if key)

    def _similarity_score(
        self,
        candidate: DeduplicatableJob,
        job: DeduplicatableJob,
    ) -> float:
        title_score = _ratio(candidate.title, job.title)
        location_score = _ratio(candidate.location or "", job.location or "")
        description_score = _ratio(
            candidate.description[: self._config.description_prefix_chars],
            job.description[: self._config.description_prefix_chars],
        )
        return (title_score * 0.5) + (description_score * 0.4) + (location_score * 0.1)


def _job_fingerprint(
    *,
    title: str,
    company_id: UUID,
    location: str | None,
    description: str,
    prefix_chars: int,
) -> str:
    normalized = "|".join(
        [
            str(company_id),
            normalize_for_match(title),
            normalize_for_match(location or ""),
            normalize_for_match(description[:prefix_chars]),
        ]
    )
    return sha256_text(normalized)


def _ratio(left: str, right: str) -> float:
    return SequenceMatcher(
        None,
        normalize_for_match(left),
        normalize_for_match(right),
        autojunk=False,
    ).ratio()
