from pydantic import BaseModel, Field


class PointToPointResult(BaseModel):
    """Result of a SPLAT! point-to-point path analysis between two tower sites."""

    path_loss_db: float = Field(description="Total path loss in dB between the two sites.")
    has_los: bool = Field(description="Whether line-of-sight exists between the two sites.")
    distance_km: float = Field(description="Distance between the two sites in kilometers.")
