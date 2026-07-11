"""SQLite persistence — engine, session dependency, and table creation.

Used for the demo scope's two needs (Section 6.1 of the dev plan): logged
actual production (feeds calibration) and surviving a page refresh during a
live walkthrough. No migrations framework — `init_db()` just creates tables
that don't exist yet, which is enough for a single-file demo database.
"""

from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from backend.config import settings

_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=_connect_args)


def init_db() -> None:
    """Create any tables that don't already exist. Call once on app startup."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a database session."""
    with Session(engine) as session:
        yield session
