"""Shared pytest configuration and fixtures for all backend tests.

Sets SPLAT_PATH and DB_PATH environment variables before any app modules
are imported, so the real SPLAT! binaries are used (no mocks) and the
database points to a temporary file.
"""

import json
import os
import tempfile
from pathlib import Path
from uuid import uuid4

# ---------------------------------------------------------------------------
# Environment setup — must happen before any app imports
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Point to the locally-built SPLAT! binaries
_splat_bin_dir = _PROJECT_ROOT / "splat" / "bin"
if _splat_bin_dir.is_dir():
    os.environ.setdefault("SPLAT_PATH", str(_splat_bin_dir))

# Use a temporary database for tests
_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp_db_path = _tmp_db.name
_tmp_db.close()
os.environ["DB_PATH"] = _tmp_db_path

# ---------------------------------------------------------------------------
# Imports that depend on environment setup above
# ---------------------------------------------------------------------------

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import app.auth as auth_mod  # noqa: E402
from app.db import db_connection, init_db  # noqa: E402
from app.main import app  # noqa: E402


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_db():
    """Re-initialize and wipe the database before every test."""
    init_db(_tmp_db_path)
    with db_connection() as conn:
        conn.execute("DELETE FROM tasks")
        conn.execute("DELETE FROM tower_paths")
        conn.execute("DELETE FROM towers")
        conn.execute("DELETE FROM settings")
        conn.commit()
    yield


@pytest.fixture()
def client():
    """FastAPI TestClient with auth disabled."""
    original = auth_mod.ADMIN_PASSWORD
    auth_mod.ADMIN_PASSWORD = None
    with TestClient(app) as c:
        yield c
    auth_mod.ADMIN_PASSWORD = original


@pytest.fixture()
def client_with_auth():
    """FastAPI TestClient with auth enabled (password = 's3cret')."""
    original = auth_mod.ADMIN_PASSWORD
    auth_mod.ADMIN_PASSWORD = "s3cret"
    auth_mod._login_attempts.clear()
    yield TestClient(app)
    auth_mod.ADMIN_PASSWORD = original


@pytest.fixture()
def valid_payload() -> dict:
    """Minimal valid payload for POST /predict."""
    return {"lat": 40.0, "lon": -105.0, "tx_power": 20.0}


# ---------------------------------------------------------------------------
# Shared DB helpers
# ---------------------------------------------------------------------------

def insert_tower(
    tower_id: str | None = None,
    name: str = "Test Tower",
    geotiff: bytes | None = None,
) -> str:
    """Insert a tower row and return its id."""
    tower_id = tower_id or str(uuid4())
    with db_connection() as conn:
        conn.execute(
            "INSERT INTO towers (id, name, params, geotiff) VALUES (?, ?, ?, ?)",
            (tower_id, name, json.dumps({"lat": 0, "lon": 0}), geotiff),
        )
        conn.commit()
    return tower_id


def insert_task(
    task_id: str | None = None,
    tower_id: str = "",
    status: str = "processing",
    error: str | None = None,
) -> str:
    """Insert a task row and return its id."""
    task_id = task_id or str(uuid4())
    with db_connection() as conn:
        conn.execute(
            "INSERT INTO tasks (id, tower_id, status, error) VALUES (?, ?, ?, ?)",
            (task_id, tower_id, status, error),
        )
        conn.commit()
    return task_id


def set_tower_geotiff(tower_id: str, data: bytes) -> None:
    """Set geotiff blob on an existing tower."""
    with db_connection() as conn:
        conn.execute("UPDATE towers SET geotiff = ? WHERE id = ?", (data, tower_id))
        conn.commit()
