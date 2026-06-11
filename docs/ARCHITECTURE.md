# ARCHITECTURE.md

# CareerFit Radar Architecture

## 1. Purpose

CareerFit Radar is an AI job intelligence platform that:

* Discovers jobs from public and permitted sources
* Stores data in PostgreSQL
* Uses pgvector for semantic resume-to-job matching
* Orchestrates workflows with LangGraph
* Provides explainable job-fit scoring

This document defines the approved architecture and prevents unnecessary tooling, unsafe scraping, and architectural drift.

---

## 2. Architecture Principles

1. Prefer deterministic code over LLM reasoning.
2. Use LLMs only for language understanding tasks.
3. Store critical data in PostgreSQL.
4. Use pgvector for semantic search and matching.
5. Use LangGraph for workflow orchestration.
6. Use only public and permitted job sources.
7. Never auto-apply to jobs.
8. Never send automated cold emails.
9. Never scrape login-protected platforms.
10. Keep the MVP simple and production-ready.
11. Design for Google Cloud Platform deployment.

---

## 3. System Overview

### Layers

1. User Interface
2. API
3. Workflow Orchestration
4. Intelligence Services
5. Data Layer

```text
User
 ↓
React Dashboard
 ↓
FastAPI Backend
 ↓
LangGraph Workflow
 ↓
Source Connectors + Gemini Services + Scoring
 ↓
Neon PostgreSQL + pgvector
```

---

## 4. Deployment Architecture

### GCP Services

| Component         | Service         |
| ----------------- | --------------- |
| Backend API       | Cloud Run       |
| React Dashboard   | Cloud Run       |
| Scheduled Refresh | Cloud Scheduler |
| Secrets           | Secret Manager  |
| Logging           | Cloud Logging   |
| Database          | Neon PostgreSQL |
| Vector Search     | pgvector        |

### Deployable Services

#### FastAPI Backend

Responsibilities:

* Resume APIs
* Job APIs
* Scoring APIs
* Application tracking APIs
* LangGraph execution
* Database access
* Gemini integration
* Source connector execution

#### React Dashboard

Responsibilities:

* Resume management
* Job shortlist and details
* Candidate profile view
* Application tracking
* Manual workflow triggers

### Service Separation

FastAPI and React remain separate because:

* Backend workflows must not depend on frontend state.
* Cloud Scheduler targets backend endpoints.
* Frontend can be replaced without backend changes.

---

## 5. Runtime Flows

### Resume Processing

```text
User uploads resume
 ↓
Resume parsed and chunked
 ↓
Embeddings generated
 ↓
Chunks + vectors stored in PostgreSQL + pgvector
 ↓
Candidate profile extracted
 ↓
Profile stored and reviewed in dashboard
```

### Job Discovery

```text
Scheduler or user triggers refresh
 ↓
LangGraph workflow starts
 ↓
Jobs fetched and normalised
 ↓
Hard filtering
 ↓
Deduplication
 ↓
Requirement extraction
 ↓
Embedding generation
 ↓
Storage in PostgreSQL + pgvector
 ↓
Scoring and gap analysis
 ↓
Shortlist generation
 ↓
Dashboard display
```

### Application Tracking

```text
User reviews job
 ↓
User applies externally
 ↓
Application status updated
 ↓
Status and notes stored
```

The platform must never submit applications automatically.

---

## 6. Core Components

### 6.1 React Dashboard

Responsibilities:

* Resume upload
* Candidate profile display
* Job shortlist and details
* Search and filtering
* Application tracking
* Source health monitoring
* Workflow triggers

Rules:

* Communicate only through FastAPI APIs.
* Contain no business logic.
* No direct Gemini calls.
* No direct database writes.
* API base URL configured via `VITE_API_URL` environment variable.

---

### 6.2 FastAPI Backend

Responsibilities:

* API endpoints
* Input validation with Pydantic
* LangGraph execution
* Database operations
* Gemini integration
* Source connector execution
* Workflow logging

Business logic belongs in services, not route handlers.

---

### 6.3 LangGraph Workflow

#### Main Graph

```text
job_discovery_graph
```

#### Graph State

```python
{
    "run_id": str,
    "source_name": str | None,
    "fetched_jobs": list,
    "normalised_jobs": list,
    "filtered_jobs": list,
    "rejected_jobs": list,
    "deduplicated_jobs": list,
    "jobs_for_extraction": list,
    "jobs_for_embedding": list,
    "scored_jobs": list,
    "shortlisted_jobs": list,
    "errors": list,
    "started_at": datetime,
    "completed_at": datetime | None
}
```

#### Required Nodes

```text
start_run_node
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

#### Workflow Rules

* Single responsibility per node.
* Structured state updates.
* Log failures.
* Continue when one source fails.
* Run expensive LLM tasks only after filtering and deduplication.
* Cache embeddings.
* Mark failed jobs for review.

---

### 6.4 Source Connectors

#### Current MVP Source

```text
Tavily web search constrained to approved ATS domains
```

#### Optional Sources

```text
SmartRecruiters
Public company career pages
```

#### Connector Contract

```python
fetch_jobs(query: JobSourceQuery) -> list[RawJob]
normalise(raw_job: RawJob) -> NormalisedJob
```

#### Normalised Job Schema

```python
{
    "source": str,
    "source_job_id": str,
    "title": str,
    "company": str,
    "location": str | None,
    "remote_type": str | None,
    "posted_at": datetime | None,
    "apply_url": str,
    "description": str,
    "raw_payload": dict,
    "fetched_at": datetime
}
```

#### Source Rules

Allowed:

* Public APIs
* Public ATS endpoints
* Public job feeds
* Public company career pages

Forbidden:

* Login-required scraping
* CAPTCHA bypassing
* LinkedIn scraping
* Indeed scraping
* Naukri scraping
* Glassdoor scraping
* Automated applications
* Private ATS access

---

### 6.5 Resume Parser

Supported formats:

```text
PDF
DOCX
```

Responsibilities:

* Text extraction
* Section detection
* Chunking
* Storage
* Embedding generation trigger
* Candidate profile extraction trigger

Must never invent missing information.

---

### 6.6 Gemini Embedding Service

Model:

```text
gemini-embedding-2
```

Responsibilities:

* Resume embeddings
* Job embeddings
* Requirement embeddings
* Caching
* Duplicate prevention
* pgvector storage

Rules:

* Store model name and text hash.
* Skip regeneration when hash is unchanged.
* Generate embeddings only after filtering and deduplication.
* Log failures.

---

### 6.7 Gemini LLM Service

Model:

```text
gemini-3.1-flash-lite
```

Responsibilities:

* Requirement extraction
* Candidate profile extraction
* Job summarisation
* Fit-score explanations
* Resume-tailoring recommendations
* Risk detection

Rules:

* Return structured JSON when required.
* Include confidence values.
* Separate evidence from inference.
* Retry once on schema validation failure.

Must not invent skills, experience, company details, sponsorship claims, or deterministic decisions.

---

### 6.8 Scoring Service

#### Weights

| Category            | Weight |
| ------------------- | ------ |
| Role Match          | 15     |
| Skill Match         | 20     |
| Semantic Similarity | 20     |
| Experience Fit      | 15     |
| Freshness           | 15     |
| Location Fit        | 10     |
| Source Reliability  | 5      |
| Total               | 100    |

#### Output

```python
{
    "job_id": str,
    "final_score": int,
    "role_match_score": int,
    "skill_match_score": int,
    "semantic_similarity_score": int,
    "experience_fit_score": int,
    "freshness_score": int,
    "location_fit_score": int,
    "source_reliability_score": int,
    "matched_skills": list[str],
    "missing_skills": list[str],
    "risk_flags": list[str],
    "explanation": str
}
```

Scores must be explainable and stored.

---

### 6.9 Hard Filter Service

Reject unsuitable jobs before expensive processing.

Examples:

* Senior, Lead, Principal, Staff
* Architect or Manager-only roles
* 5+ years experience requirements
* Citizenship or clearance restrictions
* Unsupported language requirements
* Unpaid, commission-only, or unsuitable role types

Store:

```text
job_id
reason
filter_name
rejected_at
can_restore
```

Users must be able to restore rejected jobs.

---

### 6.10 Deduplication Service

Signals:

* Same apply URL
* Same source job ID
* Same company and title
* Similar title, location, description, or embedding

Priority:

1. Company career page
2. ATS posting
3. Remote job board
4. Aggregator

Never permanently delete duplicates.

---

### 6.11 Gap Analysis Service

Outputs:

* Matched skills
* Missing skills
* Partial matches
* Relevant projects
* Keywords to emphasise
* Risks
* Tailoring notes
* Suggested application angle

Must never recommend false skills, fake experience, companies, or metrics.

---

## 7. Data Architecture

### Database

```text
Neon PostgreSQL
pgvector
```

Rules:

* PostgreSQL stores relational and vector data.
* No SQLite.
* No separate vector database.

### Core Tables

```text
resumes
resume_chunks
candidate_profiles
companies
jobs
job_requirements
job_embeddings
resume_embeddings
job_scores
applications
rejected_jobs
source_runs
workflow_runs
user_preferences
```

### Embedding Metadata

```text
id
entity_type
entity_id
embedding_model
text_hash
embedding_vector
created_at
updated_at
```

Entity types:

```text
resume_chunk
job_description
job_requirements
```

Vector dimensions must match the selected Gemini embedding model.

---

## 8. User Preferences

Required fields:

```text
target_roles
preferred_countries
native_country
preferred_work_modes
minimum_fit_score
maximum_experience_years
visa_sponsorship_required
relocation_open
remote_open
excluded_keywords
preferred_keywords
```

Default configuration:

```text
native_country: India

preferred_countries:
- India
- Germany
- Luxembourg
- UAE
- Saudi Arabia
- Qatar
- Singapore
- Remote
```

Preferences influence search, filtering, and scoring.

---

## 9. API Architecture

### API Style

* REST APIs
* Pydantic request and response schemas
* Predictable structured responses
* CORS enabled for React frontend

### API Groups

```text
/resumes
/profile
/jobs
/workflows
/applications
/sources
/exports
/health
```

### Example Endpoints

#### Resume

```text
POST /resumes/upload
GET /resumes
GET /resumes/{resume_id}
PATCH /resumes/{resume_id}
DELETE /resumes/{resume_id}
```

#### Profile

```text
GET /profiles
POST /profiles/score-jobs
GET /profiles/{profile_id}
PATCH /profiles/{profile_id}
```

#### Jobs

```text
GET /jobs
GET /jobs/{job_id}
POST /jobs/manual
PATCH /jobs/{job_id}
DELETE /jobs/{job_id}
```

#### Workflows

```text
POST /workflows/run
GET /workflows/{run_id}
PATCH /workflows/{workflow_id}
```

#### Applications

```text
GET /applications
POST /applications
PATCH /applications/{application_id}
```

#### Sources

```text
GET /sources/runs
POST /sources/import/web-search
```

#### Exports

```text
GET /exports/jobs.csv
GET /exports/applications.csv
```

---

## 10. Forbidden Architecture Changes

Do not:

* Replace PostgreSQL with SQLite.
* Replace pgvector with a separate vector database.
* Remove LangGraph orchestration.
* Merge frontend and backend into a single service.
* Add automated job applications.
* Add automated cold-email systems.
* Scrape login-protected platforms.
* Add LinkedIn, Indeed, Naukri, or Glassdoor scraping.
* Bypass source access restrictions.
* Move core business logic into the React frontend.
