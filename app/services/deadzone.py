"""
Deadzone analysis service.

Merges coverage GeoTIFFs from all towers onto a common grid, identifies contiguous
deadzone regions via connected-component labeling, scores them by area and proximity
to existing coverage edges, and generates up to 5 candidate tower site suggestions.
"""

import contextlib
import logging
import math

import numpy as np
import rasterio
import rasterio.warp
from rasterio.enums import Resampling
from rasterio.transform import from_bounds
from scipy.ndimage import binary_dilation, center_of_mass, label

from app.models.DeadzoneResponse import (
    AnalysisBounds,
    DeadzoneAnalysisResponse,
    DeadzoneRegionResponse,
    SiteSuggestionResponse,
)

logger = logging.getLogger(__name__)

# Minimum region size in pixels to avoid noise
_MIN_REGION_PIXELS = 25

# Maximum number of site suggestions to return
_MAX_SUGGESTIONS = 5


class DeadzoneAnalyzer:
    """Analyzes gaps in combined tower coverage and identifies remediation sites."""

    def __init__(self, geotiff_blobs: list[bytes]) -> None:
        """
        Initialize the analyzer with raw GeoTIFF bytes from each tower simulation.

        Args:
            geotiff_blobs: List of GeoTIFF file contents (bytes), one per tower.
        """
        if len(geotiff_blobs) < 2:
            raise ValueError("Deadzone analysis requires at least 2 tower simulations")
        self.geotiff_blobs = geotiff_blobs
        self._memory_files: list[rasterio.MemoryFile] = []

    def _cleanup_rasters(self, rasters: list[rasterio.DatasetReader]) -> None:
        """Close all open dataset readers and their backing MemoryFile objects."""
        for reader in rasters:
            with contextlib.suppress(Exception):
                reader.close()
        for mem_file in self._memory_files:
            with contextlib.suppress(Exception):
                mem_file.close()
        self._memory_files.clear()

    def analyze(self) -> DeadzoneAnalysisResponse:
        """Run the full deadzone analysis pipeline and return results."""
        logger.info("Starting deadzone analysis with %d towers", len(self.geotiff_blobs))

        rasters = self._open_rasters()
        try:
            return self._run_analysis(rasters)
        finally:
            self._cleanup_rasters(rasters)

    def _run_analysis(self, rasters: list[rasterio.DatasetReader]) -> DeadzoneAnalysisResponse:
        """Core analysis logic, separated so callers can guarantee cleanup."""
        bounds = self._compute_union_bounds(rasters)
        merged, transform, pixel_area_km2 = self._merge_to_common_grid(rasters, bounds)

        # Build coverage mask: True where any tower provides signal (NaN means no signal in float32 GeoTIFFs)
        coverage_mask = ~np.isnan(merged)

        total_pixels = merged.size
        covered_pixels = int(np.sum(coverage_mask))
        deadzone_pixels = total_pixels - covered_pixels

        total_coverage_km2 = covered_pixels * pixel_area_km2
        total_deadzone_km2 = deadzone_pixels * pixel_area_km2
        coverage_fraction = covered_pixels / total_pixels if total_pixels > 0 else 0.0

        # Identify contiguous deadzone regions
        deadzone_mask = ~coverage_mask
        regions = self._find_regions(deadzone_mask, coverage_mask, bounds, transform, pixel_area_km2)

        # Generate suggestions from top-priority regions
        suggestions = self._generate_suggestions(regions)

        analysis_bounds = AnalysisBounds(
            north=bounds[0],
            south=bounds[1],
            east=bounds[2],
            west=bounds[3],
        )

        logger.info(
            "Deadzone analysis complete: %.1f km2 covered, %.1f km2 deadzone, %d regions, %d suggestions",
            total_coverage_km2,
            total_deadzone_km2,
            len(regions),
            len(suggestions),
        )

        return DeadzoneAnalysisResponse(
            bounds=analysis_bounds,
            total_coverage_km2=round(total_coverage_km2, 2),
            total_deadzone_km2=round(total_deadzone_km2, 2),
            coverage_fraction=round(coverage_fraction, 4),
            regions=regions,
            suggestions=suggestions,
            tower_count=len(self.geotiff_blobs),
        )

    def _open_rasters(self) -> list[rasterio.DatasetReader]:
        """Open all GeoTIFF blobs as rasterio dataset readers.

        MemoryFile references are stored in ``self._memory_files`` so they can
        be closed later via ``_cleanup_rasters``.

        If opening fails partway through, already-opened readers and
        MemoryFile objects are cleaned up before the exception propagates.
        """
        readers: list[rasterio.DatasetReader] = []
        try:
            for blob in self.geotiff_blobs:
                mem_file = rasterio.MemoryFile(blob)
                self._memory_files.append(mem_file)
                readers.append(mem_file.open())
        except Exception:
            self._cleanup_rasters(readers)
            raise
        return readers

    @staticmethod
    def _compute_union_bounds(rasters: list[rasterio.DatasetReader]) -> tuple[float, float, float, float]:
        """Compute the union bounding box (north, south, east, west) across all rasters."""
        north = max(r.bounds.top for r in rasters)
        south = min(r.bounds.bottom for r in rasters)
        east = max(r.bounds.right for r in rasters)
        west = min(r.bounds.left for r in rasters)
        return (north, south, east, west)

    @staticmethod
    def _merge_to_common_grid(
        rasters: list[rasterio.DatasetReader],
        bounds: tuple[float, float, float, float],
    ) -> tuple[np.ndarray, rasterio.Affine, float]:
        """
        Resample all rasters onto a common grid covering the union bounds,
        keeping the strongest signal (highest dBm value) per pixel.

        Returns:
            Tuple of (merged_array, transform, pixel_area_km2).
        """
        north, south, east, west = bounds

        # Use resolution from the first raster as reference
        ref = rasters[0]
        res_x = abs(ref.transform.a)
        res_y = abs(ref.transform.e)

        width = max(1, int(math.ceil((east - west) / res_x)))
        height = max(1, int(math.ceil((north - south) / res_y)))

        # Cap grid size to avoid memory issues
        max_dim = 2000
        if width > max_dim or height > max_dim:
            scale = max_dim / max(width, height)
            width = int(width * scale)
            height = int(height * scale)
            res_x = (east - west) / width
            res_y = (north - south) / height

        transform = from_bounds(west, south, east, north, width, height)

        # Start with all-NaN (no signal)
        merged = np.full((height, width), np.nan, dtype=np.float32)

        for raster in rasters:
            # Resample each raster into the common grid
            resampled = np.full((1, height, width), np.nan, dtype=np.float32)
            rasterio.warp.reproject(
                source=rasterio.band(raster, 1),
                destination=resampled,
                src_transform=raster.transform,
                src_crs=raster.crs,
                dst_transform=transform,
                dst_crs="EPSG:4326",
                dst_nodata=float("nan"),
                resampling=Resampling.nearest,
            )
            band = resampled[0]
            # Keep the strongest signal (highest dBm value — less negative = stronger)
            both_valid = ~np.isnan(merged) & ~np.isnan(band)
            only_new = np.isnan(merged) & ~np.isnan(band)
            merged = np.where(both_valid, np.maximum(merged, band), merged)
            merged = np.where(only_new, band, merged)

        # Calculate pixel area in km2 using center latitude
        center_lat = (north + south) / 2.0
        lat_km = res_y * 111.32
        lon_km = res_x * 111.32 * math.cos(math.radians(center_lat))
        pixel_area_km2 = lat_km * lon_km

        return merged, transform, pixel_area_km2

    def _find_regions(
        self,
        deadzone_mask: np.ndarray,
        coverage_mask: np.ndarray,
        bounds: tuple[float, float, float, float],
        transform: rasterio.Affine,
        pixel_area_km2: float,
    ) -> list[DeadzoneRegionResponse]:
        """
        Find contiguous deadzone regions, score them, and return sorted by priority.

        Scoring considers:
        - Region area (larger = higher priority)
        - Proximity to existing coverage edges (closer = higher priority, because these
          are gaps that existing towers almost reach)
        """
        labeled_array, num_features = label(deadzone_mask)
        if num_features == 0:
            return []

        # Compute edge proximity: dilate coverage mask to find pixels near coverage boundary
        coverage_edge = binary_dilation(coverage_mask, iterations=3) & ~coverage_mask

        regions: list[DeadzoneRegionResponse] = []
        edge_fractions: dict[int, float] = {}
        max_area = 0.0

        for region_id in range(1, num_features + 1):
            region_mask = labeled_array == region_id
            pixel_count = int(np.sum(region_mask))

            if pixel_count < _MIN_REGION_PIXELS:
                continue

            area_km2 = pixel_count * pixel_area_km2

            # Check proximity to coverage edges
            edge_overlap = int(np.sum(region_mask & coverage_edge))
            edge_fraction = edge_overlap / pixel_count if pixel_count > 0 else 0.0

            # Skip regions that are completely disconnected from any coverage
            if edge_fraction == 0.0 and not np.any(binary_dilation(region_mask, iterations=10) & coverage_mask):
                continue

            if area_km2 > max_area:
                max_area = area_km2

            edge_fractions[region_id] = edge_fraction

            # Compute centroid in pixel coords and convert to lat/lon
            centroid = center_of_mass(region_mask)
            row, col = centroid[0], centroid[1]
            lon, lat = rasterio.transform.xy(transform, int(row), int(col))

            regions.append(
                DeadzoneRegionResponse(
                    region_id=region_id,
                    center_lat=round(lat, 6),
                    center_lon=round(lon, 6),
                    area_km2=round(area_km2, 2),
                    priority_score=0.0,  # computed below
                    pixel_count=pixel_count,
                )
            )

        # Compute priority scores: weighted combination of area and edge proximity
        if max_area > 0 and regions:
            for region in regions:
                edge_fraction = edge_fractions[region.region_id]

                area_score = min(region.area_km2 / max_area, 1.0)
                proximity_score = min(edge_fraction * 5.0, 1.0)  # scale up since edge fractions are small
                priority = 0.6 * area_score + 0.4 * proximity_score
                region.priority_score = round(min(max(priority, 0.0), 1.0), 4)

        # Sort by priority descending
        regions.sort(key=lambda r: r.priority_score, reverse=True)
        return regions

    @staticmethod
    def _generate_suggestions(regions: list[DeadzoneRegionResponse]) -> list[SiteSuggestionResponse]:
        """Generate up to 5 site suggestions from the highest-priority deadzone regions."""
        suggestions: list[SiteSuggestionResponse] = []

        for rank, region in enumerate(regions[:_MAX_SUGGESTIONS], start=1):
            suggestion = SiteSuggestionResponse(
                lat=region.center_lat,
                lon=region.center_lon,
                estimated_coverage_km2=round(region.area_km2 * 0.7, 2),  # conservative estimate
                priority_rank=rank,
                reason=(
                    f"Deadzone of {region.area_km2:.1f} km2 adjacent to existing coverage"
                    f" (priority {region.priority_score:.2f})"
                ),
            )
            region.suggestion = suggestion
            suggestions.append(suggestion)

        return suggestions
