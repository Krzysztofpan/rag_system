from dataclasses import dataclass
from typing import Any
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.jwt import decode_access_token

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    access_token: str
    user_id: UUID
    email: str | None
    role: str | None
    phone: str | None
    app_metadata: dict[str, Any]
    user_metadata: dict[str, Any]


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> AuthenticatedUser:
    """Sync on purpose: FastAPI runs it in a threadpool, so the blocking JWKS
    fetch inside `decode_access_token` never stalls the event loop."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = credentials.credentials
    claims = decode_access_token(access_token)
    return AuthenticatedUser(
        access_token=access_token,
        user_id=claims.user_id,
        email=claims.email,
        role=claims.role,
        phone=claims.phone,
        app_metadata=claims.app_metadata,
        user_metadata=claims.user_metadata,
    )
