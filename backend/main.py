from fastapi import FastAPI

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
