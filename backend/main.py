"""Yudiaz Sentinel - Application Bootstrap & ASGI Entrypoint.

Author: Idris Nakamura (Senior Developer, Yudiaz Creative Studio)
Spec: Kael Ashford (Lead Architect) - YCS-ARCH-2026-001 (Section 7, 8, 10)
"""

from __future__ import annotations

from contextlib import asynccontextmanager
import os
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend import __app_name__, __version__
from backend.collector import collector
from backend.routes import router as api_router

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown events cleanly."""
    # Startup: Initialize and launch background metrics collection worker
    await collector.start()
    yield
    # Shutdown: Gracefully stop background worker tasks
    await collector.stop()


app = FastAPI(
    title="Yudiaz Sentinel API",
    description="Next-Generation Lightweight VPS Infrastructure & AI Agent Cluster Telemetry",
    version=__version__,
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

# Cross-Origin Resource Sharing (CORS) Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. Mount API Router (High Priority)
app.include_router(api_router)

# 2. Mount Frontend Static Assets
# Ensures root path (/) serves frontend/index.html and static assets
if not FRONTEND_DIR.exists():
    FRONTEND_DIR.mkdir(parents=True, exist_ok=True)

app.mount(
    "/",
    StaticFiles(directory=str(FRONTEND_DIR), html=True),
    name="frontend",
)


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("SENTINEL_HOST", "127.0.0.1")
    port = int(os.getenv("SENTINEL_PORT", "9229"))
    uvicorn.run(
        "backend.main:app",
        host=host,
        port=port,
        workers=1,
        log_level="info",
    )
