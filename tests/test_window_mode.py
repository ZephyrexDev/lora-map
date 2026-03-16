"""Tests for window mode — directional attenuation through glass/structure."""


import numpy as np
import pytest
from pydantic import ValidationError

from app.models.CoveragePredictionRequest import CoveragePredictionRequest
from app.services.splat import Splat

VALID_BASE = {"lat": 53.5, "lon": -113.5, "tx_power": 20.0}


def _make(**overrides) -> CoveragePredictionRequest:
    return CoveragePredictionRequest(**{**VALID_BASE, **overrides})


# ---------------------------------------------------------------------------
# Model validation
# ---------------------------------------------------------------------------
class TestWindowModeModelDefaults:
    def test_window_mode_defaults_off(self):
        req = _make()
        assert req.window_mode is False

    def test_default_azimuth(self):
        req = _make()
        assert req.window_azimuth == 0.0

    def test_default_fov(self):
        req = _make()
        assert req.window_fov == 90.0

    def test_default_glass_type(self):
        req = _make()
        assert req.glass_type == "double"

    def test_default_structural_material(self):
        req = _make()
        assert req.structural_material == "brick"


class TestWindowModeModelValidation:
    def test_azimuth_lower_bound(self):
        req = _make(window_azimuth=0)
        assert req.window_azimuth == 0

    def test_azimuth_upper_bound_exclusive(self):
        with pytest.raises(ValidationError):
            _make(window_azimuth=360)

    def test_azimuth_negative_rejected(self):
        with pytest.raises(ValidationError):
            _make(window_azimuth=-1)

    def test_fov_lower_bound(self):
        req = _make(window_fov=1)
        assert req.window_fov == 1

    def test_fov_zero_rejected(self):
        with pytest.raises(ValidationError):
            _make(window_fov=0)

    def test_fov_max(self):
        req = _make(window_fov=360)
        assert req.window_fov == 360

    def test_fov_over_360_rejected(self):
        with pytest.raises(ValidationError):
            _make(window_fov=361)

    def test_glass_type_valid(self):
        for gt in ("single", "double", "triple"):
            req = _make(glass_type=gt)
            assert req.glass_type == gt

    def test_glass_type_invalid(self):
        with pytest.raises(ValidationError):
            _make(glass_type="quadruple")

    def test_structural_material_valid(self):
        for sm in ("drywall", "brick", "metal"):
            req = _make(structural_material=sm)
            assert req.structural_material == sm

    def test_structural_material_invalid(self):
        with pytest.raises(ValidationError):
            _make(structural_material="wood")


# ---------------------------------------------------------------------------
# Attenuation constants
# ---------------------------------------------------------------------------
class TestAttenuationConstants:
    def test_glass_values(self):
        assert Splat.GLASS_ATTENUATION_DB == {"single": 2.0, "double": 4.0, "triple": 6.0}

    def test_structural_values(self):
        assert Splat.STRUCTURAL_ATTENUATION_DB == {"drywall": 3.0, "brick": 10.0, "metal": 20.0}


# ---------------------------------------------------------------------------
# _apply_window_attenuation — unit tests on raw numpy arrays
# ---------------------------------------------------------------------------
class TestApplyWindowAttenuation:
    """Test the static _apply_window_attenuation method directly."""

    # 3x3 grid centered on transmitter at (0, 0), bounds ±1 degree
    TX_LAT = 0.0
    TX_LON = 0.0
    NORTH = 1.0
    SOUTH = -1.0
    EAST = 1.0
    WEST = -1.0

    def _uniform_grid(self, dbm: float = -80.0) -> np.ndarray:
        """Create a 3x3 uniform dBm array."""
        return np.full((3, 3), dbm, dtype=np.float32)

    def test_no_mutation_of_input(self):
        arr = self._uniform_grid(-80.0)
        original = arr.copy()
        Splat._apply_window_attenuation(
            arr,
            self.TX_LAT,
            self.TX_LON,
            self.NORTH,
            self.SOUTH,
            self.EAST,
            self.WEST,
            window_azimuth=0,
            window_fov=90,
            glass_attenuation=4.0,
            structural_attenuation=10.0,
        )
        np.testing.assert_array_equal(arr, original)

    def test_nan_pixels_unchanged(self):
        arr = np.full((3, 3), np.nan, dtype=np.float32)
        result = Splat._apply_window_attenuation(
            arr,
            self.TX_LAT,
            self.TX_LON,
            self.NORTH,
            self.SOUTH,
            self.EAST,
            self.WEST,
            window_azimuth=0,
            window_fov=90,
            glass_attenuation=4.0,
            structural_attenuation=10.0,
        )
        assert np.all(np.isnan(result))

    def test_full_fov_all_glass(self):
        """With 360-degree FOV, all pixels get glass attenuation."""
        arr = self._uniform_grid(-80.0)
        result = Splat._apply_window_attenuation(
            arr,
            self.TX_LAT,
            self.TX_LON,
            self.NORTH,
            self.SOUTH,
            self.EAST,
            self.WEST,
            window_azimuth=0,
            window_fov=360,
            glass_attenuation=4.0,
            structural_attenuation=10.0,
        )
        np.testing.assert_allclose(result, -84.0)

    def test_north_facing_window(self):
        """Window facing north (azimuth=0, FOV=90). Top row should get glass; bottom row should get structural."""
        arr = self._uniform_grid(-80.0)
        result = Splat._apply_window_attenuation(
            arr,
            self.TX_LAT,
            self.TX_LON,
            self.NORTH,
            self.SOUTH,
            self.EAST,
            self.WEST,
            window_azimuth=0,
            window_fov=90,
            glass_attenuation=4.0,
            structural_attenuation=10.0,
        )
        # Top row (north) — pixels at azimuth ~0° from TX, within ±45° FOV → glass
        assert result[0, 1] == pytest.approx(-84.0)
        # Bottom row (south) — pixels at azimuth ~180° → structural
        assert result[2, 1] == pytest.approx(-90.0)

    def test_south_facing_window(self):
        """Window facing south (azimuth=180, FOV=90)."""
        arr = self._uniform_grid(-80.0)
        result = Splat._apply_window_attenuation(
            arr,
            self.TX_LAT,
            self.TX_LON,
            self.NORTH,
            self.SOUTH,
            self.EAST,
            self.WEST,
            window_azimuth=180,
            window_fov=90,
            glass_attenuation=4.0,
            structural_attenuation=10.0,
        )
        # Bottom row (south) — within FOV → glass
        assert result[2, 1] == pytest.approx(-84.0)
        # Top row (north) — outside FOV → structural
        assert result[0, 1] == pytest.approx(-90.0)

    def test_east_facing_window(self):
        """Window facing east (azimuth=90, FOV=90)."""
        arr = self._uniform_grid(-80.0)
        result = Splat._apply_window_attenuation(
            arr,
            self.TX_LAT,
            self.TX_LON,
            self.NORTH,
            self.SOUTH,
            self.EAST,
            self.WEST,
            window_azimuth=90,
            window_fov=90,
            glass_attenuation=2.0,
            structural_attenuation=20.0,
        )
        # Right column (east) — within FOV → glass
        assert result[1, 2] == pytest.approx(-82.0)
        # Left column (west) — outside FOV → structural
        assert result[1, 0] == pytest.approx(-100.0)

    def test_mixed_nan_and_valid(self):
        """NaN pixels should remain NaN; valid pixels get attenuation."""
        arr = np.array([[-80.0, np.nan, -80.0], [-80.0, -80.0, -80.0], [np.nan, -80.0, np.nan]], dtype=np.float32)
        result = Splat._apply_window_attenuation(
            arr,
            self.TX_LAT,
            self.TX_LON,
            self.NORTH,
            self.SOUTH,
            self.EAST,
            self.WEST,
            window_azimuth=0,
            window_fov=360,
            glass_attenuation=5.0,
            structural_attenuation=10.0,
        )
        assert np.isnan(result[0, 1])
        assert np.isnan(result[2, 0])
        assert np.isnan(result[2, 2])
        assert result[1, 1] == pytest.approx(-85.0)

    def test_wraparound_azimuth(self):
        """Window at azimuth=350, FOV=40: should cover 330-10 (wrapping around north)."""
        arr = self._uniform_grid(-80.0)
        result = Splat._apply_window_attenuation(
            arr,
            self.TX_LAT,
            self.TX_LON,
            self.NORTH,
            self.SOUTH,
            self.EAST,
            self.WEST,
            window_azimuth=350,
            window_fov=40,
            glass_attenuation=4.0,
            structural_attenuation=10.0,
        )
        # Top-center pixel is roughly azimuth 0 from center, within 330-10 range
        assert result[0, 1] == pytest.approx(-84.0)
        # Bottom-center pixel is roughly azimuth 180, outside FOV
        assert result[2, 1] == pytest.approx(-90.0)

    def test_zero_attenuation_preserves_values(self):
        """With zero attenuation for both, values should be unchanged."""
        arr = self._uniform_grid(-80.0)
        result = Splat._apply_window_attenuation(
            arr,
            self.TX_LAT,
            self.TX_LON,
            self.NORTH,
            self.SOUTH,
            self.EAST,
            self.WEST,
            window_azimuth=0,
            window_fov=90,
            glass_attenuation=0.0,
            structural_attenuation=0.0,
        )
        np.testing.assert_allclose(result, -80.0)


# ---------------------------------------------------------------------------
# Integration: model round-trip with window mode enabled
# ---------------------------------------------------------------------------
class TestWindowModeModelRoundTrip:
    def test_model_dump_includes_window_fields(self):
        req = _make(
            window_mode=True,
            window_azimuth=45.0,
            window_fov=120.0,
            glass_type="triple",
            structural_material="metal",
        )
        data = req.model_dump()
        assert data["window_mode"] is True
        assert data["window_azimuth"] == 45.0
        assert data["window_fov"] == 120.0
        assert data["glass_type"] == "triple"
        assert data["structural_material"] == "metal"

    def test_model_copy_with_window_overrides(self):
        req = _make()
        updated = req.model_copy(update={"window_mode": True, "window_azimuth": 270.0})
        assert updated.window_mode is True
        assert updated.window_azimuth == 270.0
        assert req.window_mode is False  # original unchanged
