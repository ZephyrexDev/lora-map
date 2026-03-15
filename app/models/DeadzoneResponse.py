from pydantic import BaseModel, Field


class AnalysisBounds(BaseModel):
    """Geographic bounding box for the deadzone analysis area."""

    north: float = Field(description="Northern latitude boundary")
    south: float = Field(description="Southern latitude boundary")
    east: float = Field(description="Eastern longitude boundary")
    west: float = Field(description="Western longitude boundary")


class SiteSuggestionResponse(BaseModel):
    """A suggested tower site to remediate a deadzone."""

    lat: float = Field(description="Suggested tower latitude")
    lon: float = Field(description="Suggested tower longitude")
    estimated_coverage_km2: float = Field(description="Estimated new coverage area in square kilometers")
    priority_rank: int = Field(ge=1, le=5, description="Priority ranking (1 = highest)")
    reason: str = Field(description="Human-readable explanation of why this site was suggested")


class DeadzoneRegionResponse(BaseModel):
    """A contiguous deadzone region identified by the analysis."""

    region_id: int = Field(description="Unique identifier for this deadzone region")
    center_lat: float = Field(description="Centroid latitude of the deadzone")
    center_lon: float = Field(description="Centroid longitude of the deadzone")
    area_km2: float = Field(description="Area of the deadzone in square kilometers")
    priority_score: float = Field(ge=0.0, le=1.0, description="Priority score from 0 (low) to 1 (high)")
    pixel_count: int = Field(description="Number of pixels in this deadzone region")
    suggestion: SiteSuggestionResponse | None = Field(
        default=None, description="Suggested tower site to remediate this deadzone, if applicable"
    )


class DeadzoneAnalysisResponse(BaseModel):
    """Full deadzone analysis result including regions and site suggestions."""

    bounds: AnalysisBounds = Field(description="Geographic bounds of the analysis area")
    total_coverage_km2: float = Field(description="Total area with signal coverage in square kilometers")
    total_deadzone_km2: float = Field(description="Total deadzone area in square kilometers")
    coverage_fraction: float = Field(ge=0.0, le=1.0, description="Fraction of analysis area with coverage")
    regions: list[DeadzoneRegionResponse] = Field(description="Identified deadzone regions, sorted by priority")
    suggestions: list[SiteSuggestionResponse] = Field(description="Up to 5 suggested tower sites for remediation")
    tower_count: int = Field(description="Number of towers included in the analysis")
