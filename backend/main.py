import uvicorn

from app.config import get_settings

if __name__ == "__main__":
    settings = get_settings()
    reload_enabled = settings.app_env == "development" and settings.uvicorn_reload

    uvicorn.run(
        "app.app:app",
        host=settings.uvicorn_host,
        port=settings.backend_port,
        reload=reload_enabled,
        reload_delay=settings.uvicorn_reload_delay if reload_enabled else None,
        timeout_graceful_shutdown=(
            settings.uvicorn_timeout_graceful_shutdown if reload_enabled else None
        ),
    )
