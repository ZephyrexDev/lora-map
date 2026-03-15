"""Tests for the FastAPI endpoints in app.main."""

from uuid import uuid4

from app.db import db_connection
from tests.conftest import insert_task, insert_tower, set_tower_geotiff

# ===========================================================================
# POST /predict
# ===========================================================================


class TestPostPredict:
    def test_returns_201_with_ids(self, client, valid_payload):
        resp = client.post("/predict", json=valid_payload)
        assert resp.status_code == 201
        body = resp.json()
        assert "task_id" in body
        assert "tower_id" in body

    def test_creates_rows_in_towers_and_tasks(self, client, valid_payload):
        resp = client.post("/predict", json=valid_payload)
        body = resp.json()

        with db_connection() as conn:
            tower = conn.execute("SELECT * FROM towers WHERE id = ?", (body["tower_id"],)).fetchone()
            assert tower is not None
            assert tower["name"] == "Unnamed"

            task = conn.execute("SELECT * FROM tasks WHERE id = ?", (body["task_id"],)).fetchone()
            assert task is not None
            assert task["tower_id"] == body["tower_id"]

    def test_assigns_color_to_tower(self, client, valid_payload):
        resp = client.post("/predict", json=valid_payload)
        body = resp.json()
        with db_connection() as conn:
            tower = conn.execute("SELECT color FROM towers WHERE id = ?", (body["tower_id"],)).fetchone()
            assert tower["color"] is not None
            assert tower["color"].startswith("#")

    def test_returns_422_for_missing_payload(self, client):
        resp = client.post("/predict", json={})
        assert resp.status_code == 422

    def test_returns_422_for_invalid_lat(self, client, valid_payload):
        valid_payload["lat"] = 999
        resp = client.post("/predict", json=valid_payload)
        assert resp.status_code == 422


# ===========================================================================
# GET /status/{task_id}
# ===========================================================================


class TestGetStatus:
    def test_returns_404_for_unknown_task(self, client):
        resp = client.get(f"/status/{uuid4()}")
        assert resp.status_code == 404
        assert "error" in resp.json()

    def test_returns_status_for_existing_task(self, client):
        tid = insert_tower()
        kid = insert_task(tower_id=tid)
        resp = client.get(f"/status/{kid}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "processing"

    def test_failed_task_includes_error(self, client):
        tid = insert_tower()
        kid = insert_task(tower_id=tid, status="failed", error="Tile download failed")
        body = client.get(f"/status/{kid}").json()
        assert body["status"] == "failed"
        assert body["error"] == "Tile download failed"

    def test_completed_task_has_no_error_key(self, client):
        tid = insert_tower()
        kid = insert_task(tower_id=tid, status="completed")
        body = client.get(f"/status/{kid}").json()
        assert body["status"] == "completed"
        assert "error" not in body


# ===========================================================================
# GET /result/{task_id}
# ===========================================================================


class TestGetResult:
    def test_returns_404_for_unknown_task(self, client):
        resp = client.get(f"/result/{uuid4()}")
        assert resp.status_code == 404

    def test_returns_processing_for_in_progress_task(self, client):
        tid = insert_tower()
        kid = insert_task(tower_id=tid)
        body = client.get(f"/result/{kid}").json()
        assert body["status"] == "processing"

    def test_returns_geotiff_for_completed_task(self, client):
        tid = insert_tower()
        kid = insert_task(tower_id=tid, status="completed")
        fake_tiff = b"FAKE_GEOTIFF_DATA_1234567890"
        set_tower_geotiff(tid, fake_tiff)

        resp = client.get(f"/result/{kid}")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/tiff"
        assert kid in resp.headers["content-disposition"]
        assert resp.content == fake_tiff

    def test_failed_task_returns_error(self, client):
        tid = insert_tower()
        kid = insert_task(tower_id=tid, status="failed", error="SPLAT! crashed")
        body = client.get(f"/result/{kid}").json()
        assert body["status"] == "failed"
        assert "SPLAT! crashed" in body["error"]

    def test_completed_task_missing_geotiff_returns_500(self, client):
        tid = insert_tower()
        kid = insert_task(tower_id=tid, status="completed")
        resp = client.get(f"/result/{kid}")
        assert resp.status_code == 500


# ===========================================================================
# GET /towers
# ===========================================================================


class TestGetTowers:
    def test_returns_empty_list_when_no_towers(self, client):
        resp = client.get("/towers")
        assert resp.json() == {"towers": []}

    def test_returns_towers_with_expected_fields(self, client, valid_payload):
        r1 = client.post("/predict", json=valid_payload)
        r2 = client.post("/predict", json=valid_payload)
        tower_ids = {r1.json()["tower_id"], r2.json()["tower_id"]}

        towers = client.get("/towers").json()["towers"]
        assert len(towers) == 2
        assert {t["id"] for t in towers} == tower_ids

        for t in towers:
            assert "geotiff" not in t
            assert "params" in t
            assert "color" in t
            assert "created_at" in t


# ===========================================================================
# DELETE /towers/{tower_id}
# ===========================================================================


class TestDeleteTower:
    def test_returns_404_for_unknown_tower(self, client):
        resp = client.delete(f"/towers/{uuid4()}")
        assert resp.status_code == 404

    def test_deletes_existing_tower(self, client, valid_payload):
        tower_id = client.post("/predict", json=valid_payload).json()["tower_id"]
        resp = client.delete(f"/towers/{tower_id}")
        assert resp.status_code == 200
        assert "deleted" in resp.json()["message"].lower()

        with db_connection() as conn:
            assert conn.execute("SELECT * FROM towers WHERE id = ?", (tower_id,)).fetchone() is None

    def test_cascades_delete_to_tasks(self, client, valid_payload):
        body = client.post("/predict", json=valid_payload).json()
        client.delete(f"/towers/{body['tower_id']}")

        with db_connection() as conn:
            assert conn.execute("SELECT * FROM tasks WHERE id = ?", (body["task_id"],)).fetchone() is None

    def test_double_delete_returns_404(self, client):
        tid = insert_tower()
        assert client.delete(f"/towers/{tid}").status_code == 200
        assert client.delete(f"/towers/{tid}").status_code == 404
