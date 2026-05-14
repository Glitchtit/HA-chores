"""Chores – Seasonal boss event endpoints (v0.5.0)."""

from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import bosses
from database import get_connection

router = APIRouter(prefix="/api/bosses", tags=["bosses"])


class ObjectiveSpec(BaseModel):
    chore_id: int
    target_count: int = 1
    sort_order: int = 0


class BossCreate(BaseModel):
    name: str
    description: str = ""
    icon: str = "👹"
    start_date: str
    end_date: str
    reward_cosmetic_id: Optional[str] = None
    reward_badge_id: Optional[str] = None
    objectives: list[ObjectiveSpec] = []


class BossUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    reward_cosmetic_id: Optional[str] = None
    reward_badge_id: Optional[str] = None
    objectives: Optional[list[ObjectiveSpec]] = None  # if provided, replaces existing objectives


@router.get("/active")
def get_active_boss():
    """Return the active boss event (with objectives) or null."""
    conn = get_connection()
    boss = bosses.get_active(conn)
    if not boss:
        return None
    return bosses.get_with_objectives(conn, boss["id"])


@router.get("/")
def list_bosses():
    """Return all boss events (most recent first), with objectives."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT id FROM boss_events ORDER BY id DESC"
    ).fetchall()
    return [bosses.get_with_objectives(conn, r["id"]) for r in rows]


def _insert_objectives(conn, boss_id: int, objs: list[ObjectiveSpec]):
    for o in objs:
        conn.execute(
            """INSERT INTO boss_objectives (boss_id, chore_id, target_count, sort_order)
               VALUES (?, ?, ?, ?)""",
            (boss_id, o.chore_id, o.target_count, o.sort_order),
        )
    conn.commit()


@router.post("/", status_code=201)
def create_boss(body: BossCreate):
    """Admin: create a new boss event with its objectives."""
    if body.start_date > body.end_date:
        raise HTTPException(422, "start_date must be <= end_date")
    conn = get_connection()
    # Validate referenced chores exist
    for o in body.objectives:
        chore = conn.execute(
            "SELECT id FROM chores WHERE id = ? AND active = 1", (o.chore_id,)
        ).fetchone()
        if not chore:
            raise HTTPException(422, f"Chore {o.chore_id} not found or inactive")

    cursor = conn.execute(
        """INSERT INTO boss_events
             (name, description, icon, start_date, end_date, status,
              reward_cosmetic_id, reward_badge_id)
           VALUES (?, ?, ?, ?, ?, 'upcoming', ?, ?)""",
        (
            body.name,
            body.description,
            body.icon,
            body.start_date,
            body.end_date,
            body.reward_cosmetic_id,
            body.reward_badge_id,
        ),
    )
    conn.commit()
    boss_id = cursor.lastrowid
    if body.objectives:
        _insert_objectives(conn, boss_id, body.objectives)
    # Move it to active immediately if dates qualify
    bosses.tick(conn)
    return bosses.get_with_objectives(conn, boss_id)


@router.put("/{boss_id}")
def update_boss(boss_id: int, body: BossUpdate):
    """Admin: edit a boss event. If objectives are provided, they replace existing ones."""
    conn = get_connection()
    existing = conn.execute(
        "SELECT id FROM boss_events WHERE id = ?", (boss_id,)
    ).fetchone()
    if not existing:
        raise HTTPException(404, "Boss not found")

    fields = []
    params = []
    for col in ("name", "description", "icon", "start_date", "end_date",
                "reward_cosmetic_id", "reward_badge_id"):
        v = getattr(body, col)
        if v is not None:
            fields.append(f"{col} = ?")
            params.append(v)
    if fields:
        params.append(boss_id)
        conn.execute(f"UPDATE boss_events SET {', '.join(fields)} WHERE id = ?", params)

    if body.objectives is not None:
        conn.execute("DELETE FROM boss_objectives WHERE boss_id = ?", (boss_id,))
        _insert_objectives(conn, boss_id, body.objectives)
    conn.commit()
    bosses.tick(conn)
    return bosses.get_with_objectives(conn, boss_id)


@router.delete("/{boss_id}")
def cancel_boss(boss_id: int):
    """Admin: cancel a boss event (transitions to expired). Returns 404 if not found."""
    conn = get_connection()
    cursor = conn.execute(
        "UPDATE boss_events SET status = 'expired' WHERE id = ? AND status IN ('upcoming', 'active')",
        (boss_id,),
    )
    conn.commit()
    if cursor.rowcount == 0:
        raise HTTPException(404, "No upcoming/active boss with that id")
    return {"cancelled": boss_id}
