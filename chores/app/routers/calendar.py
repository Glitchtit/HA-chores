"""Chores – Calendar sync and conflict detection endpoints."""

from __future__ import annotations
from fastapi import APIRouter
from database import get_connection
from ha_client import get_calendar_events

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


@router.get("/conflicts")
async def check_conflicts(
    calendar_entity: str,
    date: str,
    person: str | None = None,
):
    """Check HA calendar for events that might conflict with chores on a given date.

    Returns any HA calendar events on the target date so the UI can warn
    the user before scheduling a chore.
    """
    ha_events = await get_calendar_events(
        calendar_entity=calendar_entity,
        start=f"{date}T00:00:00",
        end=f"{date}T23:59:59",
    )

    # Get chore instances already scheduled for that date
    conn = get_connection()
    query = "SELECT ci.*, c.name as chore_name FROM chore_instances ci JOIN chores c ON ci.chore_id = c.id WHERE ci.due_date = ?"
    params = [date]
    if person:
        query += " AND ci.assigned_to = ?"
        params.append(person)

    existing_chores = conn.execute(query, params).fetchall()

    return {
        "date": date,
        "ha_calendar_events": [
            {
                "summary": e.get("summary", ""),
                "start": e.get("start", {}).get("dateTime", e.get("start", {}).get("date", "")),
                "end": e.get("end", {}).get("dateTime", e.get("end", {}).get("date", "")),
            }
            for e in ha_events
        ],
        "scheduled_chores": [
            {"id": c["id"], "name": c["chore_name"], "assigned_to": c["assigned_to"]}
            for c in existing_chores
        ],
        "has_conflicts": len(ha_events) > 0 and len(existing_chores) > 0,
    }


@router.get("/ha-calendars")
async def list_ha_calendars():
    """List available HA calendar entities for conflict detection."""
    import httpx
    import os

    token = os.environ.get("SUPERVISOR_TOKEN", "")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "http://supervisor/core/api/calendars",
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()
            return resp.json()
    except Exception:
        return []
