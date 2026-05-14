"""Chores – Seasonal boss chores (v0.5.0).

A boss event is a time-boxed limited event with 1–8 sub-objectives (each
backed by a real chore). When every objective reaches its target_count the
event transitions to 'defeated' and every household member receives the
configured cosmetic + commemorative badge.
"""

from __future__ import annotations
import json
import logging
from datetime import date, datetime

logger = logging.getLogger(__name__)


def get_active(conn) -> dict | None:
    """Return the currently-active boss event (within window, status='active')."""
    today_str = date.today().isoformat()
    row = conn.execute(
        """SELECT * FROM boss_events
           WHERE status = 'active' AND start_date <= ? AND end_date >= ?
           ORDER BY id DESC LIMIT 1""",
        (today_str, today_str),
    ).fetchone()
    return dict(row) if row else None


def get_with_objectives(conn, boss_id: int) -> dict | None:
    """Return a boss event row plus its objectives (with chore names)."""
    row = conn.execute("SELECT * FROM boss_events WHERE id = ?", (boss_id,)).fetchone()
    if not row:
        return None
    objs = conn.execute(
        """SELECT bo.id, bo.chore_id, bo.target_count, bo.progress, bo.sort_order,
                  c.name AS chore_name, c.icon AS chore_icon, c.category AS chore_category
           FROM boss_objectives bo
           JOIN chores c ON c.id = bo.chore_id
           WHERE bo.boss_id = ?
           ORDER BY bo.sort_order, bo.id""",
        (boss_id,),
    ).fetchall()
    return {**dict(row), "objectives": [dict(o) for o in objs]}


def _award_household_unlock(conn, boss: dict) -> int:
    """Grant the boss reward (cosmetic + badge) to every household member.

    Returns the number of persons who received the reward.
    """
    persons = conn.execute("SELECT entity_id FROM persons").fetchall()
    cosmetic_id = boss.get("reward_cosmetic_id")
    badge_id = boss.get("reward_badge_id")
    awarded = 0

    for p in persons:
        pid = p["entity_id"]
        if cosmetic_id:
            conn.execute(
                "INSERT OR IGNORE INTO person_cosmetics (person_id, cosmetic_id, equipped) VALUES (?, ?, 0)",
                (pid, cosmetic_id),
            )
        if badge_id:
            conn.execute(
                "INSERT OR IGNORE INTO person_badges (person_id, badge_id) VALUES (?, ?)",
                (pid, badge_id),
            )
        payload = {
            "boss_defeated": {
                "id": boss["id"],
                "name": boss["name"],
                "icon": boss.get("icon"),
                "reward_cosmetic_id": cosmetic_id,
                "reward_badge_id": badge_id,
            },
            "source": "boss",
            "completed_at": datetime.now().isoformat(),
        }
        conn.execute(
            "INSERT INTO pending_celebrations (person_id, payload) VALUES (?, ?)",
            (pid, json.dumps(payload)),
        )
        awarded += 1
    conn.commit()
    return awarded


def bump_on_completion(conn, chore_id: int) -> dict | None:
    """Increment any boss objective targeting *chore_id*. If the increment
    finishes the boss off, transition status and award rewards.

    Returns the boss row when the boss is defeated by this call, else None.
    """
    boss = get_active(conn)
    if not boss:
        return None
    obj = conn.execute(
        """SELECT * FROM boss_objectives
           WHERE boss_id = ? AND chore_id = ?
           LIMIT 1""",
        (boss["id"], chore_id),
    ).fetchone()
    if not obj:
        return None

    new_progress = min((obj["progress"] or 0) + 1, obj["target_count"])
    conn.execute(
        "UPDATE boss_objectives SET progress = ? WHERE id = ?",
        (new_progress, obj["id"]),
    )
    conn.commit()

    # Check victory
    counts = conn.execute(
        """SELECT COUNT(*) AS total,
                  SUM(CASE WHEN progress >= target_count THEN 1 ELSE 0 END) AS done
           FROM boss_objectives WHERE boss_id = ?""",
        (boss["id"],),
    ).fetchone()
    if counts and counts["total"] and counts["total"] == (counts["done"] or 0):
        # Idempotency: only transition once
        current = conn.execute(
            "SELECT status FROM boss_events WHERE id = ?", (boss["id"],)
        ).fetchone()
        if current and current["status"] == "active":
            conn.execute(
                "UPDATE boss_events SET status = 'defeated' WHERE id = ?",
                (boss["id"],),
            )
            conn.commit()
            _award_household_unlock(conn, boss)
            return {**boss, "status": "defeated"}
    return None


def tick(conn, today: date | None = None) -> dict:
    """Move events through state machine based on today's date.

    upcoming → active when start_date <= today
    active   → expired when end_date < today (and not defeated)
    """
    today = today or date.today()
    today_str = today.isoformat()
    activated = conn.execute(
        "UPDATE boss_events SET status = 'active' WHERE status = 'upcoming' AND start_date <= ? AND end_date >= ?",
        (today_str, today_str),
    ).rowcount or 0
    expired = conn.execute(
        "UPDATE boss_events SET status = 'expired' WHERE status IN ('upcoming', 'active') AND end_date < ?",
        (today_str,),
    ).rowcount or 0
    conn.commit()
    return {"activated": activated, "expired": expired}
