"""Tests for auth rate limiting and edge cases in app.auth."""

import os

import pytest
from fastapi.testclient import TestClient

import app.auth as auth_mod
from app.auth import _login_attempts
from app.db import init_db
from app.main import app


@pytest.fixture(autouse=True)
def _setup():
    init_db(os.environ["DB_PATH"])
    _login_attempts.clear()
    yield


@pytest.fixture()
def client():
    original = auth_mod.ADMIN_PASSWORD
    auth_mod.ADMIN_PASSWORD = "testpass"
    yield TestClient(app)
    auth_mod.ADMIN_PASSWORD = original


class TestRateLimit:
    def test_allows_up_to_max_attempts(self, client):
        """First 5 wrong password attempts should return 401, not 429."""
        for _ in range(5):
            resp = client.post("/auth/login", json={"password": "wrong"})
            assert resp.status_code == 401

    def test_blocks_after_max_attempts(self, client):
        """The 6th attempt within the window should return 429."""
        for _ in range(5):
            client.post("/auth/login", json={"password": "wrong"})
        resp = client.post("/auth/login", json={"password": "wrong"})
        assert resp.status_code == 429

    def test_rate_limit_resets_after_clearing(self, client):
        """After the window expires (simulated by clearing), attempts allowed again."""
        for _ in range(5):
            client.post("/auth/login", json={"password": "wrong"})

        # Simulate window expiry by clearing old timestamps
        _login_attempts.clear()

        resp = client.post("/auth/login", json={"password": "wrong"})
        assert resp.status_code == 401  # Not 429

    def test_correct_password_still_counted_for_rate_limit(self, client):
        """Even successful logins count toward rate limit attempts."""
        for _ in range(5):
            client.post("/auth/login", json={"password": "testpass"})
        resp = client.post("/auth/login", json={"password": "testpass"})
        assert resp.status_code == 429


class TestRequireAdminEdgeCases:
    def test_malformed_auth_header_no_bearer_prefix(self, client):
        resp = client.get("/auth/check", headers={"Authorization": "Basic testpass"})
        assert resp.status_code == 401

    def test_empty_authorization_header(self, client):
        resp = client.get("/auth/check", headers={"Authorization": ""})
        assert resp.status_code == 401

    def test_bearer_with_extra_spaces(self, client):
        resp = client.get("/auth/check", headers={"Authorization": "Bearer  testpass"})
        assert resp.status_code == 401  # Extra space means token is " testpass"

    def test_bearer_only_no_token(self, client):
        resp = client.get("/auth/check", headers={"Authorization": "Bearer"})
        assert resp.status_code == 401  # split produces ["Bearer"], len != 2
