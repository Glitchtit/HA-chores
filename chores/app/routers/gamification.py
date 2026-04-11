"""Chores – Gamification endpoints: leaderboard, badges, stats."""

from __future__ import annotations
from fastapi import APIRouter, HTTPException
from models import (
    LeaderboardEntry, Leaderboard, Badge, PersonBadgeStatus, PersonStats, BadgeEarned,
)
from database import get_connection

router = APIRouter(prefix="/api/gamification", tags=["gamification"])


@router.get("/leaderboard", response_model=Leaderboard)
async def leaderboard():
    conn = get_connection()
    rows = conn.execute(
        """SELECT p.*,
                  (SELECT COUNT(*) FROM person_badges pb WHERE pb.person_id = p.entity_id) as badges_count
           FROM persons p
           ORDER BY p.xp_total DESC"""
    ).fetchall()

    entries = []
    prev_xp = None
    rank = 0
    for i, row in enumerate(rows):
        if row["xp_total"] != prev_xp:
            rank = i + 1  # standard competition ranking: skip ranks on tie
            prev_xp = row["xp_total"]
        entries.append(LeaderboardEntry(
            entity_id=row["entity_id"],
            name=row["name"],
            avatar_url=row["avatar_url"],
            xp_total=row["xp_total"],
            level=row["level"],
            current_streak=row["current_streak"],
            rank=rank,
            badges_count=row["badges_count"],
        ))
    return Leaderboard(entries=entries, period="all_time")


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

    # Get rank
    rank_row = conn.execute(
        """SELECT COUNT(*) + 1 as rank FROM persons
           WHERE xp_total > (SELECT xp_total FROM persons WHERE entity_id = ?)""",
        (entity_id,),
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
