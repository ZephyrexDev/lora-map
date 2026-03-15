"""Tests for the FastAPI endpoints in app.main."""

import json
import os
import sqlite3
import tempfile
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

# Set DB_PATH before importing anything from app, so the lifespan and get_db()
# pick up the temporary database instead of /data/lora-planner.db.
_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp_db_path = _tmp_db.name
_tmp_db.close()
os.environ["DB_PATH"] = _tmp_db_path

# Patch the Splat class before app.main is imported, since it instantiates
# a Splat object at module level and the real binary is not available in tests.
with patch("app.services.splat.Splat.__init__", lambda self, **kw: None):
    from fastapi.testclient import TestClient  # noqa: E402

    from app.db import get_db, init_db  # noqa: E402
    from app.main import app  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_db():
    """Re-initialize the database before every test so each test starts clean."""
    init_db(_tmp_db_path)
    # Wipe all rows but keep the schema
    conn = get_db()
    try:
        conn.execute("DELETE FROM tasks")
        conn.execute("DELETE FROM tower_paths")
        conn.execute("DELETE FROM towers")
        conn.commit()
    finally:
        conn.close()
    yield


@pytest.fixture()
def client():
    """FastAPI TestClient wired to the application."""
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def valid_payload() -> dict:
    """Minimal valid payload for POST /predict."""
    return {
        "lat": 40.0,
        "lon": -105.0,
        "tx_power": 20.0,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _insert_tower(tower_id: str, name: str = "Test Tower") -> None:
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO towers (id, name, params) VALUES (?, ?, ?)",
            (tower_id, name, json.dumps({"lat": 0, "lon": 0})),
        )
        conn.commit()
    finally:
        conn.close()


def _insert_task(task_id: str, tower_id: str, status: str = "processing", error: str | None = None) -> None:
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO tasks (id, tower_id, status, error) VALUES (?, ?, ?, ?)",
            (task_id, tower_id, status, error),
        )
        conn.commit()
    finally:
        conn.close()


def _set_tower_geotiff(tower_id: str, data: bytes) -> None:
    conn = get_db()
    try:
        conn.execute("UPDATE towers SET geotiff = ? WHERE id = ?", (data, tower_id))
        conn.commit()
    finally:
        conn.close()


# ===========================================================================
# POST /predict
# ===========================================================================

class TestPostPredict:
    def test_returns_200_with_ids(self, client, valid_payload):
        resp = client.post("/predict", json=valid_payload)
        assert resp.status_code == 200
        body = resp.json()
        assert "task_id" in body
        assert "tower_id" in body

    def test_creates_rows_in_towers_and_tasks(self, client, valid_payload):
        # Patch run_splat so the background task doesn't execute and flip
        # the status away from "processing" before we can inspect the rows.
        with patch("app.main.run_splat"):
            resp = client.post("/predict", json=valid_payload)
        body = resp.json()

        conn = get_db()
        try:
            tower = conn.execute(
                "SELECT * FROM towers WHERE id = ?", (body["tower_id"],)
            ).fetchone()
            assert tower is not None
            assert tower["name"] == "Unnamed"

            task = conn.execute(
                "SELECT * FROM tasks WHERE id = ?", (body["task_id"],)
            ).fetchone()
            assert task is not None
            assert task["status"] == "processing"
            assert task["tower_id"] == body["tower_id"]
        finally:
            conn.close()

    def test_returns_422_for_missing_payload(self, client):
        resp = client.post("/predict", json={})
        assert resp.status_code == 422

    def test_returns_422_for_invalid_lat(self, client, valid_payload):
        valid_payload["lat"] = 999
        resp = client.post("/predict", json=valid_payload)
        assert resp.status_code == 422


# ===========================================================================
# GET /status/{task_id}
# ===========================================================================

class TestGetStatus:
    def test_returns_404_for_unknown_task(self, client):
        resp = client.get(f"/status/{uuid4()}")
        assert resp.status_code == 404
        assert "error" in resp.json()

    def test_returns_processing_for_new_task(self, client, valid_payload):
        with patch("app.main.run_splat"):
            create_resp = client.post("/predict", json=valid_payload)
        task_id = create_resp.json()["task_id"]

        resp = client.get(f"/status/{task_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["task_id"] == task_id
        assert body["status"] == "processing"


# ===========================================================================
# GET /result/{task_id}
# ===========================================================================

class TestGetResult:
    def test_returns_404_for_unknown_task(self, client):
        resp = client.get(f"/result/{uuid4()}")
        assert resp.status_code == 404
        assert "error" in resp.json()

    def test_returns_processing_status_for_in_progress_task(self, client, valid_payload):
        with patch("app.main.run_splat"):
            create_resp = client.post("/predict", json=valid_payload)
        task_id = create_resp.json()["task_id"]

        resp = client.get(f"/result/{task_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "processing"

    def test_returns_geotiff_for_completed_task(self, client):
        tower_id = str(uuid4())
        task_id = str(uuid4())
        fake_tiff = b"FAKE_GEOTIFF_DATA_1234567890"

        _insert_tower(tower_id)
        _insert_task(task_id, tower_id, status="completed")
        _set_tower_geotiff(tower_id, fake_tiff)

        resp = client.get(f"/result/{task_id}")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/tiff"
        assert "content-disposition" in resp.headers
        assert task_id in resp.headers["content-disposition"]
        assert resp.content == fake_tiff


# ===========================================================================
# GET /towers
# ===========================================================================

class TestGetTowers:
    def test_returns_empty_list_when_no_towers(self, client):
        resp = client.get("/towers")
        assert resp.status_code == 200
        assert resp.json() == {"towers": []}

    def test_returns_towers_without_geotiff(self, client, valid_payload):
        # Create two towers via /predict
        r1 = client.post("/predict", json=valid_payload)
        r2 = client.post("/predict", json=valid_payload)
        tower_ids = {r1.json()["tower_id"], r2.json()["tower_id"]}

        resp = client.get("/towers")
        assert resp.status_code == 200
        towers = resp.json()["towers"]
        assert len(towers) == 2

        returned_ids = {t["id"] for t in towers}
        assert returned_ids == tower_ids

        # Ensure no geotiff key is leaked in the response
        for t in towers:
            assert "geotiff" not in t
            assert "params" in t
            assert "created_at" in t


# ===========================================================================
# DELETE /towers/{tower_id}
# ===========================================================================

class TestDeleteTower:
    def test_returns_404_for_unknown_tower(self, client):
        resp = client.delete(f"/towers/{uuid4()}")
        assert resp.status_code == 404
        assert "error" in resp.json()

    def test_deletes_existing_tower(self, client, valid_payload):
        create_resp = client.post("/predict", json=valid_payload)
        tower_id = create_resp.json()["tower_id"]

        resp = client.delete(f"/towers/{tower_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["tower_id"] == tower_id
        assert "deleted" in body["message"].lower()

        # Confirm tower is gone
        conn = get_db()
        try:
            row = conn.execute("SELECT * FROM towers WHERE id = ?", (tower_id,)).fetchone()
            assert row is None
        finally:
            conn.close()

    def test_cascades_delete_to_tasks(self, client, valid_payload):
        create_resp = client.post("/predict", json=valid_payload)
        tower_id = create_resp.json()["tower_id"]
        task_id = create_resp.json()["task_id"]

        # Verify the task exists before deletion
        conn = get_db()
        try:
            task = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
            assert task is not None
        finally:
            conn.close()

        # Delete the tower
        resp = client.delete(f"/towers/{tower_id}")
        assert resp.status_code == 200

        # Verify the task was cascade-deleted
        conn = get_db()
        try:
            task = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
            assert task is None
        finally:
            conn.close()
