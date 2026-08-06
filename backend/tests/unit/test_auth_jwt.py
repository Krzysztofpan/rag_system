"""Unit tests for Supabase JWT verification."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import jwt
import pytest
from fastapi import HTTPException
from jwt.exceptions import PyJWKClientConnectionError

from app.auth import jwt as jwt_module
from app.auth.jwt import (
    AccessTokenClaims,
    AuthConfigurationError,
    decode_access_token,
    verify_auth_configuration,
)
from app.config import Settings


@pytest.fixture(autouse=True)
def clear_jwt_caches():
    jwt_module._issuer.cache_clear()
    jwt_module._jwks_client.cache_clear()
    yield
    jwt_module._issuer.cache_clear()
    jwt_module._jwks_client.cache_clear()


def _claims_payload(*, user_id: UUID | None = None, **extra) -> dict:
    uid = user_id or uuid4()
    return {
        "sub": str(uid),
        "email": "user@example.com",
        "role": "authenticated",
        "phone": "+48123456789",
        "app_metadata": {"provider": "email"},
        "user_metadata": {"name": "Test User"},
        **extra,
    }


def test_decode_access_token_maps_claims():
    user_id = uuid4()
    payload = _claims_payload(user_id=user_id)

    with patch.object(jwt_module, "_decode_payload", return_value=payload):
        claims = decode_access_token("signed-token")

    assert claims == AccessTokenClaims(
        user_id=user_id,
        email="user@example.com",
        role="authenticated",
        phone="+48123456789",
        app_metadata={"provider": "email"},
        user_metadata={"name": "Test User"},
        raw=payload,
    )


def test_decode_access_token_missing_sub_raises_401():
    with patch.object(jwt_module, "_decode_payload", return_value={"email": "x@y.z"}):
        with pytest.raises(HTTPException) as exc_info:
            decode_access_token("token")

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Token missing subject"
    assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}


def test_decode_access_token_invalid_user_id_raises_401():
    payload = _claims_payload()
    payload["sub"] = "not-a-uuid"

    with patch.object(jwt_module, "_decode_payload", return_value=payload):
        with pytest.raises(HTTPException) as exc_info:
            decode_access_token("token")

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid user id in token"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("email", 123),
        ("email", ""),
        ("role", None),
        ("phone", ["+48"]),
        ("app_metadata", "bad"),
        ("user_metadata", []),
    ],
)
def test_decode_access_token_sanitizes_optional_fields(field, value):
    user_id = uuid4()
    payload = _claims_payload(user_id=user_id)
    payload[field] = value

    with patch.object(jwt_module, "_decode_payload", return_value=payload):
        claims = decode_access_token("token")

    if field == "email":
        assert claims.email is None
    elif field == "role":
        assert claims.role is None
    elif field == "phone":
        assert claims.phone is None
    elif field == "app_metadata":
        assert claims.app_metadata == {}
    elif field == "user_metadata":
        assert claims.user_metadata == {}


def test_decode_payload_jwt_error_raises_401():
    mock_client = MagicMock()
    mock_client.get_signing_key_from_jwt.side_effect = jwt.InvalidTokenError("bad token")

    with patch.object(jwt_module, "_jwks_client", return_value=mock_client):
        with pytest.raises(HTTPException) as exc_info:
            jwt_module._decode_payload("token")

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid or expired token"
    assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}


def test_decode_payload_jwks_unavailable_raises_503():
    mock_client = MagicMock()
    mock_client.get_signing_key_from_jwt.side_effect = PyJWKClientConnectionError(
        "connection failed"
    )

    with patch.object(jwt_module, "_jwks_client", return_value=mock_client):
        with pytest.raises(HTTPException) as exc_info:
            jwt_module._decode_payload("token")

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "Cannot verify tokens right now, try again"
    assert exc_info.value.headers == {"Retry-After": "5"}


def test_verify_auth_configuration_initializes_jwks_client():
    mock_client = MagicMock()
    with patch.object(jwt_module, "_jwks_client", return_value=mock_client) as factory:
        verify_auth_configuration()
    factory.assert_called_once()


def test_issuer_raises_when_supabase_url_missing():
    settings = Settings(supabase_url=None)
    with patch("app.auth.jwt.get_settings", return_value=settings):
        with pytest.raises(AuthConfigurationError, match="SUPABASE_URL"):
            jwt_module._issuer()
