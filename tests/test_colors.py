"""Tests for the tower color palette and assignment logic."""

import re

from app.colors import PALETTE, next_tower_color


class TestPalette:
    """Tests for the PALETTE constant."""

    def test_palette_has_24_colors(self):
        assert len(PALETTE) == 24

    def test_no_greyscale_colors(self):
        greyscale = {"#000000", "#808080", "#ffffff"}
        for color in PALETTE:
            assert color not in greyscale, f"{color} is a greyscale color"

    def test_all_valid_hex_format(self):
        pattern = re.compile(r"^#[0-9a-f]{6}$")
        for color in PALETTE:
            assert pattern.match(color), f"{color} is not valid #RRGGBB hex"

    def test_all_colors_are_unique(self):
        assert len(set(PALETTE)) == len(PALETTE)


class TestNextTowerColor:
    """Tests for next_tower_color()."""

    def test_returns_first_color_when_none_used(self):
        result = next_tower_color([])
        assert result == PALETTE[0]

    def test_returns_first_unused_color(self):
        existing = PALETTE[:3]
        result = next_tower_color(existing)
        assert result == PALETTE[3]

    def test_skips_single_used_color(self):
        result = next_tower_color([PALETTE[0]])
        assert result == PALETTE[1]

    def test_cycles_when_all_used(self):
        result = next_tower_color(list(PALETTE))
        assert result == PALETTE[0]

    def test_case_insensitive_matching(self):
        result = next_tower_color([PALETTE[0].upper()])
        assert result == PALETTE[1]
