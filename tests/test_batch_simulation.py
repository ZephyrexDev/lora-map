"""Tests for batch simulation backend (matrix-driven simulations)."""

from unittest.mock import patch
from uuid import uuid4

from app.db import db_connection
from app.matrix import get_matrix_combinations, get_matrix_config


class TestPredictCreatesSimulations:
    """POST /predict should create simulation rows for each matrix combination."""

    def test_creates_simulation_rows_for_each_combination(self, client, valid_payload):
        with db_connection() as conn:
            config = get_matrix_config(conn)
        expected_combos = get_matrix_combinations(config)

        with patch("app.main.splat_service.coverage_prediction", return_value=b"FAKE"):
            resp = client.post("/predict", json=valid_payload)

        assert resp.status_code == 200
        tower_id = resp.json()["tower_id"]

        with db_connection() as conn:
            rows = conn.execute(
                "SELECT client_hardware, client_antenna, terrain_model, status " "FROM simulations WHERE tower_id = ?",
                (tower_id,),
            ).fetchall()

        assert len(rows) == len(expected_combos)
        for row in rows:
            assert row["status"] in ("pending", "completed", "failed")

    def test_simulation_rows_match_matrix_combinations(self, client, valid_payload):
        with db_connection() as conn:
            config = get_matrix_config(conn)
        expected_combos = get_matrix_combinations(config)

        with patch("app.main.splat_service.coverage_prediction", return_value=b"FAKE"):
            resp = client.post("/predict", json=valid_payload)

        tower_id = resp.json()["tower_id"]

        with db_connection() as conn:
            rows = conn.execute(
                "SELECT client_hardware, client_antenna, terrain_model " "FROM simulations WHERE tower_id = ?",
                (tower_id,),
            ).fetchall()

        actual = {(r["client_hardware"], r["client_antenna"], r["terrain_model"]) for r in rows}
        expected = {(c["hardware"], c["antenna"], c["terrain"]) for c in expected_combos}
        assert actual == expected


class TestGetTowerSimulations:
    """GET /towers/{tower_id}/simulations returns the list."""

    def test_returns_simulations_for_tower(self, client, valid_payload):
        with patch("app.main.splat_service.coverage_prediction", return_value=b"FAKE"):
            resp = client.post("/predict", json=valid_payload)

        tower_id = resp.json()["tower_id"]
        resp = client.get(f"/towers/{tower_id}/simulations")
        assert resp.status_code == 200
        body = resp.json()
        assert "simulations" in body
        assert len(body["simulations"]) > 0

        for sim in body["simulations"]:
            assert "id" in sim
            assert "client_hardware" in sim
            assert "client_antenna" in sim
            assert "terrain_model" in sim
            assert "status" in sim
            assert "geotiff" not in sim

    def test_returns_empty_list_for_unknown_tower(self, client):
        resp = client.get(f"/towers/{uuid4()}/simulations")
        assert resp.status_code == 200
        assert resp.json() == {"simulations": []}


class TestGetSimulationResult:
    """GET /simulations/{sim_id}/result returns 404 for unknown id."""

    def test_returns_404_for_unknown_id(self, client):
        resp = client.get(f"/simulations/{uuid4()}/result")
        assert resp.status_code == 404
        assert "error" in resp.json()

    def test_returns_geotiff_for_completed_simulation(self, client, valid_payload):
        with patch("app.main.splat_service.coverage_prediction", return_value=b"FAKE_TIFF"):
            resp = client.post("/predict", json=valid_payload)

        tower_id = resp.json()["tower_id"]

        # Pick the first simulation and mark it completed with a geotiff
        with db_connection() as conn:
            row = conn.execute(
                "SELECT id FROM simulations WHERE tower_id = ? LIMIT 1",
                (tower_id,),
            ).fetchone()
            sim_id = row["id"]
            conn.execute(
                "UPDATE simulations SET status = 'completed', geotiff = ? WHERE id = ?",
                (b"SIM_GEOTIFF_DATA", sim_id),
            )
            conn.commit()

        resp = client.get(f"/simulations/{sim_id}/result")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/tiff"
        assert resp.content == b"SIM_GEOTIFF_DATA"

    def test_returns_status_for_pending_simulation(self, client, valid_payload):
        with patch("app.main.splat_service.coverage_prediction", return_value=b"FAKE"):
            resp = client.post("/predict", json=valid_payload)

        tower_id = resp.json()["tower_id"]

        with db_connection() as conn:
            row = conn.execute(
                "SELECT id FROM simulations WHERE tower_id = ? AND status = 'pending' LIMIT 1",
                (tower_id,),
            ).fetchone()

        if row is not None:
            resp = client.get(f"/simulations/{row['id']}/result")
            assert resp.status_code == 200
            assert resp.json()["status"] == "pending"


class TestSimulationCascadeDelete:
    """Simulation rows are cascade-deleted when tower is deleted."""

    def test_cascade_deletes_simulations(self, client, valid_payload):
        with patch("app.main.splat_service.coverage_prediction", return_value=b"FAKE"):
            resp = client.post("/predict", json=valid_payload)

        tower_id = resp.json()["tower_id"]

        # Confirm simulations exist
        with db_connection() as conn:
            count_before = conn.execute(
                "SELECT COUNT(*) as cnt FROM simulations WHERE tower_id = ?",
                (tower_id,),
            ).fetchone()["cnt"]
        assert count_before > 0

        # Delete the tower
        resp = client.delete(f"/towers/{tower_id}")
        assert resp.status_code == 200

        # Confirm simulations are gone
        with db_connection() as conn:
            count_after = conn.execute(
                "SELECT COUNT(*) as cnt FROM simulations WHERE tower_id = ?",
                (tower_id,),
            ).fetchone()["cnt"]
        assert count_after == 0
