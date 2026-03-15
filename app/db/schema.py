"""SQLite schema definitions and database initialization for the LoRa Coverage Planner."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)

SCHEMA_TOWERS: str = """\
CREATE TABLE IF NOT EXISTS towers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    params TEXT NOT NULL,  -- JSON blob of all simulation params
    geotiff BLOB,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

SCHEMA_TASKS: str = """\
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    tower_id TEXT NOT NULL REFERENCES towers(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'processing',  -- processing, completed, failed
    error TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

SCHEMA_TOWER_PATHS: str = """\
CREATE TABLE IF NOT EXISTS tower_paths (
    id TEXT PRIMARY KEY,
    tower_a_id TEXT NOT NULL REFERENCES towers(id) ON DELETE CASCADE,
    tower_b_id TEXT NOT NULL REFERENCES towers(id) ON DELETE CASCADE,
    path_loss_db REAL,
    has_los INTEGER,  -- 0 or 1
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(tower_a_id, tower_b_id)
);
"""

ALL_SCHEMAS: list[str] = [SCHEMA_TOWERS, SCHEMA_TASKS, SCHEMA_TOWER_PATHS]


def init_db(db_path: str | Path) -> None:
    """Create the database file (if needed) and apply all schema migrations.

    Parameters
    ----------
    db_path:
        Filesystem path where the SQLite database should be created.
    """
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Initializing database at %s", db_path)

    conn: sqlite3.Connection = sqlite3.connect(str(db_path))
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")

        for schema in ALL_SCHEMAS:
            conn.executescript(schema)

        conn.commit()
        logger.info("Database schema applied successfully")
    finally:
        conn.close()
