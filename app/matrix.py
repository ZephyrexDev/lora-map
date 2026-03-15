"""Matrix configuration for the Signal Coverage Prediction API.

Manages the hardware/antenna/terrain matrix that defines which simulation
combinations are available.  Configuration is persisted as a JSON string
in the ``settings`` table under the key ``"matrix_config"``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from itertools import product

from sqlalchemy.orm import Session

from app.db.models import Setting
from app.models.MatrixConfigRequest import MatrixConfigRequest

HARDWARE_RX_PARAMS: dict[str, dict[str, float]] = {
    "v3": {"rx_sensitivity": -130.0},
    "v4": {"rx_sensitivity": -130.0},
}

ANTENNA_RX_PARAMS: dict[str, dict[str, float]] = {
    "ribbed_spring_helical": {"rx_gain": 0.0, "swr": 3.0},
    "duck_stubby": {"rx_gain": 1.0, "swr": 3.5},
    "bingfu_whip": {"rx_gain": 2.5, "swr": 1.8},
    "slinkdsco_omni": {"rx_gain": 4.0, "swr": 1.1},
}

# Known valid values for matrix axes — derived from preset data.
KNOWN_HARDWARE: frozenset[str] = frozenset(HARDWARE_RX_PARAMS.keys()) | {"custom"}
KNOWN_ANTENNAS: frozenset[str] = frozenset(ANTENNA_RX_PARAMS.keys())
KNOWN_TERRAIN: frozenset[str] = frozenset({"bare_earth", "dsm", "lulc_clutter", "weighted_aggregate"})

DEFAULT_MATRIX_CONFIG = MatrixConfigRequest(
    hardware=["v3", "v4"],
    antennas=list(ANTENNA_RX_PARAMS.keys()),
    terrain=["bare_earth"],
)

_SETTINGS_KEY = "matrix_config"


def get_matrix_config(session: Session) -> MatrixConfigRequest:
    """Read the matrix config from the settings table.

    Returns the default config when no row exists.
    """
    setting = session.get(Setting, _SETTINGS_KEY)
    if setting is None:
        return DEFAULT_MATRIX_CONFIG.model_copy()
    return MatrixConfigRequest.model_validate_json(setting.value)


def set_matrix_config(session: Session, config: MatrixConfigRequest) -> None:
    """Upsert the matrix config into the settings table."""
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
    setting = session.get(Setting, _SETTINGS_KEY)
    if setting is None:
        session.add(Setting(key=_SETTINGS_KEY, value=config.model_dump_json(), updated_at=now))
    else:
        setting.value = config.model_dump_json()
        setting.updated_at = now
    session.commit()


def get_matrix_combinations(config: MatrixConfigRequest) -> list[dict[str, str]]:
    """Return the cartesian product of all enabled matrix axes.

    Each element is a dict with keys ``hardware``, ``antenna``, and ``terrain``.
    Returns an empty list if any axis is empty.
    """
    hardware = config.hardware
    antennas = config.antennas
    # weighted_aggregate is derived from the three base models, not a real simulation
    terrain = [t for t in config.terrain if t != "weighted_aggregate"]

    if not hardware or not antennas or not terrain:
        return []

    return [{"hardware": h, "antenna": a, "terrain": t} for h, a, t in product(hardware, antennas, terrain)]
