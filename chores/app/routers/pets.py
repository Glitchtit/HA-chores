"""Chores – Pet endpoints (happiness, cleanliness, emoji customization)."""

from __future__ import annotations

import logging
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

import asyncio
import json

import pets
from database import get_connection
from routers.persons import sync_persons_from_ha

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/pets", tags=["pets"])


class PetEmojiUpdate(BaseModel):
    emoji: str = Field(min_length=1, max_length=8)


class PetDesignUpdate(BaseModel):
    design: Literal["orange_black", "blue_black"]


class PetNameUpdate(BaseModel):
    name: str = Field(max_length=40)


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
    """Update the emoji used to render a person's pet.

    # TODO: remove in 0.4.0 — superseded by /design in 0.3.1. Kept so cached
    # clients don't 404 during the rollout window.
    """
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


class LayoutSpot(BaseModel):
    left: float = Field(ge=0, le=100)
    top: float = Field(ge=0, le=100)


class LayoutUpdate(BaseModel):
    pet_spots: list[LayoutSpot]
    mess_spots: list[LayoutSpot]


@router.get("/layout")
async def get_layout():
    """Return saved pet/mess layout positions, or null if using defaults."""
    conn = get_connection()
    row = conn.execute(
        "SELECT value FROM config WHERE key = 'pet_layout'"
    ).fetchone()
    if row:
        return json.loads(row["value"])
    return None


@router.put("/layout")
async def save_layout(body: LayoutUpdate):
    """Save custom pet/mess layout positions."""
    conn = get_connection()
    data = body.model_dump()
    conn.execute(
        "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
        ("pet_layout", json.dumps(data)),
    )
    conn.commit()
    return data


@router.delete("/layout")
async def delete_layout():
    """Delete saved layout, reverting to random placement."""
    conn = get_connection()
    conn.execute("DELETE FROM config WHERE key = 'pet_layout'")
    conn.commit()
    return {"ok": True}


@router.get("/sun")
async def get_sun():
    """Return daytime and rain status from HA entities."""
    from ha_client import get_sun_state, get_weather_state
    is_day, is_raining = await asyncio.gather(get_sun_state(), get_weather_state())
    return {
        "is_day": is_day if is_day is not None else True,
        "is_raining": is_raining if is_raining is not None else False,
    }


@router.put("/{person_id}/design")
async def set_pet_design(person_id: str, body: PetDesignUpdate):
    """Pick which axolotl design this person's pet uses."""
    conn = get_connection()
    exists = conn.execute(
        "SELECT 1 FROM persons WHERE entity_id = ?", (person_id,)
    ).fetchone()
    if not exists:
        raise HTTPException(404, "Person not found")
    pets.set_design(conn, person_id, body.design)
    return pets.get_pet_view(conn, person_id)


@router.put("/{person_id}/name")
async def set_pet_name(person_id: str, body: PetNameUpdate):
    """Set (or clear) a custom display name for this person's pet."""
    conn = get_connection()
    exists = conn.execute(
        "SELECT 1 FROM persons WHERE entity_id = ?", (person_id,)
    ).fetchone()
    if not exists:
        raise HTTPException(404, "Person not found")
    pets.set_name(conn, person_id, body.name)
    return pets.get_pet_view(conn, person_id)
