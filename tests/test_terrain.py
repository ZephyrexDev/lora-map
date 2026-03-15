"""Tests for app.services.terrain — terrain provider classes."""

import gzip
import io

import numpy as np
import pytest
from pydantic import ValidationError

from app.models.CoveragePredictionRequest import CoveragePredictionRequest
from app.services.terrain import (
    LULC_CLUTTER_HEIGHTS,
    DsmProvider,
    LulcClutterProvider,
    SrtmProvider,
    TerrainProvider,
)

pytestmark = pytest.mark.slow


class TestTerrainProviderParseTileName:
    """Test the shared _parse_tile_name static method."""

    def test_north_west(self):
        assert TerrainProvider._parse_tile_name("N45W074.hgt.gz") == (45, -74)

    def test_south_east(self):
        assert TerrainProvider._parse_tile_name("S12E034.hgt.gz") == (-12, 34)

    def test_equator_prime_meridian(self):
        assert TerrainProvider._parse_tile_name("N00E000.hgt.gz") == (0, 0)

    def test_south_west(self):
        assert TerrainProvider._parse_tile_name("S45W120.hgt.gz") == (-45, -120)


class TestSrtmProviderS3Keys:
    """Test SrtmProvider S3 key construction."""

    def test_tile_dir_prefix_extracted(self):
        """The tile directory prefix should be the first 3 characters of the tile name."""
        tile_name = "N45W074.hgt.gz"
        expected_prefix = "N45"
        assert tile_name[:3] == expected_prefix

    def test_v3_s3_key_format(self):
        """V3 S3 key follows the v2/skadi/{dir}/{tile} pattern."""
        tile_name = "N45W074.hgt.gz"
        expected = f"v2/skadi/N45/{tile_name}"
        assert f"{SrtmProvider.PREFIX}/{tile_name[:3]}/{tile_name}" == expected


class TestDsmProviderCopernicusKey:
    """Test DsmProvider S3 key construction."""

    def test_north_west_key(self):
        key = DsmProvider._build_copernicus_key(45, -74)
        expected = "Copernicus_DSM_COG_10_N45_00_W074_00_DEM/" "Copernicus_DSM_COG_10_N45_00_W074_00_DEM.tif"
        assert key == expected

    def test_south_east_key(self):
        key = DsmProvider._build_copernicus_key(-12, 34)
        expected = "Copernicus_DSM_COG_10_S12_00_E034_00_DEM/" "Copernicus_DSM_COG_10_S12_00_E034_00_DEM.tif"
        assert key == expected

    def test_zero_zero_key(self):
        key = DsmProvider._build_copernicus_key(0, 0)
        expected = "Copernicus_DSM_COG_10_N00_00_E000_00_DEM/" "Copernicus_DSM_COG_10_N00_00_E000_00_DEM.tif"
        assert key == expected


class TestDsmProviderCogConversion:
    """Test DsmProvider COG-to-HGT conversion logic."""

    def test_cog_to_hgt_gz_produces_valid_hgt(self):
        """Conversion should produce gzipped int16 big-endian data of the right size."""
        # Create a minimal in-memory GeoTIFF using rasterio
        import rasterio
        from rasterio.transform import from_bounds

        side = 100
        data = np.full((side, side), 500, dtype=np.int16)
        transform = from_bounds(-74, 45, -73, 46, side, side)

        buf = io.BytesIO()
        with rasterio.open(
            buf,
            "w",
            driver="GTiff",
            height=side,
            width=side,
            count=1,
            dtype="int16",
            crs="EPSG:4326",
            transform=transform,
        ) as dst:
            dst.write(data, 1)

        cog_bytes = buf.getvalue()
        hgt_gz = DsmProvider._cog_to_hgt_gz(cog_bytes, 45, -74)

        # Decompress and verify
        with gzip.GzipFile(fileobj=io.BytesIO(hgt_gz)) as gz:
            raw = gz.read()

        expected_bytes = 3601 * 3601 * 2  # int16 = 2 bytes
        assert len(raw) == expected_bytes

        # Verify big-endian int16 values
        arr = np.frombuffer(raw, dtype=">i2").reshape(3601, 3601)
        assert arr.dtype == np.dtype(">i2")
        # All values should be close to 500 (resampled from uniform 500)
        assert np.all(arr == 500)


class TestLulcClutterHeights:
    """Test the LULC clutter height lookup table."""

    def test_tree_cover_height(self):
        assert LULC_CLUTTER_HEIGHTS[10] == 12.0

    def test_shrubland_height(self):
        assert LULC_CLUTTER_HEIGHTS[20] == 3.0

    def test_built_up_height(self):
        assert LULC_CLUTTER_HEIGHTS[50] == 20.0

    def test_mangroves_height(self):
        assert LULC_CLUTTER_HEIGHTS[95] == 8.0

    def test_grassland_zero(self):
        assert LULC_CLUTTER_HEIGHTS[30] == 0.0

    def test_water_zero(self):
        assert LULC_CLUTTER_HEIGHTS[80] == 0.0

    def test_all_classes_present(self):
        """All 11 ESA WorldCover classes should have entries."""
        expected_classes = {10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 100}
        assert set(LULC_CLUTTER_HEIGHTS.keys()) == expected_classes

    def test_non_zero_classes(self):
        """Only tree cover, shrubland, built-up, and mangroves should have non-zero clutter."""
        non_zero = {k for k, v in LULC_CLUTTER_HEIGHTS.items() if v > 0}
        assert non_zero == {10, 20, 50, 95}


class TestLulcWorldcoverKey:
    """Test LulcClutterProvider WorldCover key construction."""

    def test_north_west_key(self):
        key = LulcClutterProvider._build_worldcover_key(45, -75)
        assert key == "v200/2021/map/ESA_WorldCover_10m_2021_v200_N45W075_Map.tif"

    def test_south_east_key(self):
        key = LulcClutterProvider._build_worldcover_key(-12, 34)
        assert key == "v200/2021/map/ESA_WorldCover_10m_2021_v200_S12E034_Map.tif"


class TestCoveragePredictionRequestTerrainModel:
    """Test that the CoveragePredictionRequest accepts terrain_model values."""

    def test_default_terrain_model(self):
        model = CoveragePredictionRequest(lat=40.0, lon=-74.0, tx_power=20.0)
        assert model.terrain_model == "bare_earth"

    def test_bare_earth_accepted(self):
        model = CoveragePredictionRequest(lat=40.0, lon=-74.0, tx_power=20.0, terrain_model="bare_earth")
        assert model.terrain_model == "bare_earth"

    def test_dsm_accepted(self):
        model = CoveragePredictionRequest(lat=40.0, lon=-74.0, tx_power=20.0, terrain_model="dsm")
        assert model.terrain_model == "dsm"

    def test_lulc_clutter_accepted(self):
        model = CoveragePredictionRequest(lat=40.0, lon=-74.0, tx_power=20.0, terrain_model="lulc_clutter")
        assert model.terrain_model == "lulc_clutter"

    def test_invalid_terrain_model_rejected(self):
        with pytest.raises(ValidationError):
            CoveragePredictionRequest(lat=40.0, lon=-74.0, tx_power=20.0, terrain_model="invalid")

    def test_empty_string_terrain_model_rejected(self):
        with pytest.raises(ValidationError):
            CoveragePredictionRequest(lat=40.0, lon=-74.0, tx_power=20.0, terrain_model="")
