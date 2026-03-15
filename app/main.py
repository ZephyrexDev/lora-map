"""
Signal Coverage Prediction API

Provides endpoints to predict radio signal coverage
using the ITM (Irregular Terrain Model) via SPLAT! (https://github.com/jmcmellen/splat).

Data is persisted to a local SQLite database.

Endpoints:
    - POST /predict: Accepts a signal coverage prediction request and starts a background task.
    - GET /status/{task_id}: Retrieves the status of a given prediction task.
    - GET /result/{task_id}: Retrieves the result (GeoTIFF file) of a given prediction task.
    - GET /towers: Lists all towers.
    - DELETE /towers/{tower_id}: Deletes a tower and its associated tasks.
"""

import io
import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import BackgroundTasks, Depends, FastAPI, Query
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.auth import require_admin
from app.auth import router as auth_router
from app.colors import next_tower_color
from app.db import db_connection, init_db
from app.db.connection import DEFAULT_DB_PATH
from app.matrix import (
    ANTENNA_RX_PARAMS,
    HARDWARE_RX_PARAMS,
    get_matrix_combinations,
    get_matrix_config,
    set_matrix_config,
)
from app.models.CoveragePredictionRequest import CoveragePredictionRequest
from app.services.splat import Splat

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

splat_service = Splat(splat_path=os.environ.get("SPLAT_PATH", "/app/splat"))


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Initialize the SQLite database on startup."""
    db_path = os.environ.get("DB_PATH", DEFAULT_DB_PATH)
    init_db(db_path)
    logger.info("Database initialized at %s.", db_path)
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(auth_router)


def run_splat(task_id: str, tower_id: str, request: CoveragePredictionRequest) -> None:
    """Execute the SPLAT! coverage prediction and persist results to SQLite.

    Args:
        task_id: UUID identifier for the task.
        tower_id: UUID identifier for the tower.
        request: The parameters for the SPLAT! prediction.
    """
    try:
        logger.info("Starting SPLAT! coverage prediction for task %s.", task_id)
        geotiff_data: bytes = splat_service.coverage_prediction(request)

        with db_connection() as conn:
            now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
            conn.execute(
                "UPDATE towers SET geotiff = ?, updated_at = ? WHERE id = ?",
                (geotiff_data, now, tower_id),
            )
            conn.execute(
                "UPDATE tasks SET status = ? WHERE id = ?",
                ("completed", task_id),
            )
            conn.commit()
            logger.info("Task %s completed successfully.", task_id)

    except Exception as e:
        logger.error("Error in SPLAT! task %s: %s", task_id, e)
        with db_connection() as conn:
            conn.execute(
                "UPDATE tasks SET status = ?, error = ? WHERE id = ?",
                ("failed", str(e), task_id),
            )
            conn.commit()


def run_matrix_simulations(tower_id: str, payload: CoveragePredictionRequest) -> None:
    """Run all pending matrix simulations for a tower.

    Each pending simulation row is processed independently — a failure in one
    does not prevent the others from completing.
    """
    with db_connection() as conn:
        rows = conn.execute(
            "SELECT id, client_hardware, client_antenna, terrain_model "
            "FROM simulations WHERE tower_id = ? AND status = 'pending'",
            (tower_id,),
        ).fetchall()

    for row in rows:
        sim_id = row["id"]
        hw_key = row["client_hardware"]
        ant_key = row["client_antenna"]
        terrain_key = row["terrain_model"]

        try:
            overrides: dict[str, Any] = {"terrain_model": terrain_key}
            hw_params = HARDWARE_RX_PARAMS.get(hw_key, {})
            ant_params = ANTENNA_RX_PARAMS.get(ant_key, {})

            if "rx_sensitivity" in hw_params:
                overrides["signal_threshold"] = hw_params["rx_sensitivity"]
            if "rx_gain" in ant_params:
                overrides["rx_gain"] = ant_params["rx_gain"]
            if "swr" in ant_params:
                overrides["swr"] = ant_params["swr"]

            modified_request = payload.model_copy(update=overrides)
            geotiff_data: bytes = splat_service.coverage_prediction(modified_request)

            with db_connection() as conn:
                conn.execute(
                    "UPDATE simulations SET geotiff = ?, status = 'completed' WHERE id = ?",
                    (geotiff_data, sim_id),
                )
                conn.commit()
                logger.info("Simulation %s completed.", sim_id)

        except Exception as e:
            logger.error("Simulation %s failed: %s", sim_id, e)
            with db_connection() as conn:
                conn.execute(
                    "UPDATE simulations SET status = 'failed', error = ? WHERE id = ?",
                    (str(e), sim_id),
                )
                conn.commit()


@app.post("/predict", dependencies=[Depends(require_admin)])
async def predict(
    payload: CoveragePredictionRequest,
    background_tasks: BackgroundTasks,
) -> JSONResponse:
    """Submit a signal coverage prediction request.

    Generates unique tower and task identifiers, persists initial rows to
    SQLite, and queues the SPLAT! computation as a background task.

    Args:
        payload: The parameters required for the SPLAT! coverage prediction.
        background_tasks: FastAPI background tasks.

    Returns:
        JSONResponse containing the task_id and tower_id.
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

        # Create simulation rows for each matrix combination
        config = get_matrix_config(conn)
        combinations = get_matrix_combinations(config)
        for combo in combinations:
            sim_id = str(uuid4())
            conn.execute(
                "INSERT INTO simulations (id, tower_id, client_hardware, client_antenna, terrain_model) "
                "VALUES (?, ?, ?, ?, ?)",
                (sim_id, tower_id, combo["hardware"], combo["antenna"], combo["terrain"]),
            )

        conn.commit()

    background_tasks.add_task(run_splat, task_id, tower_id, payload)
    background_tasks.add_task(run_matrix_simulations, tower_id, payload)
    return JSONResponse({"task_id": task_id, "tower_id": tower_id})


@app.get("/status/{task_id}")
async def get_status(task_id: str) -> JSONResponse:
    """Retrieve the status of a prediction task from SQLite.

    Args:
        task_id: The unique identifier for the task.

    Returns:
        JSONResponse with the task status, or 404 if not found.
    """
    with db_connection() as conn:
        row = conn.execute("SELECT status, error FROM tasks WHERE id = ?", (task_id,)).fetchone()

    if row is None:
        logger.warning("Task %s not found.", task_id)
        return JSONResponse({"error": "Task not found"}, status_code=404)

    response: dict[str, Any] = {"task_id": task_id, "status": row["status"]}
    if row["status"] == "failed" and row["error"]:
        response["error"] = row["error"]

    return JSONResponse(response)


@app.get("/result/{task_id}", response_model=None)
async def get_result(task_id: str) -> JSONResponse | StreamingResponse:
    """Retrieve the result of a prediction task.

    If the task has completed, returns the GeoTIFF as a downloadable file.
    If it is still processing or has failed, returns the current status.

    Args:
        task_id: The unique identifier for the task.

    Returns:
        StreamingResponse with the GeoTIFF on success, or JSONResponse with status.
    """
    with db_connection() as conn:
        task_row = conn.execute("SELECT tower_id, status, error FROM tasks WHERE id = ?", (task_id,)).fetchone()

        if task_row is None:
            logger.warning("Task %s not found.", task_id)
            return JSONResponse({"error": "Task not found"}, status_code=404)

        status: str = task_row["status"]

        if status == "completed":
            tower_row = conn.execute("SELECT geotiff FROM towers WHERE id = ?", (task_row["tower_id"],)).fetchone()

            if tower_row is None or tower_row["geotiff"] is None:
                logger.error("No GeoTIFF data found for completed task %s.", task_id)
                return JSONResponse({"error": "No result found"}, status_code=500)

            geotiff_file = io.BytesIO(tower_row["geotiff"])
            return StreamingResponse(
                geotiff_file,
                media_type="image/tiff",
                headers={"Content-Disposition": f"attachment; filename={task_id}.tif"},
            )

        if status == "failed":
            return JSONResponse({"task_id": task_id, "status": "failed", "error": task_row["error"]})

        logger.info("Task %s is still processing.", task_id)
        return JSONResponse({"task_id": task_id, "status": "processing"})


@app.get("/towers")
async def list_towers() -> JSONResponse:
    """List all towers without their GeoTIFF blobs.

    Returns:
        JSONResponse with a list of tower objects.
    """
    with db_connection() as conn:
        rows = conn.execute("SELECT id, name, color, params, created_at, updated_at FROM towers").fetchall()

    towers: list[dict[str, Any]] = [
        {
            "id": row["id"],
            "name": row["name"],
            "color": row["color"],
            "params": json.loads(row["params"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
        for row in rows
    ]
    return JSONResponse({"towers": towers})


@app.delete("/towers/{tower_id}", dependencies=[Depends(require_admin)])
async def delete_tower(tower_id: str) -> JSONResponse:
    """Delete a tower and its associated tasks (via CASCADE).

    Args:
        tower_id: The unique identifier for the tower.

    Returns:
        JSONResponse confirming deletion or 404 if not found.
    """
    with db_connection() as conn:
        cursor = conn.execute("DELETE FROM towers WHERE id = ?", (tower_id,))
        conn.commit()

    if cursor.rowcount == 0:
        return JSONResponse({"error": "Tower not found"}, status_code=404)

    logger.info("Tower %s deleted.", tower_id)
    return JSONResponse({"message": "Tower deleted", "tower_id": tower_id})


# ---------------------------------------------------------------------------
# Simulation endpoints
# ---------------------------------------------------------------------------


@app.get("/towers/{tower_id}/simulations")
async def list_tower_simulations(
    tower_id: str,
    enabled_only: bool = Query(False, description="Filter to only simulations matching enabled matrix config members"),
) -> JSONResponse:
    """Return all simulations for a tower (without GeoTIFF blobs).

    When ``enabled_only=true``, only simulations whose hardware, antenna, and
    terrain values are all currently enabled in the matrix config are returned.

    Args:
        tower_id: The unique identifier for the tower.
        enabled_only: If true, filter by current matrix config enabled members.

    Returns:
        JSONResponse with a list of simulation objects.
    """
    with db_connection() as conn:
        rows = conn.execute(
            "SELECT id, client_hardware, client_antenna, terrain_model, status, created_at "
            "FROM simulations WHERE tower_id = ?",
            (tower_id,),
        ).fetchall()

        if enabled_only:
            config = get_matrix_config(conn)
            enabled_hw = set(config.get("hardware", []))
            enabled_ant = set(config.get("antennas", []))
            enabled_ter = set(config.get("terrain", []))
            rows = [
                r for r in rows
                if r["client_hardware"] in enabled_hw
                and r["client_antenna"] in enabled_ant
                and r["terrain_model"] in enabled_ter
            ]

    simulations = [
        {
            "id": row["id"],
            "client_hardware": row["client_hardware"],
            "client_antenna": row["client_antenna"],
            "terrain_model": row["terrain_model"],
            "status": row["status"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]
    return JSONResponse({"simulations": simulations})


@app.get("/simulations/{sim_id}/result", response_model=None)
async def get_simulation_result(sim_id: str) -> JSONResponse | StreamingResponse:
    """Return the GeoTIFF result for a completed simulation.

    Args:
        sim_id: The unique identifier for the simulation.

    Returns:
        StreamingResponse with the GeoTIFF on success, or JSONResponse with status/error.
    """
    with db_connection() as conn:
        row = conn.execute(
            "SELECT status, geotiff, error FROM simulations WHERE id = ?",
            (sim_id,),
        ).fetchone()

    if row is None:
        return JSONResponse({"error": "Simulation not found"}, status_code=404)

    if row["status"] == "completed":
        if row["geotiff"] is None:
            return JSONResponse({"error": "No result found"}, status_code=500)
        geotiff_file = io.BytesIO(row["geotiff"])
        return StreamingResponse(
            geotiff_file,
            media_type="image/tiff",
            headers={"Content-Disposition": f"attachment; filename={sim_id}.tif"},
        )

    if row["status"] == "failed":
        return JSONResponse({"sim_id": sim_id, "status": "failed", "error": row["error"]})

    return JSONResponse({"sim_id": sim_id, "status": row["status"]})


# ---------------------------------------------------------------------------
# Matrix config endpoints
# ---------------------------------------------------------------------------

# Known valid values for matrix axes (used for validation on PUT).
_KNOWN_HARDWARE = {"v3", "v4", "custom"}
_KNOWN_ANTENNAS = {
    "ribbed_spring_helical",
    "duck_stubby",
    "bingfu_whip",
    "slinkdsco_omni",
}
_KNOWN_TERRAIN = {"bare_earth", "dsm", "lulc_clutter"}


@app.get("/matrix/config")
async def get_matrix_config_endpoint() -> JSONResponse:
    """Return the current matrix configuration."""
    with db_connection() as conn:
        config = get_matrix_config(conn)
    return JSONResponse(config)


@app.put("/matrix/config", dependencies=[Depends(require_admin)])
async def put_matrix_config_endpoint(
    body: dict[str, Any],
) -> JSONResponse:
    """Update the matrix configuration (admin-only).

    Accepts a JSON body with keys ``hardware``, ``antennas``, and ``terrain``,
    each mapping to a list of string identifiers.  All values must be from
    the known presets.
    """
    errors: list[str] = []
    for key, known in [
        ("hardware", _KNOWN_HARDWARE),
        ("antennas", _KNOWN_ANTENNAS),
        ("terrain", _KNOWN_TERRAIN),
    ]:
        if key not in body:
            errors.append(f"Missing required key: {key}")
            continue
        if not isinstance(body[key], list):
            errors.append(f"{key} must be a list")
            continue
        unknown = set(body[key]) - known
        if unknown:
            errors.append(f"Unknown {key} values: {sorted(unknown)}")

    if errors:
        return JSONResponse({"errors": errors}, status_code=400)

    config = {
        "hardware": body["hardware"],
        "antennas": body["antennas"],
        "terrain": body["terrain"],
    }

    with db_connection() as conn:
        set_matrix_config(conn, config)

    return JSONResponse(config)


app.mount("/", StaticFiles(directory="app/ui", html=True), name="ui")
