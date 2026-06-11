# CareerFit Radar

CareerFit Radar is an AI-powered job intelligence platform that helps job seekers find, evaluate, and prioritize high-fit opportunities.

The platform discovers jobs from approved public sources, compares them against your resume using semantic matching, scores each job for fit, identifies skill gaps, and helps you track your application pipeline.

---

## Tech Stack

| Layer      | Technology                            |
| ---------- | ------------------------------------- |
| Backend    | FastAPI (Python 3.11+)                |
| Frontend   | React 18 + Vite + Tailwind CSS        |
| Database   | Neon PostgreSQL + pgvector            |
| AI         | Gemini (embedding + LLM)              |
| Workflows  | LangGraph                             |
| Deployment | Google Cloud Run + Docker             |

---

## Project Structure

```
careerfit-radar/
├── backend/          FastAPI backend (routes, services, workflows)
├── frontend/         React frontend (Vite + Tailwind CSS)
├── docs/             Architecture, PRD, and task documentation
├── tests/            Python backend tests
├── migrations/       Alembic database migrations
├── exports/          CSV export output directory
├── Dockerfile.backend
├── Dockerfile.frontend
├── requirements.txt  Python dependencies (backend)
└── .env.example      Backend environment variable template
```

---

## Quick Start

### Backend

```bash
# Install Python dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your DATABASE_URL, GEMINI_API_KEY, API_AUTH_TOKEN, etc.

# Run database migrations
alembic upgrade head

# Start the backend
fastapi dev backend/main.py
```

The backend runs on http://localhost:8000. Interactive API docs are at http://localhost:8000/docs.

### Frontend

```bash
cd frontend

# Install Node dependencies
npm install

# Copy and configure environment
cp .env.example .env
# Leave VITE_API_URL empty for the local /api proxy, or set it to your backend URL.
# Set VITE_API_AUTH_TOKEN if the backend API_AUTH_TOKEN is enabled.

# Start the development server
npm run dev
```

The frontend runs on http://localhost:5173.

---

## Environment Variables

### Backend (`.env`)

| Variable               | Required | Default                 | Description                  |
| ---------------------- | -------- | ----------------------- | ---------------------------- |
| `DATABASE_URL`         | Yes      | —                       | PostgreSQL connection string  |
| `API_AUTH_TOKEN`       | Production | —                     | Bearer token for protected API routes |
| `GEMINI_API_KEY`       | Yes      | —                       | Google Gemini API key         |
| `GEMINI_EMBEDDING_MODEL` | No     | `gemini-embedding-2`    | Embedding model name          |
| `GEMINI_LLM_MODEL`     | No       | `gemini-3.1-flash-lite` | LLM model name                |
| `CORS_ORIGINS`         | No       | `http://localhost:5173` | Comma-separated allowed origins |
| `APP_ENV`              | No       | `development`           | Application environment       |
| `LOG_LEVEL`            | No       | `INFO`                  | Log verbosity                 |
| `MAX_UPLOAD_BYTES`     | No       | `10485760`              | Maximum resume upload size    |
| `EMBEDDING_DIMENSIONS` | No       | unset                   | Optional embedding vector length validation |

### Frontend (`frontend/.env`)

| Variable        | Required | Default                  | Description             |
| --------------- | -------- | ------------------------ | ----------------------- |
| `VITE_API_URL`        | No       | `/api`                  | Backend API base URL or relative proxy path |
| `VITE_API_AUTH_TOKEN` | No       | unset                   | Optional bearer token for local/private deployments |

For the frontend Docker image, leave `VITE_API_URL` empty and set runtime `BACKEND_URL`
to the backend service URL so Nginx can proxy `/api/*`. In production, set
runtime `API_AUTH_TOKEN` from Secret Manager on the frontend service so Nginx can
authenticate backend API requests without exposing the token in browser
JavaScript.

---

## Docker

### Build backend

```bash
docker build -f Dockerfile.backend -t careerfit-backend .
docker run -p 8080:8080 --env-file .env careerfit-backend
```

### Build frontend

```bash
docker build -f Dockerfile.frontend \
  -t careerfit-frontend .
docker run -p 8080:8080 -e BACKEND_URL=http://your-backend-url careerfit-frontend
```

### GCP deployment

See [`docs/DEPLOYMENT_GCP.md`](docs/DEPLOYMENT_GCP.md) for the Cloud Run,
Secret Manager, Cloud Scheduler, and Cloud Logging deployment runbook.

---

## Running Tests

```bash
# All tests
pytest

# With output
pytest -v

# Backend tests only
pytest tests/ -k "not frontend"
```

---

## Code Quality

```bash
# Lint and format
ruff check .
ruff format .

# Type checking
mypy backend
```

---

## User Flow

1. **Upload Resume** — Upload a PDF or DOCX resume. Gemini extracts your candidate profile.
2. **Find Jobs** — Import jobs from approved ATS search results. Add jobs manually.
3. **Review Matches** — Browse scored job matches. Filter by status or source.
4. **Save Jobs** — Save jobs you want to track.
5. **Track Applications** — Update application status as you progress through interviews.

---

## API Reference

The FastAPI backend provides interactive docs at `/docs` (Swagger UI) and `/redoc`.

Key endpoint groups:

- `POST /resumes/upload` — Upload and parse a resume
- `GET /jobs` — List jobs with optional search/filter
- `POST /sources/import/{source}` — Import jobs from a source
- `POST /sources/import/web-search` — Trigger the scheduled job discovery workflow
- `GET /applications` — List tracked applications
- `GET /exports/jobs.csv` — Export job data as CSV
- `GET /health/ready` — Health check with database and Gemini status
