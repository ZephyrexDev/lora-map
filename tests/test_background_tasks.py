"""Tests for background task functions (run_splat, run_matrix_simulations)."""

from unittest.mock import patch
from uuid import uuid4

import pytest

from app.db import db_connection
from app.main import run_matrix_simulations, run_splat
from app.models.CoveragePredictionRequest import CoveragePredictionRequest
from tests.conftest import insert_task, insert_tower

pytestmark = pytest.mark.slow


def _make_request() -> CoveragePredictionRequest:
    return CoveragePredictionRequest(lat=45.0, lon=-74.0, tx_power=20.0)


class TestRunSplat:
    def test_success_updates_tower_and_task(self):
        tid = insert_tower()
        kid = insert_task(tower_id=tid)

        with patch("app.main.splat_service.coverage_prediction", return_value=b"GEOTIFF_DATA"):
            run_splat(kid, tid, _make_request())

        with db_connection() as conn:
            task = conn.execute("SELECT status FROM tasks WHERE id = ?", (kid,)).fetchone()
            assert task["status"] == "completed"
            tower = conn.execute("SELECT geotiff FROM towers WHERE id = ?", (tid,)).fetchone()
            assert tower["geotiff"] == b"GEOTIFF_DATA"

    def test_failure_marks_task_failed(self):
        tid = insert_tower()
        kid = insert_task(tower_id=tid)

        with patch("app.main.splat_service.coverage_prediction", side_effect=RuntimeError("SPLAT! crashed")):
            run_splat(kid, tid, _make_request())

        with db_connection() as conn:
            task = conn.execute("SELECT status, error FROM tasks WHERE id = ?", (kid,)).fetchone()
            assert task["status"] == "failed"
            assert "SPLAT! crashed" in task["error"]


class TestRunMatrixSimulations:
    def test_success_updates_simulation_rows(self):
        tid = insert_tower()
        sim_id = str(uuid4())
        with db_connection() as conn:
            conn.execute(
                "INSERT INTO simulations (id, tower_id, client_hardware, client_antenna, terrain_model, status) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (sim_id, tid, "v3", "bingfu_whip", "bare_earth", "pending"),
            )
            conn.commit()

        with patch("app.main.splat_service.coverage_prediction", return_value=b"SIM_TIFF"):
            run_matrix_simulations(tid, _make_request())

        with db_connection() as conn:
            row = conn.execute("SELECT status, geotiff FROM simulations WHERE id = ?", (sim_id,)).fetchone()
            assert row["status"] == "completed"
            assert row["geotiff"] == b"SIM_TIFF"

    def test_failure_marks_individual_simulation_failed(self):
        tid = insert_tower()
        sim_id = str(uuid4())
        with db_connection() as conn:
            conn.execute(
                "INSERT INTO simulations (id, tower_id, client_hardware, client_antenna, terrain_model, status) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (sim_id, tid, "v3", "bingfu_whip", "bare_earth", "pending"),
            )
            conn.commit()

        with patch("app.main.splat_service.coverage_prediction", side_effect=RuntimeError("boom")):
            run_matrix_simulations(tid, _make_request())

        with db_connection() as conn:
            row = conn.execute("SELECT status, error FROM simulations WHERE id = ?", (sim_id,)).fetchone()
            assert row["status"] == "failed"
            assert "boom" in row["error"]

    def test_one_failure_does_not_block_others(self):
        tid = insert_tower()
        sim1 = str(uuid4())
        sim2 = str(uuid4())
        with db_connection() as conn:
            conn.execute(
                "INSERT INTO simulations (id, tower_id, client_hardware, client_antenna, terrain_model, status) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (sim1, tid, "v3", "bingfu_whip", "bare_earth", "pending"),
            )
            conn.execute(
                "INSERT INTO simulations (id, tower_id, client_hardware, client_antenna, terrain_model, status) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (sim2, tid, "v4", "bingfu_whip", "bare_earth", "pending"),
            )
            conn.commit()

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("first fails")
            return b"SECOND_OK"

        with patch("app.main.splat_service.coverage_prediction", side_effect=side_effect):
            run_matrix_simulations(tid, _make_request())

        with db_connection() as conn:
            r1 = conn.execute("SELECT status FROM simulations WHERE id = ?", (sim1,)).fetchone()
            r2 = conn.execute("SELECT status FROM simulations WHERE id = ?", (sim2,)).fetchone()
            assert r1["status"] == "failed"
            assert r2["status"] == "completed"

    def test_skips_non_pending_simulations(self):
        tid = insert_tower()
        sim_id = str(uuid4())
        with db_connection() as conn:
            conn.execute(
                "INSERT INTO simulations (id, tower_id, client_hardware, client_antenna, terrain_model, status) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (sim_id, tid, "v3", "bingfu_whip", "bare_earth", "completed"),
            )
            conn.commit()

        with patch("app.main.splat_service.coverage_prediction") as mock:
            run_matrix_simulations(tid, _make_request())
            mock.assert_not_called()
