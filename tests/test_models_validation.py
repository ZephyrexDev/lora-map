"""Tests for CoveragePredictionRequest field bounds, enums, and edge cases."""

import pytest
from pydantic import ValidationError

from app.models.CoveragePredictionRequest import CoveragePredictionRequest


VALID_BASE = {"lat": 40.0, "lon": -105.0, "tx_power": 20.0}


def _make(**overrides) -> CoveragePredictionRequest:
    return CoveragePredictionRequest(**{**VALID_BASE, **overrides})


# ===========================================================================
# Latitude bounds: -90 to 90
# ===========================================================================

class TestLatitudeBounds:
    def test_min_latitude(self):
        assert _make(lat=-90.0).lat == -90.0

    def test_max_latitude(self):
        assert _make(lat=90.0).lat == 90.0

    def test_rejects_below_min(self):
        with pytest.raises(ValidationError):
            _make(lat=-90.1)

    def test_rejects_above_max(self):
        with pytest.raises(ValidationError):
            _make(lat=90.1)


# ===========================================================================
# Longitude bounds: -180 to 180
# ===========================================================================

class TestLongitudeBounds:
    def test_min_longitude(self):
        assert _make(lon=-180.0).lon == -180.0

    def test_max_longitude(self):
        assert _make(lon=180.0).lon == 180.0

    def test_rejects_below_min(self):
        with pytest.raises(ValidationError):
            _make(lon=-180.1)

    def test_rejects_above_max(self):
        with pytest.raises(ValidationError):
            _make(lon=180.1)


# ===========================================================================
# tx_power: gt=0
# ===========================================================================

class TestTxPowerBounds:
    def test_rejects_zero(self):
        with pytest.raises(ValidationError):
            _make(tx_power=0)

    def test_rejects_negative(self):
        with pytest.raises(ValidationError):
            _make(tx_power=-1.0)

    def test_accepts_small_positive(self):
        assert _make(tx_power=0.001).tx_power == pytest.approx(0.001)


# ===========================================================================
# tx_height, rx_height: ge=1
# ===========================================================================

class TestHeightBounds:
    def test_tx_height_min(self):
        assert _make(tx_height=1.0).tx_height == 1.0

    def test_tx_height_rejects_below_min(self):
        with pytest.raises(ValidationError):
            _make(tx_height=0.5)

    def test_rx_height_min(self):
        assert _make(rx_height=1.0).rx_height == 1.0

    def test_rx_height_rejects_below_min(self):
        with pytest.raises(ValidationError):
            _make(rx_height=0.5)


# ===========================================================================
# tx_gain, rx_gain: ge=0
# ===========================================================================

class TestGainBounds:
    def test_tx_gain_accepts_zero(self):
        assert _make(tx_gain=0).tx_gain == 0

    def test_tx_gain_rejects_negative(self):
        with pytest.raises(ValidationError):
            _make(tx_gain=-0.1)

    def test_rx_gain_accepts_zero(self):
        assert _make(rx_gain=0).rx_gain == 0

    def test_rx_gain_rejects_negative(self):
        with pytest.raises(ValidationError):
            _make(rx_gain=-1)


# ===========================================================================
# frequency_mhz: 20 to 30000
# ===========================================================================

class TestFrequencyBounds:
    def test_min_frequency(self):
        assert _make(frequency_mhz=20.0).frequency_mhz == 20.0

    def test_max_frequency(self):
        assert _make(frequency_mhz=30000.0).frequency_mhz == 30000.0

    def test_rejects_below_min(self):
        with pytest.raises(ValidationError):
            _make(frequency_mhz=19.9)

    def test_rejects_above_max(self):
        with pytest.raises(ValidationError):
            _make(frequency_mhz=30001.0)


# ===========================================================================
# signal_threshold: le=0
# ===========================================================================

class TestSignalThresholdBounds:
    def test_accepts_zero(self):
        assert _make(signal_threshold=0).signal_threshold == 0

    def test_accepts_negative(self):
        assert _make(signal_threshold=-130).signal_threshold == -130

    def test_rejects_positive(self):
        with pytest.raises(ValidationError):
            _make(signal_threshold=1)


# ===========================================================================
# clutter_height: ge=0
# ===========================================================================

class TestClutterHeightBounds:
    def test_accepts_zero(self):
        assert _make(clutter_height=0).clutter_height == 0

    def test_rejects_negative(self):
        with pytest.raises(ValidationError):
            _make(clutter_height=-1)


# ===========================================================================
# radius: ge=1
# ===========================================================================

class TestRadiusBounds:
    def test_min_radius(self):
        assert _make(radius=1.0).radius == 1.0

    def test_rejects_below_min(self):
        with pytest.raises(ValidationError):
            _make(radius=0)


# ===========================================================================
# situation_fraction and time_fraction: gt=1, le=100
# ===========================================================================

class TestFractionBounds:
    def test_situation_fraction_min_boundary(self):
        with pytest.raises(ValidationError):
            _make(situation_fraction=1.0)  # gt=1, so 1.0 is invalid

    def test_situation_fraction_max(self):
        assert _make(situation_fraction=100.0).situation_fraction == 100.0

    def test_situation_fraction_rejects_above_max(self):
        with pytest.raises(ValidationError):
            _make(situation_fraction=100.1)

    def test_time_fraction_min_boundary(self):
        with pytest.raises(ValidationError):
            _make(time_fraction=1.0)

    def test_time_fraction_max(self):
        assert _make(time_fraction=100.0).time_fraction == 100.0

    def test_time_fraction_rejects_above_max(self):
        with pytest.raises(ValidationError):
            _make(time_fraction=100.1)


# ===========================================================================
# swr: ge=1.0
# ===========================================================================

class TestSwrBounds:
    def test_accepts_one(self):
        assert _make(swr=1.0).swr == 1.0

    def test_rejects_below_one(self):
        with pytest.raises(ValidationError):
            _make(swr=0.9)


# ===========================================================================
# radio_climate: Literal enum
# ===========================================================================

class TestRadioClimateEnum:
    @pytest.mark.parametrize("climate", [
        "equatorial",
        "continental_subtropical",
        "maritime_subtropical",
        "desert",
        "continental_temperate",
        "maritime_temperate_land",
        "maritime_temperate_sea",
    ])
    def test_accepts_valid_climates(self, climate):
        assert _make(radio_climate=climate).radio_climate == climate

    def test_rejects_invalid_climate(self):
        with pytest.raises(ValidationError):
            _make(radio_climate="tropical")


# ===========================================================================
# polarization: Literal enum
# ===========================================================================

class TestPolarizationEnum:
    def test_accepts_horizontal(self):
        assert _make(polarization="horizontal").polarization == "horizontal"

    def test_accepts_vertical(self):
        assert _make(polarization="vertical").polarization == "vertical"

    def test_rejects_invalid(self):
        with pytest.raises(ValidationError):
            _make(polarization="circular")


# ===========================================================================
# colormap: must be a valid matplotlib colormap
# ===========================================================================

class TestColormapEnum:
    def test_accepts_valid_colormaps(self):
        for name in ["plasma", "viridis", "jet", "rainbow"]:
            assert _make(colormap=name).colormap == name

    def test_rejects_invalid_colormap(self):
        with pytest.raises(ValidationError):
            _make(colormap="not_a_real_colormap")


# ===========================================================================
# ground_dielectric: ge=1
# ===========================================================================

class TestGroundDielectricBounds:
    def test_min(self):
        assert _make(ground_dielectric=1.0).ground_dielectric == 1.0

    def test_rejects_below_min(self):
        with pytest.raises(ValidationError):
            _make(ground_dielectric=0.5)


# ===========================================================================
# ground_conductivity: ge=0
# ===========================================================================

class TestGroundConductivityBounds:
    def test_accepts_zero(self):
        assert _make(ground_conductivity=0).ground_conductivity == 0

    def test_rejects_negative(self):
        with pytest.raises(ValidationError):
            _make(ground_conductivity=-0.001)


# ===========================================================================
# system_loss: ge=0
# ===========================================================================

class TestSystemLossBounds:
    def test_accepts_zero(self):
        assert _make(system_loss=0).system_loss == 0

    def test_rejects_negative(self):
        with pytest.raises(ValidationError):
            _make(system_loss=-1)
