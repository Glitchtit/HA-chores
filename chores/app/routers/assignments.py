"""Chores – Assignment and completion endpoints."""

from __future__ import annotations
import json
from datetime import date, datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks
from models import ChoreInstance, InstanceCreate, InstanceComplete, InstanceClaim, CompleteResult, BadgeResult
from database import get_connection
from gamification import calculate_xp, update_streak, add_xp, check_and_award_badges
from notifications import (
    notify_chore_assigned,
    notify_badge_earned,
    notify_level_up,
)

router = APIRouter(prefix="/api/assignments", tags=["assignments"])


def _row_to_instance(row) -> dict:
    d = {k: row[k] for k in row.keys()}
    return d


@router.get("/", response_model=list[ChoreInstance])
async def list_instances(
    status: str | None = None,
    person: str | None = None,
    due_date: str | None = None,
    include_chore: bool = True,
):
    """List chore instances with optional filters."""
    conn = get_connection()
    query = """
        SELECT ci.*, c.name as chore_name, c.icon as chore_icon, c.difficulty as chore_difficulty, c.assignment_mode as chore_assignment_mode
        FROM chore_instances ci
        JOIN chores c ON ci.chore_id = c.id
        WHERE 1=1
    """
    params: list = []

    if status:
        statuses = status.split(",")
        placeholders = ",".join("?" for _ in statuses)
        query += f" AND ci.status IN ({placeholders})"
        params.extend(statuses)
    if person:
        query += " AND (ci.assigned_to = ? OR ci.assigned_to IS NULL)"
        params.append(person)
    if due_date:
        query += " AND ci.due_date = ?"
        params.append(due_date)

    query += " ORDER BY ci.due_date ASC, c.name ASC"
    rows = conn.execute(query, params).fetchall()
    return [_row_to_instance(r) for r in rows]


@router.get("/today", response_model=list[ChoreInstance])
async def today_instances(person: str | None = None):
    """Get today's chore instances."""
    today = date.today().isoformat()
    return await list_instances(
        status="pending,claimed,overdue", person=person, due_date=today
    )


@router.post("/", response_model=ChoreInstance, status_code=201)
async def create_instance(body: InstanceCreate, bg: BackgroundTasks):
    """Manually create a chore instance."""
    conn = get_connection()
    # Verify chore exists
    chore = conn.execute("SELECT * FROM chores WHERE id = ?", (body.chore_id,)).fetchone()
    if not chore:
        raise HTTPException(404, "Chore not found")

    cursor = conn.execute(
        """INSERT INTO chore_instances (chore_id, due_date, assigned_to, status)
           VALUES (?, ?, ?, 'pending')""",
        (body.chore_id, body.due_date, body.assigned_to),
    )
    conn.commit()
    instance_id = cursor.lastrowid

    if body.assigned_to:
        bg.add_task(notify_chore_assigned, body.assigned_to, chore["name"], body.due_date)

    row = conn.execute(
        """SELECT ci.*, c.name as chore_name, c.icon as chore_icon, c.difficulty as chore_difficulty, c.assignment_mode as chore_assignment_mode
           FROM chore_instances ci JOIN chores c ON ci.chore_id = c.id
           WHERE ci.id = ?""",
        (instance_id,),
    ).fetchone()
    return _row_to_instance(row)


@router.post("/{instance_id}/claim", response_model=ChoreInstance)
async def claim_instance(instance_id: int, body: InstanceClaim):
    """Claim an unassigned chore instance."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM chore_instances WHERE id = ?", (instance_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Instance not found")
    if row["status"] not in ("pending",):
        raise HTTPException(400, "Can only claim pending instances")
    if row["assigned_to"] and row["assigned_to"] != body.person_id:
        raise HTTPException(400, "Instance already assigned to someone else")

    conn.execute(
        "UPDATE chore_instances SET assigned_to = ?, status = 'claimed' WHERE id = ?",
        (body.person_id, instance_id),
    )
    conn.commit()

    updated = conn.execute(
        """SELECT ci.*, c.name as chore_name, c.icon as chore_icon, c.difficulty as chore_difficulty, c.assignment_mode as chore_assignment_mode
           FROM chore_instances ci JOIN chores c ON ci.chore_id = c.id
           WHERE ci.id = ?""",
        (instance_id,),
    ).fetchone()
    return _row_to_instance(updated)


@router.post("/{instance_id}/complete", response_model=CompleteResult)
async def complete_instance(instance_id: int, body: InstanceComplete, bg: BackgroundTasks):
    """Mark a chore instance as completed, awarding XP and checking badges."""
    conn = get_connection()
    row = conn.execute(
        """SELECT ci.*, c.xp_reward, c.assignment_mode
           FROM chore_instances ci JOIN chores c ON ci.chore_id = c.id
           WHERE ci.id = ?""",
        (instance_id,),
    ).fetchone()
    if not row:
        raise HTTPException(404, "Instance not found")
    if row["status"] == "completed":
        raise HTTPException(400, "Already completed")

    # Get person's current streak and level for XP calculation
    person = conn.execute(
        "SELECT * FROM persons WHERE entity_id = ?", (body.completed_by,)
    ).fetchone()
    streak = person["current_streak"] if person else 0
    old_level = person["level"] if person else 1

    # Calculate XP with bonuses
    early = date.fromisoformat(row["due_date"]) > date.today()
    claimed = row["assignment_mode"] == "claim" and row["assigned_to"] == body.completed_by
    xp = calculate_xp(
        base_xp=row["xp_reward"],
        streak=streak,
        early=early,
        claimed=claimed,
    )

    now = datetime.now().isoformat()
    conn.execute(
        """UPDATE chore_instances
           SET status = 'completed', completed_at = ?, completed_by = ?,
               xp_awarded = ?, notes = ?
           WHERE id = ?""",
        (now, body.completed_by, xp, body.notes, instance_id),
    )
    conn.commit()

    # Update streak and add XP
    new_streak, _ = update_streak(body.completed_by)
    new_total, new_level, leveled_up = add_xp(body.completed_by, xp)

    # Check for new badges
    new_badges = check_and_award_badges(body.completed_by)
    for badge in new_badges:
        bg.add_task(
            notify_badge_earned, body.completed_by, badge["name"], badge["icon"]
        )
    if leveled_up:
        bg.add_task(notify_level_up, body.completed_by, new_level)

    updated = conn.execute(
        """SELECT ci.*, c.name as chore_name, c.icon as chore_icon, c.difficulty as chore_difficulty, c.assignment_mode as chore_assignment_mode
           FROM chore_instances ci JOIN chores c ON ci.chore_id = c.id
           WHERE ci.id = ?""",
        (instance_id,),
    ).fetchone()
    return {
        "instance": _row_to_instance(updated),
        "xp_awarded": xp,
        "leveled_up": leveled_up,
        "old_level": old_level,
        "new_level": new_level,
        "new_streak": new_streak,
        "new_badges": [BadgeResult(**b) for b in new_badges],
    }


@router.post("/{instance_id}/skip", response_model=ChoreInstance)
async def skip_instance(instance_id: int):
    """Skip a chore instance (no XP awarded)."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM chore_instances WHERE id = ?", (instance_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Instance not found")
    if row["status"] == "completed":
        raise HTTPException(400, "Cannot skip a completed instance")

    conn.execute(
        "UPDATE chore_instances SET status = 'skipped' WHERE id = ?",
        (instance_id,),
    )
    conn.commit()

    updated = conn.execute(
        """SELECT ci.*, c.name as chore_name, c.icon as chore_icon, c.difficulty as chore_difficulty, c.assignment_mode as chore_assignment_mode
           FROM chore_instances ci JOIN chores c ON ci.chore_id = c.id
           WHERE ci.id = ?""",
        (instance_id,),
    ).fetchone()
    return _row_to_instance(updated)


@router.post("/{instance_id}/assign", response_model=ChoreInstance)
async def assign_instance(instance_id: int, body: InstanceClaim, bg: BackgroundTasks):
    """Manually assign an instance to a person."""
    conn = get_connection()
    row = conn.execute(
        """SELECT ci.*, c.name as chore_name
           FROM chore_instances ci JOIN chores c ON ci.chore_id = c.id
           WHERE ci.id = ?""",
        (instance_id,),
    ).fetchone()
    if not row:
        raise HTTPException(404, "Instance not found")

    conn.execute(
        "UPDATE chore_instances SET assigned_to = ? WHERE id = ?",
        (body.person_id, instance_id),
    )
    conn.commit()

    bg.add_task(notify_chore_assigned, body.person_id, row["chore_name"], row["due_date"])

    updated = conn.execute(
        """SELECT ci.*, c.name as chore_name, c.icon as chore_icon, c.difficulty as chore_difficulty, c.assignment_mode as chore_assignment_mode
           FROM chore_instances ci JOIN chores c ON ci.chore_id = c.id
           WHERE ci.id = ?""",
        (instance_id,),
    ).fetchone()
    return _row_to_instance(updated)
