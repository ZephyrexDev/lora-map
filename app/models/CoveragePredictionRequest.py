from typing import Literal

import matplotlib.pyplot as plt
from pydantic import BaseModel, Field

AVAILABLE_COLORMAPS = plt.colormaps()


class CoveragePredictionRequest(BaseModel):
    """
    Input payload for /coverage.
    """

    # Transmitter
    lat: float = Field(ge=-90, le=90, description="Transmitter latitude in degrees (-90 to 90)")
    lon: float = Field(ge=-180, le=180, description="Transmitter longitude in degrees (-180 to 180)")
    tx_height: float = Field(1, ge=1, description="Transmitter height above ground in meters (>= 1 m)")
    tx_power: float = Field(gt=0, description="Transmitter power in dBm (>= 1 dBm)")
    tx_gain: float = Field(1, ge=0, description="Transmitter antenna gain in dB (>= 0)")
    swr: float | None = Field(
        1.0,
        ge=1.0,
        description="Antenna standing wave ratio (>= 1.0, default: 1.0). Used to calculate SWR mismatch loss.",
    )
    frequency_mhz: float = Field(905.0, ge=20, le=30000, description="Operating frequency in MHz (20-30000 MHz)")

    # Receiver
    rx_height: float = Field(1, ge=1, description="Receiver height above ground in meters (>= 1 m)")
    rx_gain: float = Field(1, ge=0, description="Receiver antenna gain in dB (>= 0)")
    signal_threshold: float = Field(-100, le=0, description="Signal cutoff in dBm (<= 0)")
    clutter_height: float = Field(0, ge=0, description="Ground clutter height in meters (>= 0)")

    # Environmental
    ground_dielectric: float | None = Field(15.0, ge=1, description="Ground dielectric constant (default: 15.0)")
    ground_conductivity: float | None = Field(0.005, ge=0, description="Ground conductivity in S/m (default: 0.005)")
    atmosphere_bending: float | None = Field(
        301.0,
        ge=0,
        description="Atmospheric bending constant in N-units (default: 301.0)",
    )

    # Model Settings
    radius: float = Field(1000.0, ge=1, description="Model maximum range in meters (>= 1 m)")
    system_loss: float | None = Field(0.0, ge=0, description="System loss in dB (default: 0.0)")
    radio_climate: Literal[
        "equatorial",
        "continental_subtropical",
        "maritime_subtropical",
        "desert",
        "continental_temperate",
        "maritime_temperate_land",
        "maritime_temperate_sea",
    ] = Field(
        "continental_temperate",
        description="Radio climate, e.g., 'equatorial', 'continental_temperate' (default: 'continental_temperate')",
    )
    polarization: Literal["horizontal", "vertical"] = Field(
        "vertical",
        description="Signal polarization, 'horizontal' or 'vertical' (default: 'vertical')",
    )
    situation_fraction: float | None = Field(
        50,
        gt=1,
        le=100,
        description="Percentage of locations within the modeled area where the signal prediction "
        "is expected to be valid (default 50).",
    )
    time_fraction: float | None = Field(
        90,
        gt=1,
        le=100,
        description="Percentage of times where the signal prediction is expected to be valid (default 90).",
    )

    # Output Settings
    colormap: Literal[tuple(AVAILABLE_COLORMAPS)] = Field(
        "rainbow",
        description=f"Matplotlib colormap to use. Available options: {', '.join(AVAILABLE_COLORMAPS)}",
    )
    min_dbm: float = Field(
        -130.0,
        description="Minimum dBm value for the colormap (default: -130.0).",
    )
    max_dbm: float = Field(
        -30.0,
        description="Maximum dBm value for the colormap (default: -30.0).",
    )

    high_resolution: bool = Field(
        False,
        description="Use optional 1-arcsecond / 30 meter resolution terrain tiles "
        "instead of the default 3-arcsecond / 90 meter (default: False).",
    )

    terrain_model: Literal["bare_earth", "dsm", "lulc_clutter", "weighted_aggregate"] = Field(
        "bare_earth",
        description="Terrain model: bare_earth (SRTM DTM), dsm (Digital Surface Model), "
        "lulc_clutter (SRTM + land cover clutter heights), or weighted_aggregate (blend of all three)",
    )

    # Tower display
    color: str | None = Field(
        None,
        description="Hex color for this tower on the map (e.g. '#ff0000'). Auto-assigned when omitted.",
    )
