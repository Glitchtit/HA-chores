"""Chores – Chore CRUD endpoints."""

from __future__ import annotations
import json
from fastapi import APIRouter, HTTPException
from models import ChoreCreate, ChoreUpdate, Chore
from database import get_connection
from scheduler import generate_instances
from gamification import validate_and_revoke_badges

router = APIRouter(prefix="/api/chores", tags=["chores"])


def _row_to_chore(row) -> dict:
    rotation = None
    if row["rotation_order"]:
        try:
            rotation = json.loads(row["rotation_order"])
        except (json.JSONDecodeError, TypeError):
            rotation = None
    return {
        **{k: row[k] for k in row.keys()},
        "rotation_order": rotation,
        "active": bool(row["active"]),
        "followup_chore_id": row["followup_chore_id"] if "followup_chore_id" in row.keys() else None,
    }


@router.get("/", response_model=list[Chore])
async def list_chores(active_only: bool = True):
    conn = get_connection()
    if active_only:
        rows = conn.execute("SELECT * FROM chores WHERE active = 1 ORDER BY name").fetchall()
    else:
        rows = conn.execute("SELECT * FROM chores ORDER BY name").fetchall()
    return [_row_to_chore(r) for r in rows]


@router.get("/{chore_id}", response_model=Chore)
async def get_chore(chore_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM chores WHERE id = ?", (chore_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Chore not found")
    return _row_to_chore(row)


@router.post("/", response_model=Chore, status_code=201)
async def create_chore(body: ChoreCreate):
    conn = get_connection()
    rotation_json = json.dumps(body.rotation_order) if body.rotation_order else None
    cursor = conn.execute(
        """INSERT INTO chores (name, description, icon, xp_reward, difficulty, category,
                               recurrence, estimated_minutes, assignment_mode, rotation_order,
                               followup_chore_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            body.name, body.description, body.icon, body.xp_reward,
            body.difficulty, body.category, body.recurrence, body.estimated_minutes,
            body.assignment_mode, rotation_json, body.followup_chore_id,
        ),
    )
    conn.commit()
    generate_instances(days_ahead=7)
    validate_and_revoke_badges()  # new chore may invalidate all_types badges
    return await get_chore(cursor.lastrowid)


@router.put("/{chore_id}", response_model=Chore)
async def update_chore(chore_id: int, body: ChoreUpdate):
    conn = get_connection()
    existing = conn.execute("SELECT * FROM chores WHERE id = ?", (chore_id,)).fetchone()
    if not existing:
        raise HTTPException(404, "Chore not found")

    updates = {}
    for field, value in body.model_dump(exclude_unset=True).items():
        if field == "rotation_order":
            updates["rotation_order"] = json.dumps(value) if value else None
        elif field == "active":
            updates["active"] = 1 if value else 0
        else:
            updates[field] = value

    if updates:
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [chore_id]
        conn.execute(
            f"UPDATE chores SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            values,
        )
        conn.commit()

    # Revalidate revocable badges since active chore count may have changed
    if "active" in (body.model_dump(exclude_unset=True)):
        validate_and_revoke_badges()

    return await get_chore(chore_id)


@router.delete("/{chore_id}", status_code=204)
async def delete_chore(chore_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM chores WHERE id = ?", (chore_id,))
    conn.commit()
