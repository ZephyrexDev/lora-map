"""Tests for background task functions (run_splat, run_matrix_simulations)."""

from unittest.mock import patch
from uuid import uuid4

import pytest

from app.db import db_session
from app.db.models import Simulation, Task, Tower
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

        with db_session() as session:
            task = session.get(Task, kid)
            assert task.status == "completed"
            tower = session.get(Tower, tid)
            assert tower.geotiff == b"GEOTIFF_DATA"

    def test_failure_marks_task_failed(self):
        tid = insert_tower()
        kid = insert_task(tower_id=tid)

        with patch("app.main.splat_service.coverage_prediction", side_effect=RuntimeError("SPLAT! crashed")):
            run_splat(kid, tid, _make_request())

        with db_session() as session:
            task = session.get(Task, kid)
            assert task.status == "failed"
            assert "SPLAT! crashed" in task.error


class TestRunMatrixSimulations:
    def test_success_updates_simulation_rows(self):
        tid = insert_tower()
        sim_id = str(uuid4())
        with db_session() as session:
            session.add(
                Simulation(
                    id=sim_id,
                    tower_id=tid,
                    client_hardware="v3",
                    client_antenna="bingfu_whip",
                    terrain_model="bare_earth",
                    status="pending",
                )
            )
            session.commit()

        with patch("app.main.splat_service.coverage_prediction", return_value=b"SIM_TIFF"):
            run_matrix_simulations(tid, _make_request())

        with db_session() as session:
            sim = session.get(Simulation, sim_id)
            assert sim.status == "completed"
            assert sim.geotiff == b"SIM_TIFF"

    def test_failure_marks_individual_simulation_failed(self):
        tid = insert_tower()
        sim_id = str(uuid4())
        with db_session() as session:
            session.add(
                Simulation(
                    id=sim_id,
                    tower_id=tid,
                    client_hardware="v3",
                    client_antenna="bingfu_whip",
                    terrain_model="bare_earth",
                    status="pending",
                )
            )
            session.commit()

        with (
            patch("app.main.splat_service.coverage_prediction", side_effect=RuntimeError("boom")),
            patch("app.main._SIMULATION_RETRY_DELAY_SECONDS", 0),
        ):
            run_matrix_simulations(tid, _make_request())

        with db_session() as session:
            sim = session.get(Simulation, sim_id)
            assert sim.status == "failed"
            assert "boom" in sim.error

    def test_one_failure_does_not_block_others(self):
        tid = insert_tower()
        sim1 = str(uuid4())
        sim2 = str(uuid4())
        with db_session() as session:
            session.add(
                Simulation(
                    id=sim1,
                    tower_id=tid,
                    client_hardware="v3",
                    client_antenna="bingfu_whip",
                    terrain_model="bare_earth",
                    status="pending",
                )
            )
            session.add(
                Simulation(
                    id=sim2,
                    tower_id=tid,
                    client_hardware="v4",
                    client_antenna="bingfu_whip",
                    terrain_model="bare_earth",
                    status="pending",
                )
            )
            session.commit()

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            # Fail on calls 1 and 2 (both retry attempts for sim1), succeed after
            if call_count <= 2:
                raise RuntimeError("first fails")
            return b"SECOND_OK"

        with (
            patch("app.main.splat_service.coverage_prediction", side_effect=side_effect),
            patch("app.main._SIMULATION_RETRY_DELAY_SECONDS", 0),
        ):
            run_matrix_simulations(tid, _make_request())

        with db_session() as session:
            r1 = session.get(Simulation, sim1)
            r2 = session.get(Simulation, sim2)
            assert r1.status == "failed"
            assert r2.status == "completed"

    def test_skips_non_pending_simulations(self):
        tid = insert_tower()
        sim_id = str(uuid4())
        with db_session() as session:
            session.add(
                Simulation(
                    id=sim_id,
                    tower_id=tid,
                    client_hardware="v3",
                    client_antenna="bingfu_whip",
                    terrain_model="bare_earth",
                    status="completed",
                )
            )
            session.commit()

        with patch("app.main.splat_service.coverage_prediction") as mock:
            run_matrix_simulations(tid, _make_request())
            mock.assert_not_called()
