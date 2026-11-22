"""Undo for a chore completion.

A completion touches XP, streaks, tokens, badges, power-ups, pets, quests,
challenges and bosses. Instead of reversing each rule, the rows it can touch
are snapshotted before and after it runs. Undo puts back only what differs
between the two: rows it inserted are deleted, rows it deleted come back, and
columns it changed get their old value. Anything else is left alone, so other
people's actions in the meantime survive. If something it changed has changed
again since, undo is refused rather than overwrite that. Also refused once a
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
# Popups the completion queued go with it, whether or not they were seen.
_DELETE_EVEN_IF_CHANGED = {"pending_celebrations"}

CHANGED_SINCE = "Something else changed since this completion; cannot undo it safely."


def _tables(conn, today: str) -> dict:
    # JSON round trip so these compare equal to what was stored.
    return json.loads(dumps({
        table: [dict(r) for r in conn.execute(
            f"SELECT * FROM {table} WHERE {where}", {"today": today}
        ).fetchall()]
        for table, _, where in _TABLES
    }))


def snapshot(conn, instance_row) -> dict:
    """Everything a completion of `instance_row` may change, before it runs."""
    today = date.today().isoformat()
    return {"today": today, "instance": dict(instance_row), "tables": _tables(conn, today)}


def record_after(conn, snap: dict) -> None:
    """Add the same rows as they are after the completion."""
    snap["after"] = _tables(conn, snap["today"])


def _keyed(rows, pk) -> dict:
    return {tuple(r[c] for c in pk): r for r in rows}


def _where(pk) -> str:
    return " AND ".join(f"{c} = ?" for c in pk)


def undo_completion(conn, instance_id: int, snap: dict, *, remove_instance: bool) -> None:
    """Put back what the completion changed. Raises ValueError with the reason it cannot."""
    inst = conn.execute(
        "SELECT * FROM chore_instances WHERE id = ?", (instance_id,)
    ).fetchone()
    if inst is None or inst["status"] != "completed":
        raise ValueError("That chore is not completed.")
    if "after" not in snap:
        # 0.8.12-0.8.14 kept only the before state, which can't tell the
        # completion's changes from anyone else's.
        raise ValueError("This completion was logged by an older version and cannot be undone.")
    if datetime.fromisoformat(inst["completed_at"]) < datetime.now() - timedelta(minutes=UNDO_MINUTES):
        raise ValueError(f"Only completions from the last {UNDO_MINUTES} minutes can be undone.")
    later = conn.execute(
        "SELECT 1 FROM chore_instances WHERE status = 'completed' AND completed_at > ? AND id != ?",
        (inst["completed_at"], instance_id),
    ).fetchone()
    if later:
        raise ValueError("Another chore was completed after this one; undo that first.")

    now = _tables(conn, snap["today"])
    writes = []  # (sql, params), run only once every table has been checked
    for table, pk, _ in _TABLES:
        pre = _keyed(snap["tables"].get(table, []), pk)
        post = _keyed(snap["after"].get(table, []), pk)
        cur = _keyed(now[table], pk)
        for key in pre.keys() | post.keys():
            before, after, current = pre.get(key), post.get(key), cur.get(key)
            if before == after:
                continue
            if before is None:  # inserted by the completion
                if table in _NEVER_DELETE:
                    continue
                if current != after and table not in _DELETE_EVEN_IF_CHANGED:
                    raise ValueError(CHANGED_SINCE)
                writes.append((f"DELETE FROM {table} WHERE {_where(pk)}", key))
            elif after is None:  # deleted by the completion
                if current is not None:
                    raise ValueError(CHANGED_SINCE)
                cols = list(before)
                writes.append((
                    f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join('?' for _ in cols)})",
                    tuple(before[c] for c in cols),
                ))
            else:  # changed by the completion
                changed = [c for c in before if before[c] != after.get(c)]
                if current is None or any(current.get(c) != after.get(c) for c in changed):
                    raise ValueError(CHANGED_SINCE)
                writes.append((
                    f"UPDATE {table} SET {', '.join(f'{c} = ?' for c in changed)} WHERE {_where(pk)}",
                    tuple(before[c] for c in changed) + key,
                ))

    with conn:
        for sql, params in writes:
            conn.execute(sql, params)

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
