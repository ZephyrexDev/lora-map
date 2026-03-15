"""Tests for the db_connection context manager."""

import sqlite3

from app.db.connection import db_connection


class TestDbConnection:
    def test_yields_connection(self, tmp_path):
        db_file = tmp_path / "cm.db"
        with db_connection(str(db_file)) as conn:
            assert isinstance(conn, sqlite3.Connection)

    def test_closes_connection_on_exit(self, tmp_path):
        db_file = tmp_path / "cm.db"
        with db_connection(str(db_file)) as conn:
            pass
        # After exiting, the connection should be closed.
        # Attempting to use it raises ProgrammingError.
        try:
            conn.execute("SELECT 1")
            closed = False
        except Exception:
            closed = True
        assert closed

    def test_closes_connection_on_exception(self, tmp_path):
        db_file = tmp_path / "cm.db"
        try:
            with db_connection(str(db_file)) as conn:
                raise ValueError("boom")
        except ValueError:
            pass
        try:
            conn.execute("SELECT 1")
            closed = False
        except Exception:
            closed = True
        assert closed

    def test_propagates_exception(self, tmp_path):
        db_file = tmp_path / "cm.db"
        with db_connection(str(db_file)) as conn:
            conn.execute("CREATE TABLE t (id INTEGER)")
            conn.execute("INSERT INTO t VALUES (1)")
            conn.commit()

        # Verify data persists through context manager
        with db_connection(str(db_file)) as conn:
            row = conn.execute("SELECT id FROM t").fetchone()
            assert row[0] == 1
