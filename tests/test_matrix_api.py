"""Tests for the matrix config API endpoints in app.main."""

from app.db import db_connection
from app.matrix import DEFAULT_MATRIX_CONFIG, set_matrix_config


class TestGetMatrixConfig:
    def test_returns_default_config(self, client):
        resp = client.get("/matrix/config")
        assert resp.status_code == 200
        assert resp.json() == DEFAULT_MATRIX_CONFIG

    def test_returns_updated_config_after_put(self, client):
        custom = {
            "hardware": ["v3"],
            "antennas": ["bingfu_whip"],
            "terrain": ["bare_earth"],
        }
        with db_connection() as conn:
            set_matrix_config(conn, custom)

        resp = client.get("/matrix/config")
        assert resp.status_code == 200
        assert resp.json() == custom


class TestPutMatrixConfig:
    def test_updates_config_with_valid_data(self, client):
        payload = {
            "hardware": ["v3"],
            "antennas": ["bingfu_whip", "slinkdsco_omni"],
            "terrain": ["bare_earth", "lulc_clutter"],
        }
        resp = client.put("/matrix/config", json=payload)
        assert resp.status_code == 200
        assert resp.json() == payload

        # Verify persistence
        get_resp = client.get("/matrix/config")
        assert get_resp.json() == payload

    def test_requires_admin_auth(self, client_with_auth):
        payload = {
            "hardware": ["v3"],
            "antennas": ["bingfu_whip"],
            "terrain": ["bare_earth"],
        }
        # No auth header
        resp = client_with_auth.put("/matrix/config", json=payload)
        assert resp.status_code == 401

    def test_admin_auth_succeeds_with_token(self, client_with_auth):
        payload = {
            "hardware": ["v3"],
            "antennas": ["bingfu_whip"],
            "terrain": ["bare_earth"],
        }
        resp = client_with_auth.put(
            "/matrix/config",
            json=payload,
            headers={"Authorization": "Bearer s3cret"},
        )
        assert resp.status_code == 200

    def test_rejects_unknown_hardware(self, client):
        payload = {
            "hardware": ["v3", "unknown_board"],
            "antennas": ["bingfu_whip"],
            "terrain": ["bare_earth"],
        }
        resp = client.put("/matrix/config", json=payload)
        assert resp.status_code == 422
        assert "unknown_board" in str(resp.json())

    def test_rejects_unknown_antenna(self, client):
        payload = {
            "hardware": ["v3"],
            "antennas": ["mystery_antenna"],
            "terrain": ["bare_earth"],
        }
        resp = client.put("/matrix/config", json=payload)
        assert resp.status_code == 422
        assert "mystery_antenna" in str(resp.json())

    def test_rejects_unknown_terrain(self, client):
        payload = {
            "hardware": ["v3"],
            "antennas": ["bingfu_whip"],
            "terrain": ["martian_soil"],
        }
        resp = client.put("/matrix/config", json=payload)
        assert resp.status_code == 422
        assert "martian_soil" in str(resp.json())

    def test_rejects_missing_keys(self, client):
        resp = client.put("/matrix/config", json={"hardware": ["v3"]})
        assert resp.status_code == 422
