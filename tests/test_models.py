"""Tests for app.models.CoveragePredictionRequest — Pydantic model validation."""

import pytest
from pydantic import ValidationError

from app.models.CoveragePredictionRequest import CoveragePredictionRequest


class TestCoveragePredictionRequest:
    def test_minimal_required_fields(self):
        """Model can be instantiated with only the required fields."""
        model = CoveragePredictionRequest(
            lat=40.0,
            lon=-74.0,
            tx_power=20.0,
        )
        assert model.lat == 40.0
        assert model.lon == -74.0
        assert model.tx_power == 20.0

    def test_optional_fields_have_defaults(self):
        """Optional / defaulted fields should have their documented defaults."""
        model = CoveragePredictionRequest(
            lat=0.0,
            lon=0.0,
            tx_power=10.0,
        )
        assert model.tx_height == 1
        assert model.tx_gain == 1
        assert model.frequency_mhz == 905.0
        assert model.rx_height == 1
        assert model.rx_gain == 1
        assert model.signal_threshold == -100
        assert model.clutter_height == 0
        assert model.ground_dielectric == 15.0
        assert model.ground_conductivity == 0.005
        assert model.atmosphere_bending == 301.0
        assert model.radius == 1000.0
        assert model.system_loss == 0.0
        assert model.radio_climate == "continental_temperate"
        assert model.polarization == "vertical"
        assert model.situation_fraction == 50
        assert model.time_fraction == 90
        assert model.colormap == "rainbow"
        assert model.min_dbm == -130.0
        assert model.max_dbm == -30.0
        assert model.high_resolution is False

    def test_validation_rejects_invalid_types(self):
        """Passing invalid types for required numeric fields should raise ValidationError."""
        with pytest.raises(ValidationError):
            CoveragePredictionRequest(
                lat="not_a_number",
                lon=-74.0,
                tx_power=20.0,
            )
