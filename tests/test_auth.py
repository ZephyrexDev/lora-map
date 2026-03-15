"""Tests for admin authentication in app.auth and protected endpoints."""

import pytest

pytestmark = pytest.mark.slow

from tests.conftest import insert_task, insert_tower

AUTH_PASSWORD = "s3cret"


# ===========================================================================
# Auth disabled (ADMIN_PASSWORD unset)
# ===========================================================================


class TestAuthDisabled:
    def test_post_predict_allowed(self, client, valid_payload):
        assert client.post("/predict", json=valid_payload).status_code == 201

    def test_delete_tower_allowed(self, client):
        tid = insert_tower()
        assert client.delete(f"/towers/{tid}").status_code == 200

    def test_auth_check_allowed(self, client):
        resp = client.get("/auth/check")
        assert resp.json() == {"authenticated": True}

    def test_auth_login_returns_empty_token(self, client):
        resp = client.post("/auth/login", json={"password": "anything"})
        assert resp.json() == {"token": ""}


# ===========================================================================
# Auth enabled — protected endpoints reject unauthenticated requests
# ===========================================================================


class TestAuthEnabledRejectsUnauthenticated:
    def test_post_predict_401_without_token(self, client_with_auth, valid_payload):
        assert client_with_auth.post("/predict", json=valid_payload).status_code == 401

    def test_post_predict_401_with_wrong_token(self, client_with_auth, valid_payload):
        resp = client_with_auth.post(
            "/predict",
            json=valid_payload,
            headers={"Authorization": "Bearer wrong"},
        )
        assert resp.status_code == 401

    def test_delete_tower_401_without_token(self, client_with_auth):
        tid = insert_tower()
        assert client_with_auth.delete(f"/towers/{tid}").status_code == 401

    def test_auth_check_401_without_token(self, client_with_auth):
        assert client_with_auth.get("/auth/check").status_code == 401

    def test_auth_check_401_with_wrong_token(self, client_with_auth):
        resp = client_with_auth.get("/auth/check", headers={"Authorization": "Bearer wrong"})
        assert resp.status_code == 401


# ===========================================================================
# Auth enabled — protected endpoints work with correct token
# ===========================================================================


class TestAuthEnabledWithValidToken:
    def _headers(self):
        return {"Authorization": f"Bearer {AUTH_PASSWORD}"}

    def test_post_predict_201(self, client_with_auth, valid_payload):
        resp = client_with_auth.post("/predict", json=valid_payload, headers=self._headers())
        assert resp.status_code == 201
        assert "task_id" in resp.json()

    def test_delete_tower_200(self, client_with_auth):
        tid = insert_tower()
        assert client_with_auth.delete(f"/towers/{tid}", headers=self._headers()).status_code == 200

    def test_auth_check_200(self, client_with_auth):
        resp = client_with_auth.get("/auth/check", headers=self._headers())
        assert resp.json() == {"authenticated": True}


# ===========================================================================
# POST /auth/login
# ===========================================================================


class TestAuthLogin:
    def test_correct_password_returns_token(self, client_with_auth):
        resp = client_with_auth.post("/auth/login", json={"password": AUTH_PASSWORD})
        assert resp.json() == {"token": AUTH_PASSWORD}

    def test_wrong_password_returns_401(self, client_with_auth):
        assert client_with_auth.post("/auth/login", json={"password": "wrong"}).status_code == 401

    def test_missing_password_returns_422(self, client_with_auth):
        assert client_with_auth.post("/auth/login", json={}).status_code == 422


# ===========================================================================
# Public endpoints remain accessible even with auth enabled
# ===========================================================================


class TestPublicEndpointsWithAuth:
    def test_get_towers_no_auth_needed(self, client_with_auth):
        assert client_with_auth.get("/towers").status_code == 200

    def test_get_status_no_auth_needed(self, client_with_auth):
        tid = insert_tower()
        kid = insert_task(tower_id=tid)
        assert client_with_auth.get(f"/status/{kid}").json()["status"] == "processing"

    def test_get_result_no_auth_needed(self, client_with_auth):
        tid = insert_tower()
        kid = insert_task(tower_id=tid)
        assert client_with_auth.get(f"/result/{kid}").json()["status"] == "processing"


# ===========================================================================
# Rate limiting
# ===========================================================================


class TestRateLimit:
    def test_allows_up_to_max_attempts(self, client_with_auth):
        for _ in range(5):
            assert client_with_auth.post("/auth/login", json={"password": "wrong"}).status_code == 401

    def test_blocks_after_max_attempts(self, client_with_auth):
        for _ in range(5):
            client_with_auth.post("/auth/login", json={"password": "wrong"})
        assert client_with_auth.post("/auth/login", json={"password": "wrong"}).status_code == 429

    def test_correct_password_still_counted(self, client_with_auth):
        for _ in range(5):
            client_with_auth.post("/auth/login", json={"password": AUTH_PASSWORD})
        assert client_with_auth.post("/auth/login", json={"password": AUTH_PASSWORD}).status_code == 429


# ===========================================================================
# Malformed Authorization headers
# ===========================================================================


class TestMalformedAuthHeaders:
    @pytest.mark.parametrize(
        "header",
        [
            "Basic s3cret",  # wrong scheme
            "",  # empty
            "Bearer  s3cret",  # extra space
            "Bearer",  # missing token
        ],
    )
    def test_rejects_malformed_header(self, client_with_auth, header):
        resp = client_with_auth.get("/auth/check", headers={"Authorization": header})
        assert resp.status_code == 401
