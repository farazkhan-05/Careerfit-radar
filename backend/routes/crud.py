from __future__ import annotations

import csv
from collections.abc import Iterable
from io import StringIO
from typing import Any, Generic, TypeVar
from uuid import UUID

from fastapi import HTTPException, Query, Response, status
from pydantic import BaseModel
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from backend.database import Base

ModelT = TypeVar("ModelT", bound=Base)


class PaginationParams:
    def __init__(
        self,
        limit: int = Query(default=50, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
    ) -> None:
        self.limit = limit
        self.offset = offset


class Page(BaseModel, Generic[ModelT]):
    items: list[Any]
    total: int
    limit: int
    offset: int


def paginate(
    session: Session,
    statement: Select[Any],
    pagination: PaginationParams,
) -> dict[str, Any]:
    total_statement = select(func.count()).select_from(statement.subquery())
    total = int(session.execute(total_statement).scalar_one())
    items = (
        session.execute(statement.limit(pagination.limit).offset(pagination.offset))
        .scalars()
        .all()
    )
    return {
        "items": [serialize_entity(item) for item in items],
        "total": total,
        "limit": pagination.limit,
        "offset": pagination.offset,
    }


def get_or_404(session: Session, model: type[ModelT], entity_id: UUID) -> ModelT:
    entity = session.get(model, entity_id)
    if entity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{model.__name__} not found.",
        )
    return entity


def create_entity(session: Session, model: type[ModelT], payload: BaseModel) -> ModelT:
    entity = model(**payload.model_dump(mode="json"))
    session.add(entity)
    session.commit()
    session.refresh(entity)
    return entity


def update_entity(
    session: Session,
    model: type[ModelT],
    entity_id: UUID,
    payload: dict[str, Any],
) -> ModelT:
    entity = get_or_404(session, model, entity_id)
    for key, value in payload.items():
        if value is not None and hasattr(entity, key):
            setattr(entity, key, value)
    session.commit()
    session.refresh(entity)
    return entity


def delete_entity(session: Session, model: type[ModelT], entity_id: UUID) -> Response:
    entity = get_or_404(session, model, entity_id)
    session.delete(entity)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def rows_to_csv(rows: Iterable[dict[str, Any]], fieldnames: list[str]) -> str:
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return output.getvalue()


def serialize_entity(entity: Any) -> dict[str, Any]:
    mapper = getattr(entity, "__mapper__", None)
    if mapper is None:
        if isinstance(entity, dict):
            return entity
        return {
            key: value
            for key, value in vars(entity).items()
            if not key.startswith("_")
        }
    return {
        column.key: getattr(entity, column.key)
        for column in mapper.columns
    }
