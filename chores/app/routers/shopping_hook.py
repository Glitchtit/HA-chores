"""Chores – Shopping-hook endpoint for HA-stock attribution."""

from __future__ import annotations
from datetime import date
import logging

from fastapi import APIRouter, HTTPException

from models import HookCompleteBody
from database import get_connection
from routers.assignments import apply_completion

router = APIRouter(prefix="/api/shopping-hook", tags=["shopping-hook"])
logger = logging.getLogger(__name__)


@router.post("/complete")
async def complete_via_hook(body: HookCompleteBody):
    """Complete (or create + complete) today's instance of `chore_id` for `person`.

    Mirrors POST /api/assignments/{id}/complete but takes a chore-id (not
    instance-id) and supports `suppress_followup` to inhibit the
    auto-spawn of the followup chore when Stock already covered that work.
    """
    conn = get_connection()

    chore = conn.execute(
        "SELECT * FROM chores WHERE id = ? AND active = 1", (body.chore_id,)
    ).fetchone()
    if not chore:
        raise HTTPException(404, "Chore not found or inactive")

    person = conn.execute(
        "SELECT entity_id FROM persons WHERE entity_id = ?", (body.person,)
    ).fetchone()
    if not person:
        raise HTTPException(404, "Person not found")

    today_str = date.today().isoformat()
    instance = conn.execute(
        """SELECT id FROM chore_instances
           WHERE chore_id = ? AND due_date = ? AND status IN ('pending', 'claimed')
           ORDER BY id LIMIT 1""",
        (body.chore_id, today_str),
    ).fetchone()
    if not instance:
        cursor = conn.execute(
            """INSERT INTO chore_instances (chore_id, due_date, assigned_to, status, created_by)
               VALUES (?, ?, NULL, 'pending', 'shopping-hook')""",
            (body.chore_id, today_str),
        )
        conn.commit()
        instance_id = cursor.lastrowid
    else:
        instance_id = instance["id"]

    row = conn.execute(
        """SELECT ci.*, c.xp_reward, c.assignment_mode, c.difficulty as chore_difficulty,
                  c.category as chore_category, c.followup_chore_id
           FROM chore_instances ci JOIN chores c ON ci.chore_id = c.id
           WHERE ci.id = ?""",
        (instance_id,),
    ).fetchone()

    return apply_completion(
        conn, row, body.person, body.notes,
        bg=None,
        suppress_followup=body.suppress_followup,
    )
