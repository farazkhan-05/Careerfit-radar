from typing import Any, cast

from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.config import Settings
from backend.main import app


def test_health_endpoint() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_settings_load_required_environment() -> None:
    settings = Settings(
        DATABASE_URL="postgresql://user:pass@example.com:5432/careerfit",
        GEMINI_API_KEY="test-key",
    )

    assert settings.database_url.startswith("postgresql://")
    assert settings.gemini_embedding_model == "gemini-embedding-2"
    assert settings.gemini_llm_model == "gemini-3.1-flash-lite"


def test_settings_fail_when_required_environment_is_missing() -> None:
    try:
        cast(Any, Settings)(_env_file=None)
    except ValidationError as exc:
        missing_fields = {error["loc"][0] for error in exc.errors()}
    else:
        raise AssertionError("Settings should require DATABASE_URL and GEMINI_API_KEY")

    assert {"DATABASE_URL", "GEMINI_API_KEY"}.issubset(missing_fields)
