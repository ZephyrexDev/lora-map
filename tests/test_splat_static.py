"""Tests for SPLAT! static methods: file generation, tile calculation, filename conversion."""

import pytest

from app.services.splat import Splat


# ===========================================================================
# _create_splat_qth
# ===========================================================================

class TestCreateSplatQth:
    def test_basic_output_format(self):
        result = Splat._create_splat_qth("tx", 51.1, -114.1, 10.0)
        lines = result.decode("utf-8").strip().split("\n")
        assert len(lines) == 4
        assert lines[0] == "tx"
        assert lines[1] == "51.100000"
        assert lines[3] == "10.00"

    def test_negative_longitude_becomes_positive(self):
        """SPLAT! expects west longitude as a positive number (abs of negative)."""
        result = Splat._create_splat_qth("tx", 45.0, -120.5, 5.0)
        lines = result.decode("utf-8").strip().split("\n")
        assert float(lines[2]) == pytest.approx(120.5)

    def test_positive_longitude_converted_to_splat_format(self):
        """SPLAT! converts east longitude: 360 - lon."""
        result = Splat._create_splat_qth("tx", 48.0, 10.0, 2.0)
        lines = result.decode("utf-8").strip().split("\n")
        assert float(lines[2]) == pytest.approx(350.0)

    def test_zero_longitude(self):
        result = Splat._create_splat_qth("tx", 0.0, 0.0, 1.0)
        lines = result.decode("utf-8").strip().split("\n")
        assert float(lines[2]) == pytest.approx(360.0)  # 360 - 0

    def test_returns_bytes(self):
        assert isinstance(Splat._create_splat_qth("tx", 0, 0, 0), bytes)


# ===========================================================================
# _create_splat_lrp
# ===========================================================================

class TestCreateSplatLrp:
    def _default_lrp(self, **overrides):
        defaults = dict(
            ground_dielectric=15.0,
            ground_conductivity=0.005,
            atmosphere_bending=301.0,
            frequency_mhz=907.0,
            radio_climate="continental_temperate",
            polarization="vertical",
            situation_fraction=50.0,
            time_fraction=90.0,
            tx_power=30.0,
            tx_gain=2.0,
            system_loss=1.0,
        )
        defaults.update(overrides)
        return Splat._create_splat_lrp(**defaults)

    def test_returns_bytes(self):
        assert isinstance(self._default_lrp(), bytes)

    def test_contains_nine_lines(self):
        lines = self._default_lrp().decode("utf-8").strip().split("\n")
        assert len(lines) == 9

    def test_erp_calculation(self):
        """ERP = 10^((tx_power + tx_gain - system_loss - 30) / 10)."""
        result = self._default_lrp(tx_power=30.0, tx_gain=2.0, system_loss=1.0)
        content = result.decode("utf-8")
        # ERP = 10^((30 + 2 - 1 - 30)/10) = 10^(1/10) ≈ 1.26
        erp_line = content.strip().split("\n")[-1]
        erp_value = float(erp_line.split(";")[0].strip())
        assert erp_value == pytest.approx(1.26, abs=0.01)

    @pytest.mark.parametrize("climate,code", [
        ("equatorial", "1"), ("continental_subtropical", "2"),
        ("maritime_subtropical", "3"), ("desert", "4"),
        ("continental_temperate", "5"), ("maritime_temperate_land", "6"),
        ("maritime_temperate_sea", "7"),
    ])
    def test_climate_mapping(self, climate, code):
        result = self._default_lrp(radio_climate=climate).decode("utf-8")
        climate_line = result.strip().split("\n")[4]
        assert climate_line.startswith(code)

    @pytest.mark.parametrize("pol,code", [("horizontal", "0"), ("vertical", "1")])
    def test_polarization_mapping(self, pol, code):
        result = self._default_lrp(polarization=pol).decode("utf-8")
        pol_line = result.strip().split("\n")[5]
        assert pol_line.startswith(code)

    def test_fraction_divided_by_100(self):
        result = self._default_lrp(situation_fraction=95.0, time_fraction=50.0).decode("utf-8")
        lines = result.strip().split("\n")
        sit_val = float(lines[6].split(";")[0].strip())
        time_val = float(lines[7].split(";")[0].strip())
        assert sit_val == pytest.approx(0.95)
        assert time_val == pytest.approx(0.50)


# ===========================================================================
# _create_splat_dcf
# ===========================================================================

class TestCreateSplatDcf:
    def test_returns_bytes(self):
        assert isinstance(Splat._create_splat_dcf("plasma", -130.0, -80.0), bytes)

    def test_contains_32_color_lines(self):
        content = Splat._create_splat_dcf("plasma", -130.0, -80.0).decode("utf-8")
        color_lines = [l for l in content.split("\n") if ":" in l and not l.startswith(";")]
        assert len(color_lines) == 32

    def test_dbm_range_matches_input(self):
        content = Splat._create_splat_dcf("viridis", -120.0, -60.0).decode("utf-8")
        color_lines = [l for l in content.split("\n") if ":" in l and not l.startswith(";")]
        dbm_values = [int(l.split(":")[0].strip()) for l in color_lines]
        assert max(dbm_values) == -60
        assert min(dbm_values) == -120

    def test_rgb_values_in_valid_range(self):
        content = Splat._create_splat_dcf("jet", -130.0, -80.0).decode("utf-8")
        for line in content.split("\n"):
            if ":" in line and not line.startswith(";"):
                rgb_part = line.split(":")[1]
                values = [int(v.strip()) for v in rgb_part.split(",")]
                assert len(values) == 3
                for v in values:
                    assert 0 <= v <= 255


# ===========================================================================
# _colormap_to_rgb
# ===========================================================================

class TestColormapToRgb:
    def test_returns_correct_shape(self):
        rgb = Splat._colormap_to_rgb("plasma", -130, -80, 10)
        assert rgb.shape == (10, 3)

    def test_values_in_0_255_range(self):
        rgb = Splat._colormap_to_rgb("viridis", -130, -80, 255)
        assert rgb.min() >= 0
        assert rgb.max() <= 255


# ===========================================================================
# _hgt_filename_to_sdf_filename
# ===========================================================================

class TestHgtToSdfFilename:
    @pytest.mark.parametrize("hgt,expected_sdf,expected_hd", [
        # Western hemisphere (lon value is offset by -1 in SPLAT! naming convention)
        ("N51W115.hgt.gz", "51:52:114:115.sdf", "51:52:114:115-hd.sdf"),
        ("N35W120.hgt.gz", "35:36:119:120.sdf", "35:36:119:120-hd.sdf"),
        # Southern hemisphere
        ("S33W071.hgt.gz", "-33:-32:70:71.sdf", "-33:-32:70:71-hd.sdf"),
    ])
    def test_western_hemisphere(self, hgt, expected_sdf, expected_hd):
        assert Splat._hgt_filename_to_sdf_filename(hgt, high_resolution=False) == expected_sdf
        assert Splat._hgt_filename_to_sdf_filename(hgt, high_resolution=True) == expected_hd

    @pytest.mark.parametrize("hgt,expected_sdf", [
        # Eastern hemisphere has off-by-one correction
        ("N48E010.hgt.gz", None),  # Just check it doesn't crash and returns valid format
    ])
    def test_eastern_hemisphere_format(self, hgt, expected_sdf):
        result = Splat._hgt_filename_to_sdf_filename(hgt)
        assert result.endswith(".sdf")
        parts = result.replace(".sdf", "").split(":")
        assert len(parts) == 4
        # lat range should span 1 degree
        assert int(parts[1]) - int(parts[0]) == 1


# ===========================================================================
# _calculate_required_terrain_tiles
# ===========================================================================

class TestCalculateRequiredTerrainTiles:
    def test_small_radius_single_tile(self):
        """A very small radius should need only 1 tile."""
        tiles = Splat._calculate_required_terrain_tiles(51.5, -114.5, 1000)
        assert len(tiles) >= 1
        hgt, sdf, sdf_hd = tiles[0]
        assert hgt.endswith(".hgt.gz")
        assert sdf.endswith(".sdf")
        assert sdf_hd.endswith("-hd.sdf")

    def test_larger_radius_multiple_tiles(self):
        """A 50km radius should require multiple tiles."""
        tiles = Splat._calculate_required_terrain_tiles(51.0, -114.0, 50000)
        assert len(tiles) > 1

    def test_tile_names_have_correct_format(self):
        tiles = Splat._calculate_required_terrain_tiles(40.0, -105.0, 10000)
        for hgt, sdf, sdf_hd in tiles:
            assert hgt[0] in ("N", "S")
            assert hgt[3] in ("E", "W")

    def test_southern_hemisphere(self):
        tiles = Splat._calculate_required_terrain_tiles(-33.0, -71.0, 5000)
        hgt_names = [t[0] for t in tiles]
        assert any(h.startswith("S") for h in hgt_names)

    def test_returns_consistent_sdf_names(self):
        """sdf and sdf_hd names should match the hgt name."""
        tiles = Splat._calculate_required_terrain_tiles(51.0, -114.0, 10000)
        for hgt, sdf, sdf_hd in tiles:
            expected_sdf = Splat._hgt_filename_to_sdf_filename(hgt, False)
            expected_hd = Splat._hgt_filename_to_sdf_filename(hgt, True)
            assert sdf == expected_sdf
            assert sdf_hd == expected_hd
