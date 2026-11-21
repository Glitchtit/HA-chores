"""Undo for a chore completion.

A completion touches XP, streaks, tokens, badges, power-ups, pets, quests,
challenges and bosses. Instead of reversing each rule, the rows it can touch
are snapshotted before it runs and written back on undo. Writing back is only
safe while nothing else has changed those rows, so undo is refused once a
later completion exists or after UNDO_MINUTES.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta

UNDO_MINUTES = 60

# (table, primary key columns, row filter). Tables whose rows are parents of
# ON DELETE CASCADE children are only ever updated, never deleted from.
_TABLES = [
    ("persons", ("entity_id",), "1=1"),
    ("pet_states", ("person_id",), "1=1"),
    ("person_badges", ("person_id", "badge_id"), "1=1"),
    ("person_cosmetics", ("person_id", "cosmetic_id"), "1=1"),
    ("person_powerups", ("id",), "1=1"),
    ("pending_celebrations", ("id",), "1=1"),
    ("daily_quests", ("id",), "quest_date = :today"),
    ("daily_quest_bundles", ("person_id", "quest_date"), "quest_date = :today"),
    ("household_challenges", ("id",), "1=1"),
    ("boss_events", ("id",), "1=1"),
    ("boss_objectives", ("id",), "1=1"),
]
_NEVER_DELETE = {"persons", "household_challenges", "boss_events"}


def snapshot(conn, instance_row) -> dict:
    """Everything a completion of `instance_row` may change."""
    today = date.today().isoformat()
    tables = {
        table: [dict(r) for r in conn.execute(
            f"SELECT * FROM {table} WHERE {where}", {"today": today}
        ).fetchall()]
        for table, _, where in _TABLES
    }
    return {"today": today, "instance": dict(instance_row), "tables": tables}


def undo_completion(conn, instance_id: int, snap: dict, *, remove_instance: bool) -> None:
    """Write the snapshot back. Raises ValueError with the reason it cannot."""
    inst = conn.execute(
        "SELECT * FROM chore_instances WHERE id = ?", (instance_id,)
    ).fetchone()
    if inst is None or inst["status"] != "completed":
        raise ValueError("That chore is not completed.")
    if datetime.fromisoformat(inst["completed_at"]) < datetime.now() - timedelta(minutes=UNDO_MINUTES):
        raise ValueError(f"Only completions from the last {UNDO_MINUTES} minutes can be undone.")
    later = conn.execute(
        "SELECT 1 FROM chore_instances WHERE status = 'completed' AND completed_at > ? AND id != ?",
        (inst["completed_at"], instance_id),
    ).fetchone()
    if later:
        raise ValueError("Another chore was completed after this one; undo that first.")

    with conn:
        for table, pk, where in _TABLES:
            rows = snap["tables"].get(table, [])
            keep = {tuple(r[c] for c in pk) for r in rows}
            if table not in _NEVER_DELETE:
                current = conn.execute(
                    f"SELECT {', '.join(pk)} FROM {table} WHERE {where}",
                    {"today": snap["today"]},
                ).fetchall()
                for cur in current:
                    if tuple(cur) not in keep:
                        conn.execute(
                            f"DELETE FROM {table} WHERE "
                            + " AND ".join(f"{c} = ?" for c in pk),
                            tuple(cur),
                        )
            for r in rows:
                cols = list(r)
                updates = [c for c in cols if c not in pk]
                conn.execute(
                    f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join('?' for _ in cols)})"
                    f" ON CONFLICT ({', '.join(pk)}) DO "
                    + (f"UPDATE SET {', '.join(f'{c} = excluded.{c}' for c in updates)}" if updates else "NOTHING"),
                    tuple(r[c] for c in cols),
                )

        followup = snap.get("followup_instance_id")
        if followup:
            conn.execute(
                "DELETE FROM chore_instances WHERE id = ? AND status IN ('pending', 'claimed')",
                (followup,),
            )
        if remove_instance:
            conn.execute("DELETE FROM chore_instances WHERE id = ?", (instance_id,))
        else:
            before = snap["instance"]
            conn.execute(
                """UPDATE chore_instances
                   SET status = ?, completed_at = ?, completed_by = ?, xp_awarded = ?,
                       notes = ?, undo = NULL
                   WHERE id = ?""",
                (before["status"], before["completed_at"], before["completed_by"],
                 before["xp_awarded"], before["notes"], instance_id),
            )


def dumps(snap: dict) -> str:
    return json.dumps(snap, default=str)
