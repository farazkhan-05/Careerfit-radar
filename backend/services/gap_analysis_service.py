from __future__ import annotations

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


def _build_evidence_index(candidate_profile: GapCandidateProfile) -> dict[str, str]:
    evidence: dict[str, str] = {}
    for skill in _flatten_skills(candidate_profile.skills):
        evidence.setdefault(normalize_for_match(skill), f"Resume skill: {normalize_text(skill)}")

    for role in candidate_profile.target_roles:
        evidence.setdefault(normalize_for_match(role), f"Resume target role: {normalize_text(role)}")

    for project in candidate_profile.projects:
        project_name = normalize_text(str(project.get("name") or "Project"))
        project_evidence = normalize_text(str(project.get("evidence") or project.get("summary") or project_name))
        for technology in project.get("technologies") or []:
            evidence.setdefault(
                normalize_for_match(str(technology)),
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
    for skill in skills:
        cleaned = normalize_text(skill)
        key = normalize_for_match(cleaned)
        if not cleaned or key in seen:
            continue
        seen.add(key)
        evidence = evidence_index.get(key)
        if evidence is None:
            missing.append(cleaned)
        else:
            matched.append(SkillEvidence(skill=cleaned, evidence=evidence))
    return matched, missing


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
