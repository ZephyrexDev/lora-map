"""Tests for init_engine environment variable fallback behavior."""

from app.db.connection import DEFAULT_DB_PATH, init_engine


class TestInitEngineEnvFallback:
    def test_uses_explicit_path(self, tmp_path):
        db_file = tmp_path / "explicit.db"
        engine = init_engine(str(db_file))
        with engine.connect():
            pass
        assert db_file.exists()

    def test_uses_db_path_env_when_no_arg(self, tmp_path, monkeypatch):
        db_file = tmp_path / "env.db"
        monkeypatch.setenv("DB_PATH", str(db_file))
        engine = init_engine()
        with engine.connect():
            pass
        assert db_file.exists()

    def test_explicit_arg_overrides_env(self, tmp_path, monkeypatch):
        env_file = tmp_path / "env.db"
        explicit_file = tmp_path / "explicit.db"
        monkeypatch.setenv("DB_PATH", str(env_file))
        engine = init_engine(str(explicit_file))
        with engine.connect():
            pass
        assert explicit_file.exists()
        assert not env_file.exists()

    def test_default_path_constant(self):
        assert DEFAULT_DB_PATH == "/data/lora-planner.db"
