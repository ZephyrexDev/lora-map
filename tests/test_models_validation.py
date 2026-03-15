"""Tests for CoveragePredictionRequest field bounds, enums, and edge cases."""

import pytest
from pydantic import ValidationError

from app.models.CoveragePredictionRequest import CoveragePredictionRequest

VALID_BASE = {"lat": 40.0, "lon": -105.0, "tx_power": 20.0}


def _make(**overrides) -> CoveragePredictionRequest:
    return CoveragePredictionRequest(**{**VALID_BASE, **overrides})


# ---------------------------------------------------------------------------
# Generic parametrized boundary tests
# ---------------------------------------------------------------------------

# (field_name, valid_value, invalid_value)  — covers ge/le/gt constraints
_ACCEPT_REJECT = [
    # lat: ge=-90, le=90
    ("lat", -90.0, -90.1),
    ("lat", 90.0, 90.1),
    # lon: ge=-180, le=180
    ("lon", -180.0, -180.1),
    ("lon", 180.0, 180.1),
    # tx_power: gt=0
    ("tx_power", 0.001, 0),
    ("tx_power", 0.001, -1.0),
    # tx_height / rx_height: ge=1
    ("tx_height", 1.0, 0.5),
    ("rx_height", 1.0, 0.5),
    # tx_gain / rx_gain: ge=0
    ("tx_gain", 0, -0.1),
    ("rx_gain", 0, -1),
    # frequency_mhz: ge=20, le=30000
    ("frequency_mhz", 20.0, 19.9),
    ("frequency_mhz", 30000.0, 30001.0),
    # signal_threshold: le=0
    ("signal_threshold", 0, 1),
    # clutter_height: ge=0
    ("clutter_height", 0, -1),
    # radius: ge=1
    ("radius", 1.0, 0),
    # ground_dielectric: ge=1
    ("ground_dielectric", 1.0, 0.5),
    # ground_conductivity: ge=0
    ("ground_conductivity", 0, -0.001),
    # system_loss: ge=0
    ("system_loss", 0, -1),
    # swr: ge=1.0
    ("swr", 1.0, 0.9),
]


@pytest.mark.parametrize(
    "field,valid,invalid",
    _ACCEPT_REJECT,
    ids=[f"{f}={v}" for f, v, _ in _ACCEPT_REJECT],
)
def test_field_accepts_boundary(field, valid, invalid):
    assert getattr(_make(**{field: valid}), field) == pytest.approx(valid)


@pytest.mark.parametrize(
    "field,valid,invalid",
    _ACCEPT_REJECT,
    ids=[f"{f}={i}" for f, _, i in _ACCEPT_REJECT],
)
def test_field_rejects_out_of_bounds(field, valid, invalid):
    with pytest.raises(ValidationError):
        _make(**{field: invalid})


# ---------------------------------------------------------------------------
# Fraction fields: gt=1, le=100 (special boundary — 1.0 itself is invalid)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("field", ["situation_fraction", "time_fraction"])
class TestFractionBounds:
    def test_rejects_at_one(self, field):
        with pytest.raises(ValidationError):
            _make(**{field: 1.0})

    def test_accepts_just_above_one(self, field):
        assert getattr(_make(**{field: 1.01}), field) == pytest.approx(1.01)

    def test_accepts_max(self, field):
        assert getattr(_make(**{field: 100.0}), field) == 100.0

    def test_rejects_above_max(self, field):
        with pytest.raises(ValidationError):
            _make(**{field: 100.1})


# ---------------------------------------------------------------------------
# Enum / Literal fields
# ---------------------------------------------------------------------------

_VALID_CLIMATES = [
    "equatorial",
    "continental_subtropical",
    "maritime_subtropical",
    "desert",
    "continental_temperate",
    "maritime_temperate_land",
    "maritime_temperate_sea",
]


@pytest.mark.parametrize("climate", _VALID_CLIMATES)
def test_accepts_valid_radio_climate(climate):
    assert _make(radio_climate=climate).radio_climate == climate


def test_rejects_invalid_radio_climate():
    with pytest.raises(ValidationError):
        _make(radio_climate="tropical")


@pytest.mark.parametrize("pol", ["horizontal", "vertical"])
def test_accepts_valid_polarization(pol):
    assert _make(polarization=pol).polarization == pol


def test_rejects_invalid_polarization():
    with pytest.raises(ValidationError):
        _make(polarization="circular")


@pytest.mark.parametrize("cmap", ["plasma", "viridis", "jet", "rainbow"])
def test_accepts_valid_colormap(cmap):
    assert _make(colormap=cmap).colormap == cmap


def test_rejects_invalid_colormap():
    with pytest.raises(ValidationError):
        _make(colormap="not_a_real_colormap")
