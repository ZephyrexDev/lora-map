"""Tests for app.db.schema — schema definitions and database initialization."""

import sqlite3

from app.db.schema import (
    MIGRATIONS,
    SCHEMA_TASKS,
    SCHEMA_TOWER_PATHS,
    SCHEMA_TOWERS,
    init_db,
)


class TestSchemaTowers:
    def test_contains_create_table(self):
        assert "CREATE TABLE" in SCHEMA_TOWERS


class TestSchemaTasks:
    def test_contains_tower_id(self):
        assert "tower_id" in SCHEMA_TASKS

    def test_references_towers(self):
        assert "REFERENCES towers" in SCHEMA_TASKS


class TestSchemaTowerPaths:
    def test_contains_tower_a_id(self):
        assert "tower_a_id" in SCHEMA_TOWER_PATHS

    def test_contains_tower_b_id(self):
        assert "tower_b_id" in SCHEMA_TOWER_PATHS


class TestMigrations:
    def test_has_at_least_one_migration(self):
        assert len(MIGRATIONS) >= 1

    def test_first_migration_creates_all_tables(self):
        _version, statements = MIGRATIONS[0]
        all_sql = " ".join(statements)
        for table in ("towers", "tasks", "tower_paths", "settings", "simulations"):
            assert table in all_sql


class TestInitDb:
    def test_creates_database_with_all_tables(self, tmp_path):
        db_file = tmp_path / "test.db"
        init_db(db_file)

        assert db_file.exists()

        conn = sqlite3.connect(str(db_file))
        try:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
            tables = sorted(row[0] for row in cursor.fetchall())
            assert tables == ["schema_version", "settings", "simulations", "tasks", "tower_paths", "towers"]
        finally:
            conn.close()

    def test_idempotent_init(self, tmp_path):
        """Running init_db twice should not fail or duplicate migrations."""
        db_file = tmp_path / "test.db"
        init_db(db_file)
        init_db(db_file)

        conn = sqlite3.connect(str(db_file))
        try:
            versions = conn.execute("SELECT version FROM schema_version").fetchall()
            assert len(versions) == len(MIGRATIONS)
        finally:
            conn.close()
