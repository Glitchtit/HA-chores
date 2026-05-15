"""Chores – Team household challenges router (v0.4.6)."""

from __future__ import annotations
from datetime import date
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import challenges
from database import get_connection

router = APIRouter(prefix="/api/challenges", tags=["challenges"])


class ChallengeCreate(BaseModel):
    name: str
    description: str = ""
    goal_type: str
    goal_value: int
    target_category: str = ""
    period_start: Optional[str] = None  # YYYY-MM-DD; default = today
    period_end: Optional[str] = None    # default = +6 days
    reward_multiplier: float = 2.0
    reward_hours: int = 72


@router.get("/active")
def get_active_challenge():
    """Return the currently active challenge, with progress, or null."""
    conn = get_connection()
    c = challenges.get_active(conn)
    if not c:
        return None
    # Refresh progress on read to avoid drift
    progress = challenges.recompute_progress(conn, c)
    c["progress"] = progress
    return c


@router.get("/")
def list_challenges(limit: int = 50):
    """Return a recent history of challenges (most recent first)."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM household_challenges ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


@router.post("/")
def create_challenge(body: ChallengeCreate):
    """Admin endpoint: create a new challenge."""
    if body.goal_type not in ("completions_total", "category_total", "xp_total", "claims_total"):
        raise HTTPException(422, "Unknown goal_type")
    if body.goal_value <= 0:
        raise HTTPException(422, "goal_value must be > 0")

    today = date.today()
    start = body.period_start or today.isoformat()
    if body.period_end:
        end = body.period_end
    else:
        from datetime import timedelta
        end = (today + timedelta(days=6)).isoformat()

    conn = get_connection()
    cursor = conn.execute(
        """INSERT INTO household_challenges
             (name, description, goal_type, goal_value, target_category,
              period_start, period_end, status, reward_multiplier, reward_hours)
           VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)""",
        (
            body.name,
            body.description,
            body.goal_type,
            body.goal_value,
            body.target_category,
            start,
            end,
            body.reward_multiplier,
            body.reward_hours,
        ),
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM household_challenges WHERE id = ?", (cursor.lastrowid,)
    ).fetchone()
    return dict(row)


@router.delete("/{challenge_id}")
def cancel_challenge(challenge_id: int):
    """Admin endpoint: cancel an active challenge (transitions to expired)."""
    conn = get_connection()
    cursor = conn.execute(
        "UPDATE household_challenges SET status = 'expired' WHERE id = ? AND status = 'active'",
        (challenge_id,),
    )
    conn.commit()
    if cursor.rowcount == 0:
        raise HTTPException(404, "No active challenge with that id")
    return {"cancelled": challenge_id}
