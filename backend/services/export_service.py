from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from backend.routes.crud import rows_to_csv


def build_csv(rows: Iterable[dict[str, Any]], fieldnames: list[str]) -> str:
    return rows_to_csv(rows, fieldnames)
