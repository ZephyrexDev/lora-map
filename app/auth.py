"""Admin authentication for the Signal Coverage Prediction API.

Provides a simple Bearer-token authentication scheme where the token is the
ADMIN_PASSWORD environment variable itself.  When ADMIN_PASSWORD is not set
(the default), authentication is disabled and all requests are allowed through.
"""

import os
import time
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel

from app.models.responses import AuthCheckResponse, AuthTokenResponse

ADMIN_PASSWORD: str | None = os.environ.get("ADMIN_PASSWORD")

# Simple in-memory rate limiter for login attempts
_login_attempts: dict[str, list[float]] = {}
_MAX_ATTEMPTS = 5
_WINDOW_SECONDS = 60


def _check_rate_limit(client_ip: str) -> None:
    """Raise 429 if client_ip has exceeded _MAX_ATTEMPTS in the last _WINDOW_SECONDS."""
    now = time.monotonic()
    attempts = _login_attempts.get(client_ip, [])
    # Prune old attempts
    attempts = [t for t in attempts if now - t < _WINDOW_SECONDS]
    _login_attempts[client_ip] = attempts

    if len(attempts) >= _MAX_ATTEMPTS:
        raise HTTPException(status_code=429, detail="Too many login attempts. Try again later.")

    attempts.append(now)
    _login_attempts[client_ip] = attempts


router = APIRouter(prefix="/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Dependency
# ---------------------------------------------------------------------------


async def require_admin(
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    """FastAPI dependency that enforces admin authentication.

    * If ``ADMIN_PASSWORD`` is not set, every request is allowed (auth disabled).
    * If ``ADMIN_PASSWORD`` is set, the request must carry an ``Authorization``
      header of the form ``Bearer <password>`` where ``<password>`` matches
      ``ADMIN_PASSWORD``.
    """
    if ADMIN_PASSWORD is None:
        return

    if authorization is None:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    parts = authorization.split(" ", maxsplit=1)
    if len(parts) != 2 or parts[0] != "Bearer" or parts[1] != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid token")


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    password: str


@router.post("/login", response_model=AuthTokenResponse)
async def login(body: LoginRequest, request: Request) -> AuthTokenResponse:
    """Validate a password and return a token on success.

    Returns ``{"token": "<password>"}`` when the password matches
    ``ADMIN_PASSWORD``, or 401 otherwise.  If auth is disabled
    (``ADMIN_PASSWORD`` unset), any password is accepted and an empty token
    is returned.  Rate limited to 5 attempts per minute per IP.
    """
    if ADMIN_PASSWORD is None:
        return AuthTokenResponse(token="")

    _check_rate_limit(request.client.host if request.client else "unknown")

    if body.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid password")

    return AuthTokenResponse(token=body.password)


@router.get("/check", response_model=AuthCheckResponse)
async def check(
    _: Annotated[None, Depends(require_admin)] = None,
) -> AuthCheckResponse:
    """Return ``{"authenticated": true}`` if the Bearer token is valid.

    Reuses the ``require_admin`` dependency so it returns 401 when the token
    is missing or wrong (and auth is enabled).
    """
    return AuthCheckResponse(authenticated=True)
