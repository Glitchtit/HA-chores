"""Chores – Gamification engine: XP, levels, streaks, badges."""

from __future__ import annotations
import json
import math
import logging
from datetime import date, datetime, timedelta

from database import get_connection

logger = logging.getLogger(__name__)

# ── Level calculation ────────────────────────────────────────────────────────

def xp_for_level(level: int) -> int:
    """Return the minimum XP required for a given level (linear: 100 XP per level)."""
    if level <= 1:
        return 0
    return (level - 1) * 100


def level_from_xp(xp: int) -> int:
    """Compute level from total XP: 100 XP per level, infinite levels."""
    if xp <= 0:
        return 1
    return xp // 100 + 1


# ── XP calculation ───────────────────────────────────────────────────────────

def calculate_xp(
    base_xp: int,
    streak: int = 0,
    early: bool = False,
    claimed: bool = False,
) -> int:
    """Compute actual XP with bonuses.

    - Streak bonus: +10% per day, capped at +100%
    - Early bird: +25% if completed before due date
    - Claim bonus: +15% if voluntarily claimed
    """
    multiplier = 1.0
    # Streak bonus: 10% per day, max 100%
    streak_bonus = min(streak * 0.10, 1.0)
    multiplier += streak_bonus
    if early:
        multiplier += 0.25
    if claimed:
        multiplier += 0.15
    return max(1, int(base_xp * multiplier))


# ── Streak management ────────────────────────────────────────────────────────

def update_streak(person_entity_id: str) -> tuple[int, int]:
    """Update a person's streak after a completion. Returns (new_streak, longest_streak)."""
    conn = get_connection()
    row = conn.execute(
        "SELECT current_streak, longest_streak, last_completion_date FROM persons WHERE entity_id = ?",
        (person_entity_id,),
    ).fetchone()
    if not row:
        return 0, 0

    current_streak = row["current_streak"]
    longest_streak = row["longest_streak"]
    last_date_str = row["last_completion_date"]
    today = date.today()

    if last_date_str:
        last_date = date.fromisoformat(last_date_str)
        delta = (today - last_date).days
        if delta == 0:
            # Already completed today, streak stays
            pass
        elif delta == 1:
            current_streak += 1
        else:
            # Streak broken
            current_streak = 1
    else:
        current_streak = 1

    longest_streak = max(longest_streak, current_streak)

    conn.execute(
        """UPDATE persons
           SET current_streak = ?, longest_streak = ?, last_completion_date = ?
           WHERE entity_id = ?""",
        (current_streak, longest_streak, today.isoformat(), person_entity_id),
    )
    conn.commit()
    return current_streak, longest_streak


def check_streak_at_risk(person_entity_id: str) -> bool:
    """Check if a person's streak is at risk (no completions today)."""
    conn = get_connection()
    row = conn.execute(
        "SELECT current_streak, last_completion_date FROM persons WHERE entity_id = ?",
        (person_entity_id,),
    ).fetchone()
    if not row or row["current_streak"] == 0:
        return False
    last_date_str = row["last_completion_date"]
    if not last_date_str:
        return False
    return date.fromisoformat(last_date_str) < date.today()


# ── Badge checking ───────────────────────────────────────────────────────────

# Condition types whose truth value can revert after being awarded
# (e.g. a new chore is added so all_types no longer holds;
#  speed_run window has long closed but was incorrectly awarded due to TZ bug).
REVOCABLE_CONDITIONS: frozenset[str] = frozenset({"all_types", "speed_run"})


def _eval_badge_condition(badge, person_entity_id: str, conn, *, person=None) -> bool:
    """Evaluate a single badge condition for a person. Returns True if met."""
    ctype  = badge["condition_type"]
    cval   = badge["condition_value"]
    try:
        cextra = badge["condition_extra"] or ""
    except (IndexError, KeyError):
        cextra = ""

    today    = date.today().isoformat()
    today_dt = date.today()

    if ctype == "badge_count":
        # Evaluated separately in check_and_award_badges; never revocable
        return False

    if ctype == "completions":
        cnt = conn.execute(
            "SELECT COUNT(*) FROM chore_instances WHERE completed_by = ? AND status = 'completed'",
            (person_entity_id,),
        ).fetchone()[0]
        return cnt >= cval

    if ctype == "streak":
        if person is None:
            person = conn.execute("SELECT * FROM persons WHERE entity_id = ?", (person_entity_id,)).fetchone()
        return bool(person and person["current_streak"] >= cval)

    if ctype == "level":
        if person is None:
            person = conn.execute("SELECT * FROM persons WHERE entity_id = ?", (person_entity_id,)).fetchone()
        return bool(person and person["level"] >= cval)

    if ctype == "daily_completions":
        cnt = conn.execute(
            "SELECT COUNT(*) FROM chore_instances WHERE completed_by = ? AND status = 'completed' AND date(completed_at) = ?",
            (person_entity_id, today),
        ).fetchone()[0]
        return cnt >= cval

    if ctype == "claims":
        cnt = conn.execute(
            """SELECT COUNT(*) FROM chore_instances ci
               JOIN chores c ON ci.chore_id = c.id
               WHERE ci.completed_by = ? AND ci.status = 'completed'
               AND c.assignment_mode = 'claim'""",
            (person_entity_id,),
        ).fetchone()[0]
        return cnt >= cval

    if ctype == "all_types":
        total = conn.execute("SELECT COUNT(*) FROM chores WHERE active = 1").fetchone()[0]
        done  = conn.execute(
            """SELECT COUNT(DISTINCT ci.chore_id) FROM chore_instances ci
               JOIN chores c ON ci.chore_id = c.id
               WHERE ci.completed_by = ? AND ci.status = 'completed' AND c.active = 1""",
            (person_entity_id,),
        ).fetchone()[0]
        return total > 0 and done >= total

    if ctype == "hour_before":
        cnt = conn.execute(
            """SELECT COUNT(*) FROM chore_instances
               WHERE completed_by = ? AND status = 'completed'
               AND CAST(strftime('%H', completed_at) AS INTEGER) < ?""",
            (person_entity_id, cval),
        ).fetchone()[0]
        return cnt > 0

    if ctype == "hour_after":
        cnt = conn.execute(
            """SELECT COUNT(*) FROM chore_instances
               WHERE completed_by = ? AND status = 'completed'
               AND CAST(strftime('%H', completed_at) AS INTEGER) >= ?""",
            (person_entity_id, cval),
        ).fetchone()[0]
        return cnt > 0

    if ctype == "hour_range":
        try:
            end_hour = int(cextra)
        except (ValueError, TypeError):
            return False
        cnt = conn.execute(
            """SELECT COUNT(*) FROM chore_instances
               WHERE completed_by = ? AND status = 'completed'
               AND CAST(strftime('%H', completed_at) AS INTEGER) >= ?
               AND CAST(strftime('%H', completed_at) AS INTEGER) < ?""",
            (person_entity_id, cval, end_hour),
        ).fetchone()[0]
        return cnt > 0

    if ctype == "midnight_count":
        cnt = conn.execute(
            """SELECT COUNT(*) FROM chore_instances
               WHERE completed_by = ? AND status = 'completed'
               AND CAST(strftime('%H', completed_at) AS INTEGER) < 4""",
            (person_entity_id,),
        ).fetchone()[0]
        return cnt >= cval

    if ctype == "calendar_date":
        # Only valid on the specific calendar date — treat as permanent once earned
        today_mmdd = today_dt.strftime("%m-%d")
        if today_mmdd != cextra:
            return True  # Don't revoke snapshot badges on other days
        cnt = conn.execute(
            """SELECT COUNT(*) FROM chore_instances
               WHERE completed_by = ? AND status = 'completed'
               AND date(completed_at) = ?""",
            (person_entity_id, today),
        ).fetchone()[0]
        return cnt > 0

    if ctype == "weekend_both":
        cnt = conn.execute(
            """SELECT COUNT(DISTINCT strftime('%w', completed_at)) FROM chore_instances
               WHERE completed_by = ? AND status = 'completed'
               AND strftime('%w', completed_at) IN ('0', '6')
               AND date(completed_at) >= date('now', '-14 days')""",
            (person_entity_id,),
        ).fetchone()[0]
        return cnt >= 2

    if ctype == "friday_night":
        cnt = conn.execute(
            """SELECT COUNT(*) FROM chore_instances
               WHERE completed_by = ? AND status = 'completed'
               AND strftime('%w', completed_at) = '5'
               AND CAST(strftime('%H', completed_at) AS INTEGER) >= 23""",
            (person_entity_id,),
        ).fetchone()[0]
        return cnt > 0

    if ctype == "monday_early":
        cnt = conn.execute(
            """SELECT COUNT(*) FROM chore_instances
               WHERE completed_by = ? AND status = 'completed'
               AND strftime('%w', completed_at) = '1'
               AND CAST(strftime('%H', completed_at) AS INTEGER) < 7""",
            (person_entity_id,),
        ).fetchone()[0]
        return cnt > 0

    if ctype == "sunday_early":
        cnt = conn.execute(
            """SELECT COUNT(*) FROM chore_instances
               WHERE completed_by = ? AND status = 'completed'
               AND strftime('%w', completed_at) = '0'
               AND CAST(strftime('%H', completed_at) AS INTEGER) < 9""",
            (person_entity_id,),
        ).fetchone()[0]
        return cnt > 0

    if ctype == "speed_run":
        cutoff = (datetime.now() - timedelta(minutes=10)).isoformat()
        cnt = conn.execute(
            """SELECT COUNT(*) FROM chore_instances
               WHERE completed_by = ? AND status = 'completed'
               AND completed_at >= ?""",
            (person_entity_id, cutoff),
        ).fetchone()[0]
        return cnt >= cval

    if ctype == "late_complete":
        cnt = conn.execute(
            """SELECT COUNT(*) FROM chore_instances
               WHERE completed_by = ? AND status = 'completed'
               AND due_date < date(completed_at)""",
            (person_entity_id,),
        ).fetchone()[0]
        return cnt >= cval

    if ctype == "days_since_first":
        row = conn.execute(
            """SELECT julianday('now') - julianday(MIN(completed_at)) as days
               FROM chore_instances
               WHERE completed_by = ? AND status = 'completed'""",
            (person_entity_id,),
        ).fetchone()
        if row and row[0] is not None:
            return row[0] >= cval
        return False

    if ctype == "midnight_window":
        cnt = conn.execute(
            """SELECT COUNT(*) FROM chore_instances
               WHERE completed_by = ? AND status = 'completed'
               AND (
                   (CAST(strftime('%H', completed_at) AS INTEGER) = 23
                    AND CAST(strftime('%M', completed_at) AS INTEGER) >= 55)
                   OR
                   (CAST(strftime('%H', completed_at) AS INTEGER) = 0
                    AND CAST(strftime('%M', completed_at) AS INTEGER) <= 5)
               )""",
            (person_entity_id,),
        ).fetchone()[0]
        return cnt > 0

    # Unknown condition type — leave badge as-is
    return True


def validate_and_revoke_badges(person_entity_id: str | None = None) -> int:
    """Re-evaluate all earned revocable badges and remove any that no longer qualify.

    Pass *person_entity_id* to check a single person, or None to check everyone.
    Returns the total number of badges revoked.
    """
    conn = get_connection()
    if person_entity_id:
        pids = [person_entity_id]
    else:
        pids = [r["entity_id"] for r in conn.execute("SELECT entity_id FROM persons").fetchall()]

    revoked = 0
    placeholders = ",".join(f"'{c}'" for c in REVOCABLE_CONDITIONS)
    for p_id in pids:
        earned = conn.execute(
            f"""SELECT pb.badge_id, b.condition_type, b.condition_value, b.condition_extra
                FROM person_badges pb
                JOIN badges b ON b.id = pb.badge_id
                WHERE pb.person_id = ? AND b.condition_type IN ({placeholders})""",
            (p_id,),
        ).fetchall()
        for badge in earned:
            if not _eval_badge_condition(badge, p_id, conn):
                conn.execute(
                    "DELETE FROM person_badges WHERE person_id = ? AND badge_id = ?",
                    (p_id, badge["badge_id"]),
                )
                revoked += 1
                logger.info("Revoked badge '%s' from %s (condition no longer met)", badge["badge_id"], p_id)
    if revoked:
        conn.commit()
    return revoked


def check_and_award_badges(person_entity_id: str) -> list[dict]:
    """Check all badge conditions for a person and award any earned badges.

    Returns list of newly earned badges.
    """
    conn = get_connection()
    person = conn.execute(
        "SELECT * FROM persons WHERE entity_id = ?", (person_entity_id,)
    ).fetchone()
    if not person:
        return []

    # Already-earned badge IDs
    earned = {
        r["badge_id"]
        for r in conn.execute(
            "SELECT badge_id FROM person_badges WHERE person_id = ?",
            (person_entity_id,),
        ).fetchall()
    }

    badges = conn.execute("SELECT * FROM badges").fetchall()

    # ── Main badge loop ──────────────────────────────────────────────────────
    newly_earned: list[dict] = []

    for badge in badges:
        bid = badge["id"]
        if bid in earned:
            continue
        if badge["condition_type"] == "badge_count":
            continue
        if _eval_badge_condition(badge, person_entity_id, conn, person=person):
            conn.execute(
                "INSERT OR IGNORE INTO person_badges (person_id, badge_id) VALUES (?, ?)",
                (person_entity_id, badge["id"]),
            )
            newly_earned.append({
                "id": badge["id"],
                "name": badge["name"],
                "description": badge["description"] or "",
                "icon": badge["icon"],
            })

    # ── Second pass: badge_count (meta-achievement) ──────────────────────────
    newly_ids = {b["id"] for b in newly_earned}
    total_badges_now = len(earned) + len(newly_earned)
    for badge in badges:
        if badge["id"] in earned or badge["id"] in newly_ids:
            continue
        if badge["condition_type"] != "badge_count":
            continue
        if total_badges_now >= badge["condition_value"]:
            conn.execute(
                "INSERT OR IGNORE INTO person_badges (person_id, badge_id) VALUES (?, ?)",
                (person_entity_id, badge["id"]),
            )
            newly_earned.append({
                "id": badge["id"],
                "name": badge["name"],
                "description": badge["description"] or "",
                "icon": badge["icon"],
            })

    if newly_earned:
        conn.commit()
        logger.info(
            "Person %s earned badges: %s",
            person_entity_id,
            [b["id"] for b in newly_earned],
        )

    return newly_earned


def add_xp(person_entity_id: str, xp: int) -> tuple[int, int, bool]:
    """Add XP to a person, updating their level. Returns (new_total, new_level, leveled_up)."""
    conn = get_connection()
    row = conn.execute(
        "SELECT xp_total, level FROM persons WHERE entity_id = ?",
        (person_entity_id,),
    ).fetchone()
    if not row:
        return 0, 1, False

    new_total = row["xp_total"] + xp
    new_level = level_from_xp(new_total)
    leveled_up = new_level > row["level"]

    conn.execute(
        "UPDATE persons SET xp_total = ?, level = ? WHERE entity_id = ?",
        (new_total, new_level, person_entity_id),
    )
    conn.commit()
    return new_total, new_level, leveled_up
