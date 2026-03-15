from pydantic import BaseModel, Field


class MatrixConfigRequest(BaseModel):
    """Request body for PUT /matrix/config."""

    hardware: list[str] = Field(description="Enabled hardware identifiers (e.g. 'v3', 'v4', 'custom').")
    antennas: list[str] = Field(description="Enabled antenna identifiers.")
    terrain: list[str] = Field(description="Enabled terrain model identifiers.")
