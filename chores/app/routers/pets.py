"""Chores – Pet endpoints (happiness, cleanliness, emoji customization)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

import pets
from database import get_connection
from routers.persons import sync_persons_from_ha

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/pets", tags=["pets"])


class PetEmojiUpdate(BaseModel):
    emoji: str = Field(min_length=1, max_length=8)


async def _resolve_person_id(request: Request, fallback: str | None) -> str | None:
    """Resolve the viewer's person entity_id from X-Remote-User-Id, with a
    `?person_id=` fallback for testability."""
    ha_user_id = request.headers.get("X-Remote-User-Id", "")
    if ha_user_id:
        conn = get_connection()
        row = conn.execute(
            "SELECT entity_id FROM persons WHERE ha_user_id = ?", (ha_user_id,)
        ).fetchone()
        if row:
            return row["entity_id"]
        try:
            await sync_persons_from_ha()
            row = conn.execute(
                "SELECT entity_id FROM persons WHERE ha_user_id = ?", (ha_user_id,)
            ).fetchone()
            if row:
                return row["entity_id"]
        except Exception as e:
            logger.warning("Re-sync in pets/me failed: %s", e)
    return fallback


@router.get("/me")
async def get_my_pet(request: Request, person_id: str | None = None):
    """Return the viewer's pet view."""
    resolved = await _resolve_person_id(request, person_id)
    if not resolved:
        raise HTTPException(404, "No person associated with this user")
    conn = get_connection()
    exists = conn.execute(
        "SELECT 1 FROM persons WHERE entity_id = ?", (resolved,)
    ).fetchone()
    if not exists:
        raise HTTPException(404, "Person not found")
    return pets.get_pet_view(conn, resolved)


@router.get("/")
async def get_household_pets():
    """Return all pets + shared household state."""
    conn = get_connection()
    return pets.get_household_view(conn)


@router.put("/{person_id}/emoji")
async def set_pet_emoji(person_id: str, body: PetEmojiUpdate):
    """Update the emoji used to render a person's pet."""
    conn = get_connection()
    exists = conn.execute(
        "SELECT 1 FROM persons WHERE entity_id = ?", (person_id,)
    ).fetchone()
    if not exists:
        raise HTTPException(404, "Person not found")
    pets.ensure_pet(conn, person_id)
    conn.execute(
        "UPDATE pet_states SET pet_emoji = ? WHERE person_id = ?",
        (body.emoji, person_id),
    )
    conn.commit()
    return pets.get_pet_view(conn, person_id)
