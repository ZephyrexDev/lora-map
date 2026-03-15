"""SQLAlchemy engine and session factory for the LoRa Coverage Planner."""

from __future__ import annotations

import logging
import os
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH: str = "/data/lora-planner.db"

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def init_engine(db_path: str | Path | None = None) -> Engine:
    """Create and configure the SQLAlchemy engine for the given database path.

    Sets WAL journal mode and enables foreign keys on every new connection.
    Initializes the global engine and session factory used by :func:`db_session`.

    Parameters
    ----------
    db_path:
        Filesystem path to the database file.  Falls back to the ``DB_PATH``
        environment variable, then to :data:`DEFAULT_DB_PATH`.
    """
    global _engine, _session_factory

    resolved = Path(db_path or os.environ.get("DB_PATH", DEFAULT_DB_PATH))
    resolved.parent.mkdir(parents=True, exist_ok=True)
    logger.debug("Creating SQLAlchemy engine for %s", resolved)

    engine = create_engine(
        f"sqlite:///{resolved}",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    _engine = engine
    _session_factory = sessionmaker(bind=engine)
    return engine


def get_engine() -> Engine:
    """Return the global engine, raising if not yet initialized."""
    if _engine is None:
        raise RuntimeError("Database engine not initialized — call init_engine() first")
    return _engine


@contextmanager
def db_session() -> Generator[Session, None, None]:
    """Context manager that yields a configured SQLAlchemy session and closes it on exit."""
    if _session_factory is None:
        raise RuntimeError("Database not initialized — call init_engine() first")
    session = _session_factory()
    try:
        yield session
    finally:
        session.close()
