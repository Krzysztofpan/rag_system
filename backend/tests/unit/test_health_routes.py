from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.app import create_app
from app.config import Settings
from app.routes.health_routes import health_router


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(health_router)
    return TestClient(app)


def test_live_ok_without_dependency_checks():
    with (
        patch("app.routes.health_routes.check_db_connection") as check_db,
        patch("app.routes.health_routes.check_pinecone_connection") as check_pinecone,
    ):
        response = _client().get("/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    check_db.assert_not_called()
    check_pinecone.assert_not_called()


@patch("app.routes.health_routes.check_db_connection", return_value=(True, "ok"))
def test_health_db_ok(_check):
    response = _client().get("/health/db")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "detail": "ok"}


@patch(
    "app.routes.health_routes.check_db_connection",
    return_value=(False, "DATABASE_URL is not configured"),
)
def test_health_db_unavailable(_check):
    response = _client().get("/health/db")

    assert response.status_code == 503
    assert response.json() == {
        "status": "error",
        "detail": "DATABASE_URL is not configured",
    }


@patch(
    "app.routes.health_routes.check_pinecone_connection",
    new_callable=AsyncMock,
    return_value=(True, "ok"),
)
@patch(
    "app.routes.health_routes.check_db_connection",
    new_callable=AsyncMock,
    return_value=(True, "ok"),
)
def test_ready_ok(_check_db, _check_pinecone):
    response = _client().get("/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "checks": {"database": "ok", "pinecone": "ok"},
    }


@patch(
    "app.routes.health_routes.check_pinecone_connection",
    new_callable=AsyncMock,
    return_value=(True, "ok"),
)
@patch(
    "app.routes.health_routes.check_db_connection",
    new_callable=AsyncMock,
    return_value=(False, "down"),
)
def test_ready_unavailable_when_database_fails(_check_db, _check_pinecone):
    response = _client().get("/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "error",
        "checks": {"database": "down", "pinecone": "ok"},
    }


@patch(
    "app.routes.health_routes.check_pinecone_connection",
    new_callable=AsyncMock,
    return_value=(False, "Pinecone index 'rag-system' not found"),
)
@patch(
    "app.routes.health_routes.check_db_connection",
    new_callable=AsyncMock,
    return_value=(True, "ok"),
)
def test_ready_unavailable_when_pinecone_fails(_check_db, _check_pinecone):
    response = _client().get("/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "error",
        "checks": {
            "database": "ok",
            "pinecone": "Pinecone index 'rag-system' not found",
        },
    }


def test_docs_enabled_in_development():
    application = create_app(Settings(app_env="development"))

    assert application.docs_url == "/docs"
    assert application.redoc_url == "/redoc"
    assert application.openapi_url == "/openapi.json"


def test_docs_disabled_in_production():
    application = create_app(Settings(app_env="production"))

    assert application.docs_url is None
    assert application.redoc_url is None
    assert application.openapi_url is None


def test_root_hello_removed():
    application = create_app(Settings(app_env="development"))
    paths = set(application.openapi()["paths"])

    assert "/" not in paths
    assert "/api/live" in paths
    assert "/live" not in paths
    assert "/api/conversations/" in paths
