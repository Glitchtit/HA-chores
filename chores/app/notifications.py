"""Chores – Notification dispatch via Home Assistant."""

from __future__ import annotations
import json
import logging

from ha_client import send_notification

logger = logging.getLogger(__name__)


def get_notif_config(key: str, default: dict, person_entity_id: str | None = None) -> dict:
    """Read a notification config entry from the DB, merged with defaults.

    Looks up ``{key}:{person_entity_id}`` first (per-person), then falls back
    to the global ``{key}`` entry, then to *default*.
    """
    try:
        from database import get_connection
        conn = get_connection()
        lookup_keys = []
        if person_entity_id:
            lookup_keys.append(f"{key}:{person_entity_id}")
        lookup_keys.append(key)
        for k in lookup_keys:
            row = conn.execute(
                "SELECT value FROM config WHERE key = ?", (k,)
            ).fetchone()
            if row and row["value"]:
                stored = json.loads(row["value"])
                return {**default, **stored}
    except Exception as e:
        logger.warning("Could not read notif config %s: %s", key, e)
    return default


async def notify_chore_assigned(person_entity_id: str, chore_name: str, due_date: str) -> None:
    cfg = get_notif_config("notif_assigned", {"enabled": True}, person_entity_id)
    if not cfg.get("enabled"):
        return
    await send_notification(
        person_entity_id,
        title="🧹 New Chore Assigned",
        message=f"{chore_name} has been assigned to you! Due {due_date}",
    )


async def notify_chore_overdue(person_entity_id: str, chore_name: str) -> None:
    cfg = get_notif_config("notif_overdue", {"enabled": True}, person_entity_id)
    if not cfg.get("enabled"):
        return
    await send_notification(
        person_entity_id,
        title="⏰ Chore Overdue",
        message=f"{chore_name} is overdue! Complete it to keep your streak",
    )


async def notify_badge_earned(person_entity_id: str, badge_name: str, badge_icon: str) -> None:
    cfg = get_notif_config("notif_badge", {"enabled": True}, person_entity_id)
    if not cfg.get("enabled"):
        return
    await send_notification(
        person_entity_id,
        title="🏆 Achievement Unlocked!",
        message=f"You earned: {badge_icon} {badge_name}!",
    )


async def notify_streak_warning(person_entity_id: str, streak_days: int) -> None:
    cfg = get_notif_config("notif_streak", {"enabled": True, "hour": 18}, person_entity_id)
    if not cfg.get("enabled"):
        return
    await send_notification(
        person_entity_id,
        title="🔥 Streak at Risk!",
        message=f"Your {streak_days}-day streak is about to break! Complete a chore today",
    )


async def notify_level_up(person_entity_id: str, new_level: int) -> None:
    cfg = get_notif_config("notif_levelup", {"enabled": True}, person_entity_id)
    if not cfg.get("enabled"):
        return
    await send_notification(
        person_entity_id,
        title="📈 Level Up!",
        message=f"Congratulations! You reached level {new_level}!",
    )


async def notify_weekly_summary(
    person_entity_id: str,
    completed: int,
    total: int,
    xp_earned: int,
    leader_name: str,
    leader_xp: int,
) -> None:
    cfg = get_notif_config("notif_weekly", {"enabled": True, "weekday": 0, "hour": 9}, person_entity_id)
    if not cfg.get("enabled"):
        return
    await send_notification(
        person_entity_id,
        title="📊 Weekly Chores Summary",
        message=(
            f"This week: {completed}/{total} chores completed. "
            f"You earned {xp_earned} XP! "
            f"{leader_name} leads with {leader_xp} XP total."
        ),
    )


async def notify_chore_reminder(person_entity_id: str, chore_name: str, due_date: str, day_before: bool) -> None:
    cfg = get_notif_config("notif_reminder", {"enabled": True, "when": "day_of", "hour": 8}, person_entity_id)
    if not cfg.get("enabled"):
        return
    timing = "tomorrow" if day_before else "today"
    await send_notification(
        person_entity_id,
        title="🔔 Chore Reminder",
        message=f"Don't forget: {chore_name} is due {timing} ({due_date})",
    )
