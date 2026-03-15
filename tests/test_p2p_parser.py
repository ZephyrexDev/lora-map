"""Tests for the SPLAT! P2P output parser in app.services.splat."""

from app.services.splat import Splat


class TestParseP2pOutput:
    def test_parses_itm_path_loss(self):
        stdout = "ITM path loss: 125.34 dB\nDistance to site_b: 12.50 kilometers\n"
        result = Splat._parse_p2p_output(stdout, fallback_distance_km=10.0)
        assert result.path_loss_db == 125.34
        assert result.distance_km == 12.5
        assert result.has_los is True

    def test_parses_itwom_path_loss(self):
        stdout = "ITWOM Version 3.0 path loss: 98.76 dB\nDistance to site_b: 5.00 kilometers\n"
        result = Splat._parse_p2p_output(stdout, fallback_distance_km=5.0)
        assert result.path_loss_db == 98.76
        assert result.distance_km == 5.0

    def test_detects_obstruction_as_nlos(self):
        stdout = (
            "ITM path loss: 150.00 dB\n"
            "Distance to site_b: 20.00 kilometers\n"
            "Between site_a and site_b, Longley-Rice obstruction at 8.23 km\n"
        )
        result = Splat._parse_p2p_output(stdout, fallback_distance_km=20.0)
        assert result.has_los is False
        assert result.path_loss_db == 150.0

    def test_no_obstruction_keeps_los_true(self):
        stdout = "ITM path loss: 100.00 dB\nNo obstruction found between sites\n"
        result = Splat._parse_p2p_output(stdout, fallback_distance_km=10.0)
        assert result.has_los is True

    def test_falls_back_to_free_space_loss(self):
        stdout = "Free space path loss: 89.12 dB\nDistance to site_b: 3.00 kilometers\n"
        result = Splat._parse_p2p_output(stdout, fallback_distance_km=3.0)
        assert result.path_loss_db == 89.12

    def test_uses_fallback_distance_when_not_parsed(self):
        stdout = "ITM path loss: 110.00 dB\n"
        result = Splat._parse_p2p_output(stdout, fallback_distance_km=7.5)
        assert result.distance_km == 7.5

    def test_computes_fspl_when_no_loss_parsed(self):
        stdout = "Some unrelated output\n"
        result = Splat._parse_p2p_output(stdout, fallback_distance_km=10.0)
        assert result.path_loss_db is not None
        assert result.path_loss_db > 0
        assert result.has_los is True
