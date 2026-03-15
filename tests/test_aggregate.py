"""Tests for app.services.aggregate — weighted terrain blending."""

import io

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_bounds


def _make_geotiff(value: float, width: int = 10, height: int = 10, nodata_mask: np.ndarray | None = None) -> bytes:
    """Create a minimal single-band float32 GeoTIFF with uniform value."""
    data = np.full((height, width), value, dtype=np.float32)
    if nodata_mask is not None:
        data[nodata_mask] = np.nan
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


class TestComputeWeightedAggregate:
    def test_uniform_inputs_return_same_value(self):
        from app.services.aggregate import compute_weighted_aggregate

        tiff = _make_geotiff(-100.0)
        result = compute_weighted_aggregate(tiff, tiff, tiff)
        with rasterio.open(io.BytesIO(result)) as src:
            arr = src.read(1)
        assert np.allclose(arr, -100.0)

    def test_weighted_average_is_correct(self):
        from app.services.aggregate import compute_weighted_aggregate

        bare = _make_geotiff(-80.0)
        dsm = _make_geotiff(-100.0)
        lulc = _make_geotiff(-120.0)
        # 0.20 * -80 + 0.40 * -100 + 0.40 * -120 = -16 + -40 + -48 = -104
        result = compute_weighted_aggregate(bare, dsm, lulc)
        with rasterio.open(io.BytesIO(result)) as src:
            arr = src.read(1)
        assert np.allclose(arr, -104.0)

    def test_nan_propagates(self):
        from app.services.aggregate import compute_weighted_aggregate

        mask = np.zeros((10, 10), dtype=bool)
        mask[0, 0] = True
        bare = _make_geotiff(-80.0, nodata_mask=mask)
        dsm = _make_geotiff(-100.0)
        lulc = _make_geotiff(-120.0)
        result = compute_weighted_aggregate(bare, dsm, lulc)
        with rasterio.open(io.BytesIO(result)) as src:
            arr = src.read(1)
        assert np.isnan(arr[0, 0])
        assert not np.isnan(arr[1, 1])

    def test_dimension_mismatch_raises(self):
        from app.services.aggregate import compute_weighted_aggregate

        small = _make_geotiff(-80.0, width=5, height=5)
        big = _make_geotiff(-80.0, width=10, height=10)
        with pytest.raises(ValueError, match="mismatch"):
            compute_weighted_aggregate(small, big, big)

    def test_custom_weights(self):
        from app.services.aggregate import compute_weighted_aggregate

        bare = _make_geotiff(-100.0)
        dsm = _make_geotiff(0.0)
        lulc = _make_geotiff(0.0)
        result = compute_weighted_aggregate(bare, dsm, lulc, weights=(1.0, 0.0, 0.0))
        with rasterio.open(io.BytesIO(result)) as src:
            arr = src.read(1)
        assert np.allclose(arr, -100.0)

    def test_output_is_valid_geotiff(self):
        from app.services.aggregate import compute_weighted_aggregate

        tiff = _make_geotiff(-90.0)
        result = compute_weighted_aggregate(tiff, tiff, tiff)
        with rasterio.open(io.BytesIO(result)) as src:
            assert src.count == 1
            assert src.dtypes[0] == "float32"
            assert src.crs.to_epsg() == 4326
