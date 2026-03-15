"""Tests for SWR mismatch loss calculation."""

import pytest

from app.services.splat import mismatch_loss_db
from app.models.CoveragePredictionRequest import CoveragePredictionRequest


@pytest.mark.parametrize("swr,expected", [
    (1.0, 0.0),
    (1.1, 0.01),
    (3.0, 1.25),
    (3.5, 1.60),
    (0.5, 0.0),   # below 1.0 → clamp to 0
])
def test_mismatch_loss_db(swr, expected):
    assert mismatch_loss_db(swr) == pytest.approx(expected, abs=0.01)


class TestCoveragePredictionRequestSwr:
    def test_swr_field_accepted(self):
        req = CoveragePredictionRequest(lat=40.0, lon=-105.0, tx_power=30.0, swr=2.5)
        assert req.swr == 2.5

    def test_swr_defaults_to_one(self):
        req = CoveragePredictionRequest(lat=40.0, lon=-105.0, tx_power=30.0)
        assert req.swr == 1.0
