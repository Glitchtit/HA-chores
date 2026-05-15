"""Chores – Assignment and completion endpoints."""

from __future__ import annotations
import json
import logging
from datetime import date, datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks
from models import ChoreInstance, InstanceCreate, InstanceComplete, InstanceClaim, CompleteResult, BadgeResult, PowerUp
from database import get_connection
from gamification import calculate_xp, update_streak, add_xp, check_and_award_badges, award_levelup_powerup, apply_powerup_to_xp
import pets
from notifications import (
    notify_chore_assigned,
    notify_badge_earned,
    notify_level_up,
)

logger = logging.getLogger(__name__)
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
        SELECT ci.*, c.name as chore_name, c.icon as chore_icon, c.difficulty as chore_difficulty, c.assignment_mode as chore_assignment_mode, c.xp_reward as chore_xp_reward
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
    """Get today's chore instances, including overdue ones from previous days."""
    today = date.today().isoformat()
    conn = get_connection()
    query = """
        SELECT ci.*, c.name as chore_name, c.icon as chore_icon, c.difficulty as chore_difficulty,
               c.assignment_mode as chore_assignment_mode, c.xp_reward as chore_xp_reward
        FROM chore_instances ci
        JOIN chores c ON ci.chore_id = c.id
        WHERE ci.status IN ('pending', 'claimed', 'overdue')
          AND ci.due_date <= ?
    """
    params: list = [today]
    if person:
        query += " AND (ci.assigned_to = ? OR ci.assigned_to IS NULL)"
        params.append(person)
    query += " ORDER BY ci.due_date ASC, c.name ASC"
    rows = conn.execute(query, params).fetchall()
    return [_row_to_instance(r) for r in rows]


@router.post("/", response_model=ChoreInstance, status_code=201)
async def create_instance(body: InstanceCreate, bg: BackgroundTasks):
    """Manually create a chore instance."""
    conn = get_connection()
    # Verify chore exists
    chore = conn.execute("SELECT * FROM chores WHERE id = ?", (body.chore_id,)).fetchone()
    if not chore:
        raise HTTPException(404, "Chore not found")

    cursor = conn.execute(
        """INSERT INTO chore_instances (chore_id, due_date, assigned_to, status, created_by)
           VALUES (?, ?, ?, 'pending', ?)""",
        (body.chore_id, body.due_date, body.assigned_to, body.created_by),
    )
    conn.commit()
    instance_id = cursor.lastrowid

    # Suppress the "assigned" notification when a user assigns a chore to themselves
    # (self-managed chores don't need a ping — the user already knows).
    if body.assigned_to and body.assigned_to != body.created_by:
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
    if row["status"] not in ("pending", "overdue"):
        raise HTTPException(400, "Can only claim pending instances")
    if row["assigned_to"] and row["assigned_to"] != body.person_id:
        raise HTTPException(400, "Instance already assigned to someone else")

    conn.execute(
        """UPDATE chore_instances
           SET assigned_to = ?, status = 'claimed',
               created_by = COALESCE(created_by, ?)
           WHERE id = ?""",
        (body.person_id, body.person_id, instance_id),
    )
    conn.commit()

    updated = conn.execute(
        """SELECT ci.*, c.name as chore_name, c.icon as chore_icon, c.difficulty as chore_difficulty, c.assignment_mode as chore_assignment_mode
           FROM chore_instances ci JOIN chores c ON ci.chore_id = c.id
           WHERE ci.id = ?""",
        (instance_id,),
    ).fetchone()
    return _row_to_instance(updated)


def apply_completion(
    conn,
    instance_row,
    completed_by: str,
    notes: str,
    *,
    bg: BackgroundTasks | None,
    suppress_followup: bool = False,
) -> dict:
    """Shared completion logic. Returns the same dict shape as CompleteResult."""
    row = instance_row
    if row["status"] == "completed":
        raise HTTPException(400, "Already completed")

    was_overdue = row["status"] == "overdue"

    person = conn.execute(
        "SELECT * FROM persons WHERE entity_id = ?", (completed_by,)
    ).fetchone()
    streak = person["current_streak"] if person else 0
    old_level = person["level"] if person else 1
    old_xp_total = person["xp_total"] if person else 0
    old_stage = pets.compute_stage(old_xp_total)

    early = date.fromisoformat(row["due_date"]) > date.today()
    claimed = row["assignment_mode"] == "claim" and row["assigned_to"] == completed_by
    try:
        chore_category = row["chore_category"]
    except (IndexError, KeyError):
        chore_category = None
    class_id = None
    if person:
        try:
            class_id = person["class_id"]
        except (IndexError, KeyError):
            class_id = None
    xp = calculate_xp(
        base_xp=row["xp_reward"],
        streak=streak,
        early=early,
        claimed=claimed,
        category=chore_category,
        class_id=class_id,
    )

    difficulty = row["chore_difficulty"] or "medium"
    powerup_multiplier, consumed_powerup = apply_powerup_to_xp(completed_by, difficulty)
    if powerup_multiplier != 1.0:
        xp = max(1, int(xp * powerup_multiplier))

    now = datetime.now().isoformat()
    conn.execute(
        """UPDATE chore_instances
           SET status = 'completed', completed_at = ?, completed_by = ?,
               xp_awarded = ?, notes = ?
           WHERE id = ?""",
        (now, completed_by, xp, notes, row["id"]),
    )
    conn.commit()

    new_streak, _ = update_streak(completed_by)
    new_total, new_level, leveled_up = add_xp(completed_by, xp)

    earned_powerup = None
    if leveled_up:
        try:
            earned_powerup = award_levelup_powerup(completed_by, new_level)
        except Exception as e:
            logger.warning("Failed to award level-up power-up: %s", e)

    try:
        pets.ensure_pet(conn, completed_by)
        old_happiness = conn.execute(
            "SELECT happiness FROM pet_states WHERE person_id = ?",
            (completed_by,),
        ).fetchone()
        prev_happiness = old_happiness["happiness"] if old_happiness else 80
        new_happiness = pets.bump_happiness(conn, completed_by, was_overdue=was_overdue)
        pet_delta = new_happiness - prev_happiness
    except Exception as e:
        logger.warning("Failed to bump pet happiness: %s", e)
        new_happiness = None
        pet_delta = None

    new_badges = check_and_award_badges(completed_by)

    # Daily quest progress + possible bundle reward (v0.4.5)
    try:
        import quests as _quests
        chore_for_quests = {
            "category": chore_category,
            "assignment_mode": row["assignment_mode"],
        }
        quest_result = _quests.bump_on_completion(
            conn, completed_by, chore_for_quests, completed_at=datetime.fromisoformat(now)
        )
    except Exception as e:
        logger.warning("Daily quest bump failed for %s: %s", completed_by, e)
        quest_result = {"bumped": [], "bundle_awarded": False, "bundle_xp": 0, "bundle_tokens": 0}

    # Household challenge progress (v0.4.6)
    try:
        import challenges as _challenges
        challenge_completed = _challenges.bump_progress(
            conn,
            completed_by=completed_by,
            chore_category=chore_category,
            xp=xp,
        )
    except Exception as e:
        logger.warning("Challenge bump failed: %s", e)
        challenge_completed = None

    # Seasonal boss objective progress (v0.5.0)
    try:
        import bosses as _bosses
        boss_defeated = _bosses.bump_on_completion(conn, row["chore_id"])
    except Exception as e:
        logger.warning("Boss bump failed: %s", e)
        boss_defeated = None

    new_stage = pets.compute_stage(new_total)
    stage_changed = new_stage != old_stage

    # Class-pick prompt at level 5 — only if person hasn't picked one yet.
    from classes import CLASS_PICK_LEVEL as _PICK_LVL
    class_prompt = (
        leveled_up
        and old_level < _PICK_LVL <= new_level
        and not (class_id or "")
    )

    bundle_xp = int(quest_result.get("bundle_xp") or 0) if quest_result else 0
    bundle_tokens = int(quest_result.get("bundle_tokens") or 0) if quest_result else 0
    bundle_awarded = bool(quest_result and quest_result.get("bundle_awarded"))

    if leveled_up or new_badges or earned_powerup or stage_changed or class_prompt or bundle_awarded:
        payload = {
            "old_level": old_level,
            "new_level": new_level,
            "leveled_up": leveled_up,
            "new_badges": new_badges,
            "powerup_earned": earned_powerup,
            "pet_evolved": stage_changed,
            "old_stage": old_stage if stage_changed else None,
            "new_stage": new_stage if stage_changed else None,
            "class_pick_prompt": class_prompt,
            "daily_bundle": bundle_awarded,
            "daily_bundle_xp": bundle_xp,
            "daily_bundle_tokens": bundle_tokens,
            "source": "shopping-hook" if bg is None else "assignment",
            "completed_at": now,
        }
        try:
            conn.execute(
                "INSERT INTO pending_celebrations (person_id, payload) VALUES (?, ?)",
                (completed_by, json.dumps(payload, default=str)),
            )
            conn.commit()
        except Exception as e:
            logger.warning("Failed to write pending celebration for %s: %s",
                           completed_by, e)

    if bg is not None:
        for badge in new_badges:
            bg.add_task(
                notify_badge_earned, completed_by, badge["name"], badge["icon"]
            )
        if leveled_up:
            bg.add_task(notify_level_up, completed_by, new_level)

    updated = conn.execute(
        """SELECT ci.*, c.name as chore_name, c.icon as chore_icon, c.difficulty as chore_difficulty, c.assignment_mode as chore_assignment_mode
           FROM chore_instances ci JOIN chores c ON ci.chore_id = c.id
           WHERE ci.id = ?""",
        (row["id"],),
    ).fetchone()

    followup_name: str | None = None
    followup_chore_id = row["followup_chore_id"]
    if followup_chore_id and not suppress_followup:
        followup_chore = conn.execute(
            "SELECT * FROM chores WHERE id = ? AND active = 1", (followup_chore_id,)
        ).fetchone()
        if followup_chore:
            today_str = date.today().isoformat()
            already_exists = conn.execute(
                """SELECT id FROM chore_instances
                   WHERE chore_id = ? AND due_date = ? AND status IN ('pending', 'claimed')""",
                (followup_chore_id, today_str),
            ).fetchone()
            if not already_exists:
                conn.execute(
                    """INSERT INTO chore_instances (chore_id, due_date, assigned_to, status)
                       VALUES (?, ?, NULL, 'pending')""",
                    (followup_chore_id, today_str),
                )
                conn.commit()
                followup_name = followup_chore["name"]

    return {
        "instance": _row_to_instance(updated),
        "xp_awarded": xp,
        "leveled_up": leveled_up,
        "old_level": old_level,
        "new_level": new_level,
        "new_streak": new_streak,
        "new_badges": [BadgeResult(**b) for b in new_badges],
        "powerup_consumed": PowerUp(**consumed_powerup) if consumed_powerup else None,
        "powerup_earned": PowerUp(**earned_powerup) if earned_powerup else None,
        "followup_triggered": followup_name is not None,
        "followup_name": followup_name,
        "pet_happiness": new_happiness,
        "pet_delta": pet_delta,
        "pet_evolved": stage_changed,
        "pet_stage": new_stage,
    }


@router.post("/{instance_id}/complete", response_model=CompleteResult)
async def complete_instance(instance_id: int, body: InstanceComplete, bg: BackgroundTasks):
    """Mark a chore instance as completed, awarding XP and checking badges."""
    conn = get_connection()
    row = conn.execute(
        """SELECT ci.*, c.xp_reward, c.assignment_mode, c.difficulty as chore_difficulty,
                  c.category as chore_category, c.followup_chore_id
           FROM chore_instances ci JOIN chores c ON ci.chore_id = c.id
           WHERE ci.id = ?""",
        (instance_id,),
    ).fetchone()
    if not row:
        raise HTTPException(404, "Instance not found")
    return apply_completion(conn, row, body.completed_by, body.notes, bg=bg)


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
        """UPDATE chore_instances
           SET assigned_to = ?, created_by = COALESCE(created_by, ?)
           WHERE id = ?""",
        (body.person_id, body.assigned_by, instance_id),
    )
    conn.commit()

    # Skip the assigned notification when the assigner is also the assignee.
    if body.person_id != body.assigned_by:
        bg.add_task(notify_chore_assigned, body.person_id, row["chore_name"], row["due_date"])

    updated = conn.execute(
        """SELECT ci.*, c.name as chore_name, c.icon as chore_icon, c.difficulty as chore_difficulty, c.assignment_mode as chore_assignment_mode
           FROM chore_instances ci JOIN chores c ON ci.chore_id = c.id
           WHERE ci.id = ?""",
        (instance_id,),
    ).fetchone()
    return _row_to_instance(updated)
