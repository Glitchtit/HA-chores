"""Chores – Calendar sync endpoints."""

from __future__ import annotations
from fastapi import APIRouter
from database import get_connection

router = APIRouter(prefix="/api/calendar", tags=["calendar"])


@router.get("/events")
async def get_events(start: str | None = None, end: str | None = None):
    """Get chore instances as calendar events."""
    conn = get_connection()
    query = """
        SELECT ci.*, c.name as chore_name, c.icon as chore_icon
        FROM chore_instances ci
        JOIN chores c ON ci.chore_id = c.id
        WHERE 1=1
    """
    params: list = []
    if start:
        query += " AND ci.due_date >= ?"
        params.append(start)
    if end:
        query += " AND ci.due_date <= ?"
        params.append(end)

    query += " ORDER BY ci.due_date ASC"
    rows = conn.execute(query, params).fetchall()

    events = []
    for row in rows:
        status_color = {
            "completed": "#22c55e",
            "pending": "#3b82f6",
            "claimed": "#f59e0b",
            "overdue": "#ef4444",
            "skipped": "#6b7280",
        }.get(row["status"], "#6b7280")

        events.append({
            "id": row["id"],
            "title": f"{row['chore_icon']} {row['chore_name']}",
            "start": row["due_date"],
            "end": row["due_date"],
            "color": status_color,
            "status": row["status"],
            "assigned_to": row["assigned_to"],
        })
    return events
