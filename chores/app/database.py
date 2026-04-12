"""Chores – SQLite database schema and connection management."""

import sqlite3
import logging
import os

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.environ.get("DATA_DIR", "/data"), "chores.db")

_conn: sqlite3.Connection | None = None


def get_connection() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode = WAL")
        _conn.execute("PRAGMA foreign_keys = ON")
    return _conn


def close_connection() -> None:
    global _conn
    if _conn is not None:
        _conn.close()
        _conn = None


def initialize() -> int:
    """Create tables and return the number of tables."""
    conn = get_connection()
    conn.executescript(SCHEMA)
    _migrate(conn)
    _seed_badges(conn)
    _seed_notif_config(conn)
    _recalc_levels(conn)
    # Run general badge validator to fix any incorrectly awarded revocable badges
    from gamification import validate_and_revoke_badges, revoke_incorrectly_awarded_badges
    revoke_incorrectly_awarded_badges()
    validate_and_revoke_badges()
    tables = conn.execute(
        "SELECT count(*) FROM sqlite_master WHERE type='table'"
    ).fetchone()[0]
    logger.info("Database initialized with %d tables", tables)
    return tables


SCHEMA = """
CREATE TABLE IF NOT EXISTS chores (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL,
    description     TEXT    DEFAULT '',
    icon            TEXT    DEFAULT '🧹',
    xp_reward       INTEGER DEFAULT 10,
    difficulty      TEXT    DEFAULT 'medium'
                            CHECK (difficulty IN ('easy', 'medium', 'hard')),
    recurrence      TEXT,
    estimated_minutes INTEGER,
    assignment_mode TEXT    DEFAULT 'manual'
                            CHECK (assignment_mode IN ('manual', 'rotation', 'claim')),
    rotation_order  TEXT,
    active          INTEGER DEFAULT 1,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chore_instances (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    chore_id        INTEGER NOT NULL REFERENCES chores(id) ON DELETE CASCADE,
    due_date        TEXT    NOT NULL,
    assigned_to     TEXT,
    status          TEXT    DEFAULT 'pending'
                            CHECK (status IN (
                                'pending', 'claimed', 'completed', 'overdue', 'skipped'
                            )),
    completed_at    TIMESTAMP,
    completed_by    TEXT,
    xp_awarded      INTEGER DEFAULT 0,
    notes           TEXT    DEFAULT '',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_instances_chore
    ON chore_instances(chore_id);
CREATE INDEX IF NOT EXISTS idx_instances_status
    ON chore_instances(status);
CREATE INDEX IF NOT EXISTS idx_instances_due
    ON chore_instances(due_date);
CREATE INDEX IF NOT EXISTS idx_instances_assigned
    ON chore_instances(assigned_to);

CREATE TABLE IF NOT EXISTS persons (
    entity_id           TEXT PRIMARY KEY,
    name                TEXT NOT NULL,
    xp_total            INTEGER DEFAULT 0,
    level               INTEGER DEFAULT 1,
    current_streak      INTEGER DEFAULT 0,
    longest_streak      INTEGER DEFAULT 0,
    last_completion_date TEXT,
    avatar_url          TEXT    DEFAULT '',
    ha_user_id          TEXT    DEFAULT ''
);

CREATE TABLE IF NOT EXISTS badges (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    description     TEXT DEFAULT '',
    icon            TEXT DEFAULT '🏅',
    condition_type  TEXT NOT NULL,
    condition_value INTEGER DEFAULT 0,
    hidden          INTEGER DEFAULT 0,
    condition_extra TEXT    DEFAULT ''
);

CREATE TABLE IF NOT EXISTS person_badges (
    person_id   TEXT NOT NULL REFERENCES persons(entity_id) ON DELETE CASCADE,
    badge_id    TEXT NOT NULL REFERENCES badges(id) ON DELETE CASCADE,
    earned_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (person_id, badge_id)
);

CREATE TABLE IF NOT EXISTS config (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""


SEED_BADGES = [
    # (id, name, description, icon, condition_type, condition_value, hidden, condition_extra)

    # ── Completions ──────────────────────────────────────────────────────────
    ("first_chore",      "First Steps",             "Complete your first chore",                       "🌟", "completions",       1,   0, ""),
    ("completions_10",   "Getting Warmed Up",        "Complete 10 chores total",                        "🧤", "completions",       10,  0, ""),
    ("completions_50",   "Regular",                  "Complete 50 chores total",                        "🪣", "completions",       50,  0, ""),
    ("completions_100",  "Century",                  "Complete 100 chores total",                       "🏆", "completions",       100, 0, ""),
    ("completions_500",  "Obsessed (Positively)",    "Complete 500 chores total",                       "💎", "completions",       500, 0, ""),

    # ── Streaks ──────────────────────────────────────────────────────────────
    ("streak_3",         "Hat Trick",                "Achieve a 3-day streak",                          "⚡", "streak",            3,   0, ""),
    ("streak_7",         "On Fire",                  "Achieve a 7-day streak",                          "🔥", "streak",            7,   0, ""),
    ("streak_30",        "Month Warrior",             "Achieve a 30-day streak",                         "🗓️", "streak",            30,  0, ""),
    ("streak_100",       "Unstoppable",              "Achieve a 100-day streak",                        "💪", "streak",            100, 0, ""),

    # ── Levels ───────────────────────────────────────────────────────────────
    ("level_5",          "Rising Star",              "Reach level 5",                                   "📈", "level",             5,   0, ""),
    ("level_10",         "Veteran",                  "Reach level 10",                                  "🌠", "level",             10,  0, ""),
    ("level_20",         "Legend",                   "Reach level 20",                                  "👑", "level",             20,  0, ""),

    # ── Speed ────────────────────────────────────────────────────────────────
    ("speed_5",          "Speed Demon",              "Complete 5 chores in one day",                    "⚡", "daily_completions", 5,   0, ""),
    ("speed_10",         "Overachiever",             "Complete 10 chores in a single day",              "🚀", "daily_completions", 10,  0, ""),

    # ── Claims ───────────────────────────────────────────────────────────────
    ("claims_10",        "Team Player",              "Voluntarily claim 10 unassigned chores",          "🤝", "claims",            10,  0, ""),
    ("claims_25",        "Social Butterfly",         "Voluntarily claim 25 unassigned chores",          "🦋", "claims",            25,  0, ""),

    # ── Special ──────────────────────────────────────────────────────────────
    ("perfect_week",     "Consistency King",         "Complete all assigned chores for a full week",    "🎯", "perfect_week",      1,   0, ""),
    ("all_types",        "Master Cleaner",           "Complete every type of chore at least once",      "🧹", "all_types",         1,   0, ""),
    ("early_bird",       "Early Bird",               "Complete a chore before 7 AM",                    "🐦", "hour_before",       7,   0, ""),
    ("night_owl",        "Night Owl",                "Complete a chore after 10 PM",                    "🦉", "hour_after",        22,  0, ""),
    ("weekend_warrior",  "Weekend Warrior",          "Complete chores on both Saturday and Sunday",     "⚔️", "weekend_both",      1,   0, ""),
    ("late_complete_5",  "Better Late Than Never",   "Complete 5 chores after their due date",          "⌛", "late_complete",     5,   0, ""),

    # ── Hidden / Funny ───────────────────────────────────────────────────────
    ("vampire_hours",    "Vampire Hours",            "Complete a chore between 1–3 AM",                 "🧛", "hour_range",        1,   1, "3"),
    ("nocturnal_pro",    "They Sleep, I Sweep",      "Accumulate 3 completions between midnight and 4 AM", "🌙", "midnight_count", 3,   1, ""),
    ("christmas_clean",  "Silent Night... Cleaning", "Complete a chore on Christmas Day",               "🎄", "calendar_date",     0,   1, "12-25"),
    ("new_year_clean",   "New Year, Clean House",    "Complete a chore on New Year's Day",              "🎆", "calendar_date",     0,   1, "01-01"),
    ("no_life",          "No Life (But Clean)",      "Complete 15 chores in a single day",              "💀", "daily_completions", 15,  1, ""),
    ("friday_night",     "No Plans Friday Night",    "Complete a chore after 11 PM on a Friday",        "🍕", "friday_night",      1,   1, ""),
    ("monday_hero",      "Monday Morning Motivation","Complete a chore before 7 AM on a Monday",        "☕", "monday_early",      1,   1, ""),
    ("sunday_scaries",   "Sunday Scaries, Defeated", "Complete a chore before 9 AM on a Sunday",       "😤", "sunday_early",      1,   1, ""),
    ("completionist",    "The Completionist",        "Earn 15 other badges",                            "🎖️", "badge_count",       15,  1, ""),
    ("speed_runner",     "Any% Completion",          "Complete 3 chores within 10 minutes",             "🎮", "speed_run",         3,   1, ""),
    ("redemption_arc",   "Redemption Arc",           "Complete 10 overdue chores",                      "📈", "late_complete",     10,  1, ""),
    ("anniversary",      "Annual Service Award",     "Complete chores consistently for an entire year", "🎂", "days_since_first",  365, 1, ""),
    ("midnight_special", "The Midnight Special",     "Complete a chore within 5 minutes of midnight",   "🌌", "midnight_window",   1,   1, ""),
]


def _recalc_levels(conn: sqlite3.Connection) -> None:
    """Recalculate every person's level from their current XP (linear curve: 100 XP/level)."""
    rows = conn.execute("SELECT entity_id, xp_total FROM persons").fetchall()
    for row in rows:
        new_level = max(1, row["xp_total"] // 100 + 1)
        conn.execute(
            "UPDATE persons SET level = ? WHERE entity_id = ?",
            (new_level, row["entity_id"]),
        )
    if rows:
        conn.commit()
        logger.info("Recalculated levels for %d persons (linear 100 XP/level)", len(rows))


def _migrate(conn: sqlite3.Connection) -> None:
    """Apply schema migrations for columns added after initial release."""
    migrations = [
        # badges columns (v0.2.7)
        ("badges",  "hidden",          "INTEGER DEFAULT 0"),
        ("badges",  "condition_extra", "TEXT DEFAULT ''"),
        # persons columns (v0.2.8)
        ("persons", "ha_user_id",      "TEXT DEFAULT ''"),
    ]
    for table, col, defn in migrations:
        try:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {defn}")
            conn.commit()
            logger.info("Migration: added column '%s.%s'", table, col)
        except Exception:
            pass  # Column already exists


def _seed_badges(conn: sqlite3.Connection) -> None:
    """Insert predefined badges if they don't exist."""
    for badge_id, name, desc, icon, ctype, cval, hidden, cextra in SEED_BADGES:
        conn.execute(
            """INSERT OR IGNORE INTO badges
               (id, name, description, icon, condition_type, condition_value, hidden, condition_extra)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (badge_id, name, desc, icon, ctype, cval, hidden, cextra),
        )
    conn.commit()


import json as _json

# Default notification configuration seeded on first run.
# Stored as JSON values in the config table.
NOTIF_DEFAULTS = {
    "notif_assigned": {"enabled": True},
    "notif_overdue":  {"enabled": True},
    "notif_badge":    {"enabled": True},
    "notif_levelup":  {"enabled": True},
    "notif_reminder": {"enabled": True, "when": "day_of", "hour": 8},
    "notif_streak":   {"enabled": True, "hour": 18},
    "notif_weekly":   {"enabled": True, "weekday": 0, "hour": 9},
}


def _seed_notif_config(conn: sqlite3.Connection) -> None:
    """Insert default notification config entries if they don't exist."""
    for key, default in NOTIF_DEFAULTS.items():
        conn.execute(
            "INSERT OR IGNORE INTO config (key, value) VALUES (?, ?)",
            (key, _json.dumps(default)),
        )
    conn.commit()
