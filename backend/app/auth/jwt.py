from dataclasses import dataclass
from functools import lru_cache
from typing import Any
from uuid import UUID

import jwt
from fastapi import HTTPException, status
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientConnectionError

from app.config import get_settings


class AuthConfigurationError(RuntimeError):
    """Supabase auth settings are missing; checked while the app boots."""


@dataclass(frozen=True, slots=True)
class AccessTokenClaims:
    user_id: UUID
    email: str | None
    role: str | None
    phone: str | None
    app_metadata: dict[str, Any]
    user_metadata: dict[str, Any]
    raw: dict[str, Any]


JWKS_TIMEOUT_SECONDS = 5


@lru_cache
def _issuer() -> str:
    settings = get_settings()
    if not settings.supabase_url:
        raise AuthConfigurationError("SUPABASE_URL is not configured")
    return f"{settings.supabase_url.rstrip('/')}/auth/v1"


@lru_cache
def _jwks_client() -> PyJWKClient:
    return PyJWKClient(
        f"{_issuer()}/.well-known/jwks.json",
        timeout=JWKS_TIMEOUT_SECONDS,
    )


def verify_auth_configuration() -> None:
    """Called from the app lifespan so misconfiguration fails the boot,
    not every request with a 500."""
    _jwks_client()


def _decode_payload(token: str) -> dict[str, Any]:
    """Verify a Supabase access token signed with ES256 (JWKS).

    Fetching the JWKS is blocking I/O, so callers must not run this on the event
    loop (see `get_current_user`).
    """
    try:
        signing_key = _jwks_client().get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256"],
            audience="authenticated",
            issuer=_issuer(),
        )
    except PyJWKClientConnectionError as exc:
        # An unreachable JWKS endpoint says nothing about the token, so don't
        # answer 401: clients read that as "signed out" and drop valid sessions.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cannot verify tokens right now, try again",
            headers={"Retry-After": str(JWKS_TIMEOUT_SECONDS)},
        ) from exc
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def decode_access_token(token: str) -> AccessTokenClaims:
    payload = _decode_payload(token)

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = UUID(sub)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user id in token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    email = payload.get("email")
    phone = payload.get("phone")
    role = payload.get("role")
    app_metadata = payload.get("app_metadata") or {}
    user_metadata = payload.get("user_metadata") or {}

    return AccessTokenClaims(
        user_id=user_id,
        email=email if isinstance(email, str) and email else None,
        role=role if isinstance(role, str) and role else None,
        phone=phone if isinstance(phone, str) and phone else None,
        app_metadata=app_metadata if isinstance(app_metadata, dict) else {},
        user_metadata=user_metadata if isinstance(user_metadata, dict) else {},
        raw=payload,
    )
