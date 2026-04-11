"""Chores – FastAPI application entry point."""

from __future__ import annotations
import asyncio
import json
import logging
import os
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Ensure app directory is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import database
from scheduler import generate_instances, mark_overdue
from routers.persons import sync_persons_from_ha

logger = logging.getLogger("chores")

# ── Version ──────────────────────────────────────────────────────────────────
VERSION = "0.0.0"
CONFIG_PATH = os.environ.get("CONFIG_PATH", "/config.json")
try:
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            VERSION = json.load(f).get("version", VERSION)
except Exception:
    pass


# ── Background scheduler ────────────────────────────────────────────────────
async def _scheduler_loop():
    """Periodically generate instances, mark overdue, sync persons."""
    while True:
        try:
            generate_instances(days_ahead=7)
            mark_overdue()
        except Exception as e:
            logger.error("Scheduler error: %s", e)
        await asyncio.sleep(900)  # Every 15 minutes


# ── Lifespan ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(
        level=logging.DEBUG if os.environ.get("DEBUG") == "1" else logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    logger.info("Chores API v%s starting...", VERSION)

    # Initialize database
    db_tables = database.initialize()
    logger.info("Database ready (%d tables)", db_tables)

    # Sync persons from HA on startup
    try:
        persons = await sync_persons_from_ha()
        logger.info("Synced %d persons from HA", len(persons))
    except Exception as e:
        logger.warning("Could not sync persons on startup: %s", e)

    # Generate initial instances
    try:
        created = generate_instances(days_ahead=7)
        mark_overdue()
        logger.info("Generated %d initial chore instances", created)
    except Exception as e:
        logger.warning("Initial instance generation failed: %s", e)

    # Start background scheduler
    scheduler_task = asyncio.create_task(_scheduler_loop())

    yield

    scheduler_task.cancel()
    database.close_connection()
    logger.info("Chores API shutdown")


# ── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(title="Chores", version=VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Ingress path rewrite middleware ──────────────────────────────────────────
@app.middleware("http")
async def ingress_strip(request: Request, call_next):
    ingress_path = request.headers.get("X-Ingress-Path", "")
    if ingress_path and request.url.path.startswith(ingress_path):
        scope = request.scope
        scope["path"] = request.url.path[len(ingress_path):]
    return await call_next(request)


# ── Global error handler ────────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled error: %s %s → %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
    )


# ── Register routers ────────────────────────────────────────────────────────
from routers import health, chores, persons, assignments, gamification, config, calendar

app.include_router(health.router)
app.include_router(chores.router)
app.include_router(persons.router)
app.include_router(assignments.router)
app.include_router(gamification.router)
app.include_router(config.router)
app.include_router(calendar.router)


# ── Entry point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8100, log_level="info")
