"""FastAPI application — Market Digest Command Center."""

import sys
from pathlib import Path

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from ui.routes import status, onboarding, settings, instruments, prompts, digests, sources, cache, history, retrace

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

# Serve built React frontend as static files
FRONTEND_DIST = Path(__file__).parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
