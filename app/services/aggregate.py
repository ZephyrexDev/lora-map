"""Weighted aggregate terrain model — blends three base terrain GeoTIFFs.

Computes a per-pixel weighted average of bare-earth, DSM, and LULC-clutter
simulation results.  No additional SPLAT! run is required.
"""

from __future__ import annotations

import io
import logging

import numpy as np
import rasterio

logger = logging.getLogger(__name__)

_BASE_TERRAIN_MODELS = ("bare_earth", "dsm", "lulc_clutter")
_DEFAULT_WEIGHTS = (0.20, 0.40, 0.40)


def compute_weighted_aggregate(
    bare_earth_tiff: bytes,
    dsm_tiff: bytes,
    lulc_tiff: bytes,
    weights: tuple[float, float, float] = _DEFAULT_WEIGHTS,
) -> bytes:
    """Blend three terrain simulation GeoTIFFs into a weighted aggregate.

    Args:
        bare_earth_tiff: GeoTIFF bytes from the bare-earth simulation.
        dsm_tiff: GeoTIFF bytes from the DSM simulation.
        lulc_tiff: GeoTIFF bytes from the LULC-clutter simulation.
        weights: (bare_earth, dsm, lulc_clutter) weights summing to 1.0.

    Returns:
        GeoTIFF bytes of the weighted aggregate result.

    Raises:
        ValueError: If the three inputs have mismatched dimensions.
    """
    arrays: list[np.ndarray] = []
    meta = None

    for _label, blob in zip(_BASE_TERRAIN_MODELS, (bare_earth_tiff, dsm_tiff, lulc_tiff), strict=True):
        with rasterio.open(io.BytesIO(blob)) as src:
            data = src.read(1).astype(np.float32)
            if meta is None:
                meta = src.meta.copy()
            arrays.append(data)

    # Verify all three have the same shape
    if not (arrays[0].shape == arrays[1].shape == arrays[2].shape):
        raise ValueError(
            f"Dimension mismatch: bare_earth={arrays[0].shape}, dsm={arrays[1].shape}, lulc={arrays[2].shape}"
        )

    # Weighted sum; NaN where any input is NaN
    result = weights[0] * arrays[0] + weights[1] * arrays[1] + weights[2] * arrays[2]

    # Write output GeoTIFF
    meta.update(dtype="float32", count=1, compress="lzw", nodata=float("nan"))
    buf = io.BytesIO()
    with rasterio.open(buf, "w", **meta) as dst:
        dst.write(result, 1)
    buf.seek(0)
    return buf.read()
