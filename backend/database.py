from collections.abc import Generator

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


SessionLocal = create_session_factory


def get_db() -> Generator[Session, None, None]:
    session_factory = create_session_factory()
    with session_factory() as session:
        yield session


def test_database_connection(engine: Engine | None = None) -> bool:
    active_engine = engine or create_database_engine()
    with active_engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return True
