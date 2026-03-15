"""Tower color palette and assignment logic."""

from __future__ import annotations

from itertools import product

# Build the 24-color palette: all permutations of {0, 128, 255} on R, G, B,
# excluding the three greyscale entries (0,0,0), (128,128,128), (255,255,255).
_GREYSCALE = {(0, 0, 0), (128, 128, 128), (255, 255, 255)}

PALETTE: list[str] = [
    f"#{r:02x}{g:02x}{b:02x}"
    for r, g, b in product((0, 128, 255), repeat=3)
    if (r, g, b) not in _GREYSCALE
]


def next_tower_color(existing_colors: list[str]) -> str:
    """Return the first palette color not yet used by existing towers.

    If all 24 palette colors are already in use, cycle back to the start.

    Parameters
    ----------
    existing_colors:
        Hex color strings currently assigned to towers.

    Returns
    -------
    str
        A hex color string from the palette.
    """
    existing_set = set(c.lower() for c in existing_colors)
    for color in PALETTE:
        if color not in existing_set:
            return color
    # All colors used — cycle back to the first one.
    return PALETTE[0]
