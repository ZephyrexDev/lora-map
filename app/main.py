"""
Signal Coverage Prediction API

Provides endpoints to predict radio signal coverage
using the ITM (Irregular Terrain Model) via SPLAT! (https://github.com/jmcmellen/splat).

Data is persisted to a local SQLite database.
"""

import asyncio
import dataclasses
import hashlib
import io
import json
import logging
import os
import sqlite3
import threading
from collections.abc import Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.auth import require_admin
from app.auth import router as auth_router
from app.colors import next_tower_color
from app.db import db_connection, init_db
from app.db.connection import DEFAULT_DB_PATH
from app.matrix import (
    ANTENNA_RX_PARAMS,
    HARDWARE_RX_PARAMS,
    KNOWN_ANTENNAS,
    KNOWN_HARDWARE,
    KNOWN_TERRAIN,
    get_matrix_combinations,
    get_matrix_config,
    set_matrix_config,
)
from app.models.CoveragePredictionRequest import CoveragePredictionRequest
from app.models.DeadzoneResponse import DeadzoneAnalysisResponse
from app.models.MatrixConfigRequest import MatrixConfigRequest
from app.models.responses import (
    ComputePathsResponse,
    CreatedPathResponse,
    DeleteResponse,
    PredictResponse,
    SimulationListResponse,
    SimulationResponse,
    TaskStatusResponse,
    TowerListResponse,
    TowerLocation,
    TowerPathListResponse,
    TowerPathResponse,
    TowerResponse,
)
from app.models.TowerPathsRequest import TowerPathsRequest
from app.services.aggregate import compute_weighted_aggregate
from app.services.deadzone import DeadzoneAnalyzer
from app.services.splat import Splat

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Lazy-initialized in lifespan — avoids import-time FileNotFoundError and
# makes testing easier (no need to mock at module level).
splat_service: Splat | None = None

# Semaphore limiting concurrent SPLAT! background tasks to avoid OOM / CPU starvation.
_SPLAT_MAX_CONCURRENT = int(os.environ.get("SPLAT_MAX_CONCURRENT", "3"))
_splat_semaphore = asyncio.Semaphore(_SPLAT_MAX_CONCURRENT)

# Allowlist for _delete_row to prevent SQL injection via table/column names.
_DELETABLE_TABLES: dict[str, str] = {
    "towers": "id",
    "tower_paths": "id",
}


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Initialize the SQLite database and SPLAT! service on startup."""
    global splat_service
    db_path = os.environ.get("DB_PATH", DEFAULT_DB_PATH)
    init_db(db_path)
    logger.info("Database initialized at %s.", db_path)

    splat_service = Splat(splat_path=os.environ.get("SPLAT_PATH", "/app/splat"))
    logger.info("SPLAT! service initialized.")

    if os.environ.get("ADMIN_PASSWORD") is None:
        logger.warning(
            "ADMIN_PASSWORD is not set — admin authentication is DISABLED. "
            "Set ADMIN_PASSWORD to secure admin endpoints in production."
        )

    yield


app = FastAPI(lifespan=lifespan)
app.include_router(auth_router)


def _get_splat() -> Splat:
    """Return the SPLAT! service, raising if not yet initialized."""
    if splat_service is None:
        raise RuntimeError("SPLAT! service not initialized — app lifespan has not started")
    return splat_service


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _geotiff_response_or_status(
    status: str,
    geotiff: bytes | None,
    error: str | None,
    resource_id: str,
) -> TaskStatusResponse | StreamingResponse:
    """Return a GeoTIFF StreamingResponse if completed, or a TaskStatusResponse."""
    if status == "completed":
        if geotiff is None:
            raise HTTPException(status_code=500, detail="No result data found")
        return StreamingResponse(
            io.BytesIO(geotiff),
            media_type="image/tiff",
            headers={"Content-Disposition": f"attachment; filename={resource_id}.tif"},
        )
    return TaskStatusResponse(id=resource_id, status=status, error=error if status == "failed" else None)


def _delete_row(table: str, row_id: str, label: str) -> DeleteResponse:
    """Delete a row by ID, raising HTTPException(404) if not found.

    Only tables registered in ``_DELETABLE_TABLES`` are accepted.
    """
    if table not in _DELETABLE_TABLES:
        raise ValueError(f"Table '{table}' is not in the deletion allowlist")
    id_column = _DELETABLE_TABLES[table]

    with db_connection() as conn:
        cursor = conn.execute(f"DELETE FROM {table} WHERE {id_column} = ?", (row_id,))  # noqa: S608
        conn.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail=f"{label} not found")
    logger.info("%s %s deleted.", label, row_id)
    return DeleteResponse(message=f"{label} deleted", id=row_id)


def _run_simulation_task(
    run_fn: Callable[[], bytes],
    on_success: Callable[[bytes], None],
    on_failure: Callable[[str], None],
    label: str,
) -> None:
    """Execute a simulation function with standardized success/failure DB updates."""
    try:
        result = run_fn()
        on_success(result)
    except Exception as e:
        logger.error("%s failed: %s", label, e)
        on_failure(str(e))


def _get_tower_location(conn: sqlite3.Connection, tower_id: str) -> TowerLocation | None:
    """Return location fields for a tower, or None if not found.

    Raises ``ValueError`` if the tower's params JSON is missing required location fields.
    """
    row = conn.execute("SELECT params FROM towers WHERE id = ?", (tower_id,)).fetchone()
    if row is None:
        return None
    params = json.loads(row["params"])

    for required in ("lat", "lon"):
        if required not in params:
            raise ValueError(f"Tower {tower_id} is missing required param '{required}'")

    return TowerLocation(
        lat=params["lat"],
        lon=params["lon"],
        tx_height=params.get("tx_height", 1),
        frequency_mhz=params.get("frequency_mhz", 905.0),
    )


# ---------------------------------------------------------------------------
# Background tasks
# ---------------------------------------------------------------------------


def run_splat(task_id: str, tower_id: str, request: CoveragePredictionRequest) -> None:
    """Execute the SPLAT! coverage prediction and persist results to SQLite."""
    svc = _get_splat()

    def execute() -> bytes:
        logger.info("Starting SPLAT! coverage prediction for task %s.", task_id)
        return svc.coverage_prediction(request)

    def on_success(geotiff_data: bytes) -> None:
        with db_connection() as conn:
            now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
            conn.execute("UPDATE towers SET geotiff = ?, updated_at = ? WHERE id = ?", (geotiff_data, now, tower_id))
            conn.execute("UPDATE tasks SET status = 'completed' WHERE id = ?", (task_id,))
            conn.commit()
        logger.info("Task %s completed successfully.", task_id)

    def on_failure(error_msg: str) -> None:
        with db_connection() as conn:
            conn.execute("UPDATE tasks SET status = 'failed', error = ? WHERE id = ?", (error_msg, task_id))
            conn.commit()

    _run_simulation_task(execute, on_success, on_failure, f"Task {task_id}")


def run_matrix_simulations(tower_id: str, payload: CoveragePredictionRequest) -> None:
    """Run all pending matrix simulations for a tower.

    Each pending simulation row is processed independently — a failure in one
    does not prevent the others from completing.
    """
    svc = _get_splat()

    with db_connection() as conn:
        rows = conn.execute(
            "SELECT id, client_hardware, client_antenna, terrain_model "
            "FROM simulations WHERE tower_id = ? AND status = 'pending'",
            (tower_id,),
        ).fetchall()

    for row in rows:
        sim_id = row["id"]

        def execute(r=row) -> bytes:
            overrides: dict[str, Any] = {"terrain_model": r["terrain_model"]}
            hw_params = HARDWARE_RX_PARAMS.get(r["client_hardware"], {})
            ant_params = ANTENNA_RX_PARAMS.get(r["client_antenna"], {})
            if "rx_sensitivity" in hw_params:
                overrides["signal_threshold"] = hw_params["rx_sensitivity"]
            if "rx_gain" in ant_params:
                overrides["rx_gain"] = ant_params["rx_gain"]
            if "swr" in ant_params:
                overrides["swr"] = ant_params["swr"]
            return svc.coverage_prediction(payload.model_copy(update=overrides))

        def on_success(geotiff_data: bytes, sid: str = sim_id) -> None:
            with db_connection() as conn:
                conn.execute(
                    "UPDATE simulations SET geotiff = ?, status = 'completed' WHERE id = ?", (geotiff_data, sid)
                )
                conn.commit()
            logger.info("Simulation %s completed.", sid)

        def on_failure(error_msg: str, sid: str = sim_id) -> None:
            with db_connection() as conn:
                conn.execute("UPDATE simulations SET status = 'failed', error = ? WHERE id = ?", (error_msg, sid))
                conn.commit()

        _run_simulation_task(execute, on_success, on_failure, f"Simulation {sim_id}")


def run_tower_path_analysis(tower_a_id: str, tower_b_id: str, path_id: str) -> None:
    """Run SPLAT! P2P analysis between two towers and store the result."""
    svc = _get_splat()
    try:
        with db_connection() as conn:
            loc_a = _get_tower_location(conn, tower_a_id)
            loc_b = _get_tower_location(conn, tower_b_id)

        if loc_a is None or loc_b is None:
            logger.warning("Tower not found for path %s, skipping.", path_id)
            return

        result = svc.point_to_point(
            lat_a=loc_a.lat,
            lon_a=loc_a.lon,
            height_a=loc_a.tx_height,
            lat_b=loc_b.lat,
            lon_b=loc_b.lon,
            height_b=loc_b.tx_height,
            frequency_mhz=loc_a.frequency_mhz,
        )

        with db_connection() as conn:
            conn.execute(
                "UPDATE tower_paths SET path_loss_db = ?, has_los = ?, distance_km = ?, status = 'completed' "
                "WHERE id = ?",
                (result.path_loss_db, int(result.has_los), result.distance_km, path_id),
            )
            conn.commit()
            logger.info(
                "Tower path %s completed: loss=%.1f dB, LOS=%s, dist=%.1f km",
                path_id,
                result.path_loss_db,
                result.has_los,
                result.distance_km,
            )

    except Exception as e:
        logger.error("Tower path %s failed: %s", path_id, e)
        with db_connection() as conn:
            conn.execute(
                "UPDATE tower_paths SET status = 'failed', error = ? WHERE id = ?",
                (str(e), path_id),
            )
            conn.commit()


# ---------------------------------------------------------------------------
# Prediction endpoints
# ---------------------------------------------------------------------------


@app.post("/predict", dependencies=[Depends(require_admin)], status_code=201, response_model=PredictResponse)
async def predict(
    payload: CoveragePredictionRequest,
    background_tasks: BackgroundTasks,
) -> PredictResponse:
    """Submit a signal coverage prediction request.

    Creates a tower and task, queues the SPLAT! computation as a background task.
    Returns 201 Created with the task_id and tower_id.
    """
    task_id: str = str(uuid4())
    tower_id: str = str(uuid4())

    with db_connection() as conn:
        existing_colors: list[str] = [
            row["color"] for row in conn.execute("SELECT color FROM towers WHERE color IS NOT NULL").fetchall()
        ]
        color: str = payload.color if payload.color else next_tower_color(existing_colors)

        conn.execute(
            "INSERT INTO towers (id, name, color, params) VALUES (?, ?, ?, ?)",
            (tower_id, "Unnamed", color, json.dumps(payload.model_dump())),
        )
        conn.execute(
            "INSERT INTO tasks (id, tower_id, status) VALUES (?, ?, ?)",
            (task_id, tower_id, "processing"),
        )

        config = get_matrix_config(conn)
        combinations = get_matrix_combinations(config)
        for combo in combinations:
            sim_id = str(uuid4())
            conn.execute(
                "INSERT INTO simulations (id, tower_id, client_hardware, client_antenna, terrain_model) "
                "VALUES (?, ?, ?, ?, ?)",
                (sim_id, tower_id, combo["hardware"], combo["antenna"], combo["terrain"]),
            )

        existing_tower_ids: list[str] = [
            r["id"] for r in conn.execute("SELECT id FROM towers WHERE id != ?", (tower_id,)).fetchall()
        ]
        for other_id in existing_tower_ids:
            path_id = str(uuid4())
            conn.execute(
                "INSERT INTO tower_paths (id, tower_a_id, tower_b_id) VALUES (?, ?, ?)",
                (path_id, tower_id, other_id),
            )

        conn.commit()

    _deadzone_cache.invalidate()

    background_tasks.add_task(run_splat, task_id, tower_id, payload)
    background_tasks.add_task(run_matrix_simulations, tower_id, payload)

    with db_connection() as conn:
        new_paths = conn.execute(
            "SELECT id, tower_a_id, tower_b_id FROM tower_paths WHERE tower_a_id = ? OR tower_b_id = ?",
            (tower_id, tower_id),
        ).fetchall()
    for path_row in new_paths:
        background_tasks.add_task(
            run_tower_path_analysis, path_row["tower_a_id"], path_row["tower_b_id"], path_row["id"]
        )

    return PredictResponse(task_id=task_id, tower_id=tower_id)


@app.get("/status/{task_id}", response_model=TaskStatusResponse)
async def get_status(task_id: str) -> TaskStatusResponse:
    """Retrieve the status of a prediction task from SQLite."""
    with db_connection() as conn:
        row = conn.execute("SELECT status, error FROM tasks WHERE id = ?", (task_id,)).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskStatusResponse(
        id=task_id,
        status=row["status"],
        error=row["error"] if row["status"] == "failed" else None,
    )


@app.get("/result/{task_id}", response_model=None)
async def get_result(task_id: str) -> TaskStatusResponse | StreamingResponse:
    """Retrieve the GeoTIFF result of a prediction task, or its current status."""
    with db_connection() as conn:
        task_row = conn.execute("SELECT tower_id, status, error FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if task_row is None:
            raise HTTPException(status_code=404, detail="Task not found")

        geotiff = None
        if task_row["status"] == "completed":
            tower_row = conn.execute("SELECT geotiff FROM towers WHERE id = ?", (task_row["tower_id"],)).fetchone()
            geotiff = tower_row["geotiff"] if tower_row else None

    return _geotiff_response_or_status(task_row["status"], geotiff, task_row["error"], task_id)


# ---------------------------------------------------------------------------
# Tower endpoints
# ---------------------------------------------------------------------------


@app.get("/towers", response_model=TowerListResponse)
async def list_towers() -> TowerListResponse:
    """List all towers without their GeoTIFF blobs."""
    with db_connection() as conn:
        rows = conn.execute("SELECT id, name, color, params, created_at, updated_at FROM towers").fetchall()

    towers = [
        TowerResponse(
            id=row["id"],
            name=row["name"],
            color=row["color"],
            params=json.loads(row["params"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        for row in rows
    ]
    return TowerListResponse(towers=towers)


@app.delete("/towers/{tower_id}", dependencies=[Depends(require_admin)])
async def delete_tower(tower_id: str) -> DeleteResponse:
    """Delete a tower and its associated tasks (via CASCADE)."""
    result = _delete_row("towers", tower_id, "Tower")
    _deadzone_cache.invalidate()
    return result


# ---------------------------------------------------------------------------
# Simulation endpoints
# ---------------------------------------------------------------------------


@app.get("/towers/{tower_id}/simulations", response_model=SimulationListResponse)
async def list_tower_simulations(
    tower_id: str,
    enabled_only: bool = Query(False, description="Filter to only simulations matching enabled matrix config members"),
) -> SimulationListResponse:
    """Return all simulations for a tower (without GeoTIFF blobs)."""
    with db_connection() as conn:
        rows = conn.execute(
            "SELECT id, client_hardware, client_antenna, terrain_model, status, created_at "
            "FROM simulations WHERE tower_id = ?",
            (tower_id,),
        ).fetchall()

        if enabled_only:
            config = get_matrix_config(conn)
            enabled_hw = set(config.hardware)
            enabled_ant = set(config.antennas)
            enabled_ter = set(config.terrain)
            rows = [
                r
                for r in rows
                if r["client_hardware"] in enabled_hw
                and r["client_antenna"] in enabled_ant
                and r["terrain_model"] in enabled_ter
            ]

    simulations = [
        SimulationResponse(
            id=row["id"],
            client_hardware=row["client_hardware"],
            client_antenna=row["client_antenna"],
            terrain_model=row["terrain_model"],
            status=row["status"],
            created_at=row["created_at"],
        )
        for row in rows
    ]
    return SimulationListResponse(simulations=simulations)


@app.get("/simulations/{sim_id}/result", response_model=None)
async def get_simulation_result(sim_id: str) -> TaskStatusResponse | StreamingResponse:
    """Return the GeoTIFF result for a completed simulation, or its current status."""
    with db_connection() as conn:
        row = conn.execute(
            "SELECT status, geotiff, error FROM simulations WHERE id = ?",
            (sim_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Simulation not found")

    return _geotiff_response_or_status(row["status"], row["geotiff"], row["error"], sim_id)


@app.get("/towers/{tower_id}/aggregate", response_model=None)
async def get_aggregate_simulation(
    tower_id: str,
    client_hardware: str = Query(..., description="Client hardware key"),
    client_antenna: str = Query(..., description="Client antenna key"),
) -> StreamingResponse:
    """Return a weighted-aggregate GeoTIFF blending bare_earth, DSM, and LULC results."""
    base_models = ("bare_earth", "dsm", "lulc_clutter")
    blobs: dict[str, bytes] = {}
    missing: list[str] = []

    with db_connection() as conn:
        for terrain in base_models:
            row = conn.execute(
                "SELECT status, geotiff FROM simulations "
                "WHERE tower_id = ? AND client_hardware = ? AND client_antenna = ? AND terrain_model = ?",
                (tower_id, client_hardware, client_antenna, terrain),
            ).fetchone()

            if row is None:
                missing.append(f"{terrain} (not found)")
            elif row["status"] != "completed":
                missing.append(f"{terrain} (status: {row['status']})")
            elif row["geotiff"] is None:
                missing.append(f"{terrain} (no GeoTIFF data)")
            else:
                blobs[terrain] = row["geotiff"]

    if missing:
        raise HTTPException(
            status_code=404,
            detail=f"Missing base simulations: {', '.join(missing)}",
        )

    try:
        aggregate_tiff = compute_weighted_aggregate(blobs["bare_earth"], blobs["dsm"], blobs["lulc_clutter"])
    except Exception as e:
        logger.error("Weighted aggregate computation failed for tower %s: %s", tower_id, e)
        raise HTTPException(status_code=500, detail="Aggregate computation failed") from e

    return StreamingResponse(
        io.BytesIO(aggregate_tiff),
        media_type="image/tiff",
        headers={"Content-Disposition": f"attachment; filename={tower_id}_aggregate.tif"},
    )


# ---------------------------------------------------------------------------
# Matrix config endpoints
# ---------------------------------------------------------------------------


@app.get("/matrix/config", response_model=MatrixConfigRequest)
async def get_matrix_config_endpoint() -> MatrixConfigRequest:
    """Return the current matrix configuration."""
    with db_connection() as conn:
        return get_matrix_config(conn)


@app.put("/matrix/config", dependencies=[Depends(require_admin)], response_model=MatrixConfigRequest)
async def put_matrix_config_endpoint(body: MatrixConfigRequest) -> MatrixConfigRequest:
    """Update the matrix configuration (admin-only).

    All values must be from the known presets.
    """
    errors: list[str] = []
    for key, known in [
        ("hardware", KNOWN_HARDWARE),
        ("antennas", KNOWN_ANTENNAS),
        ("terrain", KNOWN_TERRAIN),
    ]:
        values = getattr(body, key)
        unknown = set(values) - known
        if unknown:
            errors.append(f"Unknown {key} values: {sorted(unknown)}")

    if errors:
        raise HTTPException(status_code=422, detail=errors)

    with db_connection() as conn:
        set_matrix_config(conn, body)

    return body


# ---------------------------------------------------------------------------
# Tower path endpoints
# ---------------------------------------------------------------------------


@app.post("/tower-paths", dependencies=[Depends(require_admin)], status_code=202, response_model=ComputePathsResponse)
async def compute_tower_paths(
    background_tasks: BackgroundTasks,
    body: TowerPathsRequest | None = None,
) -> ComputePathsResponse:
    """Compute pairwise P2P paths between towers (async — returns 202 Accepted)."""
    with db_connection() as conn:
        if body and body.tower_ids:
            # Validate that all requested tower IDs actually exist
            placeholders = ",".join("?" for _ in body.tower_ids)
            existing = conn.execute(
                f"SELECT id FROM towers WHERE id IN ({placeholders})", body.tower_ids  # noqa: S608
            ).fetchall()
            existing_ids = {r["id"] for r in existing}
            missing = [tid for tid in body.tower_ids if tid not in existing_ids]
            if missing:
                raise HTTPException(status_code=404, detail=f"Tower(s) not found: {', '.join(missing)}")
            tower_ids: list[str] = body.tower_ids
        else:
            rows = conn.execute("SELECT id FROM towers").fetchall()
            tower_ids = [r["id"] for r in rows]

        if len(tower_ids) < 2:
            raise HTTPException(status_code=400, detail="Need at least 2 towers for path analysis")

        pairs: list[tuple[str, str]] = []
        for i, a in enumerate(tower_ids):
            for b in tower_ids[i + 1 :]:
                pairs.append((a, b))

        created_paths: list[CreatedPathResponse] = []
        for tower_a_id, tower_b_id in pairs:
            conn.execute(
                "DELETE FROM tower_paths WHERE "
                "(tower_a_id = ? AND tower_b_id = ?) OR (tower_a_id = ? AND tower_b_id = ?)",
                (tower_a_id, tower_b_id, tower_b_id, tower_a_id),
            )

            path_id = str(uuid4())
            conn.execute(
                "INSERT INTO tower_paths (id, tower_a_id, tower_b_id) VALUES (?, ?, ?)",
                (path_id, tower_a_id, tower_b_id),
            )
            created_paths.append(CreatedPathResponse(id=path_id, tower_a_id=tower_a_id, tower_b_id=tower_b_id))
            background_tasks.add_task(run_tower_path_analysis, tower_a_id, tower_b_id, path_id)

        conn.commit()

    return ComputePathsResponse(paths=created_paths, count=len(created_paths))


@app.get("/tower-paths", response_model=TowerPathListResponse)
async def list_tower_paths() -> TowerPathListResponse:
    """Return all computed tower paths (public endpoint for visitors)."""
    with db_connection() as conn:
        rows = conn.execute(
            "SELECT tp.id, tp.tower_a_id, tp.tower_b_id, tp.path_loss_db, tp.has_los, tp.distance_km, "
            "tp.created_at, ta.params AS params_a, tb.params AS params_b "
            "FROM tower_paths tp "
            "JOIN towers ta ON ta.id = tp.tower_a_id "
            "JOIN towers tb ON tb.id = tp.tower_b_id"
        ).fetchall()

    paths = []
    for row in rows:
        pa = json.loads(row["params_a"])
        pb = json.loads(row["params_b"])
        paths.append(
            TowerPathResponse(
                id=row["id"],
                tower_a_id=row["tower_a_id"],
                tower_b_id=row["tower_b_id"],
                lat_a=pa.get("lat", 0),
                lon_a=pa.get("lon", 0),
                lat_b=pb.get("lat", 0),
                lon_b=pb.get("lon", 0),
                path_loss_db=row["path_loss_db"],
                has_los=bool(row["has_los"]) if row["has_los"] is not None else None,
                distance_km=row["distance_km"],
                created_at=row["created_at"],
            )
        )
    return TowerPathListResponse(paths=paths)


@app.delete("/tower-paths/{path_id}", dependencies=[Depends(require_admin)])
async def delete_tower_path(path_id: str) -> DeleteResponse:
    """Delete a specific tower path."""
    return _delete_row("tower_paths", path_id, "Path")


# ---------------------------------------------------------------------------
# Deadzone analysis endpoint
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class _DeadzoneCache:
    """In-memory cache for deadzone analysis results.

    Uses a content hash of the GeoTIFF blobs to detect actual data changes,
    not just tower count.  All access is protected by a threading lock to
    prevent races between concurrent ``/deadzones`` requests.
    """

    _content_hash: str = ""
    result: DeadzoneAnalysisResponse | None = None
    _lock: threading.Lock = dataclasses.field(default_factory=threading.Lock)

    def invalidate(self) -> None:
        with self._lock:
            self._content_hash = ""
            self.result = None

    def is_valid_for(self, blobs: list[bytes]) -> bool:
        """Return True if the cache matches the current blob set."""
        with self._lock:
            if self.result is None:
                return False
            blob_hash = self._compute_hash(blobs)
            return blob_hash == self._content_hash

    def store(self, blobs: list[bytes], result: DeadzoneAnalysisResponse) -> None:
        with self._lock:
            self._content_hash = self._compute_hash(blobs)
            self.result = result

    @staticmethod
    def _compute_hash(blobs: list[bytes]) -> str:
        return hashlib.sha256(b"".join(sorted(hashlib.sha256(b).digest() for b in blobs))).hexdigest()


_deadzone_cache = _DeadzoneCache()


@app.get("/deadzones", response_model=DeadzoneAnalysisResponse)
async def get_deadzones() -> DeadzoneAnalysisResponse:
    """Analyze coverage gaps across all completed tower simulations."""
    geotiff_blobs: list[bytes] = []

    with db_connection() as conn:
        rows = conn.execute("SELECT geotiff FROM towers WHERE geotiff IS NOT NULL").fetchall()
        for row in rows:
            geotiff_blobs.append(row["geotiff"])

    if len(geotiff_blobs) < 2:
        raise HTTPException(
            status_code=400,
            detail="Deadzone analysis requires at least 2 completed tower simulations",
        )

    if _deadzone_cache.is_valid_for(geotiff_blobs):
        return _deadzone_cache.result  # type: ignore[return-value]

    try:
        analyzer = DeadzoneAnalyzer(geotiff_blobs)
        result = analyzer.analyze()
        _deadzone_cache.store(geotiff_blobs, result)
        return result
    except Exception as e:
        logger.error("Deadzone analysis failed: %s", e)
        raise HTTPException(status_code=500, detail="Deadzone analysis failed") from e


app.mount("/", StaticFiles(directory="app/ui", html=True), name="ui")
