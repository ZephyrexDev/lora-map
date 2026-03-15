"""SQLite connection factory for the LoRa Coverage Planner."""

from __future__ import annotations

import logging
import os
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH: str = "/data/lora-planner.db"


def get_db(db_path: str | None = None) -> sqlite3.Connection:
    """Return a configured SQLite connection.

    Parameters
    ----------
    db_path:
        Filesystem path to the database file.  Falls back to the ``DB_PATH``
        environment variable, then to :data:`DEFAULT_DB_PATH`.

    Returns
    -------
    sqlite3.Connection
        A connection with WAL mode, foreign keys enabled, and
        ``row_factory`` set to :class:`sqlite3.Row`.
    """
    resolved_path: Path = Path(db_path or os.environ.get("DB_PATH", DEFAULT_DB_PATH))

    logger.debug("Opening database connection to %s", resolved_path)

    conn: sqlite3.Connection = sqlite3.connect(str(resolved_path))
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.row_factory = sqlite3.Row

    return conn
