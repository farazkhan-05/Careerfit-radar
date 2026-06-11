# TECH_STACK.md

# CareerFit Radar Tech Stack

## Purpose

This document defines the approved MVP technology stack. Only the technologies listed here are approved unless the architecture is formally updated.

---

## Final Approved Stack

| Layer                  | Technology                             |
| ---------------------- | -------------------------------------- |
| Language               | Python 3.11+                           |
| Backend API            | FastAPI                                |
| Frontend               | React 18 + Vite + Tailwind CSS         |
| Workflow Orchestration | LangGraph                              |
| Database               | Neon PostgreSQL                        |
| Vector Search          | pgvector                               |
| ORM                    | SQLAlchemy                             |
| Migrations             | Alembic                                |
| Validation             | Pydantic                               |
| Embeddings             | gemini-embedding-2                     |
| LLM                    | gemini-3.1-flash-lite                  |
| Job Sources            | Approved ATS web search                |
| Optional Source        | SmartRecruiters                        |
| HTML Parsing           | BeautifulSoup                          |
| HTTP Client            | httpx                                  |
| Scheduling             | Google Cloud Scheduler                 |
| Secrets                | Google Secret Manager                  |
| Logging                | Google Cloud Logging                   |
| Deployment             | Google Cloud Run                       |
| Testing                | pytest                                 |
| Linting / Formatting   | Ruff                                   |
| Type Checking          | mypy                                   |
| Containerisation       | Docker                                 |
| Version Control        | Git + GitHub                           |

---

## Technology Usage

### Python

Primary language for APIs, workflows, source connectors, resume processing, scoring, and AI integrations.

### FastAPI

Backend API framework. Route handlers must remain thin; business logic belongs in services and workflows.

### React

MVP frontend. Built with Vite, Tailwind CSS, React Router, TanStack Query, and Axios. Communicates with FastAPI via HTTP APIs only. API base URL is configured via `VITE_API_URL` environment variable.

### LangGraph

Workflow orchestration for job discovery, normalization, filtering, deduplication, scoring, and gap analysis.

### Neon PostgreSQL

Primary database for all application data. No additional databases are permitted in MVP.

### pgvector

Semantic search and resume-to-job matching within PostgreSQL.

### SQLAlchemy

Database models, queries, relationships, and transactions.

### Alembic

Required for all schema changes and migration history.

### Pydantic

Validation for API contracts, source outputs, and structured LLM responses.

### Gemini Models

**Embeddings**

```text
gemini-embedding-2
```

Used for semantic matching, similarity search, and duplicate detection.

**LLM**

```text
gemini-3.1-flash-lite
```

Used for extraction, fit explanations, gap analysis, and resume-tailoring suggestions.

Do not use the LLM for deterministic business logic.

### Job Sources

Current MVP:

```text
Tavily web search constrained to approved ATS domains
```

Optional:

```text
SmartRecruiters
```

### BeautifulSoup

Allowed only for permitted public-page parsing.

Forbidden:

```text
LinkedIn scraping
Indeed scraping
Naukri scraping
Glassdoor scraping
Login-protected scraping
CAPTCHA bypassing
Anti-bot bypassing
Auto-apply automation
```

### httpx

Standard HTTP client for APIs and source connectors. All requests must use timeouts and error handling.

### Google Cloud Platform

**Cloud Run**

* Backend service
* Frontend service

**Cloud Scheduler**

* Scheduled workflow execution

**Secret Manager**

* API keys and credentials

**Cloud Logging**

* Production logging with workflow run tracking

### Development Tools

**pytest**

* Automated testing

**Ruff**

* Formatting and linting

**mypy**

* Static type checking

**Docker**

* Local and production deployment consistency

---

## Approved Project Structure

```text
careerfit-radar/
│
├── docs/
│   ├── PRD.md
│   ├── ARCHITECTURE.md
│   ├── TECH_STACK.md
│   ├── TASKS.md
│   └── AGENTS.md
│
├── backend/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models/
│   │   ├── db_models.py
│   │   ├── schemas.py
│   │   └── api_schemas.py
│   ├── routes/
│   │   ├── resume_routes.py
│   │   ├── profile_routes.py
│   │   ├── job_routes.py
│   │   ├── workflow_routes.py
│   │   ├── application_routes.py
│   │   ├── source_routes.py
│   │   ├── export_routes.py
│   │   └── health_routes.py
│   ├── services/
│   │   ├── resume_parser.py
│   │   ├── candidate_profile_service.py
│   │   ├── gemini_embedding_service.py
│   │   ├── gemini_llm_service.py
│   │   ├── scoring_service.py
│   │   ├── gap_analysis_service.py
│   │   ├── hard_filter_service.py
│   │   ├── deduplication_service.py
│   │   └── export_service.py
│   ├── sources/
│   │   ├── base_source.py
│   │   ├── tavily_search_source.py
│   │   └── smartrecruiters_source.py
│   ├── workflows/
│   │   └── job_discovery_graph.py
│   └── utils/
│       ├── text_utils.py
│       ├── hash_utils.py
│       └── logging_utils.py
│
├── frontend/
│   ├── src/
│   │   ├── api/          API client and endpoint modules
│   │   ├── components/   Reusable UI and layout components
│   │   ├── pages/        Page-level components
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── public/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── nginx.conf
│   └── .env.example
│
├── migrations/
├── tests/
├── exports/
├── .env.example
├── .gitignore
├── requirements.txt
├── Dockerfile.backend
├── Dockerfile.frontend
└── README.md
```

---

## Forbidden MVP Technologies

Do not introduce:

```text
SQLite
Qdrant
Pinecone
Chroma
Redis
Celery
Kubernetes
Next.js
Browser automation
LinkedIn scraping
Indeed scraping
Naukri scraping
Glassdoor scraping
Email sending
Auto-apply automation
Payment systems
Multi-user SaaS architecture
```

---

## Code Quality Standards

Required:

* Production-quality code
* Modular services
* Thin route handlers
* Typed function signatures
* Pydantic validation at boundaries
* Clear error handling
* No hardcoded secrets
* No duplicated business logic
* No silent failures
* No unvalidated LLM output
* Small, maintainable files

Avoid:

* Over-commenting
* Fake enterprise abstractions
* Unused helper classes
* Premature microservices
* Unnecessary design patterns

All public interfaces must be typed and validated.
