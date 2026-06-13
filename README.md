# CareerFit Radar - Full-stack RAG pipeline for job discovery

CareerFit Radar is a full-stack job search project that connects resume parsing, job discovery, semantic matching, fit scoring, and application tracking in one workflow.

The goal is simple: upload a resume, bring in relevant job listings, compare each role against the candidate profile, and keep track of the jobs that are worth acting on. It is built as a practical solo developer project with production minded pieces such as API auth, migrations, tests, Docker builds, Cloud Run deployment, scheduled search, and secret management.

## What It Does

- Uploads PDF, DOCX, or text resumes and stores parsed resume content.
- Extracts a candidate profile from resume text with Gemini.
- Generates embeddings for resume chunks and job data.
- Imports jobs from Tavily web search constrained to approved sources.
- Filters unsuitable listings and deduplicates repeated jobs.
- Scores job fit using skills, role match, semantic similarity, experience, freshness, location, and source quality.
- Produces gap analysis for stronger and weaker matches.
- Tracks saved jobs and application status.
- Exports job and application data as CSV.
- Runs locally with Docker or as separate frontend and backend services on Google Cloud Run.

## Tech Stack

| Area | Tools |
| --- | --- |
| Frontend | React 18, Vite, Tailwind CSS, TanStack Query, Axios |
| Backend | FastAPI, Python 3.11+, Pydantic |
| Database | Neon PostgreSQL, pgvector |
| ORM and migrations | SQLAlchemy, Alembic |
| AI and matching | Gemini embeddings, Gemini LLM, resume and job matching with retrieval context |
| Workflow | LangGraph |
| Job discovery | Tavily web search with approved source constraints |
| Deployment | Docker, Google Cloud Run, Cloud Build, Secret Manager, Cloud Scheduler |
| Quality | pytest, Ruff, mypy |

## Architecture

```text
React dashboard
  -> FastAPI backend
  -> LangGraph job discovery workflow
  -> Gemini extraction, embeddings, scoring, and gap analysis
  -> PostgreSQL with pgvector
```

The frontend and backend are deployed separately. The browser calls the frontend on `/api/*`, and the frontend container proxies those requests to the backend through Nginx. In production, the backend token stays in the Cloud Run environment instead of being exposed in browser JavaScript.

## Project Structure

```text
careerfit-radar/
|-- backend/              FastAPI routes, services, sources, and workflows
|-- frontend/             React app, API client, pages, and Nginx config
|-- docs/                 PRD, architecture, deployment, and task notes
|-- migrations/           Alembic database migrations
|-- tests/                Backend and configuration tests
|-- exports/              CSV export output directory
|-- deploy/gcp/           Cloud Build configs
|-- scripts/              Deployment and secret sync scripts
|-- Dockerfile.backend
|-- Dockerfile.frontend
|-- requirements.txt
|-- .env.example
```

## Local Setup

### Backend

```bash
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
fastapi dev backend/main.py
```

The backend runs at `http://localhost:8000`. In development, API docs are available at `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

The frontend runs at `http://localhost:5173`.

For local development, leave `VITE_API_URL` empty to use the Vite `/api` proxy. If backend auth is enabled locally, set `VITE_API_AUTH_TOKEN` to match `API_AUTH_TOKEN`.

## Environment Variables

### Backend `.env`

| Variable | Required | Notes |
| --- | --- | --- |
| `DATABASE_URL` | Yes | PostgreSQL connection string, usually Neon with SSL enabled |
| `API_AUTH_TOKEN` | Production | Bearer token for protected API routes |
| `GEMINI_API_KEY` | Yes | Gemini API key for profile extraction, requirement extraction, and embeddings |
| `GEMINI_EMBEDDING_MODEL` | No | Defaults to `gemini-embedding-2` |
| `GEMINI_LLM_MODEL` | No | Defaults to `gemini-3.1-flash-lite` |
| `TAVILY_API_KEY` | Job search | Required for Tavily web search imports |
| `CORS_ORIGINS` | No | Comma-separated allowed origins |
| `APP_ENV` | No | Use `production` in deployed services |
| `LOG_LEVEL` | No | Defaults to `INFO` |
| `MAX_UPLOAD_BYTES` | No | Resume upload limit |
| `GOOGLE_CLOUD_PROJECT` | Production | Used for Google Cloud integrations |

### Frontend `frontend/.env`

| Variable | Required | Notes |
| --- | --- | --- |
| `VITE_API_URL` | No | API base URL. Empty uses `/api` |
| `VITE_API_AUTH_TOKEN` | No | Local/private helper only. Do not treat it as a browser secret |

For the production frontend container, keep `VITE_API_URL` empty and set `BACKEND_URL` plus `API_AUTH_TOKEN` on Cloud Run. Nginx proxies `/api/*` to the backend and attaches the backend token from the server environment.

## Running Tests

```bash
pytest
ruff check .
mypy backend
```

Frontend build:

```bash
cd frontend
npm run build
```

## Docker

### Backend

```bash
docker build -f Dockerfile.backend -t careerfit-backend .
docker run -p 8080:8080 --env-file .env careerfit-backend
```

### Frontend

```bash
docker build -f Dockerfile.frontend -t careerfit-frontend .
docker run -p 8080:8080 -e BACKEND_URL=http://your-backend-url careerfit-frontend
```

## Deployment

The current deployment path uses Google Cloud Run:

- Backend API on Cloud Run.
- Frontend React build served by Nginx on Cloud Run.
- Artifact Registry and Cloud Build for images.
- Secret Manager for database URL and API keys.
- Cloud Scheduler for weekday job discovery runs.
- Cloud Logging for service logs.

See [docs/DEPLOYMENT_GCP.md](docs/DEPLOYMENT_GCP.md) for the deployment runbook.

## Main API Areas

- `POST /resumes/upload` uploads and parses a resume.
- `GET /resumes` lists stored resumes.
- `GET /profiles` lists extracted candidate profiles.
- `POST /profiles/score-jobs` scores jobs against a profile.
- `POST /sources/import/web-search` starts a web-search job import.
- `GET /jobs` lists jobs with filters.
- `POST /applications/jobs/{job_id}/save` saves a job to the application tracker.
- `GET /exports/jobs.csv` exports jobs.
- `GET /health/ready` checks database and Gemini readiness.

## Notes

This is intentionally not an automatic application or outreach tool. It does not scrape private job boards, bypass CAPTCHA, or submit applications for the user. The focus is on a cleaner job discovery workflow, explainable matching, and enough deployment discipline to run it like a small real product.
