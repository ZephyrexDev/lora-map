import gzip
import io
import logging
import math
import os
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Literal

import boto3
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from botocore import UNSIGNED
from botocore.config import Config
from diskcache import Cache
from PIL import Image
from rasterio.enums import Resampling
from rasterio.transform import Affine, from_bounds

from app.models.CoveragePredictionRequest import CoveragePredictionRequest
from app.services.terrain import DsmProvider, LulcClutterProvider, SrtmProvider, TerrainProvider

logger = logging.getLogger(__name__)
logging.getLogger("boto3").setLevel(logging.WARNING)
logging.getLogger("botocore").setLevel(logging.WARNING)
logging.getLogger("s3transfer").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)


def mismatch_loss_db(swr: float) -> float:
    """Calculate SWR mismatch loss in dB."""
    if swr <= 1.0:
        return 0.0
    reflection = ((swr - 1) / (swr + 1)) ** 2
    return -10 * math.log10(1 - reflection)

    # TODO: DRY — binary validation (lines 93-117) repeats the same
    # isfile+access check four times. Replace with a loop over a dict of
    # {attr_name: binary_name}, e.g.:
    #   BINARIES = {"splat_binary": "splat", "splat_hd_binary": "splat-hd", ...}
    #   for attr, name in BINARIES.items():
    #       path = splat_dir / name
    #       if not path.is_file() or not os.access(path, os.X_OK):
    #           raise FileNotFoundError(...)
    #       setattr(self, attr, path)
    #
    # TODO: Code standards — use pathlib.Path throughout this file per
    # CLAUDE.md ("Prefer pathlib.Path over os.path"). splat_path, binary
    # paths, tmpdir file joins, hgt_path, sdf_path all use os.path today.


class Splat:
    def __init__(
        self,
        splat_path: str,
        cache_dir: str = ".splat_tiles",
        cache_size_gb: float = 1.0,
        bucket_name: str = "elevation-tiles-prod",
        bucket_prefix: str = "v2/skadi",
    ):
        """
        SPLAT! wrapper class. Provides methods for generating SPLAT! RF coverage maps in GeoTIFF format.
        This class automatically downloads and caches the necessary terrain data from AWS:
        https://registry.opendata.aws/terrain-tiles/.

        SPLAT! and its optional utilities (splat, splat-hd, srtm2sdf, srtm2sdf-hd) must be installed
        in the `splat_path` directory and be executable.

        See the SPLAT! documentation: https://www.qsl.net/kd2bd/splat.html
        Additional details: https://github.com/jmcmellen/splat

        Args:
            splat_path (str): Path to the directory containing the SPLAT! binaries.
            cache_dir (str): Directory to store cached terrain tiles.
            cache_size_gb (float): Maximum size of the cache in gigabytes (GB). Defaults to 1.0.
                When the size of the cached tiles exceeds this value, the oldest tiles are deleted
                and will be re-downloaded as required.
            bucket_name (str): Name of the S3 bucket containing terrain tiles. Defaults to the AWS
                open data bucket `elevation-tiles-prod`.
            bucket_prefix (str): Folder in the S3 bucket containing the terrain tiles. Defaults to
                `v2/skadi`, which contains 1-arcsecond terrain data for most of the world.
        """

        # Check the provided SPLAT! path exists
        splat_dir = Path(splat_path)
        if not splat_dir.is_dir():
            raise FileNotFoundError(f"Provided SPLAT! path '{splat_path}' is not a valid directory.")

        # SPLAT! binaries — validate that each exists and is executable
        required_binaries = {
            "splat_binary": "splat",  # core SPLAT! program
            "splat_hd_binary": "splat-hd",  # used for 1-arcsecond / 30 meter resolution terrain data
            "srtm2sdf_binary": "srtm2sdf",  # convert 3-arcsecond srtm .hgt tiles to SPLAT! .sdf tiles
            "srtm2sdf_hd_binary": "srtm2sdf-hd",  # used instead of srtm2sdf for 1-arcsecond data
        }
        for attr, binary_name in required_binaries.items():
            binary_path = splat_dir / binary_name
            if not binary_path.is_file() or not os.access(binary_path, os.X_OK):
                raise FileNotFoundError(f"'{attr}' binary not found or not executable at '{binary_path}'")
            setattr(self, attr, str(binary_path))

        self.tile_cache = Cache(cache_dir, size_limit=int(cache_size_gb * 1024 * 1024 * 1024))

        self.s3 = boto3.client("s3", config=Config(signature_version=UNSIGNED))
        self.bucket_name = bucket_name
        self.bucket_prefix = bucket_prefix

        # Terrain providers
        srtm_provider = SrtmProvider(self.s3, self.tile_cache)
        self.terrain_providers: dict[str, TerrainProvider] = {
            "bare_earth": srtm_provider,
            "dsm": DsmProvider(self.s3, self.tile_cache, srtm_fallback=srtm_provider),
            "lulc_clutter": LulcClutterProvider(self.s3, self.tile_cache, srtm_provider=srtm_provider),
        }

        logger.info(
            f"Initialized SPLAT! with terrain tile cache at '{cache_dir}' with a size limit of {cache_size_gb} GB."
        )

    def coverage_prediction(self, request: CoveragePredictionRequest) -> bytes:
        """
        Execute a SPLAT! coverage prediction using the provided CoveragePredictionRequest.

        Args:
            request (CoveragePredictionRequest): The coverage prediction request object.

        Returns:
            bytes: the SPLAT! coverage prediction as a GeoTIFF.

        Raises:
            RuntimeError: If SPLAT! fails to execute.
        """
        logger.debug(f"Coverage prediction request: {request.model_dump_json()}")

        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                logger.debug(f"Temporary directory created: {tmpdir}")

                # FIXME: Eventually support high-resolution terrain data
                request.high_resolution = False

                # Set hard limit of 100 km radius
                if request.radius > 100000:
                    logger.debug(f"User tried to set radius of {request.radius} meters, setting to 100 km.")
                    request.radius = 100000

                # determine the required terrain tiles
                required_tiles = Splat._calculate_required_terrain_tiles(request.lat, request.lon, request.radius)

                # Select terrain provider based on request
                provider = self.terrain_providers.get(request.terrain_model, self.terrain_providers["bare_earth"])

                # download and convert terrain tiles to SPLAT! sdf
                for tile_name, sdf_name, sdf_hd_name in required_tiles:
                    tile_data = provider.get_tile(tile_name)
                    sdf_data = self._convert_hgt_to_sdf(tile_data, tile_name, high_resolution=request.high_resolution)

                    with open(
                        Path(tmpdir) / (sdf_hd_name if request.high_resolution else sdf_name),
                        "wb",
                    ) as sdf_file:
                        sdf_file.write(sdf_data)

                # write transmitter / qth file
                with open(Path(tmpdir) / "tx.qth", "wb") as qth_file:
                    qth_file.write(Splat._create_splat_qth("tx", request.lat, request.lon, request.tx_height))

                # Apply SWR mismatch loss to effective TX power
                effective_tx_power = request.tx_power - mismatch_loss_db(request.swr)
                logger.debug(
                    f"SWR={request.swr}, mismatch_loss={mismatch_loss_db(request.swr):.2f} dB, "
                    f"effective_tx_power={effective_tx_power:.2f} dBm (was {request.tx_power:.2f} dBm)"
                )

                # write model parameter / lrp file
                with open(Path(tmpdir) / "splat.lrp", "wb") as lrp_file:
                    lrp_file.write(
                        Splat._create_splat_lrp(
                            ground_dielectric=request.ground_dielectric,
                            ground_conductivity=request.ground_conductivity,
                            atmosphere_bending=request.atmosphere_bending,
                            frequency_mhz=request.frequency_mhz,
                            radio_climate=request.radio_climate,
                            polarization=request.polarization,
                            situation_fraction=request.situation_fraction,
                            time_fraction=request.time_fraction,
                            tx_power=effective_tx_power,
                            tx_gain=request.tx_gain,
                            system_loss=request.system_loss,
                        )
                    )

                # write colorbar / dcf file
                with open(Path(tmpdir) / "splat.dcf", "wb") as dcf_file:
                    dcf_file.write(
                        Splat._create_splat_dcf(
                            colormap_name=request.colormap,
                            min_dbm=request.min_dbm,
                            max_dbm=request.max_dbm,
                        )
                    )

                logger.debug(f"Contents of {tmpdir}: {list(Path(tmpdir).iterdir())}")

                splat_command = [
                    (self.splat_hd_binary if request.high_resolution else self.splat_binary),
                    "-t",
                    "tx.qth",
                    "-L",
                    str(request.rx_height),
                    "-metric",
                    "-R",
                    str(request.radius / 1000.0),
                    "-sc",
                    "-gc",
                    str(request.clutter_height),
                    "-ngs",
                    "-N",
                    "-o",
                    "output.ppm",
                    "-dbm",
                    "-db",
                    str(request.signal_threshold),
                    "-kml",
                    "-olditm",
                ]  # flag "olditm" uses the standard ITM model instead of ITWOM, which has produced unrealistic results.
                logger.debug(f"Executing SPLAT! command: {' '.join(splat_command)}")

                splat_result = subprocess.run(
                    splat_command,
                    cwd=tmpdir,
                    capture_output=True,
                    text=True,
                    check=False,
                )

                logger.debug(f"SPLAT! stdout:\n{splat_result.stdout}")
                logger.debug(f"SPLAT! stderr:\n{splat_result.stderr}")

                if splat_result.returncode != 0:
                    logger.error(f"SPLAT! execution failed with return code {splat_result.returncode}")
                    raise RuntimeError(
                        f"SPLAT! execution failed with return code {splat_result.returncode}\n"
                        f"Stdout: {splat_result.stdout}\nStderr: {splat_result.stderr}"
                    )

                with (
                    open(Path(tmpdir) / "output.ppm", "rb") as ppm_file,
                    open(Path(tmpdir) / "output.kml", "rb") as kml_file,
                ):
                    ppm_data = ppm_file.read()
                    kml_data = kml_file.read()
                    geotiff_data = Splat._create_splat_geotiff(
                        ppm_data,
                        kml_data,
                        request.colormap,
                        request.min_dbm,
                        request.max_dbm,
                    )

                logger.info("SPLAT! coverage prediction completed successfully.")
                return geotiff_data

            # TODO: Exception chaining — all except blocks in this file wrap
            # and re-raise without chaining (raise RuntimeError(...) instead of
            # raise RuntimeError(...) from e). This drops the original traceback.
            # Add "from e" to every re-raise to preserve the cause chain.
            except Exception as e:
                logger.error(f"Error during coverage prediction: {e}")
                raise RuntimeError(f"Error during coverage prediction: {e}") from e

    @staticmethod
    def _calculate_required_terrain_tiles(lat: float, lon: float, radius: float) -> list[tuple[str, str, str]]:
        """
        Determine the set of required terrain tiles for the specified area and their corresponding .sdf / -hd.sdf
        filenames. This is used for downloading terrain data for SPLAT! which requires the files to follow a specific
        naming convention.

        Calculates the geographic bounding box based on the provided latitude, longitude, and radius, then
        determines the necessary tiles to cover the area. It returns filenames in the following formats:

            - .hgt.gz files: raw 1 arc-second terrain elevation tiles stored in AWS Open Data / S3.
            - .sdf files: Used for standard resolution (3-arcsecond) terrain data in SPLAT!.
            - .sdf-hd files: Used for high-resolution (1-arcsecond) terrain data in SPLAT!.

        The .hgt.gz filenames have the format:
            <N|S><latitude: 2 digits><E|W><longitude: 3 digits>.hgt.gz
            Example: N35W120.hgt.gz

        The .sdf and .sdf-hd filenames have the format:
            <lat_start>:<lat_end>:<lon_start>:<lon_end>.sdf
            <lat_start>:<lat_end>:<lon_start>:<lon_end>-hd.sdf
            Example: 35:36:-120:-119.sdf, 35:36:-120:-119-hd.sdf

        Args:
            lat (float): Latitude of the center point in degrees.
            lon (float): Longitude of the center point in degrees.
            radius (float): Simulation coverage radius in meters.

        Returns:
            List[Tuple[str, str, str]]: A list of tuples, each containing:
                - .hgt.gz filename (str)
                - Corresponding .sdf filename (str)
                - Corresponding .sdf-hd filename (str)
        """

        earth_radius = 6378137  # meters, approximate.

        # Convert radius to angular distance in degrees
        delta_deg = (radius / earth_radius) * (180 / math.pi)

        # Compute bounding box in degrees
        lat_min = lat - delta_deg
        lat_max = lat + delta_deg
        lon_min = lon - delta_deg / math.cos(math.radians(lat))
        lon_max = lon + delta_deg / math.cos(math.radians(lat))

        # Determine tile boundaries (rounded to 1-degree tiles)
        lat_min_tile = math.floor(lat_min)
        lat_max_tile = math.floor(lat_max)
        lon_min_tile = math.floor(lon_min)
        lon_max_tile = math.floor(lon_max)

        # All tile names within the bounding box
        tile_names = []

        for lat_tile in range(lat_min_tile, lat_max_tile + 1):
            for lon_tile in range(lon_min_tile, lon_max_tile + 1):
                ns = "N" if lat_tile >= 0 else "S"
                ew = "E" if lon_tile >= 0 else "W"
                tile_name = f"{ns}{abs(lat_tile):02d}{ew}{abs(lon_tile):03d}.hgt.gz"

                # Generate .sdf file names
                sdf_filename = Splat._hgt_filename_to_sdf_filename(tile_name, high_resolution=False)
                sdf_hd_filename = Splat._hgt_filename_to_sdf_filename(tile_name, high_resolution=True)
                tile_names.append((tile_name, sdf_filename, sdf_hd_filename))

        logger.debug("required tile names are: ")
        logger.debug(tile_names)
        return tile_names

    @staticmethod
    def _create_splat_qth(name: str, latitude: float, longitude: float, elevation: float) -> bytes:
        """
        Generate the contents of a SPLAT! .qth file describing a transmitter or receiver site.

        Args:
            name (str): Name of the site (unused but required for SPLAT!).
            latitude (float): Latitude of the site in degrees.
            longitude (float): Longitude of the site in degrees.
            elevation (float): Elevation (AGL) of the site in meters.

        Returns:
            bytes: The content of the .qth file formatted for SPLAT!.
        """
        logger.debug(f"Generating .qth file content for site '{name}'.")

        try:
            # Create the .qth file content
            contents = (
                f"{name}\n"
                f"{latitude:.6f}\n"
                # SPLAT! expects west longitude as a positive number
                f"{abs(longitude) if longitude < 0 else 360 - longitude:.6f}\n"
                f"{elevation:.2f}\n"
            )
            logger.debug(f"Generated .qth file contents:\n{contents}")
            return contents.encode("utf-8")  # Return as bytes
        except Exception as e:
            logger.error(f"Error generating .qth file content: {e}")
            raise ValueError(f"Failed to generate .qth content: {e}") from e

    @staticmethod
    def _create_splat_lrp(
        ground_dielectric: float,
        ground_conductivity: float,
        atmosphere_bending: float,
        frequency_mhz: float,
        radio_climate: Literal[
            "equatorial",
            "continental_subtropical",
            "maritime_subtropical",
            "desert",
            "continental_temperate",
            "maritime_temperate_land",
            "maritime_temperate_sea",
        ],
        polarization: Literal["horizontal", "vertical"],
        situation_fraction: float,
        time_fraction: float,
        tx_power: float,
        tx_gain: float,
        system_loss: float,
    ) -> bytes:
        """
        Generate the contents of a SPLAT! .lrp file describing environment and propagation parameters.

        Args:
            ground_dielectric (float): Earth's dielectric constant.
            ground_conductivity (float): Earth's conductivity (Siemens per meter).
            atmosphere_bending (float): Atmospheric bending constant.
            frequency_mhz (float): Frequency in MHz.
            radio_climate (str): Radio climate type.
            polarization (str): Antenna polarization.
            situation_fraction (float): Fraction of situations (percentage, 0-100).
            time_fraction (float): Fraction of time (percentage, 0-100).
            tx_power (float): Transmitter power in dBm.
            tx_gain (float): Transmitter antenna gain in dB.
            system_loss (float): System losses in dB (e.g., cable loss).

        Returns:
            bytes: The content of the .lrp file formatted for SPLAT!.
        """
        logger.debug("Generating .lrp file content.")

        # Mapping for radio climate and polarization to SPLAT! enumerations
        climate_map = {
            "equatorial": 1,
            "continental_subtropical": 2,
            "maritime_subtropical": 3,
            "desert": 4,
            "continental_temperate": 5,
            "maritime_temperate_land": 6,
            "maritime_temperate_sea": 7,
        }
        polarization_map = {"horizontal": 0, "vertical": 1}

        # Calculate ERP in Watts
        erp_watts = 10 ** ((tx_power + tx_gain - system_loss - 30) / 10)
        logger.debug(
            f"Calculated ERP in Watts: {erp_watts:.2f} "
            f"(tx_power={tx_power}, tx_gain={tx_gain}, system_loss={system_loss})"
        )

        # Generate the content, maintaining the SPLAT! format
        try:
            contents = (
                f"{ground_dielectric:.3f}  ; Earth Dielectric Constant\n"
                f"{ground_conductivity:.6f}  ; Earth Conductivity\n"
                f"{atmosphere_bending:.3f}  ; Atmospheric Bending Constant\n"
                f"{frequency_mhz:.3f}  ; Frequency in MHz\n"
                f"{climate_map[radio_climate]}  ; Radio Climate\n"
                f"{polarization_map[polarization]}  ; Polarization\n"
                f"{situation_fraction / 100.0:.2f} ; Fraction of situations\n"
                f"{time_fraction / 100.0:.2f}  ; Fraction of time\n"
                f"{erp_watts:.2f}  ; ERP in Watts\n"
            )
            logger.debug(f"Generated .lrp file contents:\n{contents}")
            return contents.encode("utf-8")  # Return as bytes
        except Exception as e:
            logger.error(f"Error generating .lrp file content: {e}")
            raise

    @staticmethod
    def _colormap_to_rgb(name: str, min_dbm: float, max_dbm: float, n_colors: int = 255) -> np.ndarray:
        """Return an (n_colors, 3) array of RGB values (0-255) for *name*."""
        cmap = plt.get_cmap(name, max(n_colors, 256))
        norm = plt.Normalize(vmin=min_dbm, vmax=max_dbm)
        vals = np.linspace(min_dbm, max_dbm, n_colors)
        return (cmap(norm(vals))[:, :3] * 255).astype(int)

    @staticmethod
    def _create_splat_dcf(colormap_name: str, min_dbm: float, max_dbm: float) -> bytes:
        """
        Generate the content of a SPLAT! .dcf file controlling the signal level contours
        using the specified Matplotlib color map.

        Args:
            colormap_name (str): The name of the Matplotlib colormap.
            min_dbm (float): The minimum signal strength value for the colormap in dBm.
            max_dbm (float): The maximum signal strength value for the colormap in dBm.

        Returns:
            bytes: The content of the .dcf file formatted for SPLAT!.
        """
        logger.debug(
            f"Generating .dcf file content using colormap '{colormap_name}', min_dbm={min_dbm}, max_dbm={max_dbm}."
        )

        try:
            # Generate RGB values for 32 levels (SPLAT! maximum), reversed high→low
            rgb_colors = Splat._colormap_to_rgb(colormap_name, min_dbm, max_dbm, 32)
            cmap_values = np.linspace(max_dbm, min_dbm, 32)

            # Prepare .dcf content
            contents = "; SPLAT! Auto-generated DBM Signal Level Color Definition\n;\n"
            contents += "; Format: dBm: red, green, blue\n;\n"
            for value, rgb in zip(cmap_values, rgb_colors[::-1], strict=True):
                contents += f"{int(value):+4d}: {rgb[0]:3d}, {rgb[1]:3d}, {rgb[2]:3d}\n"

            logger.debug(f"Generated .dcf file contents:\n{contents}")
            return contents.encode("utf-8")

        except Exception as e:
            logger.error(f"Error generating .dcf file content: {e}")
            raise ValueError(f"Failed to generate .dcf content: {e}") from e

    @staticmethod
    def create_splat_colorbar(
        colormap_name: str,
        min_dbm: float,
        max_dbm: float,
    ) -> list:
        """Generate a list of RGB color values corresponding to the color map, min and max RSSI values in dBm."""
        return Splat._colormap_to_rgb(colormap_name, min_dbm, max_dbm, 255)

    @staticmethod
    def _build_dcf_color_to_dbm_lut(
        colormap_name: str, min_dbm: float, max_dbm: float, n_levels: int = 32
    ) -> list[tuple[np.ndarray, float]]:
        """Build a lookup table mapping DCF RGB colors to their midpoint dBm values.

        The DCF file we generate uses *n_levels* evenly-spaced dBm thresholds
        between max_dbm and min_dbm.  SPLAT! paints each pixel with the color
        whose threshold bracket contains the predicted signal level.  This
        method returns a list of (rgb_array, dbm_midpoint) tuples so we can
        reverse-map PPM pixel colors back to approximate dBm values.

        Returns:
            A list of (rgb[3], dbm_midpoint) pairs, one per DCF level.
        """
        rgb_colors = Splat._colormap_to_rgb(colormap_name, min_dbm, max_dbm, n_levels)
        # DCF thresholds go from max_dbm down to min_dbm (same order as _create_splat_dcf)
        thresholds = np.linspace(max_dbm, min_dbm, n_levels)

        lut: list[tuple[np.ndarray, float]] = []
        for i, (_threshold, rgb) in enumerate(zip(thresholds, rgb_colors[::-1], strict=True)):
            # Determine the midpoint of this contour bracket
            if i == 0:
                # Strongest signal bracket: midpoint between max_dbm and next threshold
                mid = (max_dbm + thresholds[1]) / 2.0 if n_levels > 1 else max_dbm
            elif i == n_levels - 1:
                # Weakest signal bracket: midpoint between previous threshold and min_dbm
                mid = (thresholds[-2] + min_dbm) / 2.0
            else:
                mid = (thresholds[i - 1] + thresholds[i]) / 2.0
            lut.append((np.array(rgb[:3], dtype=np.uint8), float(mid)))

        return lut

    @staticmethod
    def _reverse_map_ppm_to_dbm(
        img_rgb: np.ndarray,
        colormap_name: str,
        min_dbm: float,
        max_dbm: float,
    ) -> np.ndarray:
        """Convert a SPLAT! PPM (RGB) image to a float32 array of dBm values.

        Each pixel in the PPM is colored according to the DCF we generated.
        We find the closest DCF color for every pixel and assign the
        corresponding dBm midpoint value.  Pixels that don't match any DCF
        color (background / no-signal areas) are set to NaN (nodata).

        Args:
            img_rgb: (H, W, 3) uint8 array of the PPM image in RGB.
            colormap_name: Matplotlib colormap name used to create the DCF.
            min_dbm: Minimum dBm value used in the DCF.
            max_dbm: Maximum dBm value used in the DCF.

        Returns:
            (H, W) float32 array with dBm values; NaN for no-data pixels.
        """
        lut = Splat._build_dcf_color_to_dbm_lut(colormap_name, min_dbm, max_dbm)

        height, width = img_rgb.shape[:2]
        dbm_array = np.full((height, width), np.nan, dtype=np.float32)

        # Stack DCF colors into an (N, 3) array for vectorized distance calculation
        dcf_colors = np.array([entry[0] for entry in lut], dtype=np.float32)  # (N, 3)
        dcf_dbm = np.array([entry[1] for entry in lut], dtype=np.float32)  # (N,)

        # Reshape image to (H*W, 3) for vectorized comparison
        pixels = img_rgb.reshape(-1, 3).astype(np.float32)  # (H*W, 3)

        # Compute squared Euclidean distance from each pixel to each DCF color
        # pixels: (H*W, 1, 3), dcf_colors: (1, N, 3)
        diffs = pixels[:, np.newaxis, :] - dcf_colors[np.newaxis, :, :]  # (H*W, N, 3)
        distances = np.sum(diffs**2, axis=2)  # (H*W, N)

        # Find closest DCF color for each pixel
        best_idx = np.argmin(distances, axis=1)  # (H*W,)
        best_dist = distances[np.arange(len(best_idx)), best_idx]  # (H*W,)

        # Assign dBm values; pixels far from any DCF color are background/nodata.
        # A threshold of 50^2 = 2500 allows some tolerance for SPLAT!'s anti-aliasing
        # while rejecting clearly non-signal colors (white/black backgrounds).
        DIST_THRESHOLD = 2500
        signal_mask = best_dist < DIST_THRESHOLD
        flat_dbm = np.where(signal_mask, dcf_dbm[best_idx], np.nan)
        dbm_array = flat_dbm.reshape(height, width)

        n_signal = int(np.sum(signal_mask))
        logger.debug(
            f"Reverse-mapped {n_signal}/{height * width} pixels to dBm values "
            f"(range {np.nanmin(dbm_array):.1f} to {np.nanmax(dbm_array):.1f} dBm)"
        )

        return dbm_array

    @staticmethod
    def _create_splat_geotiff(
        ppm_bytes: bytes,
        kml_bytes: bytes,
        colormap_name: str,
        min_dbm: float,
        max_dbm: float,
        null_value: int = 255,  # kept for API compat, unused in new path
    ) -> bytes:
        """
        Generate a single-band float32 GeoTIFF containing dBm signal strength
        values from SPLAT! PPM and KML data.

        Each pixel in the output GeoTIFF contains the predicted signal strength
        in dBm (e.g. -130.0 to -60.0).  No-coverage pixels are set to NaN
        (IEEE 754 float NaN used as the nodata sentinel).

        Args:
            ppm_bytes: Binary content of the SPLAT-generated PPM file.
            kml_bytes: Binary content of the KML file containing geospatial bounds.
            colormap_name: Matplotlib colormap name used when generating the DCF.
            min_dbm: Minimum dBm value used in the DCF / colormap.
            max_dbm: Maximum dBm value used in the DCF / colormap.
            null_value: (Unused, kept for backward compatibility.)

        Returns:
            bytes: The binary content of the resulting GeoTIFF file.

        Raises:
            RuntimeError: If the conversion process fails.
        """
        logger.info("Starting dBm GeoTIFF generation from SPLAT! PPM and KML data.")

        try:
            # Parse KML and extract bounding box
            logger.debug("Parsing KML content.")
            tree = ET.ElementTree(ET.fromstring(kml_bytes))
            namespace = {"kml": "http://earth.google.com/kml/2.1"}
            box = tree.find(".//kml:LatLonBox", namespace)

            north = float(box.find("kml:north", namespace).text)
            south = float(box.find("kml:south", namespace).text)
            east = float(box.find("kml:east", namespace).text)
            west = float(box.find("kml:west", namespace).text)

            logger.debug(f"Extracted bounding box: north={north}, south={south}, east={east}, west={west}")

            # Read PPM content as RGB (not grayscale — we need colors for reverse mapping)
            logger.debug("Reading PPM content as RGB.")
            with Image.open(io.BytesIO(ppm_bytes)) as img:
                img_rgb = np.array(img.convert("RGB"))  # (H, W, 3) uint8

            logger.debug(f"PPM image dimensions: {img_rgb.shape}")

            # Reverse-map PPM pixel colors to dBm values
            dbm_array = Splat._reverse_map_ppm_to_dbm(img_rgb, colormap_name, min_dbm, max_dbm)

            # Create GeoTIFF using Rasterio
            height, width = dbm_array.shape
            transform = from_bounds(west, south, east, north, width, height)
            logger.debug(f"GeoTIFF transform matrix: {transform}")

            # Write single-band float32 GeoTIFF to memory
            with io.BytesIO() as buffer:
                with rasterio.open(
                    buffer,
                    "w",
                    driver="GTiff",
                    height=height,
                    width=width,
                    count=1,
                    dtype="float32",
                    crs="EPSG:4326",
                    transform=transform,
                    compress="lzw",
                    nodata=float("nan"),
                ) as dst:
                    dst.write(dbm_array, 1)

                buffer.seek(0)
                geotiff_bytes = buffer.read()

            logger.info("dBm GeoTIFF generation successful.")
            return geotiff_bytes

        except Exception as e:
            logger.error(f"Error during GeoTIFF generation: {e}")
            raise RuntimeError(f"Error during GeoTIFF generation: {e}") from e

    @staticmethod
    def _hgt_filename_to_sdf_filename(hgt_filename: str, high_resolution: bool = False) -> str:
        """helper method to get the expected SPLAT! .sdf filename from the .hgt.gz terrain tile."""
        lat = int(hgt_filename[1:3]) * (1 if hgt_filename[0] == "N" else -1)
        min_lon = int(hgt_filename[4:7]) - (
            -1 if hgt_filename[3] == "E" else 1
        )  # fix off-by-one error in eastern hemisphere
        min_lon = 360 - min_lon if hgt_filename[3] == "E" else min_lon
        max_lon = 0 if min_lon == 359 else min_lon + 1
        return f"{lat}:{lat + 1}:{min_lon}:{max_lon}{'-hd.sdf' if high_resolution else '.sdf'}"

    def _convert_hgt_to_sdf(self, tile: bytes, tile_name: str, high_resolution: bool = False) -> bytes:
        """
        Converts a .hgt.gz terrain tile (provided as bytes) to a SPLAT! .sdf or -hd.sdf file.

        This method checks if the converted .sdf or -hd.sdf file corresponding to the tile_name
        exists in the cache. If not, the method decompresses the tile, places it in a temporary
        directory, performs the conversion using the SPLAT! utility (srtm2sdf or srtm2sdf-hd),
        and caches the resulting .sdf file.

        Args:
            tile (bytes): The binary content of the .hgt.gz terrain tile.
            tile_name (str): The name of the terrain tile (e.g., N35W120.hgt.gz).
            high_resolution (bool): Whether to generate a high-resolution -hd.sdf file. Defaults to False.

        Returns:
            bytes: The binary content of the converted .sdf or -hd.sdf file.

        Raises:
            RuntimeError: If the conversion fails.
        """

        sdf_filename = Splat._hgt_filename_to_sdf_filename(tile_name, high_resolution)

        # Check cache for converted file
        if sdf_filename in self.tile_cache:
            logger.info(f"Cache hit: {sdf_filename} found in the local cache.")
            return self.tile_cache[sdf_filename]

        # Create temporary working directory
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                # Decompress the tile into the temporary directory
                hgt_path = Path(tmpdir) / tile_name.replace(".gz", "")
                logger.info(f"Decompressing {tile_name} into {hgt_path}.")
                with gzip.GzipFile(fileobj=io.BytesIO(tile)) as gz_file, open(hgt_path, "wb") as hgt_file:
                    hgt_file.write(gz_file.read())

                # Downsample to 3-arcsecond resolution if not in high-resolution mode
                if not high_resolution:
                    try:
                        logger.info(f"Downsampling {hgt_path} to 3-arcsecond resolution.")
                        with rasterio.open(hgt_path) as src:
                            # Apply a scaling factor to transform for 3-arcsecond resolution
                            scale_factor = 3  # 3-arcsecond is 3 times coarser than 1-arcsecond
                            transform = src.transform * Affine.scale(scale_factor, scale_factor)

                            # Resample data to 3-arcsecond resolution
                            data = src.read(
                                # 3-arcsecond SRTM tiles always have dimensions of 1201x1201 pixels.
                                out_shape=(
                                    src.count,  # Number of bands
                                    1201,  # Downsampled height
                                    1201,  # Downsampled width
                                ),
                                resampling=Resampling.average,
                            )

                            # Update metadata for the new dataset
                            meta = src.meta.copy()
                            meta.update(
                                {
                                    "transform": transform,
                                    "width": 1201,
                                    "height": 1201,
                                }
                            )

                        # Overwrite the temporary file with downsampled data
                        with rasterio.open(hgt_path, "w", **meta) as dst:
                            dst.write(data)

                        logger.info(f"Successfully downsampled {hgt_path}.")
                    except Exception as e:
                        logger.error(f"Failed to downsample {hgt_path}: {e}")
                        raise RuntimeError(f"Downsampling error for {hgt_path}: {e}") from e

                # Call srtm2sdf or srtm2sdf-hd in the temporary directory
                cmd = self.srtm2sdf_hd_binary if high_resolution else self.srtm2sdf_binary
                logger.info(f"Converting {hgt_path} to {sdf_filename} using {cmd}.")
                result = subprocess.run(
                    [cmd, Path(tile_name.replace(".gz", "")).name],
                    cwd=tmpdir,
                    capture_output=True,
                    text=True,
                    check=True,
                )

                logger.debug(f"srtm2sdf output:\n{result.stderr}")
                sdf_path = Path(tmpdir) / sdf_filename

                # Ensure the .sdf file was created
                if not sdf_path.exists():
                    logger.error(f"Expected .sdf file not found: {sdf_path}")
                    raise RuntimeError(f"Failed to generate .sdf file: {sdf_path}")

                # Read and cache the .sdf file
                with open(sdf_path, "rb") as sdf_file:
                    sdf_data = sdf_file.read()
                self.tile_cache[sdf_filename] = sdf_data

                logger.info(f"Successfully converted and cached {sdf_filename}.")
                return sdf_data

            except subprocess.CalledProcessError as e:
                logger.error(f"Subprocess error during conversion of {tile_name}: {e}")
                logger.error(f"stderr: {e.stderr}")
                raise RuntimeError(f"Subprocess error during conversion of {tile_name}: {e}") from e

            except Exception as e:
                logger.error(f"Error during conversion of {tile_name} to {sdf_filename}: {e}")
                raise RuntimeError(f"Conversion error for {tile_name}: {e}") from e


if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)
    try:
        splat_service = Splat(
            splat_path="",  # Replace with the actual SPLAT! binary path
        )

        # Create a test coverage prediction request
        test_coverage_request = CoveragePredictionRequest(
            lat=51.4408448,
            lon=-0.8994816,
            tx_height=1.0,
            ground_dielectric=15.0,
            ground_conductivity=0.005,
            atmosphere_bending=301.0,
            frequency_mhz=868.0,
            radio_climate="continental_temperate",
            polarization="vertical",
            situation_fraction=95.0,
            time_fraction=95.0,
            tx_power=30.0,
            tx_gain=1.0,
            system_loss=2.0,
            rx_height=1.0,
            radius=50000.0,
            colormap="CMRmap",
            min_dbm=-130.0,
            max_dbm=-80.0,
            signal_threshold=-130.0,
            high_resolution=False,
        )

        # Execute coverage prediction
        logger.info("Starting SPLAT! coverage prediction...")
        result = splat_service.coverage_prediction(test_coverage_request)

        # Save GeoTIFF output for inspection
        output_path = "splat_output.tif"
        with open(output_path, "wb") as output_file:
            output_file.write(result)
        logger.info(f"GeoTIFF saved to: {output_path}")

    except Exception as e:
        logger.error(f"Error during SPLAT! test: {e}")
        raise
