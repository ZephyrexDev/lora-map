"""Admin authentication for the Signal Coverage Prediction API.

Provides a simple Bearer-token authentication scheme where the token is the
ADMIN_PASSWORD environment variable itself.  When ADMIN_PASSWORD is not set
(the default), authentication is disabled and all requests are allowed through.
"""

import os
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

ADMIN_PASSWORD: str | None = os.environ.get("ADMIN_PASSWORD")

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


@router.post("/login")
async def login(body: LoginRequest) -> dict[str, str]:
    """Validate a password and return a token on success.

    Returns ``{"token": "<password>"}`` when the password matches
    ``ADMIN_PASSWORD``, or 401 otherwise.  If auth is disabled
    (``ADMIN_PASSWORD`` unset), any password is accepted and an empty token
    is returned.
    """
    if ADMIN_PASSWORD is None:
        return {"token": ""}

    if body.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid password")

    return {"token": body.password}


@router.get("/check")
async def check(
    _: Annotated[None, Depends(require_admin)] = None,
) -> dict[str, bool]:
    """Return ``{"authenticated": true}`` if the Bearer token is valid.

    Reuses the ``require_admin`` dependency so it returns 401 when the token
    is missing or wrong (and auth is enabled).
    """
    return {"authenticated": True}
