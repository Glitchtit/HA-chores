"""Chores – Daily quest rotations.

Every morning each person gets three rotating bonus objectives. Completing
all three within the same day awards a flat XP + pet-shop token bonus
(see ``BUNDLE_XP`` / ``BUNDLE_TOKENS``).
"""

from __future__ import annotations
import logging
import random
from datetime import date, datetime

logger = logging.getLogger(__name__)

# Templates: (quest_type, label, icon, target, target_extra, weight)
# - "category" target_extra targets a specific chore category
# - "claim_three_today" counts any completions today
# - "streak_today" simply requires completing any chore today (streak-saver)
# Every template must be winnable by the player's own actions on any day: no
# intra-day deadlines and no "be first" races — those can soft/hard-lock the
# all-three bundle, so they were removed in 0.7.9.
QUEST_TEMPLATES = [
    ("category",          "Knock out a dishes chore",   "🍽️", 1, "dishes",   8),
    ("category",          "Knock out a laundry chore",  "🧺", 1, "laundry",  8),
    ("category",          "Knock out a cooking chore",  "🍳", 1, "cooking",  8),
    ("category",          "Knock out a cleaning chore", "🧹", 1, "cleaning", 8),
    ("claim_three_today", "Finish 3 chores today",      "💪", 3, "",         6),
    ("streak_today",      "Keep your streak alive",     "🔥", 1, "",         5),
]

# Reward for each individual quest completed: flat pet-shop tokens (coins).
QUEST_COIN_REWARD = 5

# Reward for completing all three quests in a single day: flat XP + tokens.
# This bundle bonus is granted *on top of* the per-quest coins above.
BUNDLE_XP = 30
BUNDLE_TOKENS = 10


def generate_for_today(conn, person_id: str, today: date | None = None, rng: random.Random | None = None) -> list[dict]:
    """Pick 3 weighted quest templates for *person_id* on *today* and insert them.

    Idempotent for a given day — re-running keeps the originally-generated trio.
    Returns the rows inserted (or already-present) for today.
    """
    today = today or date.today()
    today_str = today.isoformat()
    rng = rng or random.Random(f"{person_id}:{today_str}")  # deterministic per person/day

    existing = conn.execute(
        "SELECT * FROM daily_quests WHERE person_id = ? AND quest_date = ?",
        (person_id, today_str),
    ).fetchall()
    if existing:
        return [dict(r) for r in existing]

    # Weighted sample of 3 templates without replacement
    templates = list(QUEST_TEMPLATES)
    chosen: list[tuple] = []
    while len(chosen) < 3 and templates:
        weights = [t[5] for t in templates]
        pick = rng.choices(templates, weights=weights, k=1)[0]
        chosen.append(pick)
        templates.remove(pick)

    inserted = []
    for qtype, label, icon, target, extra, _w in chosen:
        cursor = conn.execute(
            """INSERT INTO daily_quests
                 (person_id, quest_date, quest_type, target, target_extra, progress)
               VALUES (?, ?, ?, ?, ?, 0)""",
            (person_id, today_str, qtype, target, extra),
        )
        inserted.append({
            "id": cursor.lastrowid,
            "person_id": person_id,
            "quest_date": today_str,
            "quest_type": qtype,
            "label": label,
            "icon": icon,
            "target": target,
            "target_extra": extra,
            "progress": 0,
            "completed_at": None,
        })
    conn.commit()
    logger.debug("Generated %d daily quests for %s on %s",
                 len(inserted), person_id, today_str)
    return inserted


def _label_for(quest_type: str, target_extra: str) -> tuple[str, str]:
    """Look up the canonical label/icon for a stored quest row."""
    for qtype, label, icon, _t, extra, _w in QUEST_TEMPLATES:
        if qtype == quest_type and extra == target_extra:
            return label, icon
    return quest_type, "🎯"


def list_for_today(conn, person_id: str, today: date | None = None) -> dict:
    """Return today's three quests plus bundle status. Generates rows if missing."""
    today = today or date.today()
    today_str = today.isoformat()
    rows = generate_for_today(conn, person_id, today=today)
    enriched = []
    for r in rows:
        # Rows from generate_for_today already include label/icon; DB rows don't.
        if "label" not in r:
            label, icon = _label_for(r["quest_type"], r.get("target_extra") or "")
            r = {**r, "label": label, "icon": icon}
        # Per-quest coin payout, so the UI can show what each quest is worth.
        r = {**r, "coin_reward": QUEST_COIN_REWARD}
        enriched.append(r)
    bundle = conn.execute(
        "SELECT all_complete_at FROM daily_quest_bundles WHERE person_id = ? AND quest_date = ?",
        (person_id, today_str),
    ).fetchone()
    return {
        "person_id": person_id,
        "quest_date": today_str,
        "quests": enriched,
        "bundle_awarded_at": bundle["all_complete_at"] if bundle else None,
        "coin_reward": QUEST_COIN_REWARD,
        "bundle_xp": BUNDLE_XP,
        "bundle_tokens": BUNDLE_TOKENS,
    }


def _quest_matches(quest: dict, chore_row, claimed: bool, before_noon: bool, chore_count_today: int) -> int:
    """How many points to add to *quest* given a single completion. Returns 0 if no match."""
    qtype = quest["quest_type"]
    extra = quest.get("target_extra") or ""
    if qtype == "category":
        return 1 if (chore_row and chore_row.get("category") == extra) else 0
    # claim_before_noon / first_two_today are no longer generated (removed in
    # 0.7.9), but their matchers stay so any quest rolled before the upgrade can
    # still complete for the rest of that day instead of stranding the bundle.
    if qtype == "claim_before_noon":
        return 1 if (claimed and before_noon) else 0
    if qtype == "first_two_today":
        # Counts every completion today up to target
        return 1
    if qtype == "claim_three_today":
        return 1
    if qtype == "streak_today":
        # First completion of the day satisfies it
        return 1 if chore_count_today == 1 else 0
    return 0


def bump_on_completion(conn, person_id: str, chore_row, completed_at: datetime | None = None) -> dict:
    """Increment any matching quests for the just-completed chore.

    Returns a summary dict ``{bumped: [...], quest_coins_awarded: int,
    bundle_awarded: bool, bundle_xp: int, bundle_tokens: int}``.
    *chore_row* may be a dict/Row with `category` and `assignment_mode` keys
    (mirrors what apply_completion already has on hand).
    """
    completed_at = completed_at or datetime.now()
    today = completed_at.date()
    today_str = today.isoformat()

    # Snapshot today's completions count for the streak_today / first_two_today checks
    chore_count_today = conn.execute(
        """SELECT COUNT(*) AS c FROM chore_instances
           WHERE completed_by = ? AND status = 'completed'
             AND date(completed_at) = ?""",
        (person_id, today_str),
    ).fetchone()["c"] or 0

    is_claim = bool(chore_row) and chore_row.get("assignment_mode") == "claim"
    before_noon = completed_at.hour < 12

    # Ensure today's quests exist
    generate_for_today(conn, person_id, today=today)

    rows = conn.execute(
        """SELECT * FROM daily_quests
           WHERE person_id = ? AND quest_date = ?""",
        (person_id, today_str),
    ).fetchall()

    bumped = []
    quest_coins_awarded = 0
    for row in rows:
        if row["completed_at"]:
            continue
        delta = _quest_matches(dict(row), chore_row or {}, is_claim, before_noon, chore_count_today)
        if delta <= 0:
            continue
        new_progress = min(row["progress"] + delta, row["target"])
        completed_flag = new_progress >= row["target"]
        completed_ts = completed_at.isoformat() if completed_flag else None
        conn.execute(
            "UPDATE daily_quests SET progress = ?, completed_at = ? WHERE id = ?",
            (new_progress, completed_ts, row["id"]),
        )
        bumped.append({"id": row["id"], "completed": completed_flag, "progress": new_progress})
        if completed_flag:
            # Per-quest coin payout. Each quest only flips to completed once (the
            # loop skips rows with a non-null completed_at), so this fires exactly
            # once per quest.
            quest_coins_awarded += QUEST_COIN_REWARD

    conn.commit()

    if quest_coins_awarded:
        from gamification import award_tokens
        award_tokens(person_id, quest_coins_awarded, reason="daily quest")

    # All-complete bundle reward
    counts = conn.execute(
        """SELECT
             COUNT(*) AS total,
             SUM(CASE WHEN completed_at IS NOT NULL THEN 1 ELSE 0 END) AS done
           FROM daily_quests
           WHERE person_id = ? AND quest_date = ?""",
        (person_id, today_str),
    ).fetchone()

    bundle_awarded = False
    bundle_xp = 0
    bundle_tokens = 0
    if counts and counts["total"] >= 3 and (counts["done"] or 0) >= 3:
        existing_bundle = conn.execute(
            "SELECT 1 FROM daily_quest_bundles WHERE person_id = ? AND quest_date = ?",
            (person_id, today_str),
        ).fetchone()
        if not existing_bundle:
            conn.execute(
                """INSERT INTO daily_quest_bundles (person_id, quest_date, all_complete_at)
                   VALUES (?, ?, ?)""",
                (person_id, today_str, completed_at.isoformat()),
            )
            conn.commit()
            # Skip the XP→token mint so the advertised "+10 tokens" stays literal.
            from gamification import add_xp, award_tokens
            add_xp(person_id, BUNDLE_XP, mint_tokens=False)
            award_tokens(person_id, BUNDLE_TOKENS, reason="daily quest bundle")
            bundle_awarded = True
            bundle_xp = BUNDLE_XP
            bundle_tokens = BUNDLE_TOKENS
            logger.info("Daily quest bundle awarded to %s on %s (+%d XP, +%d tokens)",
                        person_id, today_str, BUNDLE_XP, BUNDLE_TOKENS)

    return {
        "bumped": bumped,
        "quest_coins_awarded": quest_coins_awarded,
        "bundle_awarded": bundle_awarded,
        "bundle_xp": bundle_xp,
        "bundle_tokens": bundle_tokens,
    }


def generate_for_all_today(conn, today: date | None = None) -> int:
    """Scheduler entry: ensure every person has today's quests. Idempotent."""
    today = today or date.today()
    persons = conn.execute("SELECT entity_id FROM persons").fetchall()
    generated = 0
    for p in persons:
        rows = generate_for_today(conn, p["entity_id"], today=today)
        if rows:
            generated += 1
    return generated
