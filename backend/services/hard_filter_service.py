from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from backend.models.schemas import RejectedJobCreate
from backend.utils.text_utils import normalize_for_match, normalize_text


class FilterableJob(Protocol):
    id: UUID
    title: str
    description: str
    location: str | None
    remote_type: str | None
    status: str


@dataclass(frozen=True)
class HardFilterConfig:
    excluded_keywords: tuple[str, ...] = (
        "senior",
        "lead",
        "staff",
        "principal",
        "manager",
        "architect",
        "director",
    )
    preferred_countries: tuple[str, ...] = ()
    preferred_work_modes: tuple[str, ...] = ()
    maximum_experience_years: float | None = None
    visa_sponsorship_required: bool = False
    relocation_open: bool = True
    remote_open: bool = True


@dataclass(frozen=True)
class RejectionDecision:
    job_id: UUID
    filter_name: str
    reason: str
    rejected_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    can_restore: bool = True

    def to_schema(self) -> RejectedJobCreate:
        return RejectedJobCreate(
            job_id=self.job_id,
            reason=self.reason,
            filter_name=self.filter_name,
            rejected_at=self.rejected_at,
            can_restore=self.can_restore,
        )


@dataclass(frozen=True)
class HardFilterResult:
    accepted_jobs: tuple[FilterableJob, ...]
    rejected_jobs: tuple[RejectionDecision, ...]


class HardFilterService:
    def __init__(self, config: HardFilterConfig) -> None:
        self._config = config

    def filter_jobs(self, jobs: list[FilterableJob]) -> HardFilterResult:
        accepted: list[FilterableJob] = []
        rejected: list[RejectionDecision] = []

        for job in jobs:
            decision = self.evaluate(job)
            if decision is None:
                accepted.append(job)
                continue

            job.status = "rejected"
            rejected.append(decision)

        return HardFilterResult(
            accepted_jobs=tuple(accepted),
            rejected_jobs=tuple(rejected),
        )

    def evaluate(self, job: FilterableJob) -> RejectionDecision | None:
        for rule in (
            self._excluded_keyword_rule,
            self._location_rule,
            self._work_mode_rule,
            self._experience_rule,
            self._visa_sponsorship_rule,
        ):
            decision = rule(job)
            if decision is not None:
                return decision
        return None

    def _excluded_keyword_rule(self, job: FilterableJob) -> RejectionDecision | None:
        haystack = normalize_for_match(f"{job.title} {job.description}")
        for keyword in self._config.excluded_keywords:
            normalized_keyword = normalize_for_match(keyword)
            if normalized_keyword and normalized_keyword in haystack:
                return self._decision(
                    job,
                    "excluded_keyword",
                    f"Matched excluded keyword: {normalize_text(keyword)}",
                )
        return None

    def _location_rule(self, job: FilterableJob) -> RejectionDecision | None:
        if not self._config.preferred_countries:
            return None
        if self._config.relocation_open:
            return None
        location = normalize_for_match(job.location or "")
        if not location:
            return None
        allowed_locations = [
            normalize_for_match(country)
            for country in self._config.preferred_countries
        ]
        if not any(country in location for country in allowed_locations):
            return self._decision(
                job,
                "location",
                f"Location is outside preferred countries: {job.location}",
            )
        return None

    def _work_mode_rule(self, job: FilterableJob) -> RejectionDecision | None:
        remote_type = normalize_for_match(job.remote_type or "")
        preferred_modes = {
            normalize_for_match(mode)
            for mode in self._config.preferred_work_modes
            if normalize_for_match(mode)
        }
        if remote_type == "remote" and not self._config.remote_open:
            return self._decision(job, "work_mode", "Remote roles are disabled.")
        if preferred_modes and remote_type and remote_type not in preferred_modes:
            return self._decision(
                job,
                "work_mode",
                f"Work mode is not preferred: {job.remote_type}",
            )
        return None

    def _experience_rule(self, job: FilterableJob) -> RejectionDecision | None:
        if self._config.maximum_experience_years is None:
            return None
        detected_years = _detect_required_experience_years(job.description)
        if detected_years is None:
            return None
        if detected_years > self._config.maximum_experience_years:
            return self._decision(
                job,
                "experience",
                (
                    f"Requires {detected_years:g}+ years, above configured maximum "
                    f"{self._config.maximum_experience_years:g}."
                ),
            )
        return None

    def _visa_sponsorship_rule(self, job: FilterableJob) -> RejectionDecision | None:
        if not self._config.visa_sponsorship_required:
            return None
        text = normalize_for_match(f"{job.title} {job.description}")
        blocked_phrases = (
            "no visa sponsorship",
            "visa sponsorship is not available",
            "does not sponsor visas",
            "we do not sponsor",
            "must be authorized to work without sponsorship",
        )
        if any(phrase in text for phrase in blocked_phrases):
            return self._decision(
                job,
                "visa_sponsorship",
                "Role indicates visa sponsorship is unavailable.",
            )
        return None

    @staticmethod
    def _decision(
        job: FilterableJob,
        filter_name: str,
        reason: str,
    ) -> RejectionDecision:
        return RejectionDecision(
            job_id=job.id,
            filter_name=filter_name,
            reason=reason,
        )


def _detect_required_experience_years(text: str) -> float | None:
    import re

    normalized = normalize_for_match(text)
    number = r"\d+(?:\.\d+)?"
    patterns = (
        rf"(?P<min>{number})\s*(?:-|to)\s*(?P<max>{number})\s*(?:years?|yrs?)\s+(?:of\s+)?experience",
        rf"(?P<single>{number})\+?\s*(?:years?|yrs?)\s+(?:of\s+)?experience",
        rf"experience\s+(?:of\s+)?(?P<single>{number})\+?\s*(?:years?|yrs?)",
        rf"(?:minimum|min|at\s+least)\s+(?P<single>{number})\+?\s*(?:years?|yrs?)",
    )
    matches: list[float] = []
    for pattern in patterns:
        for match in re.finditer(pattern, normalized):
            if match.groupdict().get("min"):
                matches.append(float(match.group("min")))
                continue
            single = match.groupdict().get("single")
            if single is not None:
                matches.append(float(single))
    if not matches:
        return None
    return min(matches)
