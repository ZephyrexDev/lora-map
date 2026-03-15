"""Tests for the matrix configuration module (app.matrix)."""

from app.db import db_connection
from app.matrix import (
    DEFAULT_MATRIX_CONFIG,
    get_matrix_combinations,
    get_matrix_config,
    set_matrix_config,
)


class TestDefaultMatrixConfig:
    def test_has_expected_keys(self):
        assert set(DEFAULT_MATRIX_CONFIG.keys()) == {"hardware", "antennas", "terrain"}

    def test_hardware_defaults(self):
        assert DEFAULT_MATRIX_CONFIG["hardware"] == ["v3", "v4"]

    def test_antennas_defaults(self):
        assert DEFAULT_MATRIX_CONFIG["antennas"] == [
            "ribbed_spring_helical",
            "duck_stubby",
            "bingfu_whip",
            "slinkdsco_omni",
        ]

    def test_terrain_defaults(self):
        assert DEFAULT_MATRIX_CONFIG["terrain"] == ["bare_earth"]


class TestGetMatrixConfig:
    def test_returns_default_when_no_row_exists(self):
        with db_connection() as conn:
            config = get_matrix_config(conn)
        assert config == DEFAULT_MATRIX_CONFIG

    def test_returns_persisted_config_after_set(self):
        custom = {
            "hardware": ["v3"],
            "antennas": ["bingfu_whip"],
            "terrain": ["bare_earth", "lulc_clutter"],
        }
        with db_connection() as conn:
            set_matrix_config(conn, custom)
            result = get_matrix_config(conn)
        assert result == custom


class TestSetMatrixConfig:
    def test_persists_and_reads_back(self):
        custom = {
            "hardware": ["v4"],
            "antennas": ["duck_stubby", "slinkdsco_omni"],
            "terrain": ["bare_earth"],
        }
        with db_connection() as conn:
            set_matrix_config(conn, custom)
            result = get_matrix_config(conn)
        assert result == custom

    def test_upsert_overwrites_previous_value(self):
        first = {
            "hardware": ["v3"],
            "antennas": ["duck_stubby"],
            "terrain": ["bare_earth"],
        }
        second = {
            "hardware": ["v4"],
            "antennas": ["bingfu_whip"],
            "terrain": ["lulc_clutter"],
        }
        with db_connection() as conn:
            set_matrix_config(conn, first)
            set_matrix_config(conn, second)
            result = get_matrix_config(conn)
        assert result == second


class TestGetMatrixCombinations:
    def test_correct_cartesian_product(self):
        config = {
            "hardware": ["v3", "v4"],
            "antennas": ["bingfu_whip", "slinkdsco_omni"],
            "terrain": ["bare_earth"],
        }
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
        config = {
            "hardware": [],
            "antennas": ["duck_stubby"],
            "terrain": ["bare_earth"],
        }
        assert get_matrix_combinations(config) == []

    def test_empty_antennas_returns_empty(self):
        config = {"hardware": ["v3"], "antennas": [], "terrain": ["bare_earth"]}
        assert get_matrix_combinations(config) == []

    def test_empty_terrain_returns_empty(self):
        config = {"hardware": ["v3"], "antennas": ["duck_stubby"], "terrain": []}
        assert get_matrix_combinations(config) == []

    def test_missing_key_returns_empty(self):
        assert get_matrix_combinations({"hardware": ["v3"], "antennas": ["duck_stubby"]}) == []
