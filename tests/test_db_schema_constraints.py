"""Tests for SQLite schema constraints, foreign keys, and idempotency."""

import sqlite3

import pytest

from app.db.connection import get_db
from app.db.schema import init_db


@pytest.fixture()
def db(tmp_path):
    db_file = tmp_path / "test.db"
    init_db(db_file)
    conn = get_db(str(db_file))
    yield conn
    conn.close()


class TestTowersTableConstraints:
    def test_id_is_primary_key(self, db):
        db.execute("INSERT INTO towers (id, name, params) VALUES ('t1', 'A', '{}')")
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("INSERT INTO towers (id, name, params) VALUES ('t1', 'B', '{}')")

    def test_name_not_null(self, db):
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("INSERT INTO towers (id, name, params) VALUES ('t1', NULL, '{}')")

    def test_params_not_null(self, db):
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("INSERT INTO towers (id, name, params) VALUES ('t1', 'A', NULL)")

    def test_created_at_has_default(self, db):
        db.execute("INSERT INTO towers (id, name, params) VALUES ('t1', 'A', '{}')")
        row = db.execute("SELECT created_at FROM towers WHERE id = 't1'").fetchone()
        assert row["created_at"] is not None

    def test_geotiff_nullable(self, db):
        db.execute("INSERT INTO towers (id, name, params) VALUES ('t1', 'A', '{}')")
        row = db.execute("SELECT geotiff FROM towers WHERE id = 't1'").fetchone()
        assert row["geotiff"] is None


class TestTasksTableConstraints:
    def test_task_requires_valid_tower_id(self, db):
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO tasks (id, tower_id, status) VALUES ('k1', 'nonexistent', 'processing')"
            )
            db.commit()

    def test_cascade_delete(self, db):
        db.execute("INSERT INTO towers (id, name, params) VALUES ('t1', 'A', '{}')")
        db.execute("INSERT INTO tasks (id, tower_id, status) VALUES ('k1', 't1', 'processing')")
        db.commit()

        db.execute("DELETE FROM towers WHERE id = 't1'")
        db.commit()

        row = db.execute("SELECT * FROM tasks WHERE id = 'k1'").fetchone()
        assert row is None

    def test_status_defaults_to_processing(self, db):
        db.execute("INSERT INTO towers (id, name, params) VALUES ('t1', 'A', '{}')")
        db.execute("INSERT INTO tasks (id, tower_id) VALUES ('k1', 't1')")
        row = db.execute("SELECT status FROM tasks WHERE id = 'k1'").fetchone()
        assert row["status"] == "processing"


class TestTowerPathsConstraints:
    def test_unique_pair(self, db):
        db.execute("INSERT INTO towers (id, name, params) VALUES ('t1', 'A', '{}')")
        db.execute("INSERT INTO towers (id, name, params) VALUES ('t2', 'B', '{}')")
        db.execute(
            "INSERT INTO tower_paths (id, tower_a_id, tower_b_id) VALUES ('p1', 't1', 't2')"
        )
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO tower_paths (id, tower_a_id, tower_b_id) VALUES ('p2', 't1', 't2')"
            )

    def test_cascade_delete_tower_a(self, db):
        db.execute("INSERT INTO towers (id, name, params) VALUES ('t1', 'A', '{}')")
        db.execute("INSERT INTO towers (id, name, params) VALUES ('t2', 'B', '{}')")
        db.execute(
            "INSERT INTO tower_paths (id, tower_a_id, tower_b_id) VALUES ('p1', 't1', 't2')"
        )
        db.commit()

        db.execute("DELETE FROM towers WHERE id = 't1'")
        db.commit()

        row = db.execute("SELECT * FROM tower_paths WHERE id = 'p1'").fetchone()
        assert row is None

    def test_cascade_delete_tower_b(self, db):
        db.execute("INSERT INTO towers (id, name, params) VALUES ('t1', 'A', '{}')")
        db.execute("INSERT INTO towers (id, name, params) VALUES ('t2', 'B', '{}')")
        db.execute(
            "INSERT INTO tower_paths (id, tower_a_id, tower_b_id) VALUES ('p1', 't1', 't2')"
        )
        db.commit()

        db.execute("DELETE FROM towers WHERE id = 't2'")
        db.commit()

        row = db.execute("SELECT * FROM tower_paths WHERE id = 'p1'").fetchone()
        assert row is None


class TestInitDbIdempotent:
    def test_can_run_twice_without_error(self, tmp_path):
        db_file = tmp_path / "idempotent.db"
        init_db(db_file)
        init_db(db_file)  # Should not raise

        conn = sqlite3.connect(str(db_file))
        try:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
            table_names = sorted(row[0] for row in tables)
            assert table_names == ["tasks", "tower_paths", "towers"]
        finally:
            conn.close()
