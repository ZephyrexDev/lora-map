"""Admin authentication for the Signal Coverage Prediction API.

Uses Bearer-token authentication with opaque session tokens.  The admin
password is read from the ``ADMIN_PASSWORD`` environment variable on each
check so that rotations take effect without a restart.  When the variable
is unset, authentication is disabled and all requests are allowed through.
"""

import hmac
import os
import secrets
import threading
import time
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel

from app.models.responses import AuthCheckResponse, AuthTokenResponse

# ---------------------------------------------------------------------------
# Session token store — maps opaque tokens to expiry timestamps.
# Protected by a lock for thread safety.
# ---------------------------------------------------------------------------
_TOKEN_TTL_SECONDS = 86400  # 24 hours
_token_lock = threading.Lock()
_active_tokens: dict[str, float] = {}  # token -> expiry (monotonic)


def _get_admin_password() -> str | None:
    """Read the admin password from the environment on every call."""
    return os.environ.get("ADMIN_PASSWORD")


def _issue_token() -> str:
    """Create a cryptographically random session token and store it."""
    token = secrets.token_urlsafe(32)
    expiry = time.monotonic() + _TOKEN_TTL_SECONDS
    with _token_lock:
        _active_tokens[token] = expiry
    return token


def _validate_token(token: str) -> bool:
    """Return True if *token* is active and not expired, pruning stale entries."""
    now = time.monotonic()
    with _token_lock:
        expiry = _active_tokens.get(token)
        if expiry is None or now > expiry:
            _active_tokens.pop(token, None)
            return False
    return True


# ---------------------------------------------------------------------------
# Rate limiter — thread-safe, bounded
# ---------------------------------------------------------------------------
_rate_lock = threading.Lock()
_login_attempts: dict[str, list[float]] = {}
_MAX_ATTEMPTS = 5
_WINDOW_SECONDS = 60
_MAX_TRACKED_IPS = 10_000


_PRUNE_INTERVAL_SECONDS = 300  # Run full sweep at most every 5 minutes
_last_prune: float = 0.0


def _check_rate_limit(client_ip: str) -> None:
    """Raise 429 if client_ip has exceeded _MAX_ATTEMPTS in the last _WINDOW_SECONDS."""
    global _last_prune
    now = time.monotonic()
    with _rate_lock:
        # Periodic sweep: prune stale entries every _PRUNE_INTERVAL_SECONDS or when dict is large
        if now - _last_prune > _PRUNE_INTERVAL_SECONDS or len(_login_attempts) > _MAX_TRACKED_IPS:
            stale = [ip for ip, ts in _login_attempts.items() if all(now - t >= _WINDOW_SECONDS for t in ts)]
            for ip in stale:
                del _login_attempts[ip]
            _last_prune = now

        attempts = _login_attempts.get(client_ip, [])
        attempts = [t for t in attempts if now - t < _WINDOW_SECONDS]

        if len(attempts) >= _MAX_ATTEMPTS:
            _login_attempts[client_ip] = attempts
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
      header of the form ``Bearer <token>`` where ``<token>`` is a valid
      session token obtained via ``POST /auth/login``.
    """
    if _get_admin_password() is None:
        return

    if authorization is None:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    parts = authorization.split(" ", maxsplit=1)
    if len(parts) != 2 or parts[0] != "Bearer":
        raise HTTPException(status_code=401, detail="Invalid token")

    if not _validate_token(parts[1]):
        raise HTTPException(status_code=401, detail="Invalid token")


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    password: str


@router.post("/login", response_model=AuthTokenResponse)
async def login(body: LoginRequest, request: Request) -> AuthTokenResponse:
    """Validate a password and return an opaque session token on success.

    If auth is disabled (``ADMIN_PASSWORD`` unset), any password is accepted
    and an empty token is returned.  Rate limited to 5 attempts per minute per IP.
    """
    admin_password = _get_admin_password()

    if admin_password is None:
        return AuthTokenResponse(token="")

    _check_rate_limit(request.client.host if request.client else "unknown")

    # Constant-time comparison to prevent timing side-channel attacks
    if not hmac.compare_digest(body.password.encode(), admin_password.encode()):
        raise HTTPException(status_code=401, detail="Invalid password")

    return AuthTokenResponse(token=_issue_token())


@router.get("/check", response_model=AuthCheckResponse)
async def check(
    _: Annotated[None, Depends(require_admin)] = None,
) -> AuthCheckResponse:
    """Return ``{"authenticated": true}`` if the Bearer token is valid.

    Reuses the ``require_admin`` dependency so it returns 401 when the token
    is missing or wrong (and auth is enabled).
    """
    return AuthCheckResponse(authenticated=True)
