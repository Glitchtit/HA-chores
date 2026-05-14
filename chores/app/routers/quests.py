"""Chores – Daily quest rotation endpoints (v0.4.5)."""

from __future__ import annotations
from datetime import date
from fastapi import APIRouter, HTTPException

import quests
from database import get_connection

router = APIRouter(prefix="/api/quests", tags=["quests"])


@router.get("/today/{person_id}")
def get_today(person_id: str):
    """Return today's three quests for *person_id*, generating them if missing."""
    conn = get_connection()
    person = conn.execute(
        "SELECT entity_id FROM persons WHERE entity_id = ?", (person_id,)
    ).fetchone()
    if not person:
        raise HTTPException(404, "Person not found")
    return quests.list_for_today(conn, person_id)


@router.get("/{person_id}")
def get_history(person_id: str, since: str | None = None):
    """Return quest history for *person_id* (most recent first).

    Optional *since* filters to quests with quest_date >= the given YYYY-MM-DD.
    """
    conn = get_connection()
    if not conn.execute(
        "SELECT 1 FROM persons WHERE entity_id = ?", (person_id,)
    ).fetchone():
        raise HTTPException(404, "Person not found")
    if since:
        rows = conn.execute(
            """SELECT * FROM daily_quests
               WHERE person_id = ? AND quest_date >= ?
               ORDER BY quest_date DESC, id ASC""",
            (person_id, since),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT * FROM daily_quests
               WHERE person_id = ?
               ORDER BY quest_date DESC, id ASC
               LIMIT 200""",
            (person_id,),
        ).fetchall()
    return [dict(r) for r in rows]
