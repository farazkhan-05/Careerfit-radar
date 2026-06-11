from __future__ import annotations

from hmac import compare_digest

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.config import Settings, get_settings

_bearer_scheme = HTTPBearer(auto_error=False)


def require_api_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    settings: Settings = Depends(get_settings),
) -> None:
    token = settings.api_auth_token
    if not token:
        if settings.app_env.casefold() in {"production", "prod"}:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="API authentication is required in production. Set API_AUTH_TOKEN.",
            )
        return
    if settings.app_env.casefold() in {"production", "prod"} and len(token) < 32:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API_AUTH_TOKEN must be at least 32 characters in production.",
        )

    supplied = credentials.credentials if credentials else x_api_key
    if supplied and compare_digest(supplied, token):
        return

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing or invalid API credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_bulk_delete_confirmation(
    confirmation: str | None = Header(default=None, alias="X-Confirm-Bulk-Delete"),
) -> None:
    if confirmation != "true":
        raise HTTPException(
            status_code=status.HTTP_428_PRECONDITION_REQUIRED,
            detail="Bulk delete requires X-Confirm-Bulk-Delete: true.",
        )
