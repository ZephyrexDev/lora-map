"""Shared pytest configuration and fixtures for all backend tests."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

import app.auth as auth_mod
import app.main as main_mod
from app.db import db_connection, init_db
from app.main import app

# ---------------------------------------------------------------------------
# Environment setup
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

_splat_bin_dir = _PROJECT_ROOT / "splat" / "bin"
if _splat_bin_dir.is_dir():
    os.environ.setdefault("SPLAT_PATH", str(_splat_bin_dir))

_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)  # noqa: SIM115
_tmp_db_path = _tmp_db.name
_tmp_db.close()
os.environ["DB_PATH"] = _tmp_db_path

# ---------------------------------------------------------------------------
# Ensure splat_service is set for tests (lazy init normally happens in lifespan)
# ---------------------------------------------------------------------------

if main_mod.splat_service is None:
    splat_path = os.environ.get("SPLAT_PATH")
    if splat_path and Path(splat_path).is_dir():
        try:
            from app.services.splat import Splat

            main_mod.splat_service = Splat(splat_path=splat_path)
        except FileNotFoundError:
            main_mod.splat_service = MagicMock()
    else:
        main_mod.splat_service = MagicMock()

# ---------------------------------------------------------------------------
# Slow-test gating via --run-slow CLI flag
# ---------------------------------------------------------------------------


def pytest_addoption(parser):
    parser.addoption("--run-slow", action="store_true", default=False, help="Run slow integration tests")


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--run-slow"):
        skip_slow = pytest.mark.skip(reason="need --run-slow option to run")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_db():
    """Re-initialize and wipe the database before every test."""
    init_db(_tmp_db_path)
    with db_connection() as conn:
        conn.execute("DELETE FROM simulations")
        conn.execute("DELETE FROM tasks")
        conn.execute("DELETE FROM tower_paths")
        conn.execute("DELETE FROM towers")
        conn.execute("DELETE FROM settings")
        conn.commit()
    yield


@pytest.fixture()
def client():
    """FastAPI TestClient with auth disabled."""
    orig = os.environ.pop("ADMIN_PASSWORD", None)
    with TestClient(app) as c:
        yield c
    if orig is not None:
        os.environ["ADMIN_PASSWORD"] = orig


@pytest.fixture()
def client_with_auth():
    """FastAPI TestClient with auth enabled (password = 's3cret').

    Also clears any active session tokens and rate-limit state.
    """
    os.environ["ADMIN_PASSWORD"] = "s3cret"
    with auth_mod._token_lock:
        auth_mod._active_tokens.clear()
    with auth_mod._rate_lock:
        auth_mod._login_attempts.clear()
    yield TestClient(app)
    del os.environ["ADMIN_PASSWORD"]


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
