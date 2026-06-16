"""Tests for household challenges (v0.4.6)."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import date, datetime, timedelta

import pytest


def _seed_person(conn, entity_id, name=None):
    conn.execute(
        "INSERT INTO persons (entity_id, name) VALUES (?, ?)",
        (entity_id, name or entity_id),
    )
    conn.commit()


def _seed_chore(conn, chore_id, category="dishes", mode="manual"):
    conn.execute(
        """INSERT INTO chores (id, name, category, xp_reward, assignment_mode, active)
           VALUES (?, ?, ?, 10, ?, 1)""",
        (chore_id, f"Chore {chore_id}", category, mode),
    )
    conn.commit()


def _seed_challenge(conn, goal_type="completions_total", goal_value=3,
                    target_category="", period_days=6):
    today = date.today()
    end = today + timedelta(days=period_days)
    cursor = conn.execute(
        """INSERT INTO household_challenges
             (name, description, goal_type, goal_value, target_category,
              period_start, period_end, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, 'active')""",
        ("Test Challenge", "test", goal_type, goal_value, target_category,
         today.isoformat(), end.isoformat()),
    )
    conn.commit()
    return cursor.lastrowid


# ── Lifecycle ─────────────────────────────────────────────────────────────────

class TestLifecycle:
    def test_get_active_returns_in_period_challenge(self, tmp_db):
        import challenges
        _seed_challenge(tmp_db)
        c = challenges.get_active(tmp_db)
        assert c is not None
        assert c["status"] == "active"

    def test_get_active_excludes_completed(self, tmp_db):
        import challenges
        cid = _seed_challenge(tmp_db)
        tmp_db.execute(
            "UPDATE household_challenges SET status = 'completed' WHERE id = ?",
            (cid,),
        )
        tmp_db.commit()
        assert challenges.get_active(tmp_db) is None

    def test_get_for_display_keeps_completed_this_period(self, tmp_db):
        import challenges
        cid = _seed_challenge(tmp_db)
        tmp_db.execute(
            "UPDATE household_challenges SET status = 'completed' WHERE id = ?",
            (cid,),
        )
        tmp_db.commit()
        # get_active hides it, but the banner endpoint keeps it visible.
        assert challenges.get_active(tmp_db) is None
        shown = challenges.get_for_display(tmp_db)
        assert shown is not None
        assert shown["status"] == "completed"

    def test_active_endpoint_returns_completed_with_reward_tokens(self, tmp_db):
        import challenges
        from routers.challenges import get_active_challenge
        cid = _seed_challenge(tmp_db)
        tmp_db.execute(
            "UPDATE household_challenges SET status = 'completed' WHERE id = ?",
            (cid,),
        )
        tmp_db.commit()
        data = get_active_challenge()
        assert data is not None
        assert data["status"] == "completed"
        assert data["reward_tokens"] == challenges.CHALLENGE_TOKENS

    def test_recompute_progress_counts_completions(self, tmp_db):
        import challenges
        _seed_person(tmp_db, "person.alice")
        _seed_chore(tmp_db, chore_id=1, category="dishes")
        cid = _seed_challenge(tmp_db, goal_type="completions_total", goal_value=5)
        today = date.today().isoformat()
        for _ in range(3):
            tmp_db.execute(
                """INSERT INTO chore_instances
                     (chore_id, due_date, completed_by, status, completed_at, xp_awarded)
                   VALUES (1, ?, 'person.alice', 'completed', ?, 10)""",
                (today, datetime.now().isoformat()),
            )
        tmp_db.commit()
        c = challenges.get_active(tmp_db)
        new = challenges.recompute_progress(tmp_db, c)
        assert new == 3


# ── Bump on completion ────────────────────────────────────────────────────────

class TestBumpAndComplete:
    def test_bump_increments_completions(self, tmp_db):
        import challenges
        _seed_person(tmp_db, "person.alice")
        _seed_challenge(tmp_db, goal_type="completions_total", goal_value=3)
        challenges.bump_progress(tmp_db, completed_by="person.alice", chore_category="dishes", xp=10)
        progress = tmp_db.execute(
            "SELECT progress FROM household_challenges WHERE status = 'active'"
        ).fetchone()
        assert progress["progress"] == 1

    def test_bump_category_only_matches_target(self, tmp_db):
        import challenges
        _seed_person(tmp_db, "person.alice")
        _seed_challenge(tmp_db, goal_type="category_total", goal_value=3, target_category="dishes")
        challenges.bump_progress(tmp_db, completed_by="person.alice", chore_category="laundry", xp=10)
        progress = tmp_db.execute(
            "SELECT progress FROM household_challenges"
        ).fetchone()["progress"]
        assert progress == 0
        challenges.bump_progress(tmp_db, completed_by="person.alice", chore_category="dishes", xp=10)
        progress = tmp_db.execute(
            "SELECT progress FROM household_challenges"
        ).fetchone()["progress"]
        assert progress == 1

    def test_bump_xp_total_adds_xp(self, tmp_db):
        import challenges
        _seed_person(tmp_db, "person.alice")
        _seed_challenge(tmp_db, goal_type="xp_total", goal_value=100)
        challenges.bump_progress(tmp_db, completed_by="person.alice", chore_category="dishes", xp=25)
        challenges.bump_progress(tmp_db, completed_by="person.alice", chore_category="dishes", xp=40)
        progress = tmp_db.execute(
            "SELECT progress FROM household_challenges"
        ).fetchone()["progress"]
        assert progress == 65

    def test_completion_awards_household_powerup(self, tmp_db):
        import challenges
        _seed_person(tmp_db, "person.alice")
        _seed_person(tmp_db, "person.bob")
        _seed_challenge(tmp_db, goal_type="completions_total", goal_value=2)
        result = challenges.bump_progress(tmp_db, completed_by="person.alice", chore_category="dishes", xp=10)
        assert result is None  # still in progress
        result = challenges.bump_progress(tmp_db, completed_by="person.bob", chore_category="dishes", xp=10)
        assert result is not None
        assert result["status"] == "completed"

        # Both persons get the 2× / 72h reward powerup
        rewards = tmp_db.execute(
            "SELECT person_id, multiplier, expires_at FROM person_powerups WHERE powerup_type = 'challenge_reward'"
        ).fetchall()
        assert len(rewards) == 2
        people = {r["person_id"] for r in rewards}
        assert people == {"person.alice", "person.bob"}
        for r in rewards:
            assert r["multiplier"] == 2.0
            expires = datetime.fromisoformat(r["expires_at"])
            delta_hours = (expires - datetime.now()).total_seconds() / 3600
            assert 71 < delta_hours <= 72  # ~72h from now

        # Both persons get +30 tokens
        token_rows = tmp_db.execute(
            "SELECT entity_id, tokens FROM persons WHERE entity_id IN ('person.alice', 'person.bob')"
        ).fetchall()
        assert {r["entity_id"]: r["tokens"] for r in token_rows} == {
            "person.alice": 30, "person.bob": 30,
        }

        # Each person gets a celebration row referencing the challenge + tokens bonus
        import json as _json
        celebrations = tmp_db.execute(
            "SELECT person_id, payload FROM pending_celebrations"
        ).fetchall()
        for r in celebrations:
            p = _json.loads(r["payload"])
            cc = p.get("challenge_completed", {})
            assert cc.get("name") == "Test Challenge"
            assert cc.get("tokens") == 30
            assert cc.get("multiplier") == 2.0
            assert cc.get("hours") == 72

    def test_completion_is_one_shot(self, tmp_db):
        import challenges
        _seed_person(tmp_db, "person.alice")
        _seed_challenge(tmp_db, goal_type="completions_total", goal_value=1)
        challenges.bump_progress(tmp_db, completed_by="person.alice", chore_category="dishes", xp=10)
        # Already completed; further bumps shouldn't re-issue rewards
        challenges.bump_progress(tmp_db, completed_by="person.alice", chore_category="dishes", xp=10)
        rewards = tmp_db.execute(
            "SELECT COUNT(*) AS c FROM person_powerups WHERE powerup_type = 'challenge_reward'"
        ).fetchone()["c"]
        assert rewards == 1  # only one award

    def test_no_active_challenge_no_bump(self, tmp_db):
        import challenges
        _seed_person(tmp_db, "person.alice")
        result = challenges.bump_progress(tmp_db, completed_by="person.alice", chore_category="dishes", xp=10)
        assert result is None


# ── Scheduler tick ────────────────────────────────────────────────────────────

class TestTick:
    def test_tick_expires_past_challenges(self, tmp_db):
        import challenges
        # Insert a challenge that ended yesterday
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        tmp_db.execute(
            """INSERT INTO household_challenges
                 (name, description, goal_type, goal_value, target_category,
                  period_start, period_end, status)
               VALUES ('Past', '', 'completions_total', 5, '',
                       date('now', '-7 days'), ?, 'active')""",
            (yesterday,),
        )
        tmp_db.commit()
        # Disable auto-gen to isolate the expire path
        tmp_db.execute("INSERT OR REPLACE INTO config (key, value) VALUES ('auto_generate_weekly_challenge', 'false')")
        tmp_db.commit()
        result = challenges.tick(tmp_db)
        assert result["expired"] == 1
        row = tmp_db.execute("SELECT status FROM household_challenges").fetchone()
        assert row["status"] == "expired"

    def test_tick_auto_creates_weekly_when_enabled(self, tmp_db):
        import challenges
        import json
        tmp_db.execute(
            "INSERT OR REPLACE INTO config (key, value) VALUES ('auto_generate_weekly_challenge', ?)",
            (json.dumps(True),),
        )
        tmp_db.commit()
        result = challenges.tick(tmp_db)
        assert result["created"] == 1
        row = tmp_db.execute(
            "SELECT * FROM household_challenges WHERE status = 'active'"
        ).fetchone()
        assert row is not None

    def test_tick_does_not_create_when_active_exists(self, tmp_db):
        import challenges
        _seed_challenge(tmp_db)
        result = challenges.tick(tmp_db)
        assert result["created"] == 0
