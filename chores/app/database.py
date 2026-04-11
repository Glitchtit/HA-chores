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
    _seed_badges(conn)
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
    avatar_url          TEXT    DEFAULT ''
);

CREATE TABLE IF NOT EXISTS badges (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    description     TEXT DEFAULT '',
    icon            TEXT DEFAULT '🏅',
    condition_type  TEXT NOT NULL,
    condition_value INTEGER DEFAULT 0
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
    ("first_chore", "First Steps", "Complete your first chore", "🌟", "completions", 1),
    ("streak_7", "On Fire", "Achieve a 7-day streak", "🔥", "streak", 7),
    ("streak_30", "Unstoppable", "Achieve a 30-day streak", "💪", "streak", 30),
    ("completions_100", "Century", "Complete 100 chores", "🏆", "completions", 100),
    ("speed_5", "Speed Demon", "Complete 5 chores in one day", "⚡", "daily_completions", 5),
    ("all_types", "Master Cleaner", "Complete every chore type at least once", "🧹", "all_types", 1),
    ("perfect_week", "Consistency King", "Complete all assigned chores for a full week", "🎯", "perfect_week", 1),
    ("level_5", "Rising Star", "Reach level 5", "📈", "level", 5),
    ("level_10", "Veteran", "Reach level 10", "🌠", "level", 10),
    ("claims_10", "Team Player", "Claim 10 unassigned chores", "🤝", "claims", 10),
]


def _seed_badges(conn: sqlite3.Connection) -> None:
    """Insert predefined badges if they don't exist."""
    for badge_id, name, desc, icon, ctype, cval in SEED_BADGES:
        conn.execute(
            """INSERT OR IGNORE INTO badges (id, name, description, icon, condition_type, condition_value)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (badge_id, name, desc, icon, ctype, cval),
        )
    conn.commit()
