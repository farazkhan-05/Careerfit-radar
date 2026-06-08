from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Protocol

from backend.utils.text_utils import normalize_for_match, normalize_text


class GapCandidateProfile(Protocol):
    target_roles: list[str]
    skills: dict[str, Any]
    projects: list[dict[str, Any]]
    experience_years: float | None


class GapJobRequirement(Protocol):
    required_skills: list[str]
    preferred_skills: list[str]
    responsibilities: list[str]
    min_experience_years: float | None


@dataclass(frozen=True)
class SkillEvidence:
    skill: str
    evidence: str


@dataclass(frozen=True)
class GapAnalysis:
    matched_required_skills: tuple[SkillEvidence, ...]
    matched_preferred_skills: tuple[SkillEvidence, ...]
    missing_required_skills: tuple[str, ...]
    missing_preferred_skills: tuple[str, ...]
    experience_gap: str | None
    application_guidance: tuple[str, ...]
    risk_flags: tuple[str, ...]


class GapAnalysisService:
    def analyze(
        self,
        *,
        candidate_profile: GapCandidateProfile,
        requirements: GapJobRequirement,
    ) -> GapAnalysis:
        evidence_index = _build_evidence_index(candidate_profile)
        matched_required, missing_required = _match_with_evidence(
            requirements.required_skills,
            evidence_index,
        )
        matched_preferred, missing_preferred = _match_with_evidence(
            requirements.preferred_skills,
            evidence_index,
        )
        experience_gap = _experience_gap(
            candidate_profile.experience_years,
            requirements.min_experience_years,
        )
        risk_flags = _risk_flags(
            missing_required=missing_required,
            experience_gap=experience_gap,
        )
        return GapAnalysis(
            matched_required_skills=tuple(matched_required),
            matched_preferred_skills=tuple(matched_preferred),
            missing_required_skills=tuple(missing_required),
            missing_preferred_skills=tuple(missing_preferred),
            experience_gap=experience_gap,
            application_guidance=tuple(
                _application_guidance(
                    matched_required=matched_required,
                    matched_preferred=matched_preferred,
                    missing_required=missing_required,
                    experience_gap=experience_gap,
                )
            ),
            risk_flags=tuple(risk_flags),
        )


_NON_WORD_RE = re.compile(r"[^a-z0-9]+")
_COMPACT_RE = re.compile(r"[^a-z0-9]+")


def _normalize_lookup_key(value: str) -> str:
    normalized = normalize_for_match(value)
    normalized = normalized.replace("&", " and ")
    normalized = normalized.replace("+", " plus ")
    return _NON_WORD_RE.sub(" ", normalized).strip()

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
    for alias in (_normalize_lookup_key(canonical), *(_normalize_lookup_key(item) for item in aliases))
}

_CANONICAL_TO_ALIASES: dict[str, frozenset[str]] = {
    canonical: frozenset(
        _normalize_lookup_key(item)
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


def _build_evidence_index(candidate_profile: GapCandidateProfile) -> dict[str, str]:
    evidence: dict[str, str] = {}
    for skill in _flatten_skills(candidate_profile.skills):
        evidence.setdefault(_normalize_lookup_key(skill), f"Resume skill: {normalize_text(skill)}")

    for role in candidate_profile.target_roles:
        evidence.setdefault(_normalize_lookup_key(role), f"Resume target role: {normalize_text(role)}")

    for project in candidate_profile.projects:
        project_name = normalize_text(str(project.get("name") or "Project"))
        project_evidence = normalize_text(str(project.get("evidence") or project.get("summary") or project_name))
        for technology in project.get("technologies") or []:
            evidence.setdefault(
                _normalize_lookup_key(str(technology)),
                f"{project_name}: {project_evidence}",
            )
    return evidence


def _flatten_skills(skills: dict[str, Any]) -> list[str]:
    flattened: list[str] = []
    for value in skills.values():
        if isinstance(value, list):
            flattened.extend(str(item) for item in value)
        elif isinstance(value, dict):
            for nested in value.values():
                if isinstance(nested, list):
                    flattened.extend(str(item) for item in nested)
                elif nested is not None:
                    flattened.append(str(nested))
        elif value is not None:
            flattened.append(str(value))
    return [normalize_text(skill) for skill in flattened if normalize_text(skill)]


def _match_with_evidence(
    skills: list[str],
    evidence_index: dict[str, str],
) -> tuple[list[SkillEvidence], list[str]]:
    matched: list[SkillEvidence] = []
    missing: list[str] = []
    seen: set[str] = set()
    evidence_keys = tuple(evidence_index)
    for skill in skills:
        cleaned = normalize_text(skill)
        key = _normalize_lookup_key(cleaned)
        seen_key = _canonical_lookup_key(key)
        if not cleaned or seen_key in seen:
            continue
        seen.add(seen_key)
        evidence = _find_evidence(key, evidence_index, evidence_keys)
        if evidence is None:
            missing.append(cleaned)
        else:
            matched.append(SkillEvidence(skill=cleaned, evidence=evidence))
    return matched, missing


def _find_evidence(
    required_key: str,
    evidence_index: dict[str, str],
    evidence_keys: tuple[str, ...],
) -> str | None:
    evidence = evidence_index.get(required_key)
    if evidence is not None:
        return evidence

    for alias in _equivalent_keys(required_key):
        evidence = evidence_index.get(alias)
        if evidence is not None:
            return evidence

    required_canonical = _canonical_lookup_key(required_key)
    for evidence_key in evidence_keys:
        if _has_logical_overlap(required_canonical, _canonical_lookup_key(evidence_key)):
            return evidence_index[evidence_key]
    return None


def _equivalent_keys(key: str) -> frozenset[str]:
    canonical = _canonical_lookup_key(key)
    return _CANONICAL_TO_ALIASES.get(canonical, frozenset((canonical,)))


def _canonical_lookup_key(value: str) -> str:
    key = _normalize_lookup_key(value)
    return _ALIAS_TO_CANONICAL.get(key, key)


def _has_logical_overlap(required_key: str, evidence_key: str) -> bool:
    if not required_key or not evidence_key:
        return False
    if required_key == evidence_key:
        return True
    if frozenset((required_key, evidence_key)) in _BLOCKED_OVERLAPS:
        return False

    required_tokens = set(_tokenize_key(required_key))
    evidence_tokens = set(_tokenize_key(evidence_key))
    if required_tokens and evidence_tokens:
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


def _experience_gap(
    candidate_years: float | None,
    required_years: float | None,
) -> str | None:
    if required_years is None:
        return None
    if candidate_years is None:
        return f"Job asks for {required_years:g}+ years; resume experience is not explicit."
    if candidate_years >= required_years:
        return None
    return (
        f"Job asks for {required_years:g}+ years; resume supports "
        f"{candidate_years:g} years."
    )


def _risk_flags(*, missing_required: list[str], experience_gap: str | None) -> list[str]:
    flags: list[str] = []
    if missing_required:
        flags.append("missing_required_skills")
    if experience_gap is not None:
        flags.append("experience_gap")
    return flags


def _application_guidance(
    *,
    matched_required: list[SkillEvidence],
    matched_preferred: list[SkillEvidence],
    missing_required: list[str],
    experience_gap: str | None,
) -> list[str]:
    guidance: list[str] = []
    if matched_required:
        skills = ", ".join(item.skill for item in matched_required[:5])
        guidance.append(f"Lead with resume-backed required skills: {skills}.")
    if matched_preferred:
        skills = ", ".join(item.skill for item in matched_preferred[:5])
        guidance.append(f"Use preferred skills as supporting proof: {skills}.")
    if missing_required:
        guidance.append(
            "Address missing required skills directly: "
            + ", ".join(missing_required[:5])
            + "."
        )
    if experience_gap is not None:
        guidance.append(experience_gap)
    if not guidance:
        guidance.append("Resume evidence covers the visible job requirements well.")
    return guidance
