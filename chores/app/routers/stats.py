"""Chores – Household statistics endpoints.

Powers the Stats tab: a Steam-style comparison matrix of how many times
each household member has completed each chore, and a per-day breakdown
of a month's completions for the calendar view.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from database import get_connection

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/matrix")
async def completion_matrix():
    """Per-chore, per-person completion counts across all time.

    Includes every active chore (so never-done chores show as zeros, like
    locked achievements) plus any inactive chore that still has recorded
    completions. Ordered by total completions, most-done first.
    """
    conn = get_connection()

    chores = conn.execute(
        "SELECT id, name, icon, category, active FROM chores"
    ).fetchall()

    counts = conn.execute(
        """SELECT chore_id, completed_by, COUNT(*) AS n
           FROM chore_instances
           WHERE status = 'completed' AND completed_by IS NOT NULL
           GROUP BY chore_id, completed_by"""
    ).fetchall()

    by_chore: dict[int, dict[str, int]] = {}
    for row in counts:
        by_chore.setdefault(row["chore_id"], {})[row["completed_by"]] = row["n"]

    out = []
    for c in chores:
        chore_counts = by_chore.get(c["id"], {})
        if not c["active"] and not chore_counts:
            continue
        out.append({
            "id": c["id"],
            "name": c["name"],
            "icon": c["icon"],
            "category": c["category"],
            "active": bool(c["active"]),
            "counts": chore_counts,
            "total": sum(chore_counts.values()),
        })

    out.sort(key=lambda ch: (-ch["total"], ch["name"].lower()))
    return {"chores": out}


@router.get("/calendar")
async def completion_calendar(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
):
    """All completions in a given month, grouped by day.

    `completed_at` is stored as a local-time ISO-8601 string (see
    assignments.apply_completion), so a string prefix match selects the
    month without any UTC/local conversion.
    """
    conn = get_connection()
    prefix = f"{year:04d}-{month:02d}-"

    rows = conn.execute(
        """SELECT substr(ci.completed_at, 1, 10) AS day,
                  ci.chore_id, ci.completed_by, ci.completed_at,
                  c.name AS chore_name, c.icon AS chore_icon
           FROM chore_instances ci
           JOIN chores c ON ci.chore_id = c.id
           WHERE ci.status = 'completed'
             AND ci.completed_by IS NOT NULL
             AND ci.completed_at LIKE ?
           ORDER BY ci.completed_at ASC""",
        (prefix + "%",),
    ).fetchall()

    days: dict[str, list[dict]] = {}
    for r in rows:
        days.setdefault(r["day"], []).append({
            "chore_id": r["chore_id"],
            "chore_name": r["chore_name"],
            "chore_icon": r["chore_icon"],
            "completed_by": r["completed_by"],
            "completed_at": r["completed_at"],
        })

    return {"year": year, "month": month, "days": days}
