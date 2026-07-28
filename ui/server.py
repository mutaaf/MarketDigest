"""FastAPI application — Market Digest Command Center."""

import sys
from pathlib import Path

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

from ui.routes import (  # noqa: E402
    cache,
    digests,
    history,
    innovation,
    instruments,
    onboarding,
    options,
    pine,
    prompts,
    retrace,
    risk,
    scorecard,
    settings,
    signals,
    sources,
    status,
    trading,
)

app = FastAPI(title="Market Digest Command Center", version="1.0.0")

# CORS for dev (Vite) and prod
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register route groups
app.include_router(status.router)
app.include_router(onboarding.router)
app.include_router(settings.router)
app.include_router(instruments.router)
app.include_router(prompts.router)
app.include_router(digests.router)
app.include_router(sources.router)
app.include_router(cache.router)
app.include_router(history.router)
app.include_router(retrace.router)
app.include_router(scorecard.router)
app.include_router(options.router)
app.include_router(signals.router)
app.include_router(trading.router)
app.include_router(risk.router)
app.include_router(pine.router)
app.include_router(innovation.router)

# Serve built React frontend
FRONTEND_DIST = Path(__file__).parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    # Serve static assets (JS, CSS, images) directly
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")

    # Catch-all: serve index.html for any non-API route so React Router handles client-side navigation
    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        # Don't intercept API routes
        if full_path.startswith("api/"):
            return
        # Try to serve exact file first (favicon, robots.txt, etc.)
        file_path = FRONTEND_DIST / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        # Otherwise return index.html for React Router
        return FileResponse(FRONTEND_DIST / "index.html")
