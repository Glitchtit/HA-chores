"""Chores – Pydantic request/response models."""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional


# ── Chore definitions ────────────────────────────────────────────────────────

class ChoreCreate(BaseModel):
    name: str
    description: str = ""
    icon: str = "🧹"
    xp_reward: int = 10
    difficulty: str = "medium"
    recurrence: Optional[str] = None
    estimated_minutes: Optional[int] = None
    assignment_mode: str = "manual"
    rotation_order: Optional[list[str]] = None


class ChoreUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    xp_reward: Optional[int] = None
    difficulty: Optional[str] = None
    recurrence: Optional[str] = None
    estimated_minutes: Optional[int] = None
    assignment_mode: Optional[str] = None
    rotation_order: Optional[list[str]] = None
    active: Optional[bool] = None


class Chore(BaseModel):
    id: int
    name: str
    description: str
    icon: str
    xp_reward: int
    difficulty: str
    recurrence: Optional[str]
    estimated_minutes: Optional[int]
    assignment_mode: str
    rotation_order: Optional[list[str]]
    active: bool
    created_at: str
    updated_at: str


# ── Chore instances ──────────────────────────────────────────────────────────

class InstanceCreate(BaseModel):
    chore_id: int
    due_date: str
    assigned_to: Optional[str] = None


class InstanceComplete(BaseModel):
    completed_by: str
    notes: str = ""


class InstanceClaim(BaseModel):
    person_id: str


class ChoreInstance(BaseModel):
    id: int
    chore_id: int
    due_date: str
    assigned_to: Optional[str]
    status: str
    completed_at: Optional[str]
    completed_by: Optional[str]
    xp_awarded: int
    notes: str
    created_at: str
    chore_name: Optional[str] = None
    chore_icon: Optional[str] = None
    chore_difficulty: Optional[str] = None
    chore_assignment_mode: Optional[str] = None


# ── Persons ──────────────────────────────────────────────────────────────────

class Person(BaseModel):
    entity_id: str
    name: str
    xp_total: int = 0
    level: int = 1
    current_streak: int = 0
    longest_streak: int = 0
    last_completion_date: Optional[str] = None
    avatar_url: str = ""


class PersonStats(Person):
    rank: int = 0
    badges: list[BadgeEarned] = []
    completions_count: int = 0


# ── Badges ───────────────────────────────────────────────────────────────────

class Badge(BaseModel):
    id: str
    name: str
    description: str
    icon: str
    condition_type: str
    condition_value: int
    hidden: int = 0
    condition_extra: str = ""


class BadgeEarned(BaseModel):
    id: str
    name: str
    icon: str
    earned_at: str


class BadgeResult(BaseModel):
    """Minimal badge info returned in a complete response."""
    id: str
    name: str
    description: str = ""
    icon: str


class PowerUp(BaseModel):
    id: int
    person_id: str
    powerup_type: str
    name: str
    icon: str
    description: str
    applies_to: Optional[str]
    multiplier: float
    uses_remaining: int
    expires_at: Optional[str]
    created_at: str


class CompleteResult(BaseModel):
    """Enriched response from POST /assignments/{id}/complete."""
    instance: ChoreInstance
    xp_awarded: int
    leveled_up: bool
    old_level: int
    new_level: int
    new_streak: int
    new_badges: list[BadgeResult]
    powerup_consumed: Optional[PowerUp] = None
    powerup_earned: Optional[PowerUp] = None


class PersonBadgeStatus(BaseModel):
    badge: Badge
    earned: bool
    earned_at: Optional[str] = None


# ── Gamification ─────────────────────────────────────────────────────────────

class LeaderboardEntry(BaseModel):
    entity_id: str
    name: str
    avatar_url: str
    xp_total: int
    level: int
    current_streak: int
    rank: int
    badges_count: int


class Leaderboard(BaseModel):
    entries: list[LeaderboardEntry]
    period: str = "all_time"


# ── Config ───────────────────────────────────────────────────────────────────

class ConfigEntry(BaseModel):
    key: str
    value: str


# ── Health ───────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = ""
    db_tables: int = 0


# Fix forward reference
PersonStats.model_rebuild()
