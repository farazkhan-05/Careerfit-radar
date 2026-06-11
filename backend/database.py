from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.config import Settings, get_settings


class Base(DeclarativeBase):
    pass


def create_database_engine(settings: Settings | None = None) -> Engine:
    active_settings = settings or get_settings()
    return create_engine(
        active_settings.database_url,
        pool_pre_ping=True,
        future=True,
    )


def create_session_factory(engine: Engine | None = None) -> sessionmaker[Session]:
    return sessionmaker(
        bind=engine or create_database_engine(),
        autoflush=False,
        expire_on_commit=False,
    )


@lru_cache
def get_engine() -> Engine:
    return create_database_engine()


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return create_session_factory(get_engine())


SessionLocal = get_session_factory


def get_db() -> Generator[Session, None, None]:
    session_factory = get_session_factory()
    with session_factory() as session:
        yield session


def test_database_connection(engine: Engine | None = None) -> bool:
    active_engine = engine or get_engine()
    with active_engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return True
