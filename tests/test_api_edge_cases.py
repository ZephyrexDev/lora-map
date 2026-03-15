"""Tests for API endpoint edge cases: failed tasks, missing geotiff, etc."""

import json
import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

import app.auth as auth_mod
from app.db import db_connection, init_db
from app.main import app


@pytest.fixture(autouse=True)
def _reset():
    init_db(os.environ["DB_PATH"])
    with db_connection() as conn:
        conn.execute("DELETE FROM tasks")
        conn.execute("DELETE FROM tower_paths")
        conn.execute("DELETE FROM towers")
        conn.commit()
    # Disable auth for these tests
    original = auth_mod.ADMIN_PASSWORD
    auth_mod.ADMIN_PASSWORD = None
    yield
    auth_mod.ADMIN_PASSWORD = original


@pytest.fixture()
def client():
    return TestClient(app)


def _insert_tower(tower_id, geotiff=None):
    with db_connection() as conn:
        conn.execute(
            "INSERT INTO towers (id, name, params, geotiff) VALUES (?, ?, ?, ?)",
            (tower_id, "Test", json.dumps({"lat": 0, "lon": 0}), geotiff),
        )
        conn.commit()


def _insert_task(task_id, tower_id, status="processing", error=None):
    with db_connection() as conn:
        conn.execute(
            "INSERT INTO tasks (id, tower_id, status, error) VALUES (?, ?, ?, ?)",
            (task_id, tower_id, status, error),
        )
        conn.commit()


class TestGetResultEdgeCases:
    def test_failed_task_returns_error(self, client):
        tower_id = str(uuid4())
        task_id = str(uuid4())
        _insert_tower(tower_id)
        _insert_task(task_id, tower_id, status="failed", error="SPLAT! crashed")

        resp = client.get(f"/result/{task_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "failed"
        assert "SPLAT! crashed" in body["error"]

    def test_completed_task_missing_geotiff_returns_500(self, client):
        tower_id = str(uuid4())
        task_id = str(uuid4())
        _insert_tower(tower_id)  # No geotiff set
        _insert_task(task_id, tower_id, status="completed")

        resp = client.get(f"/result/{task_id}")
        assert resp.status_code == 500
        assert "No result found" in resp.json()["error"]


class TestGetStatusEdgeCases:
    def test_failed_task_includes_error(self, client):
        tower_id = str(uuid4())
        task_id = str(uuid4())
        _insert_tower(tower_id)
        _insert_task(task_id, tower_id, status="failed", error="Tile download failed")

        resp = client.get(f"/status/{task_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "failed"
        assert body["error"] == "Tile download failed"

    def test_completed_task_has_no_error_key(self, client):
        tower_id = str(uuid4())
        task_id = str(uuid4())
        _insert_tower(tower_id)
        _insert_task(task_id, tower_id, status="completed")

        resp = client.get(f"/status/{task_id}")
        body = resp.json()
        assert body["status"] == "completed"
        assert "error" not in body


class TestPostPredictEdgeCases:
    def test_rejects_out_of_range_lat(self, client):
        resp = client.post("/predict", json={"lat": 91, "lon": 0, "tx_power": 20})
        assert resp.status_code == 422

    def test_rejects_out_of_range_lon(self, client):
        resp = client.post("/predict", json={"lat": 0, "lon": 181, "tx_power": 20})
        assert resp.status_code == 422

    def test_rejects_zero_power(self, client):
        resp = client.post("/predict", json={"lat": 0, "lon": 0, "tx_power": 0})
        assert resp.status_code == 422

    def test_rejects_negative_power(self, client):
        resp = client.post("/predict", json={"lat": 0, "lon": 0, "tx_power": -10})
        assert resp.status_code == 422


class TestDeleteTowerEdgeCases:
    def test_double_delete_returns_404(self, client):
        tower_id = str(uuid4())
        _insert_tower(tower_id)

        resp1 = client.delete(f"/towers/{tower_id}")
        assert resp1.status_code == 200

        resp2 = client.delete(f"/towers/{tower_id}")
        assert resp2.status_code == 404


class TestGetTowersResponse:
    def test_tower_params_are_parsed_json(self, client):
        tower_id = str(uuid4())
        params = {"lat": 51.0, "lon": -114.0, "tx_power": 30.0}
        with db_connection() as conn:
            conn.execute(
                "INSERT INTO towers (id, name, params) VALUES (?, ?, ?)",
                (tower_id, "Test", json.dumps(params)),
            )
            conn.commit()

        resp = client.get("/towers")
        towers = resp.json()["towers"]
        assert len(towers) == 1
        assert towers[0]["params"] == params
        assert isinstance(towers[0]["params"], dict)
