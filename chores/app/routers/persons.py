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


import logging as _logging
_log = _logging.getLogger(__name__)


@router.get("/me", response_model=Optional[Person])
async def whoami(request: Request):
    """Return the person matching the current HA user, or null if not found."""
    ha_user_id = request.headers.get("X-Remote-User-Id", "")
    _log.info("GET /me — X-Remote-User-Id header: %r", ha_user_id)
    if not ha_user_id:
        return None
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM persons WHERE ha_user_id = ?", (ha_user_id,)
    ).fetchone()
    if row:
        return dict(row)
    # No match — re-sync person list from HA (covers cases where link was
    # established after startup or ha_user_id was empty on first sync).
    try:
        await sync_persons_from_ha()
        row = conn.execute(
            "SELECT * FROM persons WHERE ha_user_id = ?", (ha_user_id,)
        ).fetchone()
    except Exception as e:
        _log.warning("Re-sync in /me failed: %s", e)
    return dict(row) if row else None


@router.get("/me/debug")
async def whoami_debug(request: Request):
    """Debug endpoint: shows received headers and DB person state."""
    ha_user_id = request.headers.get("X-Hass-User-ID", "")
    conn = get_connection()
    persons_db = conn.execute("SELECT entity_id, name, ha_user_id FROM persons").fetchall()
    return {
        "received_x_remote_user_id": request.headers.get("X-Remote-User-Id", ""),
        "all_ingress_headers": {k: v for k, v in request.headers.items() if "hass" in k.lower() or "ingress" in k.lower() or "remote" in k.lower() or "x-" in k.lower()},
        "persons_in_db": [{"entity_id": r["entity_id"], "name": r["name"], "ha_user_id": r["ha_user_id"]} for r in persons_db],
    }


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


@router.post("/{entity_id}/test-notification")
async def test_notification(entity_id: str):
    """Send a test push notification to a person's devices."""
    from ha_client import send_notification
    sent = await send_notification(
        entity_id,
        title="🔔 Test Notification",
        message="Chores notifications are working correctly!",
    )
    if not sent:
        raise HTTPException(404, "No mobile_app device found for this person")
    return {"ok": True}
