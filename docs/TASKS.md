# TASKS.md

# CareerFit Radar Execution Plan

## Purpose

Build CareerFit Radar in incremental, testable phases. Each phase must produce a working outcome and meet its acceptance criteria.

---

## Phase 0: Project Foundation

### Key Files

```text
backend/main.py
backend/config.py
backend/database.py
frontend/streamlit_app.py
.env.example
requirements.txt
Dockerfile.backend
Dockerfile.frontend
README.md
```

### Deliverables

* Create approved repository structure.
* Configure dependencies.
* Implement environment configuration using `pydantic-settings`.
* Add `.gitignore` and Docker files.

### Acceptance Criteria

* Project structure matches approved architecture.
* Dependencies install successfully.
* Environment variables load correctly.
* Missing required configuration fails clearly.
* No unapproved dependencies are added.

---

## Phase 1: Database and Models

### Key Files

```text
backend/database.py
backend/models/db_models.py
backend/models/schemas.py
migrations/
```

### Deliverables

* Configure PostgreSQL connection.
* Enable pgvector via Alembic migration.
* Create core SQLAlchemy models.
* Create Pydantic schemas.

### Acceptance Criteria

* Neon PostgreSQL connection works.
* pgvector extension is enabled.
* Models include relationships, timestamps, and vector fields.
* Schemas validate all external boundaries.

---

## Phase 2: Resume Parsing and Candidate Profile

### Key Files

```text
backend/services/resume_parser.py
backend/services/candidate_profile_service.py
```

### Deliverables

* Parse PDF and DOCX resumes.
* Generate resume chunks with hashes.
* Extract candidate profile using Gemini.

### Acceptance Criteria

* Resume parsing handles valid and invalid files.
* Chunking is deterministic and avoids duplication.
* Candidate profile output validates with Pydantic.
* No unsupported information is generated.

---

## Phase 3: Job Source Connectors

### Key Files

```text
backend/sources/base_source.py
backend/sources/greenhouse_source.py
backend/sources/lever_source.py
backend/sources/remotive_source.py
backend/sources/arbeitnow_source.py
backend/sources/smartrecruiters_source.py
```

### Deliverables

* Create common source interface.
* Implement Greenhouse, Lever, Remotive, and Arbeitnow connectors.
* Add optional SmartRecruiters connector.

### Acceptance Criteria

* All connectors return normalized jobs.
* Network failures are handled safely.
* Source metadata is stored.
* SmartRecruiters remains disabled by default.

---

## Phase 4: Hard Filters and Deduplication

### Key Files

```text
backend/services/hard_filter_service.py
backend/services/deduplication_service.py
```

### Deliverables

* Implement configurable rejection rules.
* Implement exact and fuzzy deduplication.

### Acceptance Criteria

* Rejected jobs store rejection reasons.
* Duplicate jobs link to a canonical record.
* Data is preserved rather than deleted.
* Tests cover filtering and deduplication.

---

## Phase 5: Gemini Integration

### Key Files

```text
backend/services/gemini_llm_service.py
backend/services/gemini_embedding_service.py
```

### Deliverables

* Centralize Gemini API access.
* Extract structured job requirements.

### Acceptance Criteria

* Models are configurable via environment variables.
* Structured outputs validate successfully.
* Failed extractions are tracked.
* Routes never call Gemini directly.

---

## Phase 6: pgvector Semantic Matching

### Key Files

```text
backend/services/embedding_store_service.py
```

### Deliverables

* Store resume and job embeddings.
* Implement similarity search queries.

### Acceptance Criteria

* Embeddings are cached using text hashes.
* Similarity search returns usable scores.
* Searches tolerate missing embeddings.
* Embedding metadata is stored.

---

## Phase 7: Fit Scoring and Gap Analysis

### Key Files

```text
backend/services/scoring_service.py
backend/services/gap_analysis_service.py
```

### Deliverables

* Implement weighted fit scoring.
* Generate gap analysis and application guidance.

### Acceptance Criteria

* Scores total 100 and remain deterministic.
* Score components are stored separately.
* Gap analysis uses resume evidence only.
* Tests cover scoring behavior.

---

## Phase 8: LangGraph Workflow

### Key Files

```text
backend/workflows/job_discovery_graph.py
```

### Deliverables

* Build end-to-end job discovery workflow.
* Persist workflow execution history.

### Required Nodes

```text
start_run_node
load_preferences_node
fetch_sources_node
normalise_jobs_node
hard_filter_node
deduplicate_jobs_node
extract_requirements_node
embed_jobs_node
store_jobs_node
score_jobs_node
gap_analysis_node
build_shortlist_node
finish_run_node
error_handler_node
```

### Acceptance Criteria

* Workflow state is explicit.
* Source failures do not stop execution.
* Run metadata is stored.
* Workflow history is queryable.

---

## Phase 9: FastAPI Routes

### Key Files

```text
backend/routes/resume_routes.py
backend/routes/profile_routes.py
backend/routes/job_routes.py
backend/routes/workflow_routes.py
backend/routes/application_routes.py
backend/routes/source_routes.py
backend/routes/export_routes.py
backend/routes/health_routes.py
```

### Deliverables

Implement routes for:

```text
Resumes
Profiles
Jobs
Workflows
Applications
Sources
Exports
Health Checks
```

### Acceptance Criteria

* CRUD operations function correctly.
* Pagination and filtering work.
* CSV exports work.
* Health checks validate database and Gemini connectivity.

---

## Phase 10: Streamlit Dashboard

### Key Files

```text
frontend/streamlit_app.py
```

### Deliverables

Pages:

```text
Dashboard
Job Detail
Resume Profile
Application Tracker
Source Health
Settings
```

### Acceptance Criteria

* Dashboard runs locally.
* Navigation works across pages.
* API endpoint is configurable.

---

## Phase 11: Testing and Quality Pass

### Deliverables

* Unit tests for services.
* Integration tests for workflows and routes.
* Static analysis and type checking.

### Acceptance Criteria

* Critical workflows are tested.
* Ruff passes.
* MyPy passes.
* No major defects remain.

---

## Phase 12: GCP Deployment

### Deliverables

* Deploy backend and frontend.
* Configure Cloud Run services.
* Configure Cloud Scheduler workflow triggers.
* Configure production environment variables.

### Acceptance Criteria

* Application runs successfully on GCP.
* Scheduled refresh jobs execute correctly.
* Health checks pass in production.
* Logs and monitoring are available.

---

# MVP Completion Checklist

## Core Platform

* [x] Repository structure created
* [x] Environment configuration completed
* [x] PostgreSQL and pgvector configured
* [x] Database models and schemas implemented

## Resume Intelligence

* [x] Resume parsing implemented
* [x] Resume chunking implemented
* [x] Candidate profile extraction implemented

## Job Discovery

* [x] Greenhouse connector implemented
* [x] Lever connector implemented
* [x] Remotive connector implemented
* [x] Arbeitnow connector implemented
* [x] Hard filtering implemented
* [x] Deduplication implemented

## AI Matching

* [x] Gemini integration completed
* [x] Job requirement extraction completed
* [x] Embedding storage completed
* [x] Semantic search completed
* [x] Fit scoring completed
* [x] Gap analysis completed

## Workflow

* [x] LangGraph workflow implemented
* [x] Workflow persistence implemented

## API

* [ ] Resume routes completed
* [ ] Profile routes completed
* [ ] Job routes completed
* [ ] Workflow routes completed
* [ ] Application routes completed
* [ ] Source routes completed
* [ ] Export routes completed
* [ ] Health routes completed

## Frontend

* [ ] Streamlit dashboard completed

## Production Readiness

* [x] Tests passing
* [x] Ruff passing
* [x] MyPy passing
* [ ] GCP deployment completed
* [ ] Production health checks passing
