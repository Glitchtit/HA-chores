"""Chores – Recurring chore scheduler and rotation logic."""

from __future__ import annotations
import json
import logging
from datetime import date, datetime, timedelta

from database import get_connection

logger = logging.getLogger(__name__)


def parse_recurrence(recurrence: str) -> dict:
    """Parse a recurrence string into a structured dict.

    Formats:
      'daily'              → every day
      'weekly:mon,thu'     → every Monday and Thursday
      'monthly:1,15'       → 1st and 15th of each month
      'biweekly:even'      → every even ISO week number, on Friday
      'biweekly:odd'       → every odd ISO week number, on Friday
      'every:3'            → every 3 days
    """
    if not recurrence:
        return {"type": "none"}

    parts = recurrence.lower().split(":")
    rtype = parts[0].strip()

    if rtype == "daily":
        return {"type": "daily"}
    elif rtype == "weekly":
        days = [d.strip() for d in parts[1].split(",")] if len(parts) > 1 else ["mon"]
        return {"type": "weekly", "days": days}
    elif rtype == "monthly":
        dom = [int(d.strip()) for d in parts[1].split(",")] if len(parts) > 1 else [1]
        return {"type": "monthly", "days_of_month": dom}
    elif rtype == "biweekly":
        parity = parts[1].strip() if len(parts) > 1 else "even"
        return {"type": "biweekly", "parity": parity}
    elif rtype == "every":
        interval = int(parts[1]) if len(parts) > 1 else 1
        return {"type": "every", "interval": interval}
    else:
        logger.warning("Unknown recurrence format: %s", recurrence)
        return {"type": "none"}


DAY_MAP = {
    "mon": 0, "tue": 1, "wed": 2, "thu": 3,
    "fri": 4, "sat": 5, "sun": 6,
}


def should_schedule_on(recurrence: str, target_date: date) -> bool:
    """Check if a chore should have an instance on the given date."""
    spec = parse_recurrence(recurrence)
    rtype = spec["type"]

    if rtype == "none":
        return False
    elif rtype == "daily":
        return True
    elif rtype == "weekly":
        weekday = target_date.weekday()
        return any(DAY_MAP.get(d, -1) == weekday for d in spec["days"])
    elif rtype == "monthly":
        return target_date.day in spec["days_of_month"]
    elif rtype == "biweekly":
        if target_date.weekday() != 4:  # must be Friday
            return False
        iso_week = target_date.isocalendar()[1]
        if spec["parity"] == "even":
            return iso_week % 2 == 0
        else:
            return iso_week % 2 == 1
    elif rtype == "every":
        return True  # Interval checking needs a reference point (handled by caller)
    return False


def get_next_assignee(chore_id: int, rotation_order: list[str]) -> str | None:
    """Determine the next person in rotation for a chore.

    Looks at the last completed instance to find who was last, then
    rotates to the next person.
    """
    if not rotation_order:
        return None

    conn = get_connection()
    last = conn.execute(
        """SELECT assigned_to FROM chore_instances
           WHERE chore_id = ? AND status IN ('completed', 'overdue', 'skipped')
           ORDER BY due_date DESC LIMIT 1""",
        (chore_id,),
    ).fetchone()

    if not last or not last["assigned_to"]:
        return rotation_order[0]

    try:
        idx = rotation_order.index(last["assigned_to"])
        return rotation_order[(idx + 1) % len(rotation_order)]
    except ValueError:
        return rotation_order[0]


def generate_instances(days_ahead: int = 7) -> int:
    """Generate chore instances for the next N days.

    Skips dates where an instance already exists. Returns count created.
    """
    conn = get_connection()
    chores = conn.execute(
        "SELECT * FROM chores WHERE active = 1 AND recurrence IS NOT NULL"
    ).fetchall()

    today = date.today()
    created = 0

    for chore in chores:
        rotation_order = None
        if chore["rotation_order"]:
            try:
                rotation_order = json.loads(chore["rotation_order"])
            except (json.JSONDecodeError, TypeError):
                rotation_order = None

        for day_offset in range(days_ahead):
            target = today + timedelta(days=day_offset)
            target_str = target.isoformat()

            if not should_schedule_on(chore["recurrence"], target):
                continue

            # Check if instance already exists
            existing = conn.execute(
                "SELECT id FROM chore_instances WHERE chore_id = ? AND due_date = ?",
                (chore["id"], target_str),
            ).fetchone()
            if existing:
                continue

            # Purge stale overdue/pending instances from previous cycles before
            # creating the new one — prevents old missed entries piling up.
            conn.execute(
                """DELETE FROM chore_instances
                   WHERE chore_id = ? AND due_date < ? AND status IN ('overdue', 'pending')""",
                (chore["id"], today.isoformat()),
            )

            # Determine assignee
            assigned_to = None
            if chore["assignment_mode"] == "rotation" and rotation_order:
                assigned_to = get_next_assignee(chore["id"], rotation_order)
            # manual and claim modes leave assigned_to as None

            conn.execute(
                """INSERT INTO chore_instances (chore_id, due_date, assigned_to, status)
                   VALUES (?, ?, ?, 'pending')""",
                (chore["id"], target_str, assigned_to),
            )
            created += 1

    conn.commit()
    logger.info("Generated %d chore instances for next %d days", created, days_ahead)
    return created


def mark_overdue() -> int:
    """Mark past-due pending/claimed instances as overdue. Returns count."""
    conn = get_connection()
    today = date.today().isoformat()

    # Collect assigned persons for overdue notifications before updating
    about_to_be_overdue = conn.execute(
        """SELECT ci.assigned_to, c.name as chore_name
           FROM chore_instances ci
           JOIN chores c ON ci.chore_id = c.id
           WHERE ci.status IN ('pending', 'claimed')
           AND ci.due_date < ?
           AND ci.assigned_to IS NOT NULL""",
        (today,),
    ).fetchall()

    # Collect unassigned overdue instances — notify all persons
    unassigned_overdue = conn.execute(
        """SELECT c.name as chore_name
           FROM chore_instances ci
           JOIN chores c ON ci.chore_id = c.id
           WHERE ci.status IN ('pending', 'claimed')
           AND ci.due_date < ?
           AND ci.assigned_to IS NULL""",
        (today,),
    ).fetchall()

    all_persons = conn.execute("SELECT entity_id FROM persons").fetchall() if unassigned_overdue else []

    cursor = conn.execute(
        """UPDATE chore_instances
           SET status = 'overdue'
           WHERE status IN ('pending', 'claimed')
           AND due_date < ?""",
        (today,),
    )
    conn.commit()
    count = cursor.rowcount
    if count > 0:
        logger.info("Marked %d instances as overdue", count)

    targets = [{"person": r["assigned_to"], "chore_name": r["chore_name"]} for r in about_to_be_overdue]
    for inst in unassigned_overdue:
        for p in all_persons:
            targets.append({"person": p["entity_id"], "chore_name": inst["chore_name"]})

    return count, targets


def get_streak_at_risk_persons() -> list[dict]:
    """Return persons who have an active streak but haven't completed today."""
    conn = get_connection()
    today = date.today().isoformat()
    rows = conn.execute(
        """SELECT entity_id, name, current_streak
           FROM persons
           WHERE current_streak > 0
           AND (last_completion_date IS NULL OR last_completion_date < ?)""",
        (today,),
    ).fetchall()
    return [{"entity_id": r["entity_id"], "name": r["name"], "streak": r["current_streak"]} for r in rows]


def get_weekly_summary_data() -> list[dict]:
    """Compute weekly summary stats for each person."""
    conn = get_connection()
    week_start = (date.today() - timedelta(days=7)).isoformat()

    persons = conn.execute("SELECT entity_id, name, xp_total FROM persons").fetchall()
    if not persons:
        return []

    # Find leader
    leader = max(persons, key=lambda p: p["xp_total"])

    summaries = []
    for p in persons:
        completed = conn.execute(
            """SELECT COUNT(*) as cnt FROM chore_instances
               WHERE completed_by = ? AND status = 'completed'
               AND completed_at >= ?""",
            (p["entity_id"], week_start),
        ).fetchone()["cnt"]

        total = conn.execute(
            """SELECT COUNT(*) as cnt FROM chore_instances
               WHERE (assigned_to = ? OR completed_by = ?)
               AND due_date >= ?""",
            (p["entity_id"], p["entity_id"], week_start),
        ).fetchone()["cnt"]

        xp_earned = conn.execute(
            """SELECT COALESCE(SUM(xp_awarded), 0) as total FROM chore_instances
               WHERE completed_by = ? AND status = 'completed'
               AND completed_at >= ?""",
            (p["entity_id"], week_start),
        ).fetchone()["total"]

        summaries.append({
            "entity_id": p["entity_id"],
            "completed": completed,
            "total": max(total, completed),
            "xp_earned": xp_earned,
            "leader_name": leader["name"],
            "leader_xp": leader["xp_total"],
        })

    return summaries


def check_perfect_week(person_entity_id: str) -> bool:
    """Check if a person completed all assigned chores for the past 7 days."""
    conn = get_connection()
    week_start = (date.today() - timedelta(days=7)).isoformat()

    assigned = conn.execute(
        """SELECT COUNT(*) as cnt FROM chore_instances
           WHERE assigned_to = ? AND due_date >= ? AND due_date < ?""",
        (person_entity_id, week_start, date.today().isoformat()),
    ).fetchone()["cnt"]

    if assigned == 0:
        return False

    completed = conn.execute(
        """SELECT COUNT(*) as cnt FROM chore_instances
           WHERE assigned_to = ? AND due_date >= ? AND due_date < ?
           AND status = 'completed'""",
        (person_entity_id, week_start, date.today().isoformat()),
    ).fetchone()["cnt"]

    return completed >= assigned
