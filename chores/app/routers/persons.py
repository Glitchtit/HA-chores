"""Chores – Person management endpoints (synced from HA)."""

from __future__ import annotations
from fastapi import APIRouter
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
            """INSERT INTO persons (entity_id, name, avatar_url)
               VALUES (?, ?, ?)
               ON CONFLICT(entity_id) DO UPDATE SET
                   name = excluded.name,
                   avatar_url = excluded.avatar_url""",
            (p["entity_id"], p["name"], p.get("avatar_url", "")),
        )
    conn.commit()
    return ha_persons


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
