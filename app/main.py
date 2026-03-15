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
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import BackgroundTasks, Depends, FastAPI
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.auth import require_admin, router as auth_router
from app.db import db_connection, init_db
from app.db.connection import DEFAULT_DB_PATH
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
            now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
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
        conn.execute(
            "INSERT INTO towers (id, name, params) VALUES (?, ?, ?)",
            (tower_id, "Unnamed", json.dumps(payload.model_dump())),
        )
        conn.execute(
            "INSERT INTO tasks (id, tower_id, status) VALUES (?, ?, ?)",
            (task_id, tower_id, "processing"),
        )
        conn.commit()

    background_tasks.add_task(run_splat, task_id, tower_id, payload)
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
        row = conn.execute(
            "SELECT status, error FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()

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
        task_row = conn.execute(
            "SELECT tower_id, status, error FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()

        if task_row is None:
            logger.warning("Task %s not found.", task_id)
            return JSONResponse({"error": "Task not found"}, status_code=404)

        status: str = task_row["status"]

        if status == "completed":
            tower_row = conn.execute(
                "SELECT geotiff FROM towers WHERE id = ?", (task_row["tower_id"],)
            ).fetchone()

            if tower_row is None or tower_row["geotiff"] is None:
                logger.error("No GeoTIFF data found for completed task %s.", task_id)
                return JSONResponse({"error": "No result found"}, status_code=500)

            geotiff_file = io.BytesIO(tower_row["geotiff"])
            return StreamingResponse(
                geotiff_file,
                media_type="image/tiff",
                headers={
                    "Content-Disposition": f"attachment; filename={task_id}.tif"
                },
            )

        if status == "failed":
            return JSONResponse(
                {"task_id": task_id, "status": "failed", "error": task_row["error"]}
            )

        logger.info("Task %s is still processing.", task_id)
        return JSONResponse({"task_id": task_id, "status": "processing"})


@app.get("/towers")
async def list_towers() -> JSONResponse:
    """List all towers without their GeoTIFF blobs.

    Returns:
        JSONResponse with a list of tower objects.
    """
    with db_connection() as conn:
        rows = conn.execute(
            "SELECT id, name, params, created_at, updated_at FROM towers"
        ).fetchall()

    towers: list[dict[str, Any]] = [
        {
            "id": row["id"],
            "name": row["name"],
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


app.mount("/", StaticFiles(directory="app/ui", html=True), name="ui")
