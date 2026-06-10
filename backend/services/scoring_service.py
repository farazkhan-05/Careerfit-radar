from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from backend.models.schemas import JobScoreCreate
from backend.utils.text_utils import normalize_for_match, normalize_text

_NON_WORD_RE = re.compile(r"[^a-z0-9]+")
_COMPACT_RE = re.compile(r"[^a-z0-9]+")

_SKILL_SYNONYMS: dict[str, tuple[str, ...]] = {
    "angular": ("angularjs", "angular.js", "angular js"),
    "aws": ("amazon web services",),
    "c sharp": ("c#", "csharp"),
    "ci cd": ("ci/cd", "cicd", "continuous integration", "continuous delivery"),
    "css": ("css3", "cascading style sheets"),
    "express": ("express.js", "expressjs", "express js"),
    "fastapi": ("fast api",),
    "frontend": ("front end", "front-end"),
    "frontend engineer": (
        "front end engineer",
        "front-end engineer",
        "frontend developer",
        "front end developer",
        "front-end developer",
    ),
    "git": ("github", "gitlab"),
    "html": ("html5",),
    "javascript": ("js", "ecmascript", "java script"),
    "kubernetes": ("k8s",),
    "mongodb": ("mongo db", "mongo"),
    "node": ("node.js", "nodejs", "node js"),
    "postgresql": ("postgres", "postgres sql"),
    "react": ("react.js", "reactjs", "react js"),
    "software engineer": (
        "software developer",
        "software engineering",
        "full time software engineer",
        "full-time software engineer",
        "fulltime software engineer",
        "full time software engineering",
        "full-time software engineering",
        "fulltime software engineering",
    ),
    "typescript": ("ts", "type script"),
    "vue": ("vue.js", "vuejs", "vue js"),
}

_ALIAS_TO_CANONICAL = {
    alias: canonical
    for canonical, aliases in _SKILL_SYNONYMS.items()
    for alias in (
        _NON_WORD_RE.sub(" ", canonical.casefold()).strip(),
        *(_NON_WORD_RE.sub(" ", item.casefold()).strip() for item in aliases),
    )
}

_CANONICAL_TO_ALIASES: dict[str, frozenset[str]] = {
    canonical: frozenset(
        _NON_WORD_RE.sub(" ", item.casefold()).strip()
        for item in (canonical, *aliases)
    )
    for canonical, aliases in _SKILL_SYNONYMS.items()
}

_BLOCKED_OVERLAPS = {
    frozenset(("java", "javascript")),
    frozenset(("go", "django")),
    frozenset(("r", "rust")),
    frozenset(("sql", "nosql")),
}


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
        "tavily_search",
        "manual",
        "greenhouse",
        "lever",
        "smartrecruiters",
    )


@dataclass(frozen=True)
class FitScoreWeights:
    role_match: int = 18
    skill_match: int = 30
    semantic_similarity: int = 22
    experience_fit: int = 10
    freshness: int = 8
    location_fit: int = 7
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
        semantic_component = (
            _bounded_component(semantic_similarity_score, self._weights.semantic_similarity)
            if semantic_similarity_score is not None
            else _weighted_score(
                _semantic_similarity_ratio(
                    job=job,
                    candidate_profile=candidate_profile,
                    requirements=requirements,
                    matched_skills=matched_skills,
                ),
                self._weights.semantic_similarity,
            )
        )
        component_scores = {
            "role_match_score": _weighted_score(
                _role_match_ratio(job.title, candidate_profile.target_roles),
                self._weights.role_match,
            ),
            "skill_match_score": _weighted_score(
                _skill_match_ratio(
                    matched_skills,
                    requirements.required_skills,
                    requirements.preferred_skills,
                ),
                self._weights.skill_match,
            ),
            "semantic_similarity_score": semantic_component,
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
    values.extend(str(role) for role in candidate_profile.target_roles)
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
    return {
        _canonical_lookup_key(_normalize_lookup_key(value))
        for value in values
        if normalize_text(value)
    }


def _match_skills(
    candidate_profile: ScorableCandidateProfile,
    requirements: ScorableJobRequirement,
) -> tuple[list[str], list[str]]:
    candidate_skills = _candidate_skill_set(candidate_profile)
    required = _dedupe(requirements.required_skills)
    preferred = _dedupe(requirements.preferred_skills)
    required_keys = {_canonical_lookup_key(_normalize_lookup_key(skill)) for skill in required}
    all_skills = required + [
        skill
        for skill in preferred
        if _canonical_lookup_key(_normalize_lookup_key(skill)) not in required_keys
    ]
    matched = [
        skill
        for skill in all_skills
        if _skill_matches_candidate(skill, candidate_skills)
    ]
    missing = [
        skill
        for skill in required
        if not _skill_matches_candidate(skill, candidate_skills)
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


def _skill_match_ratio(
    matched_skills: list[str],
    required_skills: list[str],
    preferred_skills: list[str],
) -> float:
    required = _dedupe(required_skills)
    preferred = _dedupe(preferred_skills)
    matched_keys = {_canonical_lookup_key(_normalize_lookup_key(skill)) for skill in matched_skills}
    if required:
        required_keys = {_canonical_lookup_key(_normalize_lookup_key(skill)) for skill in required}
        return len(required_keys & matched_keys) / len(required_keys)
    if preferred:
        preferred_keys = {_canonical_lookup_key(_normalize_lookup_key(skill)) for skill in preferred}
        return len(preferred_keys & matched_keys) / len(preferred_keys)
    return 0.4


def _experience_fit_ratio(
    candidate_years: float | None,
    required_years: float | None,
) -> float:
    if required_years is None:
        return 0.7
    if candidate_years is None:
        return 0.4
    candidate_years = max(0.0, float(candidate_years))
    required_years = max(0.0, float(required_years))
    if required_years == 0:
        return 1.0
    if candidate_years >= required_years:
        return 1.0
    return candidate_years / required_years


def _freshness_ratio(posted_at: datetime | None) -> float:
    if posted_at is None:
        return 0.7
    age_days = max(0, (datetime.now(UTC) - posted_at.astimezone(UTC)).days)
    if age_days <= 7:
        return 1.0
    if age_days <= 14:
        return 0.75
    if age_days <= 30:
        return 0.3
    return 0.0


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


def _semantic_similarity_ratio(
    *,
    job: ScorableJob,
    candidate_profile: ScorableCandidateProfile,
    requirements: ScorableJobRequirement,
    matched_skills: list[str],
) -> float:
    role_ratio = _role_match_ratio(job.title, candidate_profile.target_roles)
    visible_skill_ratio = _visible_skill_signal_ratio(
        matched_skills,
        requirements.required_skills,
        requirements.preferred_skills,
    )
    term_ratio = _profile_term_presence_ratio(job=job, candidate_profile=candidate_profile)
    if visible_skill_ratio == 0 and term_ratio == 0:
        return role_ratio * 0.35
    return (role_ratio * 0.3) + (visible_skill_ratio * 0.5) + (term_ratio * 0.2)


def _visible_skill_signal_ratio(
    matched_skills: list[str],
    required_skills: list[str],
    preferred_skills: list[str],
) -> float:
    required = _dedupe(required_skills)
    preferred = _dedupe(preferred_skills)
    visible = required + [skill for skill in preferred if skill not in required]
    if not visible:
        return 0.0
    visible_keys = {_canonical_lookup_key(_normalize_lookup_key(skill)) for skill in visible}
    matched_keys = {_canonical_lookup_key(_normalize_lookup_key(skill)) for skill in matched_skills}
    return len(visible_keys & matched_keys) / len(visible_keys)


def _profile_term_presence_ratio(
    *,
    job: ScorableJob,
    candidate_profile: ScorableCandidateProfile,
) -> float:
    terms = _candidate_profile_terms(candidate_profile)
    if not terms:
        return 0.0
    job_text = _normalize_lookup_key(
        " ".join(
            (
                job.title,
                getattr(job, "description", "") or "",
                job.location or "",
                job.remote_type or "",
            )
        )
    )
    matched = sum(1 for term in terms if _term_present_in_text(term, job_text))
    return min(1.0, matched / min(len(terms), 6))


def _candidate_profile_terms(candidate_profile: ScorableCandidateProfile) -> tuple[str, ...]:
    values: list[str] = []
    values.extend(str(role) for role in candidate_profile.target_roles)
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
    projects = getattr(candidate_profile, "projects", []) or []
    for project in projects:
        if not isinstance(project, dict):
            continue
        for technology in project.get("technologies") or []:
            values.append(str(technology))

    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        key = _canonical_lookup_key(_normalize_lookup_key(value))
        if key and key not in seen:
            seen.add(key)
            deduped.append(key)
    return tuple(deduped)


def _term_present_in_text(term_key: str, text_key: str) -> bool:
    if not term_key or not text_key:
        return False
    equivalent_terms = _equivalent_keys(term_key)
    text_tokens = set(_tokenize_key(text_key))
    text_compact_tokens = {_compact_key(token) for token in text_tokens}
    for candidate in equivalent_terms:
        candidate_tokens = set(_tokenize_key(candidate))
        if candidate_tokens and candidate_tokens.issubset(text_tokens):
            return True
        compact = _compact_key(candidate)
        if compact and compact in text_compact_tokens:
            return True
    return False


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


def _skill_matches_candidate(skill: str, candidate_skills: set[str]) -> bool:
    key = _canonical_lookup_key(_normalize_lookup_key(skill))
    if key in candidate_skills:
        return True
    return any(_has_logical_overlap(key, candidate_key) for candidate_key in candidate_skills)


def _normalize_lookup_key(value: str) -> str:
    normalized = normalize_for_match(value)
    normalized = normalized.replace("&", " and ")
    normalized = normalized.replace("+", " plus ")
    return _NON_WORD_RE.sub(" ", normalized).strip()


def _canonical_lookup_key(value: str) -> str:
    key = _normalize_lookup_key(value)
    return _ALIAS_TO_CANONICAL.get(key, key)


def _equivalent_keys(key: str) -> frozenset[str]:
    canonical = _canonical_lookup_key(key)
    return _CANONICAL_TO_ALIASES.get(canonical, frozenset((canonical,)))


def _has_logical_overlap(required_key: str, evidence_key: str) -> bool:
    if not required_key or not evidence_key:
        return False
    if required_key == evidence_key:
        return True
    if frozenset((required_key, evidence_key)) in _BLOCKED_OVERLAPS:
        return False

    required_tokens = set(_tokenize_key(required_key))
    evidence_tokens = set(_tokenize_key(evidence_key))
    meaningful_required = {token for token in required_tokens if len(token) >= 4}
    meaningful_evidence = {token for token in evidence_tokens if len(token) >= 4}
    if meaningful_required and meaningful_required.issubset(meaningful_evidence):
        return True
    if meaningful_evidence and meaningful_evidence.issubset(meaningful_required):
        return True

    required_compact = _compact_key(required_key)
    evidence_compact = _compact_key(evidence_key)
    if not required_compact or not evidence_compact:
        return False
    if frozenset((required_compact, evidence_compact)) in _BLOCKED_OVERLAPS:
        return False

    shorter, longer = sorted((required_compact, evidence_compact), key=len)
    if len(shorter) < 4:
        return False
    return longer.startswith(shorter)


def _compact_key(value: str) -> str:
    return _COMPACT_RE.sub("", value)


def _tokenize_key(value: str) -> tuple[str, ...]:
    return tuple(token for token in _NON_WORD_RE.split(value) if token)
