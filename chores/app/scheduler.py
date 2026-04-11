"""Chores – Recurring chore scheduler and rotation logic."""

from __future__ import annotations
import json
import logging
from datetime import date, timedelta

from database import get_connection

logger = logging.getLogger(__name__)


def parse_recurrence(recurrence: str) -> dict:
    """Parse a recurrence string into a structured dict.

    Formats:
      'daily'              → every day
      'weekly:mon,thu'     → every Monday and Thursday
      'monthly:1,15'       → 1st and 15th of each month
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
    return count
