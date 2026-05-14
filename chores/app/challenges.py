"""Chores – Team household challenges (v0.4.6).

A challenge is a household-wide weekly co-op goal. On completion every person
gets a 24h 1.5× XP power-up (via the existing `person_powerups` table).
"""

from __future__ import annotations
import json
import logging
import random
from datetime import date, datetime, timedelta

logger = logging.getLogger(__name__)

# Weekly challenge templates used when auto_generate_weekly_challenge is enabled.
# Each template is a dict ready to insert into household_challenges (period_*
# computed by the scheduler).
WEEKLY_TEMPLATES = [
    {
        "name": "Marathon Week",
        "description": "Complete 30 chores together this week",
        "goal_type": "completions_total",
        "goal_value": 30,
        "target_category": "",
    },
    {
        "name": "Dish Domination",
        "description": "Knock out 10 dish chores this week",
        "goal_type": "category_total",
        "goal_value": 10,
        "target_category": "dishes",
    },
    {
        "name": "Laundry Landslide",
        "description": "Tackle 8 laundry chores this week",
        "goal_type": "category_total",
        "goal_value": 8,
        "target_category": "laundry",
    },
    {
        "name": "Spotless Sprint",
        "description": "10 cleaning chores together this week",
        "goal_type": "category_total",
        "goal_value": 10,
        "target_category": "cleaning",
    },
    {
        "name": "XP Avalanche",
        "description": "Earn 300 XP across the household this week",
        "goal_type": "xp_total",
        "goal_value": 300,
        "target_category": "",
    },
    {
        "name": "Free-Pickers",
        "description": "Claim 10 unassigned chores this week",
        "goal_type": "claims_total",
        "goal_value": 10,
        "target_category": "",
    },
]

CHALLENGE_REWARD_POWERUP = {
    "powerup_type": "challenge_reward",
    "name": "Team Bonus",
    "icon": "🎉",
    "description": "Household co-op victory — 1.5× XP for 24 hours",
}


def get_active(conn) -> dict | None:
    """Return the currently-active challenge (status='active' and within period)."""
    today_str = date.today().isoformat()
    row = conn.execute(
        """SELECT * FROM household_challenges
           WHERE status = 'active' AND period_start <= ? AND period_end >= ?
           ORDER BY id DESC LIMIT 1""",
        (today_str, today_str),
    ).fetchone()
    return dict(row) if row else None


def recompute_progress(conn, challenge: dict) -> int:
    """Recompute the *progress* aggregate for the given challenge from chore_instances.

    Updates the row and returns the new value.
    """
    start = challenge["period_start"]
    end = challenge["period_end"]
    gtype = challenge["goal_type"]
    cat = challenge.get("target_category") or ""

    if gtype == "completions_total":
        cnt = conn.execute(
            """SELECT COUNT(*) AS c FROM chore_instances
               WHERE status = 'completed'
                 AND date(completed_at) BETWEEN ? AND ?""",
            (start, end),
        ).fetchone()["c"] or 0
    elif gtype == "category_total":
        cnt = conn.execute(
            """SELECT COUNT(*) AS c FROM chore_instances ci
               JOIN chores c ON ci.chore_id = c.id
               WHERE ci.status = 'completed'
                 AND date(ci.completed_at) BETWEEN ? AND ?
                 AND c.category = ?""",
            (start, end, cat),
        ).fetchone()["c"] or 0
    elif gtype == "xp_total":
        cnt = conn.execute(
            """SELECT COALESCE(SUM(xp_awarded), 0) AS c FROM chore_instances
               WHERE status = 'completed'
                 AND date(completed_at) BETWEEN ? AND ?""",
            (start, end),
        ).fetchone()["c"] or 0
    elif gtype == "claims_total":
        cnt = conn.execute(
            """SELECT COUNT(*) AS c FROM chore_instances ci
               JOIN chores c ON ci.chore_id = c.id
               WHERE ci.status = 'completed'
                 AND date(ci.completed_at) BETWEEN ? AND ?
                 AND c.assignment_mode = 'claim'""",
            (start, end),
        ).fetchone()["c"] or 0
    else:
        return challenge.get("progress") or 0

    conn.execute(
        "UPDATE household_challenges SET progress = ? WHERE id = ?",
        (cnt, challenge["id"]),
    )
    conn.commit()
    return cnt


def _award_household_powerup(conn, challenge: dict) -> int:
    """Insert a 24h 1.5× XP power-up for every person. Returns count inserted."""
    persons = conn.execute("SELECT entity_id FROM persons").fetchall()
    if not persons:
        return 0
    expires_at = (datetime.now() + timedelta(hours=int(challenge["reward_hours"] or 24))).isoformat()
    mult = float(challenge["reward_multiplier"] or 1.5)
    inserted = 0
    for p in persons:
        conn.execute(
            """INSERT INTO person_powerups
                 (person_id, powerup_type, name, icon, description, applies_to,
                  multiplier, uses_remaining, expires_at)
               VALUES (?, ?, ?, ?, ?, 'any', ?, 999, ?)""",
            (
                p["entity_id"],
                CHALLENGE_REWARD_POWERUP["powerup_type"],
                CHALLENGE_REWARD_POWERUP["name"],
                CHALLENGE_REWARD_POWERUP["icon"],
                CHALLENGE_REWARD_POWERUP["description"]
                + f" (from “{challenge['name']}”)",
                mult,
                expires_at,
            ),
        )
        # Celebration popup per person
        payload = {
            "challenge_completed": {
                "id": challenge["id"],
                "name": challenge["name"],
                "multiplier": mult,
                "hours": int(challenge["reward_hours"] or 24),
            },
            "source": "challenge",
            "completed_at": datetime.now().isoformat(),
        }
        conn.execute(
            "INSERT INTO pending_celebrations (person_id, payload) VALUES (?, ?)",
            (p["entity_id"], json.dumps(payload)),
        )
        inserted += 1
    conn.commit()
    return inserted


def bump_progress(conn, *, completed_by: str, chore_category: str | None, xp: int) -> dict | None:
    """Update active-challenge progress after a chore completion.

    Returns the challenge row if the bump caused it to flip to completed,
    along with the side-effect (powerup awards). Otherwise None.
    """
    challenge = get_active(conn)
    if not challenge:
        return None

    gtype = challenge["goal_type"]
    cat = challenge.get("target_category") or ""
    delta = 0
    if gtype == "completions_total":
        delta = 1
    elif gtype == "category_total":
        delta = 1 if (chore_category and chore_category == cat) else 0
    elif gtype == "xp_total":
        delta = max(0, xp or 0)
    elif gtype == "claims_total":
        # Caller passes None for chore_category if the chore isn't a 'claim' mode
        # so we approximate with a re-aggregation: cheaper to recompute.
        delta = 0
    if delta <= 0 and gtype != "claims_total":
        return None

    if gtype == "claims_total":
        new_progress = recompute_progress(conn, challenge)
    else:
        new_progress = (challenge["progress"] or 0) + delta
        conn.execute(
            "UPDATE household_challenges SET progress = ? WHERE id = ?",
            (new_progress, challenge["id"]),
        )
        conn.commit()

    if new_progress >= (challenge["goal_value"] or 0) and challenge["status"] == "active":
        conn.execute(
            "UPDATE household_challenges SET status = 'completed' WHERE id = ?",
            (challenge["id"],),
        )
        conn.commit()
        _award_household_powerup(conn, challenge)
        return {**challenge, "progress": new_progress, "status": "completed"}
    return None


def _next_week_period(today: date) -> tuple[str, str]:
    """Return (Mon ISO, Sun ISO) for the week containing *today*."""
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    return monday.isoformat(), sunday.isoformat()


def tick(conn, today: date | None = None) -> dict:
    """Scheduler entry: expire ended challenges and auto-create a fresh weekly
    one when configured to do so. Idempotent for a given day."""
    today = today or date.today()
    today_str = today.isoformat()
    results = {"expired": 0, "created": 0}

    # Expire any active challenge whose period has ended without completion
    cursor = conn.execute(
        "UPDATE household_challenges SET status = 'expired' WHERE status = 'active' AND period_end < ?",
        (today_str,),
    )
    conn.commit()
    results["expired"] = cursor.rowcount or 0

    # Auto-generate weekly?
    cfg = conn.execute(
        "SELECT value FROM config WHERE key = 'auto_generate_weekly_challenge'"
    ).fetchone()
    enabled = True
    if cfg:
        try:
            enabled = bool(json.loads(cfg["value"]))
        except Exception:
            enabled = cfg["value"] in ("1", "true", "True")

    if not enabled:
        return results

    existing = conn.execute(
        """SELECT 1 FROM household_challenges
           WHERE status IN ('active', 'completed') AND period_start <= ? AND period_end >= ?
           LIMIT 1""",
        (today_str, today_str),
    ).fetchone()
    if existing:
        return results

    period_start, period_end = _next_week_period(today)
    template = random.Random(f"weekly:{period_start}").choice(WEEKLY_TEMPLATES)
    conn.execute(
        """INSERT INTO household_challenges
             (name, description, goal_type, goal_value, target_category,
              period_start, period_end, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, 'active')""",
        (
            template["name"],
            template["description"],
            template["goal_type"],
            template["goal_value"],
            template["target_category"],
            period_start,
            period_end,
        ),
    )
    conn.commit()
    results["created"] = 1
    logger.info("Auto-generated weekly challenge %r (%s → %s)",
                template["name"], period_start, period_end)
    return results
