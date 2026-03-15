"""Tests for admin authentication in app.auth and protected endpoints."""

import json
import os
import tempfile
from unittest.mock import patch
from uuid import uuid4

import pytest


# ---------------------------------------------------------------------------
# Database setup (must happen before app import)
# ---------------------------------------------------------------------------

# Reuse an existing DB_PATH if another test module already set one; otherwise
# create a fresh temp file.  This avoids overwriting the env var when pytest
# collects multiple test modules in the same process.
if "DB_PATH" in os.environ:
    _tmp_db_path = os.environ["DB_PATH"]
else:
    _tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    _tmp_db_path = _tmp_db.name
    _tmp_db.close()
    os.environ["DB_PATH"] = _tmp_db_path

# Patch Splat so the real binary isn't required in tests.
with patch("app.services.splat.Splat.__init__", lambda self, **kw: None):
    from fastapi.testclient import TestClient

    from app.db import get_db, init_db
    from app.main import app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_db():
    """Re-initialize and wipe the database before every test."""
    init_db(_tmp_db_path)
    conn = get_db()
    try:
        conn.execute("DELETE FROM tasks")
        conn.execute("DELETE FROM tower_paths")
        conn.execute("DELETE FROM towers")
        conn.commit()
    finally:
        conn.close()
    yield


@pytest.fixture()
def valid_payload() -> dict:
    return {"lat": 40.0, "lon": -105.0, "tx_power": 20.0}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _insert_tower(tower_id: str) -> None:
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO towers (id, name, params) VALUES (?, ?, ?)",
            (tower_id, "Test", json.dumps({"lat": 0, "lon": 0})),
        )
        conn.commit()
    finally:
        conn.close()


def _insert_task(task_id: str, tower_id: str, status: str = "processing") -> None:
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO tasks (id, tower_id, status) VALUES (?, ?, ?)",
            (task_id, tower_id, status),
        )
        conn.commit()
    finally:
        conn.close()


def _client_no_auth() -> TestClient:
    """Return a TestClient with ADMIN_PASSWORD disabled (None)."""
    import app.auth as auth_mod

    original = auth_mod.ADMIN_PASSWORD
    auth_mod.ADMIN_PASSWORD = None
    client = TestClient(app)
    yield client
    auth_mod.ADMIN_PASSWORD = original


def _client_with_auth(password: str = "s3cret") -> TestClient:
    """Return a TestClient with ADMIN_PASSWORD set."""
    import app.auth as auth_mod

    original = auth_mod.ADMIN_PASSWORD
    auth_mod.ADMIN_PASSWORD = password
    client = TestClient(app)
    yield client
    auth_mod.ADMIN_PASSWORD = original


@pytest.fixture()
def client_no_auth():
    yield from _client_no_auth()


@pytest.fixture()
def client_with_auth():
    yield from _client_with_auth()


AUTH_PASSWORD = "s3cret"


# ===========================================================================
# Auth disabled (ADMIN_PASSWORD unset)
# ===========================================================================

class TestAuthDisabled:
    """When ADMIN_PASSWORD is None, all endpoints should work without auth."""

    def test_post_predict_allowed(self, client_no_auth, valid_payload):
        resp = client_no_auth.post("/predict", json=valid_payload)
        assert resp.status_code == 200

    def test_delete_tower_allowed(self, client_no_auth):
        tower_id = str(uuid4())
        _insert_tower(tower_id)
        resp = client_no_auth.delete(f"/towers/{tower_id}")
        assert resp.status_code == 200

    def test_auth_check_allowed(self, client_no_auth):
        resp = client_no_auth.get("/auth/check")
        assert resp.status_code == 200
        assert resp.json() == {"authenticated": True}

    def test_auth_login_returns_empty_token(self, client_no_auth):
        resp = client_no_auth.post("/auth/login", json={"password": "anything"})
        assert resp.status_code == 200
        assert resp.json() == {"token": ""}


# ===========================================================================
# Auth enabled — protected endpoints reject unauthenticated requests
# ===========================================================================

class TestAuthEnabledRejectsUnauthenticated:
    """With ADMIN_PASSWORD set, protected endpoints must return 401."""

    def test_post_predict_401_without_token(self, client_with_auth, valid_payload):
        resp = client_with_auth.post("/predict", json=valid_payload)
        assert resp.status_code == 401

    def test_post_predict_401_with_wrong_token(self, client_with_auth, valid_payload):
        resp = client_with_auth.post(
            "/predict",
            json=valid_payload,
            headers={"Authorization": "Bearer wrong"},
        )
        assert resp.status_code == 401

    def test_delete_tower_401_without_token(self, client_with_auth):
        tower_id = str(uuid4())
        _insert_tower(tower_id)
        resp = client_with_auth.delete(f"/towers/{tower_id}")
        assert resp.status_code == 401

    def test_auth_check_401_without_token(self, client_with_auth):
        resp = client_with_auth.get("/auth/check")
        assert resp.status_code == 401

    def test_auth_check_401_with_wrong_token(self, client_with_auth):
        resp = client_with_auth.get(
            "/auth/check",
            headers={"Authorization": "Bearer wrong"},
        )
        assert resp.status_code == 401


# ===========================================================================
# Auth enabled — protected endpoints work with correct token
# ===========================================================================

class TestAuthEnabledWithValidToken:
    """With correct Bearer token, protected endpoints should succeed."""

    def test_post_predict_200(self, client_with_auth, valid_payload):
        resp = client_with_auth.post(
            "/predict",
            json=valid_payload,
            headers={"Authorization": f"Bearer {AUTH_PASSWORD}"},
        )
        assert resp.status_code == 200
        assert "task_id" in resp.json()

    def test_delete_tower_200(self, client_with_auth):
        tower_id = str(uuid4())
        _insert_tower(tower_id)
        resp = client_with_auth.delete(
            f"/towers/{tower_id}",
            headers={"Authorization": f"Bearer {AUTH_PASSWORD}"},
        )
        assert resp.status_code == 200

    def test_auth_check_200(self, client_with_auth):
        resp = client_with_auth.get(
            "/auth/check",
            headers={"Authorization": f"Bearer {AUTH_PASSWORD}"},
        )
        assert resp.status_code == 200
        assert resp.json() == {"authenticated": True}


# ===========================================================================
# POST /auth/login
# ===========================================================================

class TestAuthLogin:
    def test_correct_password_returns_token(self, client_with_auth):
        resp = client_with_auth.post(
            "/auth/login", json={"password": AUTH_PASSWORD}
        )
        assert resp.status_code == 200
        assert resp.json() == {"token": AUTH_PASSWORD}

    def test_wrong_password_returns_401(self, client_with_auth):
        resp = client_with_auth.post(
            "/auth/login", json={"password": "wrong"}
        )
        assert resp.status_code == 401

    def test_missing_password_returns_422(self, client_with_auth):
        resp = client_with_auth.post("/auth/login", json={})
        assert resp.status_code == 422


# ===========================================================================
# Public endpoints remain accessible even with auth enabled
# ===========================================================================

class TestPublicEndpointsWithAuth:
    """GET /towers, GET /status, GET /result should never require auth."""

    def test_get_towers_no_auth_needed(self, client_with_auth):
        resp = client_with_auth.get("/towers")
        assert resp.status_code == 200
        assert "towers" in resp.json()

    def test_get_status_no_auth_needed(self, client_with_auth):
        tower_id = str(uuid4())
        task_id = str(uuid4())
        _insert_tower(tower_id)
        _insert_task(task_id, tower_id)

        resp = client_with_auth.get(f"/status/{task_id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "processing"

    def test_get_result_no_auth_needed(self, client_with_auth):
        tower_id = str(uuid4())
        task_id = str(uuid4())
        _insert_tower(tower_id)
        _insert_task(task_id, tower_id)

        resp = client_with_auth.get(f"/result/{task_id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "processing"
