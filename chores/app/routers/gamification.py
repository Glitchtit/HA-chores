"""Chores – Gamification endpoints: leaderboard, badges, stats."""

from __future__ import annotations
from datetime import date
from fastapi import APIRouter, HTTPException
from models import (
    LeaderboardEntry, Leaderboard, Badge, PersonBadgeStatus, PersonStats, BadgeEarned,
    MonthEndCheck, MonthEndEntry,
)
from database import get_connection

router = APIRouter(prefix="/api/gamification", tags=["gamification"])

_MONTH_NAMES = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def _current_month_str() -> str:
    """Return current month as 'YYYY-MM'."""
    return date.today().strftime("%Y-%m")


def _prev_month_str() -> str:
    """Return previous calendar month as 'YYYY-MM'."""
    today = date.today()
    if today.month == 1:
        return f"{today.year - 1}-12"
    return f"{today.year}-{today.month - 1:02d}"


def _month_display_name(ym: str) -> str:
    """Convert 'YYYY-MM' to 'Month YYYY'."""
    try:
        year, month = ym.split("-")
        return f"{_MONTH_NAMES[int(month)]} {year}"
    except Exception:
        return ym


def _monthly_leaderboard_rows(conn, month_str: str):
    """Return rows ordered by monthly XP for the given YYYY-MM."""
    return conn.execute(
        """SELECT
               p.*,
               COALESCE(SUM(ci.xp_awarded), 0) AS xp_month,
               (SELECT COUNT(*) FROM person_badges pb WHERE pb.person_id = p.entity_id) AS badges_count
           FROM persons p
           LEFT JOIN chore_instances ci
               ON ci.completed_by = p.entity_id
               AND ci.status = 'completed'
               AND strftime('%Y-%m', ci.completed_at) = ?
           GROUP BY p.entity_id
           ORDER BY xp_month DESC""",
        (month_str,),
    ).fetchall()


@router.get("/leaderboard", response_model=Leaderboard)
async def leaderboard():
    conn = get_connection()
    month_str = _current_month_str()
    rows = _monthly_leaderboard_rows(conn, month_str)

    entries = []
    prev_xp = None
    rank = 0
    for i, row in enumerate(rows):
        if row["xp_month"] != prev_xp:
            rank = i + 1
            prev_xp = row["xp_month"]
        entries.append(LeaderboardEntry(
            entity_id=row["entity_id"],
            name=row["name"],
            avatar_url=row["avatar_url"],
            xp_total=row["xp_total"],
            xp_month=row["xp_month"],
            level=row["level"],
            current_streak=row["current_streak"],
            rank=rank,
            badges_count=row["badges_count"],
        ))
    return Leaderboard(entries=entries, period=month_str)


@router.get("/month-end-check/{entity_id}", response_model=MonthEndCheck)
async def month_end_check(entity_id: str):
    conn = get_connection()
    person = conn.execute(
        "SELECT last_month_end_seen FROM persons WHERE entity_id = ?", (entity_id,)
    ).fetchone()
    if not person:
        raise HTTPException(404, "Person not found")

    prev = _prev_month_str()
    last_seen = person["last_month_end_seen"] or ""

    # Don't show for brand-new persons (no seen date set yet) on their first open —
    # only show if they were active before (seen date is non-empty) and haven't seen this one,
    # OR if they completed any chores in the previous month.
    if last_seen == prev:
        return MonthEndCheck(pending=False, month="", month_name="", entries=[])

    # Check if there were any completions in prev month for any person
    rows = _monthly_leaderboard_rows(conn, prev)
    total_xp = sum(r["xp_month"] for r in rows)

    # If nobody earned anything AND person has never seen a month-end, skip
    if total_xp == 0 and not last_seen:
        return MonthEndCheck(pending=False, month="", month_name="", entries=[])

    # Build ranked entries for the overlay
    entries = []
    prev_xp = None
    rank = 0
    for i, row in enumerate(rows):
        if row["xp_month"] != prev_xp:
            rank = i + 1
            prev_xp = row["xp_month"]
        entries.append(MonthEndEntry(
            entity_id=row["entity_id"],
            name=row["name"],
            avatar_url=row["avatar_url"],
            xp_month=row["xp_month"],
            rank=rank,
        ))

    return MonthEndCheck(
        pending=True,
        month=prev,
        month_name=_month_display_name(prev),
        entries=entries,
    )


@router.post("/month-end-seen/{entity_id}")
async def month_end_seen(entity_id: str):
    conn = get_connection()
    prev = _prev_month_str()
    result = conn.execute(
        "UPDATE persons SET last_month_end_seen = ? WHERE entity_id = ?",
        (prev, entity_id),
    )
    conn.commit()
    if result.rowcount == 0:
        raise HTTPException(404, "Person not found")
    return {"ok": True}


@router.get("/badges", response_model=list[Badge])
async def list_badges():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM badges ORDER BY condition_value").fetchall()
    return [dict(r) for r in rows]


@router.get("/person/{entity_id}/badges", response_model=list[PersonBadgeStatus])
async def person_badges(entity_id: str):
    conn = get_connection()
    person = conn.execute(
        "SELECT * FROM persons WHERE entity_id = ?", (entity_id,)
    ).fetchone()
    if not person:
        raise HTTPException(404, "Person not found")

    badges = conn.execute("SELECT * FROM badges ORDER BY condition_value").fetchall()
    earned = {
        r["badge_id"]: r["earned_at"]
        for r in conn.execute(
            "SELECT badge_id, earned_at FROM person_badges WHERE person_id = ?",
            (entity_id,),
        ).fetchall()
    }

    result = []
    for b in badges:
        result.append(PersonBadgeStatus(
            badge=Badge(**dict(b)),
            earned=b["id"] in earned,
            earned_at=earned.get(b["id"]),
        ))
    return result


@router.get("/person/{entity_id}/stats", response_model=PersonStats)
async def person_stats(entity_id: str):
    conn = get_connection()
    person = conn.execute(
        "SELECT * FROM persons WHERE entity_id = ?", (entity_id,)
    ).fetchone()
    if not person:
        raise HTTPException(404, "Person not found")

    # Get rank (by monthly XP)
    month_str = _current_month_str()
    rank_row = conn.execute(
        """SELECT COUNT(*) + 1 AS rank
           FROM persons p2
           LEFT JOIN (
               SELECT completed_by, COALESCE(SUM(xp_awarded), 0) AS xp_month
               FROM chore_instances
               WHERE status = 'completed' AND strftime('%Y-%m', completed_at) = ?
               GROUP BY completed_by
           ) ci ON ci.completed_by = p2.entity_id
           WHERE COALESCE(ci.xp_month, 0) > (
               SELECT COALESCE(SUM(xp_awarded), 0)
               FROM chore_instances
               WHERE completed_by = ? AND status = 'completed'
               AND strftime('%Y-%m', completed_at) = ?
           )""",
        (month_str, entity_id, month_str),
    ).fetchone()

    # Get badges
    badge_rows = conn.execute(
        """SELECT b.id, b.name, b.icon, pb.earned_at
           FROM person_badges pb JOIN badges b ON pb.badge_id = b.id
           WHERE pb.person_id = ?
           ORDER BY pb.earned_at DESC""",
        (entity_id,),
    ).fetchall()

    # Count completions
    completions = conn.execute(
        "SELECT COUNT(*) as cnt FROM chore_instances WHERE completed_by = ? AND status = 'completed'",
        (entity_id,),
    ).fetchone()["cnt"]

    return PersonStats(
        **dict(person),
        rank=rank_row["rank"],
        badges=[BadgeEarned(**dict(r)) for r in badge_rows],
        completions_count=completions,
    )

