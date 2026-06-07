# AGENTS.md

# CareerFit Radar Agent Instructions

## Purpose

AI coding agents must follow project documentation, use only approved technologies, and produce production-ready code. Do not invent features, architecture, or requirements.

---

## Required Reading Order

Read before making any code changes:

```text
docs/PRD.md
docs/ARCHITECTURE.md
docs/TECH_STACK.md
docs/TASKS.md
docs/AGENTS.md
```

Never code from assumptions.

---

## Core Rules

### Required

* Follow the approved architecture and tech stack.
* Implement only the current task and phase.
* Keep code typed, modular, and maintainable.
* Keep FastAPI routes thin; place business logic in services.
* Validate external data and LLM outputs with Pydantic.
* Use Alembic for all schema changes.
* Use PostgreSQL + pgvector for storage and vector search.
* Use `gemini-embedding-2` for embeddings.
* Use `gemini-3.1-flash-lite` for LLM tasks.
* Write tests for important logic.
* Update documentation when required.

### Forbidden

* Unapproved technologies or architecture changes.
* Unnecessary abstractions or enterprise patterns.
* Hardcoded secrets or configuration.
* Silent error handling.
* Skipping validation.
* Excessive comments.
* Direct Gemini calls from routes.
* Direct database writes from Streamlit.

---

## Forbidden MVP Additions

```text
SQLite
Qdrant
Pinecone
Chroma
Redis
Celery
Kubernetes
React
Next.js
LangChain unless explicitly needed
OpenAI API
LinkedIn scraper
Indeed scraper
Naukri scraper
Glassdoor scraper
Browser automation
CAPTCHA bypass
Email sender
Auto-apply bot
Payment system
Multi-user SaaS features
```

---

## Approved Stack

```text
Python
FastAPI
Streamlit
LangGraph
Neon PostgreSQL
pgvector
SQLAlchemy
Alembic
Pydantic
gemini-embedding-2
gemini-3.1-flash-lite
Greenhouse
Lever
Remotive
Arbeitnow
BeautifulSoup (public pages only)
httpx
Google Cloud Run
Google Cloud Scheduler
Google Secret Manager
Google Cloud Logging
pytest
Ruff
mypy
Docker
GitHub
```

---

## Production Code Standards

### Required

* Typed public functions.
* Clear module boundaries.
* Small focused services.
* Consistent naming.
* Explicit error handling.
* Safe database session management.
* Structured logging.
* Pydantic schemas at system boundaries.
* Tests for core business logic.

### Avoid

* Giant files.
* Duplicated logic.
* Unused abstractions.
* Over-commenting.
* Hardcoded configuration.
* Silent exceptions.
* Mixed frontend/backend responsibilities.

### Comments

Use comments only for:

* Non-obvious business rules.
* Edge cases.
* External API quirks.
* Scoring logic.
* Data safety decisions.

---

## Work Protocol

For every task:

1. Identify the phase in `TASKS.md`.
2. Review relevant sections of PRD, Architecture, and Tech Stack.
3. Modify only necessary files.
4. Keep implementations small and testable.
5. Add or update tests.
6. Run validation checks.
7. Summarize changes.

Do not skip phases or implement future work.

---

## Agent Responsibilities

### Backend Agent

Owns:

* FastAPI routes
* Services
* Database access
* Pydantic schemas
* Gemini integrations
* Source connectors
* Workflow APIs

Rules:

* Thin routes only.
* Business logic belongs in services.
* Use dependency injection for database sessions.
* Never expose secrets.
* Return structured, predictable errors.

### Database Agent

Owns:

* SQLAlchemy models
* Alembic migrations
* pgvector setup
* Indexes and relationships
* Query performance

Rules:

* Every schema change requires a migration.
* Enable pgvector via migration.
* Store timestamps on important tables.
* Store embedding model name and text hash.
* Do not permanently delete duplicate jobs.
* Avoid unnecessary personal data storage.

### Source Connector Agent

Owns:

* Greenhouse
* Lever
* Remotive
* Arbeitnow
* Optional SmartRecruiters

Rules:

* Use public, permitted sources only.
* Use `httpx` with timeouts.
* Handle network failures.
* Normalize all sources into a common schema.
* Log source runs.
* Never bypass platform restrictions.

### AI Agent

Owns:

* Gemini calls
* Requirement extraction
* Candidate profile extraction
* Fit explanations
* Gap analysis

Rules:

* System-consumed outputs must be JSON.
* Validate outputs with Pydantic.
* Retry invalid output once.
* Store failed raw outputs.
* Never invent skills, experience, or sponsorship claims.
* Use deterministic logic before LLM calls.

### Workflow Agent

Owns LangGraph workflows.

Required workflow:

```text
load_preferences
fetch_sources
normalise_jobs
apply_hard_filters
deduplicate_jobs
extract_requirements
generate_embeddings
store_jobs
score_jobs
run_gap_analysis
build_shortlist
finish_run
```

Rules:

* One responsibility per node.
* Explicit workflow state.
* Every run requires a `run_id`.
* Source failures must not stop the workflow.
* Filter and deduplicate before expensive AI calls.
* Persist workflow results.

### Frontend Agent

Owns Streamlit UI.

Rules:

* Streamlit communicates through FastAPI only.
* No direct Gemini calls.
* No direct database writes.
* Keep UI simple and useful.
* Display score breakdowns and failure states.
* Never add auto-apply functionality.

Required pages:

```text
Dashboard
Job Detail
Resume Profile
Application Tracker
Source Health
Settings
```

### Testing Agent

Owns:

* Unit tests
* Integration tests
* Source connector tests
* Workflow tests
* Schema validation tests

Coverage must include:

* Resume parsing
* Source normalization
* Hard filters
* Deduplication
* Scoring
* LLM validation
* Embedding caching
* Application tracking
* Workflow execution

Mock external APIs unless explicitly running integration tests.

### Deployment Agent

Owns:

* Dockerfiles
* Cloud Run deployment
* Cloud Scheduler
* Secret Manager
* Cloud Logging

Rules:

* Never hardcode secrets.
* Use runtime environment variables.
* Deploy backend and frontend separately.
* Scheduler triggers FastAPI, not Streamlit.
* Health checks must pass before deployment is complete.

---

## Validation Rules

Run before completion:

```text
ruff check .
ruff format .
mypy backend
pytest
```

All relevant tests must pass.

---

## Documentation Updates

Update documentation when changing:

* Architecture
* Tech stack
* Database schema
* API contracts
* Workflow steps
* Scoring logic
* Source connector behavior
* Deployment model

Keep code and documentation synchronized.

---

## Final Instruction

Build CareerFit Radar as a reliable job intelligence platform. Prioritize accuracy, maintainability, clear fit explanations, and production-quality implementation over adding technologies or unnecessary complexity.