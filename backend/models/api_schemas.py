from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PageResponse(BaseModel):
    items: list[Any]
    total: int
    limit: int
    offset: int


class HealthResponse(BaseModel):
    status: str
    checks: dict[str, str] = Field(default_factory=dict)
