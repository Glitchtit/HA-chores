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
    _seed_cosmetics(conn)
    _seed_notif_config(conn)
    _seed_pet_states(conn)
    _seed_other_chores(conn)
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
    category        TEXT    DEFAULT 'other',
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

CREATE TABLE IF NOT EXISTS person_powerups (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id       TEXT    NOT NULL REFERENCES persons(entity_id) ON DELETE CASCADE,
    powerup_type    TEXT    NOT NULL,
    name            TEXT    NOT NULL,
    icon            TEXT    DEFAULT '⚡',
    description     TEXT    DEFAULT '',
    applies_to      TEXT,
    multiplier      REAL    DEFAULT 1.0,
    uses_remaining  INTEGER DEFAULT 1,
    expires_at      TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_powerups_person
    ON person_powerups(person_id);

CREATE TABLE IF NOT EXISTS pet_states (
    person_id     TEXT PRIMARY KEY REFERENCES persons(entity_id) ON DELETE CASCADE,
    happiness     INTEGER DEFAULT 80 CHECK (happiness BETWEEN 0 AND 100),
    pet_emoji     TEXT    DEFAULT '🐶',
    pet_design    TEXT    DEFAULT 'orange_black',
    pet_name      TEXT    DEFAULT NULL,
    last_tick_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_bump_at  TIMESTAMP,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pending_celebrations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id   TEXT    NOT NULL REFERENCES persons(entity_id) ON DELETE CASCADE,
    payload     TEXT    NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    seen_at     TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_pending_celebrations_person_unseen
    ON pending_celebrations(person_id, created_at)
    WHERE seen_at IS NULL;

-- ── v0.4.3: Cosmetics shop ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS cosmetics (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    slot          TEXT NOT NULL
                       CHECK (slot IN ('hat', 'background', 'particle', 'nameplate', 'evolution')),
    icon          TEXT DEFAULT '✨',
    cost_tokens   INTEGER DEFAULT 0,
    unlock_type   TEXT DEFAULT 'shop'
                       CHECK (unlock_type IN ('shop', 'boss', 'level', 'gift')),
    unlock_value  TEXT DEFAULT '',
    pet_design    TEXT DEFAULT '',
    hidden        INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS person_cosmetics (
    person_id    TEXT NOT NULL REFERENCES persons(entity_id) ON DELETE CASCADE,
    cosmetic_id  TEXT NOT NULL REFERENCES cosmetics(id) ON DELETE CASCADE,
    equipped     INTEGER DEFAULT 0,
    acquired_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (person_id, cosmetic_id)
);

-- ── v0.4.5: Daily quests ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS daily_quests (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id     TEXT NOT NULL REFERENCES persons(entity_id) ON DELETE CASCADE,
    quest_date    TEXT NOT NULL,
    quest_type    TEXT NOT NULL,
    target        INTEGER DEFAULT 1,
    target_extra  TEXT DEFAULT '',
    progress      INTEGER DEFAULT 0,
    completed_at  TIMESTAMP,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_daily_quests_unique
    ON daily_quests(person_id, quest_date, quest_type, target_extra);
CREATE INDEX IF NOT EXISTS idx_daily_quests_person_date
    ON daily_quests(person_id, quest_date);

CREATE TABLE IF NOT EXISTS daily_quest_bundles (
    person_id        TEXT NOT NULL REFERENCES persons(entity_id) ON DELETE CASCADE,
    quest_date       TEXT NOT NULL,
    all_complete_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (person_id, quest_date)
);

-- ── v0.4.6: Team household challenges ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS household_challenges (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    name              TEXT NOT NULL,
    description       TEXT DEFAULT '',
    goal_type         TEXT NOT NULL
                          CHECK (goal_type IN ('completions_total', 'category_total', 'xp_total', 'claims_total')),
    goal_value        INTEGER NOT NULL,
    target_category   TEXT DEFAULT '',
    progress          INTEGER DEFAULT 0,
    period_start      TEXT NOT NULL,
    period_end        TEXT NOT NULL,
    status            TEXT DEFAULT 'active'
                          CHECK (status IN ('active', 'completed', 'expired')),
    reward_multiplier REAL DEFAULT 1.5,
    reward_hours      INTEGER DEFAULT 24,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_challenges_active_period
    ON household_challenges(status, period_start, period_end);

-- ── v0.5.0: Seasonal boss chores ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS boss_events (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    name               TEXT NOT NULL,
    description        TEXT DEFAULT '',
    icon               TEXT DEFAULT '👹',
    start_date         TEXT NOT NULL,
    end_date           TEXT NOT NULL,
    status             TEXT DEFAULT 'upcoming'
                            CHECK (status IN ('upcoming', 'active', 'defeated', 'expired')),
    reward_cosmetic_id TEXT REFERENCES cosmetics(id) ON DELETE SET NULL,
    reward_badge_id    TEXT REFERENCES badges(id) ON DELETE SET NULL,
    created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_boss_events_status_dates
    ON boss_events(status, start_date, end_date);

CREATE TABLE IF NOT EXISTS boss_objectives (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    boss_id       INTEGER NOT NULL REFERENCES boss_events(id) ON DELETE CASCADE,
    chore_id      INTEGER NOT NULL REFERENCES chores(id) ON DELETE CASCADE,
    target_count  INTEGER DEFAULT 1,
    progress      INTEGER DEFAULT 0,
    sort_order    INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_boss_objectives_chore
    ON boss_objectives(chore_id);
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
        ("persons", "ha_user_id",           "TEXT DEFAULT ''"),
        # persons columns (v0.2.69)
        ("persons", "last_month_end_seen",  "TEXT DEFAULT ''"),
        # chores columns (v0.2.70)
        ("chores", "followup_chore_id", "INTEGER DEFAULT NULL REFERENCES chores(id) ON DELETE SET NULL"),
        # chores columns (v0.3.0 — pet feature)
        ("chores", "category", "TEXT DEFAULT 'other'"),
        # pet_states columns (v0.3.1 — axolotl sprites)
        ("pet_states", "pet_design", "TEXT DEFAULT 'orange_black'"),
        # pet_states columns (v0.3.18 — pet name)
        ("pet_states", "pet_name", "TEXT DEFAULT NULL"),
        # chore_instances columns (v0.3.27 — track who created/claimed the instance
        # so self-managed chores can suppress assigned/reminder notifications)
        ("chore_instances", "created_by", "TEXT DEFAULT NULL"),
        # pet_states columns (v0.4.2 — pet evolution stages: egg → baby → teen → adult → mythic)
        ("pet_states", "stage", "TEXT DEFAULT 'egg'"),
        # persons columns (v0.4.3 — cosmetic-shop currency, 1 token per 10 XP earned)
        ("persons", "tokens", "INTEGER DEFAULT 0"),
        # persons columns (v0.4.4 — skill specialization / class picks)
        ("persons", "class_id", "TEXT DEFAULT ''"),
        ("persons", "class_chosen_at", "TEXT DEFAULT ''"),
    ]
    for table, col, defn in migrations:
        try:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {defn}")
            conn.commit()
            logger.info("Migration: added column '%s.%s'", table, col)
        except Exception:
            pass  # Column already exists


SEED_COSMETICS = [
    # (id, name, slot, icon, cost_tokens, unlock_type, unlock_value, pet_design, hidden)
    # ── Hats (tokens) ────────────────────────────────────────────────────────
    ("hat_party",         "Party Hat",            "hat", "🎉", 50,   "shop",  "",       "", 0),
    ("hat_crown",         "Crown",                "hat", "👑", 250,  "shop",  "",       "", 0),
    ("hat_chef",          "Chef Hat",             "hat", "👨‍🍳", 80,   "shop",  "",       "", 0),
    ("hat_top",           "Top Hat",              "hat", "🎩", 120,  "shop",  "",       "", 0),
    ("hat_wizard",        "Wizard Hat",           "hat", "🧙", 180,  "shop",  "",       "", 0),
    # ── Backgrounds (tokens) ─────────────────────────────────────────────────
    ("bg_meadow",         "Meadow",               "background", "🌼", 60,  "shop", "", "", 0),
    ("bg_beach",          "Beach",                "background", "🏖️", 120, "shop", "", "", 0),
    ("bg_space",          "Outer Space",          "background", "🌌", 200, "shop", "", "", 0),
    ("bg_forest",         "Forest",               "background", "🌲", 100, "shop", "", "", 0),
    # ── Particles (tokens) ───────────────────────────────────────────────────
    ("particle_sparkle",  "Sparkles",             "particle", "✨", 100, "shop", "", "", 0),
    ("particle_hearts",   "Hearts",               "particle", "💖", 150, "shop", "", "", 0),
    ("particle_fire",     "Fire",                 "particle", "🔥", 200, "shop", "", "", 0),
    # ── Nameplates (tokens) ──────────────────────────────────────────────────
    ("plate_gold",        "Gold Nameplate",       "nameplate", "🏷️", 200, "shop",  "",  "", 0),
    ("plate_silver",      "Silver Nameplate",     "nameplate", "🥈", 100, "shop",  "",  "", 0),
    # ── Level-locked unlocks (free at the milestone) ─────────────────────────
    ("hat_graduate",      "Graduate Cap",         "hat", "🎓", 0, "level", "10", "", 0),
    ("hat_halo",          "Halo",                 "hat", "😇", 0, "level", "20", "", 0),
    ("particle_stars",    "Stardust",             "particle", "💫", 0, "level", "15", "", 0),
    # ── Boss-defeat exclusives (revealed at defeat; hidden until then) ───────
    ("hat_laurel",        "Spring Laurel",        "hat", "🌿", 0, "boss", "spring_cleaning", "", 1),
    ("bg_aurora",         "Aurora",               "background", "🌠", 0, "boss", "deep_clean", "", 1),

    # ── Expansion pack (v0.6.1): 12 new hats + 8 new particles ──────────────
    # Hats (tokens)
    ("hat_beanie",        "Cozy Beanie",          "hat", "🧣", 70,  "shop", "", "", 0),
    ("hat_cowboy",        "Cowboy Hat",           "hat", "🤠", 120, "shop", "", "", 0),
    ("hat_pirate",        "Pirate Tricorn",       "hat", "🏴‍☠️", 220, "shop", "", "", 0),
    ("hat_viking",        "Viking Helmet",        "hat", "⚒️", 200, "shop", "", "", 0),
    ("hat_propeller",     "Propeller Beanie",     "hat", "🎈", 90,  "shop", "", "", 0),
    ("hat_cat_ears",      "Cat Ears",             "hat", "🐱", 80,  "shop", "", "", 0),
    ("hat_fox_ears",      "Fox Ears",             "hat", "🦊", 90,  "shop", "", "", 0),
    ("hat_bunny_ears",    "Bunny Ears",           "hat", "🐰", 80,  "shop", "", "", 0),
    ("hat_flower_crown",  "Flower Crown",         "hat", "🌸", 150, "shop", "", "", 0),
    ("hat_santa",         "Santa Hat",            "hat", "🎅", 100, "shop", "", "", 0),
    ("hat_sun",           "Straw Sun Hat",        "hat", "👒", 90,  "shop", "", "", 0),
    ("hat_beret",         "Black Beret",          "hat", "🎨", 120, "shop", "", "", 0),
    # Particles (tokens)
    ("particle_snow",      "Snowfall",            "particle", "❄️", 130, "shop", "", "", 0),
    ("particle_leaves",    "Autumn Leaves",       "particle", "🍂", 130, "shop", "", "", 0),
    ("particle_blossoms",  "Cherry Petals",       "particle", "🌸", 150, "shop", "", "", 0),
    ("particle_lightning", "Lightning",           "particle", "⚡", 220, "shop", "", "", 0),
    ("particle_music",     "Music Notes",         "particle", "🎵", 160, "shop", "", "", 0),
    ("particle_bubbles",   "Bubbles",             "particle", "🫧", 110, "shop", "", "", 0),
    ("particle_paws",      "Paw Prints",          "particle", "🐾", 140, "shop", "", "", 0),
    ("particle_rainbow",   "Rainbow Swirls",      "particle", "🌈", 250, "shop", "", "", 0),
]


def _seed_cosmetics(conn: sqlite3.Connection) -> None:
    """Insert predefined cosmetics if they don't already exist."""
    for cid, name, slot, icon, cost, utype, uval, pdesign, hidden in SEED_COSMETICS:
        conn.execute(
            """INSERT OR IGNORE INTO cosmetics
                 (id, name, slot, icon, cost_tokens, unlock_type, unlock_value, pet_design, hidden)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (cid, name, slot, icon, cost, utype, uval, pdesign, hidden),
        )
    conn.commit()


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
    "auto_generate_weekly_challenge": True,  # v0.4.6
}


def _seed_notif_config(conn: sqlite3.Connection) -> None:
    """Insert default notification config entries if they don't exist."""
    for key, default in NOTIF_DEFAULTS.items():
        conn.execute(
            "INSERT OR IGNORE INTO config (key, value) VALUES (?, ?)",
            (key, _json.dumps(default)),
        )
    conn.commit()


def _seed_pet_states(conn: sqlite3.Connection) -> None:
    """Ensure every person has a pet_states row. Idempotent."""
    conn.execute(
        "INSERT OR IGNORE INTO pet_states (person_id) SELECT entity_id FROM persons"
    )
    conn.commit()


# Catch-all ad-hoc chores — one per difficulty — so any small task can be
# logged without creating a dedicated chore first.
SEED_OTHER_CHORES = [
    ("Other (easy)",   "Log a small ad-hoc task",  "📦",  5, "easy"),
    ("Other (medium)", "Log a medium ad-hoc task", "📦", 10, "medium"),
    ("Other (hard)",   "Log a big ad-hoc task",    "📦", 20, "hard"),
]


def _seed_other_chores(conn: sqlite3.Connection) -> None:
    """Seed three "Other" catch-all chores (one per difficulty) on first run.

    Re-inserts any that are missing by name so users can't accidentally end up
    with only two of them, but won't duplicate if they already exist. Tests
    that need a pristine chores table set ``CHORES_SKIP_SEED_OTHER=1``.
    """
    if os.environ.get("CHORES_SKIP_SEED_OTHER") == "1":
        return
    for name, desc, icon, xp, diff in SEED_OTHER_CHORES:
        exists = conn.execute(
            "SELECT 1 FROM chores WHERE name = ? LIMIT 1", (name,)
        ).fetchone()
        if exists:
            continue
        conn.execute(
            """INSERT INTO chores
                 (name, description, icon, xp_reward, difficulty, category,
                  assignment_mode, active)
               VALUES (?, ?, ?, ?, ?, 'other', 'claim', 1)""",
            (name, desc, icon, xp, diff),
        )
    conn.commit()
