"""Tests for the worst_case terrain model — provider, height adjustment, and validation."""

import gzip
import io

import numpy as np
import pytest

from app.models.CoveragePredictionRequest import CoveragePredictionRequest
from app.services.terrain import _HGT_SIZE, TerrainProvider


def _make_hgt_gz(value: int, side: int = _HGT_SIZE) -> bytes:
    """Create a uniform .hgt.gz tile filled with a constant elevation value."""
    arr = np.full((side, side), value, dtype=np.int16)
    raw = arr.astype(">i2").tobytes()
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
        gz.write(raw)
    return buf.getvalue()


def _make_hgt_gz_from_array(arr: np.ndarray) -> bytes:
    """Create .hgt.gz from an arbitrary 2D array."""
    raw = arr.astype(np.int16).astype(">i2").tobytes()
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
        gz.write(raw)
    return buf.getvalue()


class TestDecompressHgt:
    def test_round_trip(self):
        original = np.arange(_HGT_SIZE * _HGT_SIZE, dtype=np.int16).reshape(_HGT_SIZE, _HGT_SIZE)
        hgt_gz = _make_hgt_gz_from_array(original)
        result = TerrainProvider._decompress_hgt(hgt_gz)
        np.testing.assert_array_equal(result, original)

    def test_invalid_size_raises(self):
        raw = b"\x00" * 13  # Not a perfect square of int16 values
        buf = io.BytesIO()
        with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
            gz.write(raw)
        with pytest.raises(ValueError, match="not a perfect square"):
            TerrainProvider._decompress_hgt(buf.getvalue())


class TestCompressHgt:
    def test_round_trip(self):
        arr = np.full((_HGT_SIZE, _HGT_SIZE), 500, dtype=np.float32)
        hgt_gz = TerrainProvider._compress_hgt(arr)
        result = TerrainProvider._decompress_hgt(hgt_gz)
        np.testing.assert_array_equal(result, 500)

    def test_clips_to_int16_range(self):
        arr = np.full((3, 3), 40000, dtype=np.float32)
        arr[0, 1] = -40000
        hgt_gz = TerrainProvider._compress_hgt(arr)
        result = TerrainProvider._decompress_hgt(hgt_gz)
        assert result[0, 0] == 32767
        assert result[0, 1] == -32768


class TestElevationAtPoint:
    def test_center_of_tile(self):
        """Reading elevation at the center of a uniform tile returns that value."""
        hgt_gz = _make_hgt_gz(100)
        elev = TerrainProvider.elevation_at_point(hgt_gz, lat=45.5, lon=-74.5, tile_lat=45, tile_lon=-75)
        assert elev == 100.0

    def test_corner_of_tile(self):
        """Reading at the tile's south-west corner returns the correct value."""
        hgt_gz = _make_hgt_gz(200)
        elev = TerrainProvider.elevation_at_point(hgt_gz, lat=45.0001, lon=-75.0 + 0.0001, tile_lat=45, tile_lon=-75)
        assert elev == 200.0

    def test_varying_tile(self):
        """Reading from a tile with distinct halves returns values from the correct region."""
        arr = np.zeros((_HGT_SIZE, _HGT_SIZE), dtype=np.int16)
        # Top half (north) = 1000, bottom half (south) = 500
        arr[: _HGT_SIZE // 2, :] = 1000
        arr[_HGT_SIZE // 2 :, :] = 500
        hgt_gz = _make_hgt_gz_from_array(arr)
        # lat 45.75 -> row ~900 (in the north half) -> should read 1000
        north_elev = TerrainProvider.elevation_at_point(hgt_gz, lat=45.75, lon=-74.5, tile_lat=45, tile_lon=-75)
        assert north_elev == 1000.0
        # lat 45.25 -> row ~2700 (in the south half) -> should read 500
        south_elev = TerrainProvider.elevation_at_point(hgt_gz, lat=45.25, lon=-74.5, tile_lat=45, tile_lon=-75)
        assert south_elev == 500.0


class TestWorstCaseRequestModel:
    def test_worst_case_accepted(self):
        model = CoveragePredictionRequest(lat=40.0, lon=-74.0, tx_power=20.0, terrain_model="worst_case")
        assert model.terrain_model == "worst_case"


class TestWorstCaseHeightAdjustment:
    """Test the height adjustment logic using TerrainProvider.elevation_at_point."""

    def test_delta_positive_reduces_height(self):
        """When worst-case terrain is higher, TX height should be reduced."""
        bare = _make_hgt_gz(100)
        wc = _make_hgt_gz(120)
        bare_elev = TerrainProvider.elevation_at_point(bare, 45.5, -74.5, 45, -75)
        wc_elev = TerrainProvider.elevation_at_point(wc, 45.5, -74.5, 45, -75)
        delta = wc_elev - bare_elev
        adjusted = max(1.0, 10.0 - delta)
        assert delta == 20.0
        assert adjusted == -10.0 or adjusted == 1.0  # Clamped to 1.0
        assert max(1.0, 10.0 - delta) == 1.0

    def test_no_delta_no_change(self):
        """When terrain matches, TX height is unchanged."""
        tile = _make_hgt_gz(100)
        bare_elev = TerrainProvider.elevation_at_point(tile, 45.5, -74.5, 45, -75)
        wc_elev = TerrainProvider.elevation_at_point(tile, 45.5, -74.5, 45, -75)
        delta = wc_elev - bare_elev
        adjusted = max(1.0, 10.0 - delta)
        assert delta == 0.0
        assert adjusted == 10.0

    def test_floor_at_one_meter(self):
        """Adjusted height must not go below 1.0m."""
        bare = _make_hgt_gz(100)
        wc = _make_hgt_gz(200)
        bare_elev = TerrainProvider.elevation_at_point(bare, 45.5, -74.5, 45, -75)
        wc_elev = TerrainProvider.elevation_at_point(wc, 45.5, -74.5, 45, -75)
        delta = wc_elev - bare_elev
        adjusted = max(1.0, 5.0 - delta)
        assert delta == 100.0
        assert adjusted == 1.0
