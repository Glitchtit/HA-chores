"""Tests for seasonal boss chores (v0.5.0)."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import date, timedelta

import pytest


def _seed_person(conn, eid, name=None):
    conn.execute(
        "INSERT INTO persons (entity_id, name) VALUES (?, ?)",
        (eid, name or eid),
    )
    conn.commit()


def _seed_chore(conn, cid, category="dishes"):
    conn.execute(
        """INSERT INTO chores (id, name, category, xp_reward, active)
           VALUES (?, ?, ?, 10, 1)""",
        (cid, f"Chore {cid}", category),
    )
    conn.commit()


def _seed_boss(conn, *, status="active", days=7, cosmetic="hat_party", badge=None):
    today = date.today()
    cursor = conn.execute(
        """INSERT INTO boss_events
             (name, description, icon, start_date, end_date, status,
              reward_cosmetic_id, reward_badge_id)
           VALUES (?, '', '👹', ?, ?, ?, ?, ?)""",
        (
            "Test Boss",
            today.isoformat(),
            (today + timedelta(days=days)).isoformat(),
            status,
            cosmetic,
            badge,
        ),
    )
    conn.commit()
    return cursor.lastrowid


def _seed_objective(conn, boss_id, chore_id, target=2):
    conn.execute(
        """INSERT INTO boss_objectives (boss_id, chore_id, target_count)
           VALUES (?, ?, ?)""",
        (boss_id, chore_id, target),
    )
    conn.commit()


# ── Lifecycle ─────────────────────────────────────────────────────────────────

class TestLifecycle:
    def test_get_active_returns_in_window_boss(self, tmp_db):
        import bosses
        _seed_boss(tmp_db)
        b = bosses.get_active(tmp_db)
        assert b is not None
        assert b["status"] == "active"

    def test_get_active_returns_none_when_no_active(self, tmp_db):
        import bosses
        assert bosses.get_active(tmp_db) is None

    def test_get_with_objectives_returns_chore_names(self, tmp_db):
        import bosses
        _seed_chore(tmp_db, 1, category="dishes")
        _seed_chore(tmp_db, 2, category="laundry")
        bid = _seed_boss(tmp_db)
        _seed_objective(tmp_db, bid, 1, target=3)
        _seed_objective(tmp_db, bid, 2, target=2)
        b = bosses.get_with_objectives(tmp_db, bid)
        assert len(b["objectives"]) == 2
        assert {o["chore_id"] for o in b["objectives"]} == {1, 2}
        assert {o["chore_name"] for o in b["objectives"]} == {"Chore 1", "Chore 2"}


# ── State machine ────────────────────────────────────────────────────────────

class TestTick:
    def test_tick_activates_upcoming_boss(self, tmp_db):
        import bosses
        bid = _seed_boss(tmp_db, status="upcoming")
        bosses.tick(tmp_db)
        row = tmp_db.execute(
            "SELECT status FROM boss_events WHERE id = ?", (bid,)
        ).fetchone()
        assert row["status"] == "active"

    def test_tick_expires_overdue_boss(self, tmp_db):
        import bosses
        # Boss with end date in the past
        cursor = tmp_db.execute(
            """INSERT INTO boss_events
                 (name, start_date, end_date, status)
               VALUES ('Old', date('now', '-10 days'), date('now', '-1 day'), 'active')"""
        )
        tmp_db.commit()
        bosses.tick(tmp_db)
        row = tmp_db.execute(
            "SELECT status FROM boss_events WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
        assert row["status"] == "expired"


# ── Bump and defeat ──────────────────────────────────────────────────────────

class TestBump:
    def test_bump_increments_objective(self, tmp_db):
        import bosses
        _seed_chore(tmp_db, 1)
        bid = _seed_boss(tmp_db)
        _seed_objective(tmp_db, bid, 1, target=3)
        bosses.bump_on_completion(tmp_db, 1)
        progress = tmp_db.execute(
            "SELECT progress FROM boss_objectives WHERE boss_id = ?", (bid,)
        ).fetchone()["progress"]
        assert progress == 1

    def test_bump_ignored_for_non_objective_chore(self, tmp_db):
        import bosses
        _seed_chore(tmp_db, 1)
        _seed_chore(tmp_db, 99)  # not an objective
        bid = _seed_boss(tmp_db)
        _seed_objective(tmp_db, bid, 1, target=3)
        result = bosses.bump_on_completion(tmp_db, 99)
        assert result is None
        progress = tmp_db.execute(
            "SELECT progress FROM boss_objectives"
        ).fetchone()["progress"]
        assert progress == 0

    def test_completing_all_objectives_defeats_boss(self, tmp_db):
        import bosses
        _seed_person(tmp_db, "person.alice")
        _seed_person(tmp_db, "person.bob")
        _seed_chore(tmp_db, 1)
        _seed_chore(tmp_db, 2)
        bid = _seed_boss(tmp_db, cosmetic="hat_party")
        _seed_objective(tmp_db, bid, 1, target=2)
        _seed_objective(tmp_db, bid, 2, target=1)

        bosses.bump_on_completion(tmp_db, 1)
        bosses.bump_on_completion(tmp_db, 1)
        result = bosses.bump_on_completion(tmp_db, 2)
        assert result is not None
        assert result["status"] == "defeated"

        # Cosmetic granted to every person
        owners = tmp_db.execute(
            "SELECT person_id FROM person_cosmetics WHERE cosmetic_id = 'hat_party'"
        ).fetchall()
        assert {r["person_id"] for r in owners} == {"person.alice", "person.bob"}

    def test_defeat_is_idempotent(self, tmp_db):
        import bosses
        _seed_person(tmp_db, "person.alice")
        _seed_chore(tmp_db, 1)
        bid = _seed_boss(tmp_db, cosmetic="hat_party")
        _seed_objective(tmp_db, bid, 1, target=1)
        bosses.bump_on_completion(tmp_db, 1)
        # Further bumps shouldn't re-grant
        bosses.bump_on_completion(tmp_db, 1)
        bosses.bump_on_completion(tmp_db, 1)
        owners_count = tmp_db.execute(
            "SELECT COUNT(*) AS c FROM person_cosmetics WHERE cosmetic_id = 'hat_party'"
        ).fetchone()["c"]
        assert owners_count == 1

    def test_no_active_boss_no_bump(self, tmp_db):
        import bosses
        _seed_chore(tmp_db, 1)
        # No boss seeded
        result = bosses.bump_on_completion(tmp_db, 1)
        assert result is None
