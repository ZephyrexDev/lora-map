"""Pydantic response models for all API endpoints."""

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


class AuthTokenResponse(BaseModel):
    token: str


class AuthCheckResponse(BaseModel):
    authenticated: bool


# ---------------------------------------------------------------------------
# Prediction / Tasks
# ---------------------------------------------------------------------------


class PredictResponse(BaseModel):
    task_id: str
    tower_id: str


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    error: str | None = None


# ---------------------------------------------------------------------------
# Towers
# ---------------------------------------------------------------------------


class TowerResponse(BaseModel):
    id: str
    name: str
    color: str | None
    params: dict
    created_at: str
    updated_at: str


class TowerListResponse(BaseModel):
    towers: list[TowerResponse]


class TowerLocation(BaseModel):
    """Extracted location fields from a tower's params JSON."""

    lat: float
    lon: float
    tx_height: float
    frequency_mhz: float


# ---------------------------------------------------------------------------
# Simulations
# ---------------------------------------------------------------------------


class SimulationResponse(BaseModel):
    id: str
    client_hardware: str
    client_antenna: str
    terrain_model: str
    status: str
    created_at: str


class SimulationListResponse(BaseModel):
    simulations: list[SimulationResponse]


# ---------------------------------------------------------------------------
# Tower Paths
# ---------------------------------------------------------------------------


class TowerPathResponse(BaseModel):
    id: str
    tower_a_id: str
    tower_b_id: str
    lat_a: float
    lon_a: float
    lat_b: float
    lon_b: float
    path_loss_db: float | None
    has_los: bool | None
    distance_km: float | None
    created_at: str


class TowerPathListResponse(BaseModel):
    paths: list[TowerPathResponse]


class CreatedPathResponse(BaseModel):
    id: str
    tower_a_id: str
    tower_b_id: str


class ComputePathsResponse(BaseModel):
    paths: list[CreatedPathResponse]
    count: int


# ---------------------------------------------------------------------------
# Generic
# ---------------------------------------------------------------------------


class DeleteResponse(BaseModel):
    message: str
    id: str
