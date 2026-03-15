from pydantic import BaseModel, Field


class TowerPathsRequest(BaseModel):
    """Request body for POST /tower-paths."""

    tower_ids: list[str] | None = Field(
        None,
        description="Optional list of tower IDs to compute paths between. " "If omitted, all towers are used.",
    )
