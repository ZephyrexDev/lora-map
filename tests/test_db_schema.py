"""Tests for app.db.schema — schema definitions and database initialization."""

import sqlite3

from app.db.schema import (
    ALL_SCHEMAS,
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


class TestAllSchemas:
    def test_has_four_entries(self):
        assert len(ALL_SCHEMAS) == 4


class TestInitDb:
    def test_creates_database_with_all_tables(self, tmp_path):
        db_file = tmp_path / "test.db"
        init_db(db_file)

        assert db_file.exists()

        conn = sqlite3.connect(str(db_file))
        try:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
            )
            tables = sorted(row[0] for row in cursor.fetchall())
            assert tables == ["settings", "tasks", "tower_paths", "towers"]
        finally:
            conn.close()
