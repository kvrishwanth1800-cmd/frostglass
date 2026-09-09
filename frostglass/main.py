"""FastAPI application factory."""

from fastapi import FastAPI

from frostglass.config import Settings


def create_app() -> FastAPI:
    """Create the application after validating security-critical configuration."""
    settings = Settings()
    app = FastAPI(title="Frostglass", version=settings.version)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": settings.version}

    return app


app = create_app()
