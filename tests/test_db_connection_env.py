"""Tests for get_db() environment variable fallback behavior."""

import os
import sqlite3
from unittest.mock import patch

from app.db.connection import DEFAULT_DB_PATH, get_db


class TestGetDbEnvFallback:
    def test_uses_db_path_env_when_no_arg(self, tmp_path):
        db_file = tmp_path / "env.db"
        with patch.dict(os.environ, {"DB_PATH": str(db_file)}):
            conn = get_db()
            try:
                assert isinstance(conn, sqlite3.Connection)
                assert db_file.exists()
            finally:
                conn.close()

    def test_explicit_arg_overrides_env(self, tmp_path):
        env_file = tmp_path / "env.db"
        explicit_file = tmp_path / "explicit.db"
        with patch.dict(os.environ, {"DB_PATH": str(env_file)}):
            conn = get_db(str(explicit_file))
            try:
                assert explicit_file.exists()
                # env_file should NOT be created since explicit arg takes priority
                assert not env_file.exists()
            finally:
                conn.close()

    def test_default_path_constant(self):
        assert DEFAULT_DB_PATH == "/data/lora-planner.db"
