"""Tests for the GET /towers/{tower_id}/aggregate endpoint."""

import io
from uuid import uuid4

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_bounds

from app.db import db_connection
from tests.conftest import insert_tower

pytestmark = pytest.mark.slow


def _make_geotiff(value: float, width: int = 10, height: int = 10) -> bytes:
    data = np.full((height, width), value, dtype=np.float32)
    transform = from_bounds(-74, 45, -73, 46, width, height)
    buf = io.BytesIO()
    with rasterio.open(
        buf,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=transform,
        nodata=float("nan"),
    ) as dst:
        dst.write(data, 1)
    return buf.getvalue()


def _insert_simulation(
    tower_id: str, hw: str, ant: str, terrain: str, geotiff: bytes | None, status: str = "completed"
):
    sim_id = str(uuid4())
    with db_connection() as conn:
        conn.execute(
            "INSERT INTO simulations (id, tower_id, client_hardware, client_antenna, terrain_model, status, geotiff) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (sim_id, tower_id, hw, ant, terrain, status, geotiff),
        )
        conn.commit()
    return sim_id


class TestGetAggregateSimulation:
    def test_returns_404_when_no_simulations_exist(self, client):
        tid = insert_tower()
        resp = client.get(f"/towers/{tid}/aggregate", params={"client_hardware": "v3", "client_antenna": "bingfu_whip"})
        assert resp.status_code == 404

    def test_returns_404_when_only_some_terrain_models_complete(self, client):
        tid = insert_tower()
        tiff = _make_geotiff(-90.0)
        _insert_simulation(tid, "v3", "bingfu_whip", "bare_earth", tiff)
        _insert_simulation(tid, "v3", "bingfu_whip", "dsm", tiff)
        # lulc_clutter missing
        resp = client.get(f"/towers/{tid}/aggregate", params={"client_hardware": "v3", "client_antenna": "bingfu_whip"})
        assert resp.status_code == 404
        assert "lulc_clutter" in resp.json()["detail"]

    def test_returns_404_when_simulation_not_completed(self, client):
        tid = insert_tower()
        tiff = _make_geotiff(-90.0)
        _insert_simulation(tid, "v3", "bingfu_whip", "bare_earth", tiff)
        _insert_simulation(tid, "v3", "bingfu_whip", "dsm", tiff)
        _insert_simulation(tid, "v3", "bingfu_whip", "lulc_clutter", None, status="pending")
        resp = client.get(f"/towers/{tid}/aggregate", params={"client_hardware": "v3", "client_antenna": "bingfu_whip"})
        assert resp.status_code == 404

    def test_returns_geotiff_when_all_three_complete(self, client):
        tid = insert_tower()
        tiff = _make_geotiff(-90.0)
        _insert_simulation(tid, "v3", "bingfu_whip", "bare_earth", tiff)
        _insert_simulation(tid, "v3", "bingfu_whip", "dsm", tiff)
        _insert_simulation(tid, "v3", "bingfu_whip", "lulc_clutter", tiff)
        resp = client.get(f"/towers/{tid}/aggregate", params={"client_hardware": "v3", "client_antenna": "bingfu_whip"})
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/tiff"

    def test_requires_client_hardware_param(self, client):
        tid = insert_tower()
        resp = client.get(f"/towers/{tid}/aggregate", params={"client_antenna": "bingfu_whip"})
        assert resp.status_code == 422

    def test_requires_client_antenna_param(self, client):
        tid = insert_tower()
        resp = client.get(f"/towers/{tid}/aggregate", params={"client_hardware": "v3"})
        assert resp.status_code == 422
