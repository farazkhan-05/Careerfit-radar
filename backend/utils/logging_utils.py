from __future__ import annotations

import logging

from backend.config import Settings


def configure_logging(settings: Settings) -> None:
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    if settings.app_env.casefold() not in {"production", "prod"}:
        return
    if not settings.google_cloud_project:
        return

    try:
        import google.cloud.logging
    except ImportError:
        logging.getLogger(__name__).warning(
            "google-cloud-logging is not installed; using standard logging."
        )
        return

    try:
        client = google.cloud.logging.Client(project=settings.google_cloud_project)
        client.setup_logging(log_level=level)
    except Exception as exc:  # pragma: no cover - provider setup varies by runtime.
        logging.getLogger(__name__).warning(
            "Cloud Logging setup failed; using standard logging: %s",
            exc,
        )
