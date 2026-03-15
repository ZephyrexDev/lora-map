"""Tests for the matrix configuration module (app.matrix)."""

from app.db import db_connection
from app.matrix import (
    DEFAULT_MATRIX_CONFIG,
    get_matrix_combinations,
    get_matrix_config,
    set_matrix_config,
)
from app.models.MatrixConfigRequest import MatrixConfigRequest


class TestDefaultMatrixConfig:
    def test_has_expected_fields(self):
        assert DEFAULT_MATRIX_CONFIG.hardware == ["v3", "v4"]
        assert DEFAULT_MATRIX_CONFIG.antennas == [
            "ribbed_spring_helical",
            "duck_stubby",
            "bingfu_whip",
            "slinkdsco_omni",
        ]
        assert DEFAULT_MATRIX_CONFIG.terrain == ["bare_earth"]


class TestGetMatrixConfig:
    def test_returns_default_when_no_row_exists(self):
        with db_connection() as conn:
            config = get_matrix_config(conn)
        assert config == DEFAULT_MATRIX_CONFIG

    def test_returns_persisted_config_after_set(self):
        custom = MatrixConfigRequest(
            hardware=["v3"],
            antennas=["bingfu_whip"],
            terrain=["bare_earth", "lulc_clutter"],
        )
        with db_connection() as conn:
            set_matrix_config(conn, custom)
            result = get_matrix_config(conn)
        assert result == custom


class TestSetMatrixConfig:
    def test_persists_and_reads_back(self):
        custom = MatrixConfigRequest(
            hardware=["v4"],
            antennas=["duck_stubby", "slinkdsco_omni"],
            terrain=["bare_earth"],
        )
        with db_connection() as conn:
            set_matrix_config(conn, custom)
            result = get_matrix_config(conn)
        assert result == custom

    def test_upsert_overwrites_previous_value(self):
        first = MatrixConfigRequest(
            hardware=["v3"],
            antennas=["duck_stubby"],
            terrain=["bare_earth"],
        )
        second = MatrixConfigRequest(
            hardware=["v4"],
            antennas=["bingfu_whip"],
            terrain=["lulc_clutter"],
        )
        with db_connection() as conn:
            set_matrix_config(conn, first)
            set_matrix_config(conn, second)
            result = get_matrix_config(conn)
        assert result == second


class TestGetMatrixCombinations:
    def test_correct_cartesian_product(self):
        config = MatrixConfigRequest(
            hardware=["v3", "v4"],
            antennas=["bingfu_whip", "slinkdsco_omni"],
            terrain=["bare_earth"],
        )
        combos = get_matrix_combinations(config)
        assert len(combos) == 4  # 2 x 2 x 1
        assert {
            "hardware": "v3",
            "antenna": "bingfu_whip",
            "terrain": "bare_earth",
        } in combos
        assert {
            "hardware": "v4",
            "antenna": "slinkdsco_omni",
            "terrain": "bare_earth",
        } in combos

    def test_empty_hardware_returns_empty(self):
        config = MatrixConfigRequest(hardware=[], antennas=["duck_stubby"], terrain=["bare_earth"])
        assert get_matrix_combinations(config) == []

    def test_empty_antennas_returns_empty(self):
        config = MatrixConfigRequest(hardware=["v3"], antennas=[], terrain=["bare_earth"])
        assert get_matrix_combinations(config) == []

    def test_empty_terrain_returns_empty(self):
        config = MatrixConfigRequest(hardware=["v3"], antennas=["duck_stubby"], terrain=[])
        assert get_matrix_combinations(config) == []

    def test_weighted_aggregate_excluded(self):
        config = MatrixConfigRequest(
            hardware=["v3"],
            antennas=["duck_stubby"],
            terrain=["bare_earth", "weighted_aggregate"],
        )
        combos = get_matrix_combinations(config)
        assert len(combos) == 1
        assert combos[0]["terrain"] == "bare_earth"
