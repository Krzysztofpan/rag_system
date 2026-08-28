from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.auth.deps import AuthenticatedUser, get_current_user
from app.auth.jwt import AccessTokenClaims


def _bearer(token: str = "access-token") -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def test_get_current_user_requires_credentials():
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(MagicMock(), None)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Not authenticated"


def test_get_current_user_rejects_non_bearer_scheme():
    credentials = HTTPAuthorizationCredentials(scheme="Basic", credentials="abc")

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(MagicMock(), credentials)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Not authenticated"


def test_get_current_user_decodes_bearer_token():
    user_id = uuid4()
    claims = AccessTokenClaims(
        user_id=user_id,
        email="user@example.com",
        role="authenticated",
        phone=None,
        app_metadata={},
        user_metadata={},
        raw={"sub": str(user_id)},
    )
    request = MagicMock()

    with patch("app.auth.deps.decode_access_token", return_value=claims):
        user = get_current_user(request, _bearer("signed-token"))

    assert user == AuthenticatedUser(
        access_token="signed-token",
        user_id=user_id,
        email="user@example.com",
        role="authenticated",
        phone=None,
        app_metadata={},
        user_metadata={},
    )
    assert request.state.user_id == str(user_id)
