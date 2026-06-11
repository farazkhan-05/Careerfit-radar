# GCP Deployment

This runbook deploys CareerFit Radar to Google Cloud Run using Artifact Registry,
Secret Manager, Cloud Scheduler, and Cloud Logging.

## Prerequisites

Install and authenticate the Google Cloud CLI:

```powershell
gcloud auth login
gcloud auth application-default login
```

Select or create a GCP project with billing enabled. The deploying account needs
permissions for Cloud Run, Cloud Build, Artifact Registry, Secret Manager, Cloud
Scheduler, and Cloud Logging.

## Required Secrets

Create or update the required Secret Manager secrets from the local `.env` file:

```powershell
.\scripts\sync-gcp-secrets.ps1 -ProjectId "careerfit-radar-prod"
```

Use the Neon pooled PostgreSQL URL with SSL enabled, for example
`sslmode=require`. `API_AUTH_TOKEN` must be at least 32 characters in production.

## Deploy

From the repository root:

```powershell
.\scripts\deploy-gcp.ps1 `
  -ProjectId "careerfit-radar-prod" `
  -Region "us-central1" `
  -SearchQuery '("Junior AI Engineer" OR "Associate GenAI Engineer" OR "Full Stack AI Developer") Python FastAPI React RAG LangChain LangGraph -sales -support -WordPress -internship' `
  -SearchLocation "India remote" `
  -SchedulerCron "0 9 * * 1-5" `
  -SchedulerTimeZone "Asia/Kolkata"
```

The script:

- Enables required GCP APIs.
- Creates a dedicated Cloud Run runtime service account if missing.
- Grants the runtime service account Secret Manager read access and log-writing access.
- Creates the Artifact Registry Docker repository if missing.
- Builds backend and frontend images with Cloud Build.
- Deploys both services to Cloud Run.
- Injects production secrets from Secret Manager.
- Updates backend CORS after the frontend URL is known.
- Creates or updates a Cloud Scheduler job that calls
  `POST /sources/import/web-search`.

## Production Configuration

Backend Cloud Run environment:

```text
APP_ENV=production
LOG_LEVEL=INFO
GOOGLE_CLOUD_PROJECT=<project-id>
CORS_ORIGINS=<frontend-url>,<backend-url>
DATABASE_URL=<Secret Manager>
GEMINI_API_KEY=<Secret Manager>
API_AUTH_TOKEN=<Secret Manager>
TAVILY_API_KEY=<Secret Manager>
```

Frontend Cloud Run environment:

```text
BACKEND_URL=<backend-cloud-run-url>
API_AUTH_TOKEN=<Secret Manager>
```

The frontend image keeps `VITE_API_URL` empty so the browser calls `/api`.
Nginx proxies `/api/*` to the backend and attaches the backend bearer token from
the Cloud Run environment. Do not build `VITE_API_AUTH_TOKEN` into the production
browser bundle.

## Verification

Check backend readiness:

```powershell
curl <backend-url>/health/ready
```

Expected response:

```json
{"status":"ok","checks":{"database":"ok","gemini":"configured"}}
```

Trigger the scheduled import manually:

```powershell
gcloud scheduler jobs run careerfit-scheduled-web-search `
  --location us-central1 `
  --project <your-gcp-project-id>
```

Then inspect Cloud Run logs:

```powershell
gcloud run services logs read careerfit-backend `
  --region us-central1 `
  --project <your-gcp-project-id> `
  --limit 100
```

## Notes

The backend Cloud Run service is deployed as publicly reachable, but protected
API routes require `API_AUTH_TOKEN`. This allows the frontend Nginx proxy and
Cloud Scheduler to call the backend without exposing credentials in browser
JavaScript.
