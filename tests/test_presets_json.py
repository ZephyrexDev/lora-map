"""Tests for src/presets/presets.json — preset data integrity."""

import json
import math
from pathlib import Path

PRESETS_PATH = Path(__file__).resolve().parent.parent / "src" / "presets" / "presets.json"


def _load_presets():
    with open(PRESETS_PATH) as f:
        return json.load(f)


class TestPresetsStructure:
    def test_valid_json_with_four_keys(self):
        data = _load_presets()
        assert set(data.keys()) == {"hardware", "antennas", "frequencies", "heights"}


class TestHardwareEntries:
    def test_required_fields(self):
        data = _load_presets()
        required = {"name", "max_power_dbm", "chip", "is_custom"}
        for entry in data["hardware"]:
            assert required.issubset(entry.keys()), f"Missing fields in {entry}"


class TestAntennaEntries:
    def test_required_fields(self):
        data = _load_presets()
        required = {"name", "gain_dbi", "swr"}
        for entry in data["antennas"]:
            assert required.issubset(entry.keys()), f"Missing fields in {entry}"

    def test_swr_mismatch_loss_calculation(self):
        """Verify SWR mismatch loss: -10 * log10(1 - ((swr-1)/(swr+1))^2)."""
        data = _load_presets()
        for antenna in data["antennas"]:
            swr = antenna["swr"]
            reflection = (swr - 1) / (swr + 1)
            mismatch_loss = -10 * math.log10(1 - reflection ** 2)
            assert mismatch_loss >= 0, (
                f"Mismatch loss for {antenna['name']} should be non-negative, got {mismatch_loss}"
            )
            assert math.isfinite(mismatch_loss), (
                f"Mismatch loss for {antenna['name']} is not finite (SWR={swr})"
            )


class TestFrequencyEntries:
    def test_required_fields(self):
        data = _load_presets()
        required = {"region", "code", "frequency_mhz", "max_power_dbm"}
        for entry in data["frequencies"]:
            assert required.issubset(entry.keys()), f"Missing fields in {entry}"


class TestHeightEntries:
    def test_required_fields(self):
        data = _load_presets()
        required = {"label", "height_m"}
        for entry in data["heights"]:
            assert required.issubset(entry.keys()), f"Missing fields in {entry}"
