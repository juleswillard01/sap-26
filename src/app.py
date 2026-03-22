"""FastAPI application factory — CDC §8."""

from __future__ import annotations

from fastapi import FastAPI


def create_app() -> FastAPI:
    """Crée l'application FastAPI."""
    app = FastAPI(title="SAP-Facture", version="0.1.0")

    @app.get("/")
    async def index() -> dict[str, str]:  # pyright: ignore[reportUnusedFunction]
        """Dashboard principal."""
        return {"status": "ok", "message": "SAP-Facture — Dashboard"}

    return app


app = create_app()
