"""Chores – Pet state logic (happiness, cleanliness, mood, household aggregate).

Cleanliness is NOT stored; it's derived from `chore_instances.status='overdue'` on
read so it can't drift. Happiness is persisted (accumulates from bumps, decays
daily).
"""

from __future__ import annotations

import sqlite3

# ── Tuning constants (one-line changes for later balance work) ────────────────
HAPPINESS_BUMP = 5
HAPPINESS_OVERDUE_BONUS = 2
HAPPINESS_DAILY_DECAY = 3
CLEANLINESS_PER_OVERDUE = 10

CATEGORIES = ("dishes", "laundry", "cleaning", "trash", "cooking", "other")
DESIGNS = ("orange_black", "blue_black")
DEFAULT_DESIGN = "orange_black"


def _empty_mess_counts() -> dict[str, int]:
    return {c: 0 for c in CATEGORIES}


# ── Happiness ─────────────────────────────────────────────────────────────────

def ensure_pet(conn: sqlite3.Connection, person_id: str) -> None:
    """Create a pet_states row for this person if one doesn't exist."""
    conn.execute(
        "INSERT OR IGNORE INTO pet_states (person_id) VALUES (?)",
        (person_id,),
    )
    conn.commit()


def bump_happiness(
    conn: sqlite3.Connection,
    person_id: str,
    *,
    was_overdue: bool = False,
) -> int:
    """Increase this pet's happiness after a chore completion.

    Returns the new clamped happiness value.
    """
    ensure_pet(conn, person_id)
    row = conn.execute(
        "SELECT happiness FROM pet_states WHERE person_id = ?", (person_id,)
    ).fetchone()
    current = row["happiness"] if row else 80
    delta = HAPPINESS_BUMP + (HAPPINESS_OVERDUE_BONUS if was_overdue else 0)
    new_val = min(100, current + delta)
    conn.execute(
        """UPDATE pet_states
           SET happiness = ?,
               last_bump_at = CURRENT_TIMESTAMP,
               last_tick_at = CURRENT_TIMESTAMP
           WHERE person_id = ?""",
        (new_val, person_id),
    )
    conn.commit()
    return new_val


def decay_all(conn: sqlite3.Connection) -> int:
    """Apply daily happiness decay to every pet based on elapsed whole days since
    last_tick_at. Multi-day absences decay once, not compounded.

    Returns the number of pets that were decayed.
    """
    rows = conn.execute(
        """SELECT person_id, happiness,
                  CAST((julianday('now') - julianday(last_tick_at)) AS INTEGER) AS days_elapsed
           FROM pet_states"""
    ).fetchall()
    affected = 0
    for r in rows:
        days = max(0, int(r["days_elapsed"] or 0))
        if days < 1:
            continue
        new_val = max(0, (r["happiness"] or 0) - HAPPINESS_DAILY_DECAY * days)
        conn.execute(
            """UPDATE pet_states
               SET happiness = ?,
                   last_tick_at = CURRENT_TIMESTAMP
               WHERE person_id = ?""",
            (new_val, r["person_id"]),
        )
        affected += 1
    if affected:
        conn.commit()
    return affected


# ── Cleanliness (derived from chore_instances.status='overdue') ───────────────

def _mess_from_rows(rows) -> tuple[int, dict[str, int]]:
    counts = _empty_mess_counts()
    total = 0
    for r in rows:
        cat = r["category"] if "category" in r.keys() else None
        cat = cat if cat in counts else "other"
        counts[cat] += 1
        total += 1
    score = max(0, 100 - CLEANLINESS_PER_OVERDUE * total)
    return score, counts


def compute_cleanliness(
    conn: sqlite3.Connection, person_id: str
) -> tuple[int, dict[str, int]]:
    """Cleanliness score for one person. Only counts overdue instances assigned
    to them — unassigned overdue chores dirty only the shared household house."""
    rows = conn.execute(
        """SELECT c.category FROM chore_instances ci
           JOIN chores c ON ci.chore_id = c.id
           WHERE ci.status = 'overdue' AND ci.assigned_to = ?""",
        (person_id,),
    ).fetchall()
    return _mess_from_rows(rows)


def compute_household_cleanliness(
    conn: sqlite3.Connection,
) -> tuple[int, dict[str, int]]:
    """Shared-house cleanliness. Includes all overdue instances — assigned and
    unassigned. This is the 'common area' of the household view."""
    rows = conn.execute(
        """SELECT c.category FROM chore_instances ci
           JOIN chores c ON ci.chore_id = c.id
           WHERE ci.status = 'overdue'"""
    ).fetchall()
    return _mess_from_rows(rows)


# ── Mood ──────────────────────────────────────────────────────────────────────

def mood_from(happiness: int, cleanliness: int) -> str:
    """Server-side mood derivation so the HA sensor and UI agree."""
    avg = (happiness + cleanliness) / 2
    if avg >= 80:
        return "ecstatic"
    if avg >= 50:
        return "happy"
    if avg >= 30:
        return "meh"
    return "sad"


# ── Views ─────────────────────────────────────────────────────────────────────

def _pet_row(conn: sqlite3.Connection, person_id: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM pet_states WHERE person_id = ?", (person_id,)
    ).fetchone()


def set_design(conn: sqlite3.Connection, person_id: str, design: str) -> str:
    """Persist the chosen axolotl design for this person. Raises ValueError on
    an unknown design."""
    if design not in DESIGNS:
        raise ValueError(f"unknown pet design: {design!r}")
    ensure_pet(conn, person_id)
    conn.execute(
        "UPDATE pet_states SET pet_design = ? WHERE person_id = ?",
        (design, person_id),
    )
    conn.commit()
    return design


def set_name(conn: sqlite3.Connection, person_id: str, name: str) -> str | None:
    """Persist a custom pet name for this person. Pass empty string to clear."""
    ensure_pet(conn, person_id)
    stored = name.strip() if name else None
    conn.execute(
        "UPDATE pet_states SET pet_name = ? WHERE person_id = ?",
        (stored, person_id),
    )
    conn.commit()
    return stored


def _state_design(state: sqlite3.Row | None) -> str:
    if state is None:
        return DEFAULT_DESIGN
    # Row access via key is tolerant of missing columns on very old rows.
    try:
        val = state["pet_design"]
    except (IndexError, KeyError):
        val = None
    return val if val in DESIGNS else DEFAULT_DESIGN


def get_pet_view(conn: sqlite3.Connection, person_id: str) -> dict:
    """Build the per-person pet response."""
    ensure_pet(conn, person_id)
    state = _pet_row(conn, person_id)
    happiness = state["happiness"] if state else 80
    emoji = state["pet_emoji"] if state else "🐶"
    last_bump = state["last_bump_at"] if state else None
    pet_name = state["pet_name"] if state else None
    cleanliness, mess_counts = compute_cleanliness(conn, person_id)
    return {
        "person_id": person_id,
        "pet_emoji": emoji,
        "pet_design": _state_design(state),
        "pet_name": pet_name,
        "happiness": happiness,
        "cleanliness": cleanliness,
        "mess_counts": mess_counts,
        "mood": mood_from(happiness, cleanliness),
        "last_bump_at": last_bump,
    }


def get_household_view(conn: sqlite3.Connection) -> dict:
    """Build the household response — per-person pets + shared-house aggregate."""
    persons = conn.execute(
        "SELECT entity_id FROM persons ORDER BY name ASC"
    ).fetchall()
    pets = [get_pet_view(conn, p["entity_id"]) for p in persons]
    shared_score, shared_counts = compute_household_cleanliness(conn)
    return {
        "pets": pets,
        "shared": {
            "cleanliness": shared_score,
            "mess_counts": shared_counts,
        },
    }
