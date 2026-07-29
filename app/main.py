from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.api.routes import router as api_router
from app.core.settings import settings
from app.voice.router import router as voice_router


app = FastAPI(title="SiteMind", version=__version__)
app.include_router(api_router)
app.include_router(voice_router)

frontend = settings.project_root / "frontend"
app.mount("/assets", StaticFiles(directory=frontend / "assets"), name="assets")


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "product": "SiteMind",
        "version": __version__,
        "generation_provider": settings.generation_provider,
        "embedding_model": settings.embedding_model,
    }


@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    return FileResponse(frontend / "index.html")


@app.get("/widget.js", include_in_schema=False)
def widget_script() -> FileResponse:
    return FileResponse(frontend / "widget.js", media_type="application/javascript")
