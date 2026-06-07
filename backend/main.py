from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import get_settings
from backend.routes import (
    application_routes,
    export_routes,
    health_routes,
    job_routes,
    profile_routes,
    resume_routes,
    source_routes,
    workflow_routes,
)

app = FastAPI(title="CareerFit Radar")

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(health_routes.router)
app.include_router(resume_routes.router)
app.include_router(profile_routes.router)
app.include_router(job_routes.router)
app.include_router(workflow_routes.router)
app.include_router(application_routes.router)
app.include_router(source_routes.router)
app.include_router(export_routes.router)
