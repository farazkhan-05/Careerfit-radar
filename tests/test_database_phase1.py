from datetime import UTC, datetime
from uuid import uuid4

from backend.config import Settings
from backend.database import Base, create_database_engine
from backend.models import db_models
from backend.models.schemas import (
    CandidateProfileCreate,
    CompanyCreate,
    JobCreate,
    JobEmbeddingCreate,
    JobRequirementCreate,
    JobScoreCreate,
    ResumeChunkCreate,
    ResumeCreate,
    ResumeEmbeddingCreate,
    UserPreferenceCreate,
)


def test_database_config_loads_postgresql_engine() -> None:
    settings = Settings(
        DATABASE_URL="postgresql+psycopg://user:pass@example.com:5432/careerfit",
        GEMINI_API_KEY="test-key",
    )

    engine = create_database_engine(settings)

    assert engine.url.drivername == "postgresql+psycopg"
    engine.dispose()


def test_models_import_and_register_expected_tables() -> None:
    expected_tables = {
        "resumes",
        "resume_chunks",
        "candidate_profiles",
        "companies",
        "jobs",
        "job_requirements",
        "job_embeddings",
        "resume_embeddings",
        "job_scores",
        "applications",
        "rejected_jobs",
        "source_runs",
        "workflow_runs",
        "user_preferences",
    }

    assert db_models.Resume.__tablename__ == "resumes"
    assert expected_tables.issubset(Base.metadata.tables.keys())


def test_schemas_validate_sample_data() -> None:
    now = datetime.now(UTC)
    resume_id = uuid4()
    resume_chunk_id = uuid4()
    company_id = uuid4()
    job_id = uuid4()
    candidate_profile_id = uuid4()

    resume = ResumeCreate(
        file_name="resume.pdf",
        content_type="application/pdf",
        text_hash="resume-hash",
    )
    chunk = ResumeChunkCreate(
        resume_id=resume_id,
        chunk_index=0,
        content="Python backend engineer",
        text_hash="chunk-hash",
    )
    profile = CandidateProfileCreate(
        resume_id=resume_id,
        target_roles=["Backend Engineer"],
        skills={"languages": ["Python"]},
        experience_years=2,
    )
    company = CompanyCreate(
        name="Example Co", career_site_url="https://example.com/jobs"
    )
    job = JobCreate(
        company_id=company_id,
        source="greenhouse",
        source_job_id="job-123",
        title="Backend Engineer",
        apply_url="https://example.com/apply/job-123",
        description="Build APIs",
        fetched_at=now,
    )
    requirements = JobRequirementCreate(
        job_id=job_id,
        required_skills=["Python"],
        confidence=0.9,
    )
    job_embedding = JobEmbeddingCreate(
        job_id=job_id,
        entity_type="job_description",
        embedding_model="gemini-embedding-2",
        text_hash="job-text-hash",
        embedding_vector=[0.1, 0.2],
    )
    resume_embedding = ResumeEmbeddingCreate(
        resume_chunk_id=resume_chunk_id,
        entity_type="resume_chunk",
        embedding_model="gemini-embedding-2",
        text_hash="resume-text-hash",
        embedding_vector=[0.1, 0.2],
    )
    score = JobScoreCreate(
        job_id=job_id,
        candidate_profile_id=candidate_profile_id,
        final_score=82,
        explanation="Strong role and skill match.",
    )
    preferences = UserPreferenceCreate(target_roles=["Backend Engineer"])

    assert resume.file_name == "resume.pdf"
    assert chunk.chunk_index == 0
    assert profile.skills["languages"] == ["Python"]
    assert str(company.career_site_url) == "https://example.com/jobs"
    assert job.source == "greenhouse"
    assert requirements.required_skills == ["Python"]
    assert job_embedding.embedding_vector == [0.1, 0.2]
    assert resume_embedding.entity_type == "resume_chunk"
    assert score.final_score == 82
    assert preferences.native_country == "India"
