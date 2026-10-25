"""FastAPI application factory and static file serving."""

from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .routes import router

web_dir = Path(__file__).resolve().parent.parent / "web"


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="The Retirement Whisperer API",
        description="Adversarial Multi-Agent Resilience Platform for Retirement AI",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)

    # Mount static assets for web UI
    if web_dir.exists():
        app.mount("/static", StaticFiles(directory=str(web_dir)), name="static_dir")
        app.mount("/", StaticFiles(directory=str(web_dir), html=True), name="static")

    return app


app = create_app()
