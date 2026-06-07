from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from backend.models.schemas import JobScoreCreate
from backend.utils.text_utils import normalize_for_match, normalize_text


class ScorableJob(Protocol):
    id: UUID
    title: str
    location: str | None
    remote_type: str | None
    posted_at: datetime | None
    source: str


class ScorableCandidateProfile(Protocol):
    id: UUID
    target_roles: list[str]
    skills: dict[str, Any]
    experience_years: float | None


class ScorableJobRequirement(Protocol):
    required_skills: list[str]
    preferred_skills: list[str]
    min_experience_years: float | None


@dataclass(frozen=True)
class ScoringPreferences:
    preferred_countries: tuple[str, ...] = ()
    preferred_work_modes: tuple[str, ...] = ()
    preferred_sources: tuple[str, ...] = (
        "greenhouse",
        "lever",
        "remotive",
        "arbeitnow",
    )


@dataclass(frozen=True)
class FitScoreWeights:
    role_match: int = 15
    skill_match: int = 25
    semantic_similarity: int = 20
    experience_fit: int = 15
    freshness: int = 10
    location_fit: int = 10
    source_reliability: int = 5

    def validate(self) -> None:
        total = (
            self.role_match
            + self.skill_match
            + self.semantic_similarity
            + self.experience_fit
            + self.freshness
            + self.location_fit
            + self.source_reliability
        )
        if total != 100:
            raise ValueError("Fit score weights must total 100.")


@dataclass(frozen=True)
class FitScoreResult:
    score: JobScoreCreate
    component_scores: dict[str, int]


class FitScoringService:
    def __init__(
        self,
        *,
        weights: FitScoreWeights | None = None,
        preferences: ScoringPreferences | None = None,
    ) -> None:
        self._weights = weights or FitScoreWeights()
        self._weights.validate()
        self._preferences = preferences or ScoringPreferences()

    def score_job(
        self,
        *,
        job: ScorableJob,
        candidate_profile: ScorableCandidateProfile,
        requirements: ScorableJobRequirement,
        semantic_similarity_score: int | None = None,
    ) -> FitScoreResult:
        matched_skills, missing_skills = _match_skills(candidate_profile, requirements)
        component_scores = {
            "role_match_score": _weighted_score(
                _role_match_ratio(job.title, candidate_profile.target_roles),
                self._weights.role_match,
            ),
            "skill_match_score": _weighted_score(
                _skill_match_ratio(matched_skills, requirements.required_skills),
                self._weights.skill_match,
            ),
            "semantic_similarity_score": _bounded_component(
                semantic_similarity_score,
                self._weights.semantic_similarity,
            ),
            "experience_fit_score": _weighted_score(
                _experience_fit_ratio(
                    candidate_profile.experience_years,
                    requirements.min_experience_years,
                ),
                self._weights.experience_fit,
            ),
            "freshness_score": _weighted_score(
                _freshness_ratio(job.posted_at),
                self._weights.freshness,
            ),
            "location_fit_score": _weighted_score(
                _location_fit_ratio(
                    location=job.location,
                    remote_type=job.remote_type,
                    preferences=self._preferences,
                ),
                self._weights.location_fit,
            ),
            "source_reliability_score": _weighted_score(
                _source_reliability_ratio(job.source, self._preferences),
                self._weights.source_reliability,
            ),
        }
        final_score = min(100, sum(component_scores.values()))
        risk_flags = _risk_flags(
            missing_skills=missing_skills,
            candidate_years=candidate_profile.experience_years,
            required_years=requirements.min_experience_years,
        )
        score = JobScoreCreate(
            job_id=job.id,
            candidate_profile_id=candidate_profile.id,
            final_score=final_score,
            role_match_score=component_scores["role_match_score"],
            skill_match_score=component_scores["skill_match_score"],
            semantic_similarity_score=component_scores["semantic_similarity_score"],
            experience_fit_score=component_scores["experience_fit_score"],
            freshness_score=component_scores["freshness_score"],
            location_fit_score=component_scores["location_fit_score"],
            source_reliability_score=component_scores["source_reliability_score"],
            matched_skills=matched_skills,
            missing_skills=missing_skills,
            risk_flags=risk_flags,
            explanation=_build_explanation(
                final_score=final_score,
                matched_skills=matched_skills,
                missing_skills=missing_skills,
                risk_flags=risk_flags,
            ),
        )
        return FitScoreResult(score=score, component_scores=component_scores)


def _candidate_skill_set(candidate_profile: ScorableCandidateProfile) -> set[str]:
    values: list[str] = []
    for raw_value in candidate_profile.skills.values():
        if isinstance(raw_value, list):
            values.extend(str(item) for item in raw_value)
        elif isinstance(raw_value, dict):
            for nested_value in raw_value.values():
                if isinstance(nested_value, list):
                    values.extend(str(item) for item in nested_value)
                elif nested_value is not None:
                    values.append(str(nested_value))
        elif raw_value is not None:
            values.append(str(raw_value))
    return {normalize_for_match(value) for value in values if normalize_text(value)}


def _match_skills(
    candidate_profile: ScorableCandidateProfile,
    requirements: ScorableJobRequirement,
) -> tuple[list[str], list[str]]:
    candidate_skills = _candidate_skill_set(candidate_profile)
    required = _dedupe(requirements.required_skills)
    preferred = _dedupe(requirements.preferred_skills)
    all_skills = required + [skill for skill in preferred if skill not in required]
    matched = [
        skill
        for skill in all_skills
        if normalize_for_match(skill) in candidate_skills
    ]
    missing = [
        skill
        for skill in required
        if normalize_for_match(skill) not in candidate_skills
    ]
    return matched, missing


def _role_match_ratio(title: str, target_roles: list[str]) -> float:
    normalized_title = normalize_for_match(title)
    if not target_roles:
        return 0.5
    if any(normalize_for_match(role) in normalized_title for role in target_roles):
        return 1.0
    title_terms = set(normalized_title.split())
    best_overlap = 0.0
    for role in target_roles:
        role_terms = set(normalize_for_match(role).split())
        if role_terms:
            best_overlap = max(best_overlap, len(title_terms & role_terms) / len(role_terms))
    return best_overlap


def _skill_match_ratio(matched_skills: list[str], required_skills: list[str]) -> float:
    required = _dedupe(required_skills)
    if not required:
        return 1.0
    required_keys = {normalize_for_match(skill) for skill in required}
    matched_keys = {normalize_for_match(skill) for skill in matched_skills}
    return len(required_keys & matched_keys) / len(required_keys)


def _experience_fit_ratio(
    candidate_years: float | None,
    required_years: float | None,
) -> float:
    if required_years is None:
        return 1.0
    if candidate_years is None:
        return 0.4
    if candidate_years >= required_years:
        return 1.0
    return max(0.0, candidate_years / required_years)


def _freshness_ratio(posted_at: datetime | None) -> float:
    if posted_at is None:
        return 0.5
    age_days = max(0, (datetime.now(UTC) - posted_at.astimezone(UTC)).days)
    if age_days <= 7:
        return 1.0
    if age_days <= 30:
        return 0.75
    if age_days <= 90:
        return 0.45
    return 0.2


def _location_fit_ratio(
    *,
    location: str | None,
    remote_type: str | None,
    preferences: ScoringPreferences,
) -> float:
    if normalize_for_match(remote_type or "") == "remote":
        return 1.0
    if not preferences.preferred_countries:
        return 0.7
    normalized_location = normalize_for_match(location or "")
    if any(normalize_for_match(country) in normalized_location for country in preferences.preferred_countries):
        return 1.0
    return 0.3


def _source_reliability_ratio(source: str, preferences: ScoringPreferences) -> float:
    preferred_sources = {normalize_for_match(value) for value in preferences.preferred_sources}
    return 1.0 if normalize_for_match(source) in preferred_sources else 0.6


def _weighted_score(ratio: float, weight: int) -> int:
    return round(max(0.0, min(1.0, ratio)) * weight)


def _bounded_component(value: int | None, max_score: int) -> int:
    if value is None:
        return 0
    return max(0, min(max_score, value))


def _risk_flags(
    *,
    missing_skills: list[str],
    candidate_years: float | None,
    required_years: float | None,
) -> list[str]:
    flags: list[str] = []
    if missing_skills:
        flags.append("missing_required_skills")
    if (
        candidate_years is not None
        and required_years is not None
        and candidate_years < required_years
    ):
        flags.append("experience_below_requirement")
    return flags


def _build_explanation(
    *,
    final_score: int,
    matched_skills: list[str],
    missing_skills: list[str],
    risk_flags: list[str],
) -> str:
    matched = ", ".join(matched_skills) if matched_skills else "no required skills"
    missing = ", ".join(missing_skills) if missing_skills else "none"
    risks = ", ".join(risk_flags) if risk_flags else "none"
    return (
        f"Fit score {final_score}/100. Matched skills: {matched}. "
        f"Missing required skills: {missing}. Risk flags: {risks}."
    )


def _dedupe(values: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = normalize_text(value)
        key = normalize_for_match(cleaned)
        if cleaned and key not in seen:
            seen.add(key)
            deduped.append(cleaned)
    return deduped
