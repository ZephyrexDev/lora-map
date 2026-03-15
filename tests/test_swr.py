import pytest

from app.services.splat import mismatch_loss_db
from app.models.CoveragePredictionRequest import CoveragePredictionRequest


class TestMismatchLossDb:
    def test_perfect_match(self):
        """SWR of 1.0 means no mismatch loss."""
        assert mismatch_loss_db(1.0) == 0.0

    def test_swr_1_1(self):
        """SWR of 1.1 should produce approximately 0.01 dB loss."""
        assert mismatch_loss_db(1.1) == pytest.approx(0.01, abs=0.01)

    def test_swr_3_0(self):
        """SWR of 3.0 should produce approximately 1.25 dB loss."""
        assert mismatch_loss_db(3.0) == pytest.approx(1.25, abs=0.01)

    def test_swr_3_5(self):
        """SWR of 3.5 should produce approximately 1.60 dB loss."""
        assert mismatch_loss_db(3.5) == pytest.approx(1.60, abs=0.01)

    def test_below_one_returns_zero(self):
        """SWR values below 1.0 should return 0.0."""
        assert mismatch_loss_db(0.5) == 0.0


class TestCoveragePredictionRequestSwr:
    def test_swr_field_accepted(self):
        """Model should accept an explicit swr value."""
        req = CoveragePredictionRequest(
            lat=40.0,
            lon=-105.0,
            tx_power=30.0,
            swr=2.5,
        )
        assert req.swr == 2.5

    def test_swr_defaults_to_one(self):
        """When swr is not provided it should default to 1.0."""
        req = CoveragePredictionRequest(
            lat=40.0,
            lon=-105.0,
            tx_power=30.0,
        )
        assert req.swr == 1.0
