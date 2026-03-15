"""Tests for the tower-paths API endpoints in app.main."""

import pytest

pytestmark = pytest.mark.slow

from uuid import uuid4

from app.db import db_connection
from tests.conftest import insert_tower


class TestGetTowerPaths:
    def test_returns_empty_list_when_no_paths(self, client):
        resp = client.get("/tower-paths")
        assert resp.status_code == 200
        assert resp.json() == {"paths": []}

    def test_returns_paths_with_expected_fields(self, client):
        t1 = insert_tower(name="Tower A")
        t2 = insert_tower(name="Tower B")
        path_id = str(uuid4())
        with db_connection() as conn:
            conn.execute(
                "INSERT INTO tower_paths (id, tower_a_id, tower_b_id, path_loss_db, has_los, distance_km) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (path_id, t1, t2, 120.5, 1, 15.3),
            )
            conn.commit()

        resp = client.get("/tower-paths")
        assert resp.status_code == 200
        paths = resp.json()["paths"]
        assert len(paths) == 1
        path = paths[0]
        assert path["id"] == path_id
        assert path["tower_a_id"] == t1
        assert path["tower_b_id"] == t2
        assert path["path_loss_db"] == 120.5
        assert path["has_los"] is True
        assert path["distance_km"] == 15.3
        assert "lat_a" in path
        assert "lon_a" in path
        assert "lat_b" in path
        assert "lon_b" in path


class TestPostTowerPaths:
    def test_requires_at_least_two_towers(self, client):
        insert_tower()
        resp = client.post("/tower-paths")
        assert resp.status_code == 400

    def test_creates_paths_for_tower_pair(self, client):
        t1 = insert_tower(name="Tower A")
        t2 = insert_tower(name="Tower B")
        resp = client.post("/tower-paths")
        assert resp.status_code == 202
        body = resp.json()
        assert body["count"] == 1
        assert len(body["paths"]) == 1
        assert body["paths"][0]["tower_a_id"] == t1
        assert body["paths"][0]["tower_b_id"] == t2

    def test_creates_correct_pair_count(self, client):
        for i in range(4):
            insert_tower(name=f"Tower {i}")
        resp = client.post("/tower-paths")
        assert resp.status_code == 202
        # 4 towers = 6 pairs (4 choose 2)
        assert resp.json()["count"] == 6

    def test_accepts_subset_of_tower_ids(self, client):
        t1 = insert_tower(name="Tower A")
        t2 = insert_tower(name="Tower B")
        insert_tower(name="Tower C")
        resp = client.post("/tower-paths", json={"tower_ids": [t1, t2]})
        assert resp.status_code == 202
        assert resp.json()["count"] == 1


class TestDeleteTowerPath:
    def test_returns_404_for_unknown_path(self, client):
        resp = client.delete(f"/tower-paths/{uuid4()}")
        assert resp.status_code == 404

    def test_deletes_existing_path(self, client):
        t1 = insert_tower(name="Tower A")
        t2 = insert_tower(name="Tower B")
        path_id = str(uuid4())
        with db_connection() as conn:
            conn.execute(
                "INSERT INTO tower_paths (id, tower_a_id, tower_b_id) VALUES (?, ?, ?)",
                (path_id, t1, t2),
            )
            conn.commit()

        resp = client.delete(f"/tower-paths/{path_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert "deleted" in body["message"].lower()
        assert body["id"] == path_id

        with db_connection() as conn:
            assert conn.execute("SELECT * FROM tower_paths WHERE id = ?", (path_id,)).fetchone() is None


class TestTowerDeletionCascade:
    def test_deleting_tower_removes_its_paths(self, client):
        t1 = insert_tower(name="Tower A")
        t2 = insert_tower(name="Tower B")
        path_id = str(uuid4())
        with db_connection() as conn:
            conn.execute(
                "INSERT INTO tower_paths (id, tower_a_id, tower_b_id) VALUES (?, ?, ?)",
                (path_id, t1, t2),
            )
            conn.commit()

        client.delete(f"/towers/{t1}")

        with db_connection() as conn:
            assert conn.execute("SELECT * FROM tower_paths WHERE id = ?", (path_id,)).fetchone() is None


class TestAutoPathCreation:
    def test_predict_creates_paths_to_existing_towers(self, client, valid_payload):
        # Create first tower via predict
        resp1 = client.post("/predict", json=valid_payload)
        t1 = resp1.json()["tower_id"]

        # Create second tower — should auto-create a path to the first
        resp2 = client.post("/predict", json=valid_payload)
        t2 = resp2.json()["tower_id"]

        with db_connection() as conn:
            paths = conn.execute(
                "SELECT * FROM tower_paths WHERE "
                "(tower_a_id = ? AND tower_b_id = ?) OR (tower_a_id = ? AND tower_b_id = ?)",
                (t1, t2, t2, t1),
            ).fetchall()
            assert len(paths) == 1
