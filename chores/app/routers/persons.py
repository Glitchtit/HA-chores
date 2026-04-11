"""Chores – Person management endpoints (synced from HA)."""

from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Request
from models import Person
from database import get_connection
from ha_client import get_persons as ha_get_persons

router = APIRouter(prefix="/api/persons", tags=["persons"])


async def sync_persons_from_ha() -> list[dict]:
    """Fetch persons from HA and upsert into local DB."""
    ha_persons = await ha_get_persons()
    conn = get_connection()
    for p in ha_persons:
        conn.execute(
            """INSERT INTO persons (entity_id, name, avatar_url, ha_user_id)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(entity_id) DO UPDATE SET
                   name       = excluded.name,
                   avatar_url = excluded.avatar_url,
                   ha_user_id = excluded.ha_user_id""",
            (p["entity_id"], p["name"], p.get("avatar_url", ""), p.get("user_id", "")),
        )
    conn.commit()
    return ha_persons


@router.get("/me", response_model=Optional[Person])
async def whoami(request: Request):
    """Return the person matching the current HA user, or null if not found."""
    ha_user_id = request.headers.get("X-Hass-User-ID", "")
    if not ha_user_id:
        return None
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM persons WHERE ha_user_id = ?", (ha_user_id,)
    ).fetchone()
    return dict(row) if row else None


@router.get("/", response_model=list[Person])
async def list_persons():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM persons ORDER BY xp_total DESC").fetchall()
    return [dict(r) for r in rows]


@router.post("/sync", response_model=list[Person])
async def sync_persons():
    """Force re-sync persons from Home Assistant."""
    await sync_persons_from_ha()
    return await list_persons()
