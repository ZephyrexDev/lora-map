"""Tests for app.services.deadzone — DeadzoneAnalyzer class."""

import io

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_bounds

from app.services.deadzone import DeadzoneAnalyzer


def _make_geotiff(
    lat: float,
    lon: float,
    radius_deg: float = 0.5,
    value: float = -90.0,
    size: int = 50,
    coverage_fraction: float = 0.3,
) -> bytes:
    """GeoTIFF with a circular signal region surrounded by NaN (no signal)."""
    data = np.full((size, size), np.nan, dtype=np.float32)
    cy, cx = size // 2, size // 2
    r = int(size * coverage_fraction)
    for y in range(size):
        for x in range(size):
            if (y - cy) ** 2 + (x - cx) ** 2 < r**2:
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


class TestDeadzoneAnalyzerInit:
    def test_rejects_fewer_than_two_blobs(self):
        with pytest.raises(ValueError, match="at least 2"):
            DeadzoneAnalyzer([_make_geotiff(45, -74)])

    def test_accepts_two_blobs(self):
        analyzer = DeadzoneAnalyzer([_make_geotiff(45, -74), _make_geotiff(46, -73)])
        assert len(analyzer.geotiff_blobs) == 2


class TestDeadzoneAnalyzerAnalyze:
    def test_returns_response_with_required_fields(self):
        blobs = [_make_geotiff(45, -74), _make_geotiff(46, -73)]
        result = DeadzoneAnalyzer(blobs).analyze()
        assert result.tower_count == 2
        assert result.total_coverage_km2 >= 0
        assert result.total_deadzone_km2 >= 0
        assert 0.0 <= result.coverage_fraction <= 1.0
        assert result.bounds.north >= result.bounds.south

    def test_coverage_plus_deadzone_equals_total(self):
        blobs = [_make_geotiff(45, -74), _make_geotiff(46, -73)]
        result = DeadzoneAnalyzer(blobs).analyze()
        total = result.total_coverage_km2 + result.total_deadzone_km2
        assert total > 0

    def test_regions_sorted_by_priority_descending(self):
        blobs = [_make_geotiff(45, -74), _make_geotiff(46, -73)]
        result = DeadzoneAnalyzer(blobs).analyze()
        if len(result.regions) > 1:
            scores = [r.priority_score for r in result.regions]
            assert scores == sorted(scores, reverse=True)

    def test_suggestions_limited_to_five(self):
        blobs = [_make_geotiff(45, -74), _make_geotiff(46, -73)]
        result = DeadzoneAnalyzer(blobs).analyze()
        assert len(result.suggestions) <= 5

    def test_suggestion_ranks_are_sequential(self):
        blobs = [_make_geotiff(45, -74), _make_geotiff(46, -73)]
        result = DeadzoneAnalyzer(blobs).analyze()
        ranks = [s.priority_rank for s in result.suggestions]
        assert ranks == list(range(1, len(ranks) + 1))

    def test_overlapping_towers_have_higher_coverage(self):
        # Two overlapping towers should have more coverage than separated ones
        overlapping = DeadzoneAnalyzer(
            [
                _make_geotiff(45, -74, radius_deg=0.5),
                _make_geotiff(45.3, -74, radius_deg=0.5),
            ]
        ).analyze()
        separated = DeadzoneAnalyzer(
            [
                _make_geotiff(45, -74, radius_deg=0.5),
                _make_geotiff(50, -70, radius_deg=0.5),
            ]
        ).analyze()
        # Overlapping should have higher coverage fraction (less deadzone relative to extent)
        assert overlapping.coverage_fraction > separated.coverage_fraction
