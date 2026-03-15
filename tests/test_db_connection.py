"""Tests for app.db.connection — SQLite connection factory."""

import sqlite3

from app.db.connection import get_db


class TestGetDb:
    def test_returns_sqlite3_connection(self, tmp_path):
        db_file = tmp_path / "conn.db"
        conn = get_db(str(db_file))
        try:
            assert isinstance(conn, sqlite3.Connection)
        finally:
            conn.close()

    def test_explicit_path_is_used(self, tmp_path):
        db_file = tmp_path / "explicit.db"
        conn = get_db(str(db_file))
        try:
            assert db_file.exists()
        finally:
            conn.close()

    def test_row_factory_is_sqlite3_row(self, tmp_path):
        db_file = tmp_path / "row.db"
        conn = get_db(str(db_file))
        try:
            assert conn.row_factory is sqlite3.Row
        finally:
            conn.close()

    def test_wal_mode_enabled(self, tmp_path):
        db_file = tmp_path / "wal.db"
        conn = get_db(str(db_file))
        try:
            result = conn.execute("PRAGMA journal_mode;").fetchone()
            assert result[0] == "wal"
        finally:
            conn.close()

    def test_foreign_keys_enabled(self, tmp_path):
        db_file = tmp_path / "fk.db"
        conn = get_db(str(db_file))
        try:
            result = conn.execute("PRAGMA foreign_keys;").fetchone()
            assert result[0] == 1
        finally:
            conn.close()
