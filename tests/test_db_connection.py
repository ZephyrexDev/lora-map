"""Tests for app.db.connection — SQLAlchemy engine and session factory."""

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.connection import db_session, init_engine


class TestInitEngine:
    def test_creates_database_file(self, tmp_path):
        db_file = tmp_path / "conn.db"
        engine = init_engine(str(db_file))
        # SQLite creates the file on first connection, not engine creation
        with engine.connect():
            pass
        assert db_file.exists()

    def test_wal_mode_enabled(self, tmp_path):
        db_file = tmp_path / "wal.db"
        engine = init_engine(str(db_file))
        with engine.connect() as conn:
            result = conn.execute(text("PRAGMA journal_mode")).scalar()
            assert result == "wal"

    def test_foreign_keys_enabled(self, tmp_path):
        db_file = tmp_path / "fk.db"
        engine = init_engine(str(db_file))
        with engine.connect() as conn:
            result = conn.execute(text("PRAGMA foreign_keys")).scalar()
            assert result == 1


class TestDbSession:
    def test_yields_session(self):
        with db_session() as session:
            assert isinstance(session, Session)
