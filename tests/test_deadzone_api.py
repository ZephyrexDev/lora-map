"""Tests for the GET /deadzones endpoint and deadzone cache."""

import io

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_bounds

from tests.conftest import insert_tower

pytestmark = pytest.mark.slow


def _make_coverage_geotiff(
    lat: float, lon: float, radius_deg: float = 0.5, value: float = -90.0, size: int = 50
) -> bytes:
    """Create a coverage GeoTIFF centred on (lat, lon) with signal in a circular area."""
    data = np.full((size, size), np.nan, dtype=np.float32)
    cy, cx = size // 2, size // 2
    for y in range(size):
        for x in range(size):
            if (y - cy) ** 2 + (x - cx) ** 2 < (size // 3) ** 2:
                data[y, x] = value

    north, south = lat + radius_deg, lat - radius_deg
    east, west = lon + radius_deg, lon - radius_deg
    transform = from_bounds(west, south, east, north, size, size)
    buf = io.BytesIO()
    with rasterio.open(
        buf,
        "w",
        driver="GTiff",
        height=size,
        width=size,
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=transform,
        nodata=float("nan"),
    ) as dst:
        dst.write(data, 1)
    return buf.getvalue()


class TestGetDeadzones:
    def test_returns_400_with_fewer_than_2_towers(self, client):
        insert_tower(geotiff=_make_coverage_geotiff(45.0, -74.0))
        resp = client.get("/deadzones")
        assert resp.status_code == 400

    def test_returns_400_with_zero_towers(self, client):
        resp = client.get("/deadzones")
        assert resp.status_code == 400

    def test_returns_200_with_two_towers(self, client):
        insert_tower(geotiff=_make_coverage_geotiff(45.0, -74.0))
        insert_tower(geotiff=_make_coverage_geotiff(45.5, -74.0))
        resp = client.get("/deadzones")
        assert resp.status_code == 200
        body = resp.json()
        assert "bounds" in body
        assert "total_coverage_km2" in body
        assert "total_deadzone_km2" in body
        assert "coverage_fraction" in body
        assert "regions" in body
        assert "suggestions" in body
        assert "tower_count" in body
        assert body["tower_count"] == 2

    def test_response_bounds_are_geographic(self, client):
        insert_tower(geotiff=_make_coverage_geotiff(45.0, -74.0))
        insert_tower(geotiff=_make_coverage_geotiff(46.0, -73.0))
        body = client.get("/deadzones").json()
        b = body["bounds"]
        assert b["north"] >= b["south"]
        assert b["east"] >= b["west"]

    def test_coverage_fraction_in_range(self, client):
        insert_tower(geotiff=_make_coverage_geotiff(45.0, -74.0))
        insert_tower(geotiff=_make_coverage_geotiff(45.5, -74.0))
        body = client.get("/deadzones").json()
        assert 0.0 <= body["coverage_fraction"] <= 1.0

    def test_regions_have_required_fields(self, client):
        insert_tower(geotiff=_make_coverage_geotiff(45.0, -74.0))
        insert_tower(geotiff=_make_coverage_geotiff(46.0, -73.0))
        body = client.get("/deadzones").json()
        for region in body["regions"]:
            assert "region_id" in region
            assert "center_lat" in region
            assert "center_lon" in region
            assert "area_km2" in region
            assert "priority_score" in region
            assert 0.0 <= region["priority_score"] <= 1.0

    def test_suggestions_have_required_fields(self, client):
        insert_tower(geotiff=_make_coverage_geotiff(45.0, -74.0))
        insert_tower(geotiff=_make_coverage_geotiff(46.0, -73.0))
        body = client.get("/deadzones").json()
        for s in body["suggestions"]:
            assert "lat" in s
            assert "lon" in s
            assert "estimated_coverage_km2" in s
            assert "priority_rank" in s
            assert "reason" in s

    def test_cache_returns_same_result(self, client):
        insert_tower(geotiff=_make_coverage_geotiff(45.0, -74.0))
        insert_tower(geotiff=_make_coverage_geotiff(45.5, -74.0))
        r1 = client.get("/deadzones").json()
        r2 = client.get("/deadzones").json()
        assert r1 == r2

    def test_cache_invalidated_on_tower_delete(self, client):
        _t1 = insert_tower(geotiff=_make_coverage_geotiff(45.0, -74.0))
        _t2 = insert_tower(geotiff=_make_coverage_geotiff(45.5, -74.0))
        t3 = insert_tower(geotiff=_make_coverage_geotiff(46.0, -74.0))
        r1 = client.get("/deadzones").json()
        assert r1["tower_count"] == 3
        client.delete(f"/towers/{t3}")
        r2 = client.get("/deadzones").json()
        assert r2["tower_count"] == 2
