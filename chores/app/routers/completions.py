"""Chores – Recent-completion lookup for duplicate-attribution guard.

Returns the chore completions a given person has done in the last hour, so
clients can show an "are you sure?" confirmation before crediting them
again. Used by HA-stock's shopping-attribution modal (filtered to the
shopping + scan chore IDs) and by HA-chores' MyChores view (no filter).
"""

from __future__ import annotations
from datetime import datetime, timedelta
import logging

from fastapi import APIRouter, Query

from database import get_connection

router = APIRouter(prefix="/api/completions", tags=["completions"])
logger = logging.getLogger(__name__)

RECENT_WINDOW_HOURS = 1


@router.get("/recent")
async def list_recent_completions(
    person: str = Query(..., description="entity_id of the person to check"),
    chore_ids: str | None = Query(
        None,
        description="Optional comma-separated list of chore IDs to filter on",
    ),
):
    """Return completions by `person` within the last RECENT_WINDOW_HOURS hour(s).

    `completed_at` is stored as a Python local-time ISO-8601 string (see
    assignments.apply_completion), so we compute the cutoff in Python with
    the same basis to avoid SQLite UTC/local mismatches.
    """
    conn = get_connection()
    cutoff_dt = datetime.now() - timedelta(hours=RECENT_WINDOW_HOURS)
    cutoff = cutoff_dt.isoformat()

    query = (
        "SELECT ci.id AS instance_id, ci.chore_id, ci.completed_at, "
        "       c.name AS chore_name, c.icon AS chore_icon "
        "FROM chore_instances ci JOIN chores c ON ci.chore_id = c.id "
        "WHERE ci.completed_by = ? AND ci.status = 'completed' "
        "  AND ci.completed_at > ?"
    )
    params: list = [person, cutoff]

    if chore_ids:
        ids: list[int] = []
        for part in chore_ids.split(","):
            part = part.strip()
            if not part:
                continue
            try:
                ids.append(int(part))
            except ValueError:
                continue
        if ids:
            placeholders = ",".join("?" for _ in ids)
            query += f" AND ci.chore_id IN ({placeholders})"
            params.extend(ids)
        else:
            return []

    query += " ORDER BY ci.completed_at DESC LIMIT 20"

    rows = conn.execute(query, params).fetchall()
    now = datetime.now()
    out: list[dict] = []
    for r in rows:
        try:
            done_at = datetime.fromisoformat(r["completed_at"])
            minutes_ago = max(0, int((now - done_at).total_seconds() // 60))
        except (TypeError, ValueError):
            minutes_ago = None
        out.append({
            "instance_id": r["instance_id"],
            "chore_id": r["chore_id"],
            "chore_name": r["chore_name"],
            "chore_icon": r["chore_icon"],
            "completed_at": r["completed_at"],
            "minutes_ago": minutes_ago,
        })
    return out
