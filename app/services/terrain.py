"""Terrain data providers for multi-source elevation pipelines.

Each provider returns raw .hgt.gz bytes for a given tile name, compatible
with the existing SPLAT! ``_convert_hgt_to_sdf`` pipeline.  Providers share
S3 access and tile caching through a common base class.

Supported terrain models:
    - **bare_earth** (SRTM DTM): Standard SRTM elevation from ``elevation-tiles-prod``.
    - **dsm** (Digital Surface Model): Copernicus GLO-30 DSM from ``copernicus-dem-30m``.
    - **lulc_clutter**: SRTM + ESA WorldCover land-cover clutter heights.
"""

from __future__ import annotations

import gzip
import io
import logging
from abc import ABC, abstractmethod

import boto3
import numpy as np
import rasterio
from botocore.exceptions import ClientError
from diskcache import Cache
from rasterio.enums import Resampling

logger = logging.getLogger(__name__)

# ESA WorldCover class -> clutter height in meters
LULC_CLUTTER_HEIGHTS: dict[int, float] = {
    10: 12.0,  # Tree cover
    20: 3.0,  # Shrubland
    30: 0.0,  # Grassland
    40: 0.0,  # Cropland
    50: 20.0,  # Built-up
    60: 0.0,  # Bare / sparse vegetation
    70: 0.0,  # Snow and ice
    80: 0.0,  # Permanent water
    90: 0.0,  # Herbaceous wetland
    95: 8.0,  # Mangroves
    100: 0.0,  # Moss and lichen
}

# 1-arcsecond tile dimensions
_HGT_SIZE = 3601


class TerrainProvider(ABC):
    """Base class for terrain tile providers.

    Subclasses implement :meth:`get_tile` to return ``.hgt.gz`` bytes for
    a given tile name (e.g. ``N45W074.hgt.gz``).  Shared helpers handle
    S3 fetching and diskcache storage.
    """

    def __init__(self, s3: boto3.client, tile_cache: Cache) -> None:
        self.s3 = s3
        self.tile_cache = tile_cache

    @abstractmethod
    def get_tile(self, tile_name: str) -> bytes:
        """Return raw .hgt.gz bytes for *tile_name*."""

    def _fetch_tile_from_s3(self, bucket: str, s3_key: str, cache_key: str) -> bytes | None:
        """Download a tile from S3, cache on success, return ``None`` on ``NoSuchKey``."""
        try:
            obj = self.s3.get_object(Bucket=bucket, Key=s3_key)
            tile_data: bytes = obj["Body"].read()
            self.tile_cache[cache_key] = tile_data
            return tile_data
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                return None
            raise

    @staticmethod
    def _parse_tile_name(tile_name: str) -> tuple[int, int]:
        """Extract (lat, lon) integers from a tile name like ``N45W074.hgt.gz``."""
        base = tile_name.replace(".hgt.gz", "")
        lat = int(base[1:3]) * (1 if base[0] == "N" else -1)
        lon = int(base[4:7]) * (1 if base[3] == "E" else -1)
        return lat, lon


class SrtmProvider(TerrainProvider):
    """Bare-earth SRTM tiles from the ``elevation-tiles-prod`` bucket."""

    BUCKET = "elevation-tiles-prod"
    PREFIX = "v2/skadi"

    def get_tile(self, tile_name: str) -> bytes:
        cache_key = f"srtm:{tile_name}"
        if cache_key in self.tile_cache:
            logger.info("Cache hit: %s", cache_key)
            return self.tile_cache[cache_key]

        tile_dir = tile_name[:3]  # e.g. "N45"
        s3_key_v3 = f"{self.PREFIX}/{tile_dir}/{tile_name}"
        logger.info("Downloading SRTM tile %s from %s/%s ...", tile_name, self.BUCKET, s3_key_v3)

        data = self._fetch_tile_from_s3(self.BUCKET, s3_key_v3, cache_key)
        if data is not None:
            return data

        # Fallback to V1 prefix
        s3_key_v1 = f"skadi/{tile_dir}/{tile_name}"
        logger.info("V3 miss for %s, trying V1 at %s ...", tile_name, s3_key_v1)
        data = self._fetch_tile_from_s3(self.BUCKET, s3_key_v1, cache_key)
        if data is not None:
            return data

        raise FileNotFoundError(f"SRTM tile {tile_name} not found at {s3_key_v3} or {s3_key_v1}")


class DsmProvider(TerrainProvider):
    """Copernicus GLO-30 DSM tiles from ``copernicus-dem-30m`` (COG GeoTIFF).

    Downloads the COG, resamples to a 1-arcsecond 3601x3601 grid, converts
    to ``.hgt.gz`` format, and caches.  Falls back to :class:`SrtmProvider`
    when the DSM tile is unavailable.
    """

    BUCKET = "copernicus-dem-30m"

    def __init__(self, s3: boto3.client, tile_cache: Cache, srtm_fallback: SrtmProvider) -> None:
        super().__init__(s3, tile_cache)
        self._srtm = srtm_fallback

    def get_tile(self, tile_name: str) -> bytes:
        cache_key = f"dsm:{tile_name}"
        if cache_key in self.tile_cache:
            logger.info("Cache hit: %s", cache_key)
            return self.tile_cache[cache_key]

        lat, lon = self._parse_tile_name(tile_name)
        s3_key = self._build_copernicus_key(lat, lon)
        logger.info("Downloading Copernicus DSM tile from %s/%s ...", self.BUCKET, s3_key)

        try:
            obj = self.s3.get_object(Bucket=self.BUCKET, Key=s3_key)
            cog_bytes: bytes = obj["Body"].read()
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                logger.info("Copernicus DSM tile not found for %s, falling back to SRTM.", tile_name)
                return self._srtm.get_tile(tile_name)
            raise

        hgt_gz = self._cog_to_hgt_gz(cog_bytes, lat, lon)
        self.tile_cache[cache_key] = hgt_gz
        return hgt_gz

    @staticmethod
    def _build_copernicus_key(lat: int, lon: int) -> str:
        """Build the S3 key for a Copernicus GLO-30 DSM tile."""
        ns = "N" if lat >= 0 else "S"
        ew = "E" if lon >= 0 else "W"
        tile_id = f"Copernicus_DSM_COG_10_{ns}{abs(lat):02d}_00_{ew}{abs(lon):03d}_00_DEM"
        return f"{tile_id}/{tile_id}.tif"

    @staticmethod
    def _cog_to_hgt_gz(cog_bytes: bytes, lat: int, lon: int) -> bytes:
        """Convert a Copernicus COG GeoTIFF to .hgt.gz (int16 big-endian raw, gzipped).

        Resamples the source raster to a 3601x3601 grid covering the 1-degree tile
        from (lat, lon) to (lat+1, lon+1).
        """
        with rasterio.open(io.BytesIO(cog_bytes)) as src:
            data = src.read(
                1,
                out_shape=(_HGT_SIZE, _HGT_SIZE),
                resampling=Resampling.bilinear,
            )

        # HGT format: int16 big-endian, row-major, north-to-south
        elevation = np.clip(data, -32768, 32767).astype(np.int16)
        raw = elevation.astype(">i2").tobytes()

        buf = io.BytesIO()
        with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
            gz.write(raw)
        return buf.getvalue()


class LulcClutterProvider(TerrainProvider):
    """SRTM elevation + ESA WorldCover clutter heights.

    Downloads the bare-earth SRTM tile and the corresponding ESA WorldCover
    tile, resamples the land-cover classification to match the SRTM grid,
    and adds per-pixel clutter heights to the elevation values.
    """

    WORLDCOVER_BUCKET = "esa-worldcover"
    WORLDCOVER_PREFIX = "v200/2021/map"

    def __init__(self, s3: boto3.client, tile_cache: Cache, srtm_provider: SrtmProvider) -> None:
        super().__init__(s3, tile_cache)
        self._srtm = srtm_provider

    def get_tile(self, tile_name: str) -> bytes:
        cache_key = f"lulc:{tile_name}"
        if cache_key in self.tile_cache:
            logger.info("Cache hit: %s", cache_key)
            return self.tile_cache[cache_key]

        # Load bare-earth SRTM tile
        srtm_hgt_gz = self._srtm.get_tile(tile_name)

        # Decompress SRTM to int16 array
        with gzip.GzipFile(fileobj=io.BytesIO(srtm_hgt_gz)) as gz:
            raw = gz.read()

        n_values = len(raw) // 2
        side = int(n_values**0.5)
        elevation = np.frombuffer(raw, dtype=">i2").reshape(side, side).astype(np.float32)

        # Fetch WorldCover tile and compute clutter heights
        lat, lon = self._parse_tile_name(tile_name)
        clutter = self._get_clutter_grid(lat, lon, side)

        # Add clutter heights to elevation
        combined = np.clip(elevation + clutter, -32768, 32767).astype(np.int16)
        combined_raw = combined.astype(">i2").tobytes()

        buf = io.BytesIO()
        with gzip.GzipFile(fileobj=buf, mode="wb") as gz_out:
            gz_out.write(combined_raw)

        hgt_gz = buf.getvalue()
        self.tile_cache[cache_key] = hgt_gz
        return hgt_gz

    def _get_clutter_grid(self, lat: int, lon: int, target_size: int) -> np.ndarray:
        """Fetch and resample ESA WorldCover to produce a clutter height grid."""
        s3_key = self._build_worldcover_key(lat, lon)
        logger.info("Downloading ESA WorldCover tile from %s/%s ...", self.WORLDCOVER_BUCKET, s3_key)

        try:
            obj = self.s3.get_object(Bucket=self.WORLDCOVER_BUCKET, Key=s3_key)
            wc_bytes: bytes = obj["Body"].read()
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                ns = "N" if lat >= 0 else "S"
                ew = "E" if lon >= 0 else "W"
                logger.warning(
                    "ESA WorldCover tile not found for %s%02d/%s%03d, using zero clutter.",
                    ns,
                    abs(lat),
                    ew,
                    abs(lon),
                )
                return np.zeros((target_size, target_size), dtype=np.float32)
            raise

        with rasterio.open(io.BytesIO(wc_bytes)) as src:
            lulc = src.read(
                1,
                out_shape=(target_size, target_size),
                resampling=Resampling.nearest,
            )

        # Map land-cover classes to clutter heights
        clutter = np.zeros_like(lulc, dtype=np.float32)
        for lc_class, height in LULC_CLUTTER_HEIGHTS.items():
            if height > 0:
                clutter[lulc == lc_class] = height

        return clutter

    @staticmethod
    def _build_worldcover_key(lat: int, lon: int) -> str:
        """Build the S3 key for an ESA WorldCover tile."""
        ns = "N" if lat >= 0 else "S"
        ew = "E" if lon >= 0 else "W"
        return f"v200/2021/map/ESA_WorldCover_10m_2021_v200_{ns}{abs(lat):02d}{ew}{abs(lon):03d}_Map.tif"
