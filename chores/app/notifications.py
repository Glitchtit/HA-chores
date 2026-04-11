"""Chores – Notification dispatch via Home Assistant."""

from __future__ import annotations
import logging

from ha_client import send_notification

logger = logging.getLogger(__name__)


async def notify_chore_assigned(person_entity_id: str, chore_name: str, due_date: str) -> None:
    await send_notification(
        person_entity_id,
        title="🧹 New Chore Assigned",
        message=f"{chore_name} has been assigned to you! Due {due_date}",
    )


async def notify_chore_overdue(person_entity_id: str, chore_name: str) -> None:
    await send_notification(
        person_entity_id,
        title="⏰ Chore Overdue",
        message=f"{chore_name} is overdue! Complete it to keep your streak",
    )


async def notify_badge_earned(person_entity_id: str, badge_name: str, badge_icon: str) -> None:
    await send_notification(
        person_entity_id,
        title="🏆 Achievement Unlocked!",
        message=f"You earned: {badge_icon} {badge_name}!",
    )


async def notify_streak_warning(person_entity_id: str, streak_days: int) -> None:
    await send_notification(
        person_entity_id,
        title="🔥 Streak at Risk!",
        message=f"Your {streak_days}-day streak is about to break! Complete a chore today",
    )


async def notify_level_up(person_entity_id: str, new_level: int) -> None:
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
    await send_notification(
        person_entity_id,
        title="📊 Weekly Chores Summary",
        message=(
            f"This week: {completed}/{total} chores completed. "
            f"You earned {xp_earned} XP! "
            f"{leader_name} leads with {leader_xp} XP total."
        ),
    )
