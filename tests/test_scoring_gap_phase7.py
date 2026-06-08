from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from backend.services.gap_analysis_service import GapAnalysisService
from backend.services.scoring_service import (
    FitScoreWeights,
    FitScoringService,
    ScoringPreferences,
    _experience_fit_ratio,
    _freshness_ratio,
)


@dataclass
class FakeJob:
    title: str
    id: UUID = field(default_factory=uuid4)
    location: str | None = "India"
    remote_type: str | None = "remote"
    posted_at: datetime | None = field(default_factory=lambda: datetime.now(UTC) - timedelta(days=2))
    source: str = "greenhouse"


@dataclass
class FakeCandidateProfile:
    id: UUID = field(default_factory=uuid4)
    target_roles: list[str] = field(default_factory=lambda: ["AI Backend Developer"])
    skills: dict[str, Any] = field(
        default_factory=lambda: {
            "technical": ["Python", "FastAPI", "PostgreSQL", "LangGraph"],
            "tools": ["Docker"],
        }
    )
    experience_years: float | None = 1.0
    projects: list[dict[str, Any]] = field(
        default_factory=lambda: [
            {
                "name": "RAG Tutor",
                "technologies": ["Python", "FastAPI", "PostgreSQL", "LangGraph"],
                "evidence": "Resume project used Python, FastAPI, PostgreSQL, and LangGraph.",
            }
        ]
    )


@dataclass
class FakeRequirement:
    required_skills: list[str] = field(default_factory=lambda: ["Python", "FastAPI", "Kubernetes"])
    preferred_skills: list[str] = field(default_factory=lambda: ["PostgreSQL", "Docker"])
    responsibilities: list[str] = field(default_factory=lambda: ["Build APIs"])
    min_experience_years: float | None = 2.0


def test_fit_scoring_is_deterministic_and_components_total_final_score() -> None:
    service = FitScoringService(
        preferences=ScoringPreferences(
            preferred_countries=("India",),
            preferred_work_modes=("remote",),
        )
    )
    job = FakeJob(title="AI Backend Developer")
    candidate = FakeCandidateProfile()
    requirements = FakeRequirement()

    first = service.score_job(
        job=job,
        candidate_profile=candidate,
        requirements=requirements,
        semantic_similarity_score=17,
    )
    second = service.score_job(
        job=job,
        candidate_profile=candidate,
        requirements=requirements,
        semantic_similarity_score=17,
    )

    assert first.score == second.score
    assert first.score.final_score == sum(first.component_scores.values())
    assert first.score.final_score <= 100
    assert first.score.matched_skills == ["Python", "FastAPI", "PostgreSQL", "Docker"]
    assert first.score.missing_skills == ["Kubernetes"]
    assert "missing_required_skills" in first.score.risk_flags
    assert "experience_below_requirement" in first.score.risk_flags


def test_fit_score_weights_must_total_100() -> None:
    try:
        FitScoringService(weights=FitScoreWeights(source_reliability=6))
    except ValueError as exc:
        assert "must total 100" in str(exc)
    else:
        raise AssertionError("Invalid weights should fail clearly.")


def test_default_fit_score_weights_balance_skills_and_freshness() -> None:
    weights = FitScoreWeights()

    assert weights.skill_match == 20
    assert weights.freshness == 15
    weights.validate()


def test_experience_fit_ratio_scores_unknown_and_fractional_experience() -> None:
    assert _experience_fit_ratio(0.5, None) == 0.5
    assert _experience_fit_ratio(0.5, 1.0) == 0.5
    assert _experience_fit_ratio(0.5, 2.0) == 0.25
    assert _experience_fit_ratio(1.0, 2.0) == 0.5
    assert _experience_fit_ratio(2.0, 2.0) == 1.0


def test_freshness_ratio_uses_stricter_decay_bands() -> None:
    now = datetime.now(UTC)

    assert _freshness_ratio(now - timedelta(days=7)) == 1.0
    assert _freshness_ratio(now - timedelta(days=14)) == 0.75
    assert _freshness_ratio(now - timedelta(days=30)) == 0.3
    assert _freshness_ratio(now - timedelta(days=31)) == 0.0


def test_gap_analysis_uses_resume_evidence_only() -> None:
    analysis = GapAnalysisService().analyze(
        candidate_profile=FakeCandidateProfile(),
        requirements=FakeRequirement(),
    )

    matched_required = {item.skill: item.evidence for item in analysis.matched_required_skills}
    matched_preferred = {item.skill: item.evidence for item in analysis.matched_preferred_skills}

    assert matched_required["Python"].startswith("Resume skill:")
    assert matched_required["FastAPI"].startswith("Resume skill:")
    assert "Kubernetes" in analysis.missing_required_skills
    assert matched_preferred["PostgreSQL"].startswith("Resume skill:")
    assert "experience_gap" in analysis.risk_flags
    assert all("Kubernetes" not in item.evidence for item in analysis.matched_required_skills)


def test_gap_analysis_guidance_handles_strong_match() -> None:
    candidate = FakeCandidateProfile(experience_years=3)
    requirements = FakeRequirement(
        required_skills=["Python", "FastAPI"],
        preferred_skills=["PostgreSQL"],
        min_experience_years=2,
    )

    analysis = GapAnalysisService().analyze(
        candidate_profile=candidate,
        requirements=requirements,
    )

    assert analysis.missing_required_skills == ()
    assert analysis.experience_gap is None
    assert analysis.risk_flags == ()
    assert analysis.application_guidance[0].startswith("Lead with resume-backed")
