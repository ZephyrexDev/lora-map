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
import logging
import os
import threading
from collections.abc import Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.auth import require_admin
from app.auth import router as auth_router
from app.colors import next_tower_color
from app.db import db_session, init_db
from app.db.connection import DEFAULT_DB_PATH
from app.db.models import Simulation, Task, Tower, TowerPath
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


def _delete_row(model: type, row_id: str, label: str) -> DeleteResponse:
    """Delete a row by primary key, raising HTTPException(404) if not found."""
    with db_session() as session:
        obj = session.get(model, row_id)
        if obj is None:
            raise HTTPException(status_code=404, detail=f"{label} not found")
        session.delete(obj)
        session.commit()
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


def _get_tower_location(session: Session, tower_id: str) -> TowerLocation | None:
    """Return location fields for a tower, or None if not found.

    Raises ``ValueError`` if the tower's params JSON is missing required location fields.
    """
    tower = session.get(Tower, tower_id)
    if tower is None:
        return None
    params = tower.params

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
        with db_session() as session:
            now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
            tower = session.get(Tower, tower_id)
            tower.geotiff = geotiff_data
            tower.updated_at = now
            task = session.get(Task, task_id)
            task.status = "completed"
            session.commit()
        logger.info("Task %s completed successfully.", task_id)

    def on_failure(error_msg: str) -> None:
        with db_session() as session:
            task = session.get(Task, task_id)
            task.status = "failed"
            task.error = error_msg
            session.commit()

    _run_simulation_task(execute, on_success, on_failure, f"Task {task_id}")


def run_matrix_simulations(tower_id: str, payload: CoveragePredictionRequest) -> None:
    """Run all pending matrix simulations for a tower.

    Each pending simulation row is processed independently — a failure in one
    does not prevent the others from completing.
    """
    svc = _get_splat()

    with db_session() as session:
        rows = session.query(Simulation).filter_by(tower_id=tower_id, status="pending").all()
        sim_data = [(s.id, s.client_hardware, s.client_antenna, s.terrain_model) for s in rows]

    for sim_id, hw, ant, terrain in sim_data:

        def execute(hw=hw, ant=ant, terrain=terrain) -> bytes:
            overrides: dict[str, Any] = {"terrain_model": terrain}
            hw_params = HARDWARE_RX_PARAMS.get(hw, {})
            ant_params = ANTENNA_RX_PARAMS.get(ant, {})
            if "rx_sensitivity" in hw_params:
                overrides["signal_threshold"] = hw_params["rx_sensitivity"]
            if "rx_gain" in ant_params:
                overrides["rx_gain"] = ant_params["rx_gain"]
            if "swr" in ant_params:
                overrides["swr"] = ant_params["swr"]
            return svc.coverage_prediction(payload.model_copy(update=overrides))

        def on_success(geotiff_data: bytes, sid: str = sim_id) -> None:
            with db_session() as session:
                sim = session.get(Simulation, sid)
                sim.geotiff = geotiff_data
                sim.status = "completed"
                session.commit()
            logger.info("Simulation %s completed.", sid)

        def on_failure(error_msg: str, sid: str = sim_id) -> None:
            with db_session() as session:
                sim = session.get(Simulation, sid)
                sim.status = "failed"
                sim.error = error_msg
                session.commit()

        _run_simulation_task(execute, on_success, on_failure, f"Simulation {sim_id}")


def run_tower_path_analysis(tower_a_id: str, tower_b_id: str, path_id: str) -> None:
    """Run SPLAT! P2P analysis between two towers and store the result."""
    svc = _get_splat()
    try:
        with db_session() as session:
            loc_a = _get_tower_location(session, tower_a_id)
            loc_b = _get_tower_location(session, tower_b_id)

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

        with db_session() as session:
            path = session.get(TowerPath, path_id)
            path.path_loss_db = result.path_loss_db
            path.has_los = int(result.has_los)
            path.distance_km = result.distance_km
            path.status = "completed"
            session.commit()
            logger.info(
                "Tower path %s completed: loss=%.1f dB, LOS=%s, dist=%.1f km",
                path_id,
                result.path_loss_db,
                result.has_los,
                result.distance_km,
            )

    except Exception as e:
        logger.error("Tower path %s failed: %s", path_id, e)
        with db_session() as session:
            path = session.get(TowerPath, path_id)
            path.status = "failed"
            path.error = str(e)
            session.commit()


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

    with db_session() as session:
        existing_colors = [row.color for row in session.query(Tower.color).filter(Tower.color.isnot(None)).all()]
        color: str = payload.color if payload.color else next_tower_color(existing_colors)

        session.add(Tower(id=tower_id, name="Unnamed", color=color, params=payload.model_dump()))
        session.add(Task(id=task_id, tower_id=tower_id, status="processing"))

        config = get_matrix_config(session)
        combinations = get_matrix_combinations(config)
        for combo in combinations:
            session.add(
                Simulation(
                    id=str(uuid4()),
                    tower_id=tower_id,
                    client_hardware=combo["hardware"],
                    client_antenna=combo["antenna"],
                    terrain_model=combo["terrain"],
                )
            )

        existing_tower_ids = [r.id for r in session.query(Tower.id).filter(Tower.id != tower_id).all()]
        for other_id in existing_tower_ids:
            session.add(TowerPath(id=str(uuid4()), tower_a_id=tower_id, tower_b_id=other_id))

        session.commit()

    _deadzone_cache.invalidate()

    background_tasks.add_task(run_splat, task_id, tower_id, payload)
    background_tasks.add_task(run_matrix_simulations, tower_id, payload)

    with db_session() as session:
        new_paths = (
            session.query(TowerPath)
            .filter(or_(TowerPath.tower_a_id == tower_id, TowerPath.tower_b_id == tower_id))
            .all()
        )
        path_tuples = [(p.tower_a_id, p.tower_b_id, p.id) for p in new_paths]

    for a_id, b_id, pid in path_tuples:
        background_tasks.add_task(run_tower_path_analysis, a_id, b_id, pid)

    return PredictResponse(task_id=task_id, tower_id=tower_id)


@app.get("/status/{task_id}", response_model=TaskStatusResponse)
async def get_status(task_id: str) -> TaskStatusResponse:
    """Retrieve the status of a prediction task from SQLite."""
    with db_session() as session:
        task = session.get(Task, task_id)

    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskStatusResponse(
        id=task_id,
        status=task.status,
        error=task.error if task.status == "failed" else None,
    )


@app.get("/result/{task_id}", response_model=None)
async def get_result(task_id: str) -> TaskStatusResponse | StreamingResponse:
    """Retrieve the GeoTIFF result of a prediction task, or its current status."""
    with db_session() as session:
        task = session.get(Task, task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")

        geotiff = None
        if task.status == "completed":
            tower = session.get(Tower, task.tower_id)
            geotiff = tower.geotiff if tower else None

        return _geotiff_response_or_status(task.status, geotiff, task.error, task_id)


# ---------------------------------------------------------------------------
# Tower endpoints
# ---------------------------------------------------------------------------


@app.get("/towers", response_model=TowerListResponse)
async def list_towers() -> TowerListResponse:
    """List all towers without their GeoTIFF blobs."""
    with db_session() as session:
        rows = session.query(Tower).all()
        towers = [
            TowerResponse(
                id=t.id,
                name=t.name,
                color=t.color,
                params=t.params,
                created_at=t.created_at,
                updated_at=t.updated_at,
            )
            for t in rows
        ]
    return TowerListResponse(towers=towers)


@app.delete("/towers/{tower_id}", dependencies=[Depends(require_admin)])
async def delete_tower(tower_id: str) -> DeleteResponse:
    """Delete a tower and its associated tasks (via CASCADE)."""
    result = _delete_row(Tower, tower_id, "Tower")
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
    with db_session() as session:
        rows = session.query(Simulation).filter_by(tower_id=tower_id).all()

        if enabled_only:
            config = get_matrix_config(session)
            enabled_hw = set(config.hardware)
            enabled_ant = set(config.antennas)
            enabled_ter = set(config.terrain)
            rows = [
                r
                for r in rows
                if r.client_hardware in enabled_hw
                and r.client_antenna in enabled_ant
                and r.terrain_model in enabled_ter
            ]

        simulations = [
            SimulationResponse(
                id=r.id,
                client_hardware=r.client_hardware,
                client_antenna=r.client_antenna,
                terrain_model=r.terrain_model,
                status=r.status,
                created_at=r.created_at,
            )
            for r in rows
        ]
    return SimulationListResponse(simulations=simulations)


@app.get("/simulations/{sim_id}/result", response_model=None)
async def get_simulation_result(sim_id: str) -> TaskStatusResponse | StreamingResponse:
    """Return the GeoTIFF result for a completed simulation, or its current status."""
    with db_session() as session:
        sim = session.get(Simulation, sim_id)

    if sim is None:
        raise HTTPException(status_code=404, detail="Simulation not found")

    return _geotiff_response_or_status(sim.status, sim.geotiff, sim.error, sim_id)


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

    with db_session() as session:
        for terrain in base_models:
            sim = (
                session.query(Simulation)
                .filter_by(
                    tower_id=tower_id,
                    client_hardware=client_hardware,
                    client_antenna=client_antenna,
                    terrain_model=terrain,
                )
                .first()
            )

            if sim is None:
                missing.append(f"{terrain} (not found)")
            elif sim.status != "completed":
                missing.append(f"{terrain} (status: {sim.status})")
            elif sim.geotiff is None:
                missing.append(f"{terrain} (no GeoTIFF data)")
            else:
                blobs[terrain] = sim.geotiff

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
    with db_session() as session:
        return get_matrix_config(session)


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

    with db_session() as session:
        set_matrix_config(session, body)

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
    with db_session() as session:
        if body and body.tower_ids:
            # Validate that all requested tower IDs actually exist
            existing = session.query(Tower.id).filter(Tower.id.in_(body.tower_ids)).all()
            existing_ids = {r.id for r in existing}
            missing = [tid for tid in body.tower_ids if tid not in existing_ids]
            if missing:
                raise HTTPException(status_code=404, detail=f"Tower(s) not found: {', '.join(missing)}")
            tower_ids: list[str] = body.tower_ids
        else:
            tower_ids = [r.id for r in session.query(Tower.id).all()]

        if len(tower_ids) < 2:
            raise HTTPException(status_code=400, detail="Need at least 2 towers for path analysis")

        pairs: list[tuple[str, str]] = []
        for i, a in enumerate(tower_ids):
            for b in tower_ids[i + 1 :]:
                pairs.append((a, b))

        created_paths: list[CreatedPathResponse] = []
        for tower_a_id, tower_b_id in pairs:
            session.query(TowerPath).filter(
                or_(
                    (TowerPath.tower_a_id == tower_a_id) & (TowerPath.tower_b_id == tower_b_id),
                    (TowerPath.tower_a_id == tower_b_id) & (TowerPath.tower_b_id == tower_a_id),
                )
            ).delete(synchronize_session=False)

            path_id = str(uuid4())
            session.add(TowerPath(id=path_id, tower_a_id=tower_a_id, tower_b_id=tower_b_id))
            created_paths.append(CreatedPathResponse(id=path_id, tower_a_id=tower_a_id, tower_b_id=tower_b_id))
            background_tasks.add_task(run_tower_path_analysis, tower_a_id, tower_b_id, path_id)

        session.commit()

    return ComputePathsResponse(paths=created_paths, count=len(created_paths))


@app.get("/tower-paths", response_model=TowerPathListResponse)
async def list_tower_paths() -> TowerPathListResponse:
    """Return all computed tower paths (public endpoint for visitors)."""
    with db_session() as session:
        rows = session.query(TowerPath).options(joinedload(TowerPath.tower_a), joinedload(TowerPath.tower_b)).all()

        paths = []
        for tp in rows:
            pa = tp.tower_a.params
            pb = tp.tower_b.params
            paths.append(
                TowerPathResponse(
                    id=tp.id,
                    tower_a_id=tp.tower_a_id,
                    tower_b_id=tp.tower_b_id,
                    lat_a=pa.get("lat", 0),
                    lon_a=pa.get("lon", 0),
                    lat_b=pb.get("lat", 0),
                    lon_b=pb.get("lon", 0),
                    path_loss_db=tp.path_loss_db,
                    has_los=bool(tp.has_los) if tp.has_los is not None else None,
                    distance_km=tp.distance_km,
                    created_at=tp.created_at,
                )
            )
    return TowerPathListResponse(paths=paths)


@app.delete("/tower-paths/{path_id}", dependencies=[Depends(require_admin)])
async def delete_tower_path(path_id: str) -> DeleteResponse:
    """Delete a specific tower path."""
    return _delete_row(TowerPath, path_id, "Path")


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
    with db_session() as session:
        geotiff_blobs = [t.geotiff for t in session.query(Tower.geotiff).filter(Tower.geotiff.isnot(None)).all()]

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
