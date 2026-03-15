"""Tests for GET /towers/{tower_id}/simulations with enabled_only filter."""

from unittest.mock import patch

import pytest

from app.db import db_connection
from app.matrix import set_matrix_config
from app.models.MatrixConfigRequest import MatrixConfigRequest

pytestmark = pytest.mark.slow


class TestSimulationsEnabledOnlyFilter:
    def test_returns_all_without_filter(self, client, valid_payload):
        with patch("app.main.splat_service.coverage_prediction", return_value=b"FAKE"):
            tower_id = client.post("/predict", json=valid_payload).json()["tower_id"]

        resp = client.get(f"/towers/{tower_id}/simulations")
        assert resp.status_code == 200
        all_sims = resp.json()["simulations"]
        assert len(all_sims) > 0

    def test_filters_by_enabled_config(self, client, valid_payload):
        with patch("app.main.splat_service.coverage_prediction", return_value=b"FAKE"):
            tower_id = client.post("/predict", json=valid_payload).json()["tower_id"]

        # Narrow the matrix config to just one hardware + one antenna
        narrow = MatrixConfigRequest(hardware=["v3"], antennas=["bingfu_whip"], terrain=["bare_earth"])
        with db_connection() as conn:
            set_matrix_config(conn, narrow)

        resp = client.get(f"/towers/{tower_id}/simulations", params={"enabled_only": "true"})
        assert resp.status_code == 200
        filtered = resp.json()["simulations"]
        for sim in filtered:
            assert sim["client_hardware"] == "v3"
            assert sim["client_antenna"] == "bingfu_whip"
            assert sim["terrain_model"] == "bare_earth"

    def test_enabled_only_returns_subset(self, client, valid_payload):
        with patch("app.main.splat_service.coverage_prediction", return_value=b"FAKE"):
            tower_id = client.post("/predict", json=valid_payload).json()["tower_id"]

        all_sims = client.get(f"/towers/{tower_id}/simulations").json()["simulations"]

        narrow = MatrixConfigRequest(hardware=["v3"], antennas=["bingfu_whip"], terrain=["bare_earth"])
        with db_connection() as conn:
            set_matrix_config(conn, narrow)

        filtered = client.get(f"/towers/{tower_id}/simulations", params={"enabled_only": "true"}).json()["simulations"]
        assert len(filtered) < len(all_sims)

    def test_enabled_only_false_returns_all(self, client, valid_payload):
        with patch("app.main.splat_service.coverage_prediction", return_value=b"FAKE"):
            tower_id = client.post("/predict", json=valid_payload).json()["tower_id"]

        all_sims = client.get(f"/towers/{tower_id}/simulations").json()["simulations"]
        explicit_false = client.get(f"/towers/{tower_id}/simulations", params={"enabled_only": "false"}).json()[
            "simulations"
        ]
        assert len(explicit_false) == len(all_sims)
