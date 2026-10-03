"""Engine, session factory and the FastAPI session dependency.

SQLite keeps the local-run path to zero services. Tables are created on startup; there are no
migrations during the hackathon (docs/decisions/0001-stack.md, 0009-sqlite-over-duckdb.md).
"""

from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.db.base import Base

_settings = get_settings()

if _settings.database_url.startswith("sqlite:///"):
    Path(_settings.database_url.removeprefix("sqlite:///")).parent.mkdir(
        parents=True, exist_ok=True
    )

engine = create_engine(
    _settings.database_url,
    # The pipeline runs in a background thread, so the connection is shared across threads.
    connect_args={"check_same_thread": False}
    if _settings.database_url.startswith("sqlite")
    else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

if engine.dialect.name == "sqlite":

    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        # WAL lets the UI keep reading while the pipeline thread writes.
        cursor.execute("PRAGMA journal_mode=WAL")
        # Wait for a competing writer instead of failing with "database is locked".
        cursor.execute("PRAGMA busy_timeout=5000")
        # SQLite ignores foreign keys unless asked, per connection.
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def init_db() -> None:
    from app.db import models  # noqa: F401  (registers tables on Base.metadata)

    Base.metadata.create_all(engine)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
