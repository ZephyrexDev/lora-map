"""SQLite schema definitions and database initialization for the LoRa Coverage Planner."""

from __future__ import annotations

import logging
from pathlib import Path

from app.db.connection import db_connection

logger = logging.getLogger(__name__)

SCHEMA_TOWERS: str = """\
CREATE TABLE IF NOT EXISTS towers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    color TEXT,  -- hex color assigned to this tower (e.g. #ff0000)
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
    distance_km REAL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(tower_a_id, tower_b_id)
);
"""

SCHEMA_SETTINGS: str = """\
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

SCHEMA_SIMULATIONS: str = """\
CREATE TABLE IF NOT EXISTS simulations (
    id TEXT PRIMARY KEY,
    tower_id TEXT NOT NULL REFERENCES towers(id) ON DELETE CASCADE,
    client_hardware TEXT NOT NULL,
    client_antenna TEXT NOT NULL,
    terrain_model TEXT NOT NULL DEFAULT 'bare_earth',
    status TEXT NOT NULL DEFAULT 'pending',
    geotiff BLOB,
    error TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(tower_id, client_hardware, client_antenna, terrain_model)
);
"""

SCHEMA_VERSION: str = """\
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

# Ordered list of (version, DDL statements).  Each entry is applied at most once.
# To add a migration, append a new tuple with the next version number.
MIGRATIONS: list[tuple[int, list[str]]] = [
    (
        1,
        [
            SCHEMA_TOWERS,
            SCHEMA_TASKS,
            SCHEMA_TOWER_PATHS,
            SCHEMA_SETTINGS,
            SCHEMA_SIMULATIONS,
        ],
    ),
]


def init_db(db_path: str | Path) -> None:
    """Create the database file (if needed) and apply all pending schema migrations.

    Each migration is applied inside a single transaction and its version
    number is recorded in the ``schema_version`` table so it is never
    re-applied.

    Parameters
    ----------
    db_path:
        Filesystem path where the SQLite database should be created.
    """
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Initializing database at %s", db_path)

    with db_connection(str(db_path)) as conn:
        # Bootstrap the version-tracking table (always safe to re-run)
        conn.execute(SCHEMA_VERSION)

        current = conn.execute("SELECT COALESCE(MAX(version), 0) FROM schema_version").fetchone()[0]
        logger.info("Current schema version: %s", current)

        for version, statements in MIGRATIONS:
            if version <= current:
                continue
            for stmt in statements:
                conn.execute(stmt)
            conn.execute("INSERT INTO schema_version (version) VALUES (?)", (version,))
            logger.info("Applied schema migration v%s", version)

        conn.commit()
        logger.info("Database schema up to date")
