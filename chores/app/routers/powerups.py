"""Chores – Power-up endpoints."""

from __future__ import annotations
from fastapi import APIRouter, HTTPException
from models import PowerUp
from database import get_connection
from gamification import get_active_powerups

router = APIRouter(prefix="/api/powerups", tags=["powerups"])


@router.get("/{person_id}", response_model=list[PowerUp])
async def list_powerups(person_id: str):
    """Return all active power-ups for a person."""
    conn = get_connection()
    person = conn.execute(
        "SELECT entity_id FROM persons WHERE entity_id = ?", (person_id,)
    ).fetchone()
    if not person:
        raise HTTPException(404, "Person not found")
    return get_active_powerups(person_id)


@router.delete("/{powerup_id}", status_code=204)
async def discard_powerup(powerup_id: int):
    """Discard (delete) a specific power-up by its row ID."""
    conn = get_connection()
    row = conn.execute(
        "SELECT id FROM person_powerups WHERE id = ?", (powerup_id,)
    ).fetchone()
    if not row:
        raise HTTPException(404, "Power-up not found")
    conn.execute("DELETE FROM person_powerups WHERE id = ?", (powerup_id,))
    conn.commit()
