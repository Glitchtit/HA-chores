"""Tests for the gamification engine."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gamification import calculate_xp, level_from_xp, xp_for_level


class TestXPCalculation:
    def test_base_xp_no_bonuses(self):
        assert calculate_xp(10) == 10

    def test_streak_bonus(self):
        # 5-day streak = +50%
        assert calculate_xp(10, streak=5) == 15

    def test_streak_bonus_capped_at_100_percent(self):
        # 15-day streak would be +150%, but capped at +100%
        assert calculate_xp(10, streak=15) == 20

    def test_early_bird_bonus(self):
        assert calculate_xp(10, early=True) == 12  # +25%

    def test_claim_bonus(self):
        assert calculate_xp(10, claimed=True) == 11  # +15%

    def test_all_bonuses_combined(self):
        # streak=3 (+30%) + early (+25%) + claimed (+15%) = +70%
        assert calculate_xp(10, streak=3, early=True, claimed=True) == 17

    def test_minimum_1_xp(self):
        assert calculate_xp(0) >= 1


class TestLevels:
    def test_level_1_at_zero_xp(self):
        assert level_from_xp(0) == 1

    def test_level_2_at_50_xp(self):
        assert level_from_xp(50) == 2

    def test_level_3_at_200_xp(self):
        assert level_from_xp(200) == 3

    def test_level_5_at_800_xp(self):
        assert level_from_xp(800) == 5

    def test_xp_for_level_roundtrip(self):
        for lvl in range(1, 20):
            xp = xp_for_level(lvl)
            assert level_from_xp(xp) >= lvl

    def test_negative_xp(self):
        assert level_from_xp(-10) == 1


class TestStreaks:
    def test_update_streak_new_person(self, tmp_db):
        from gamification import update_streak
        tmp_db.execute(
            "INSERT INTO persons (entity_id, name) VALUES ('person.test', 'Test')"
        )
        tmp_db.commit()
        streak, longest = update_streak("person.test")
        assert streak == 1
        assert longest == 1

    def test_streak_increments_on_consecutive_days(self, tmp_db):
        from gamification import update_streak
        from datetime import date, timedelta

        yesterday = (date.today() - timedelta(days=1)).isoformat()
        tmp_db.execute(
            """INSERT INTO persons (entity_id, name, current_streak, longest_streak, last_completion_date)
               VALUES ('person.test', 'Test', 3, 5, ?)""",
            (yesterday,),
        )
        tmp_db.commit()
        streak, longest = update_streak("person.test")
        assert streak == 4
        assert longest == 5

    def test_streak_increments_after_gap(self, tmp_db):
        """update_streak always does +1; decay_streaks handles the decrement at midnight."""
        from gamification import update_streak
        from datetime import date, timedelta

        three_days_ago = (date.today() - timedelta(days=3)).isoformat()
        tmp_db.execute(
            """INSERT INTO persons (entity_id, name, current_streak, longest_streak, last_completion_date)
               VALUES ('person.test', 'Test', 5, 10, ?)""",
            (three_days_ago,),
        )
        tmp_db.commit()
        streak, longest = update_streak("person.test")
        # Decay (5→3) has already happened via decay_streaks; update_streak just adds 1
        assert streak == 6  # 5 + 1 (background job not involved here)
        assert longest == 10

    def test_streak_no_change_when_already_today(self, tmp_db):
        """Completing twice on the same day should not increment the streak."""
        from gamification import update_streak
        from datetime import date

        today = date.today().isoformat()
        tmp_db.execute(
            """INSERT INTO persons (entity_id, name, current_streak, longest_streak, last_completion_date)
               VALUES ('person.test', 'Test', 3, 5, ?)""",
            (today,),
        )
        tmp_db.commit()
        streak, longest = update_streak("person.test")
        assert streak == 3
        assert longest == 5


class TestDecayStreaks:
    def test_decay_decrements_for_missed_day(self, tmp_db):
        from gamification import decay_streaks
        from datetime import date, timedelta

        two_days_ago = (date.today() - timedelta(days=2)).isoformat()
        tmp_db.execute(
            """INSERT INTO persons (entity_id, name, current_streak, last_completion_date)
               VALUES ('person.test', 'Test', 5, ?)""",
            (two_days_ago,),
        )
        tmp_db.commit()
        affected = decay_streaks()
        assert affected == 1
        row = tmp_db.execute("SELECT current_streak FROM persons WHERE entity_id='person.test'").fetchone()
        assert row[0] == 4  # 5 - 1 missed day (yesterday)

    def test_decay_no_change_when_completed_yesterday(self, tmp_db):
        from gamification import decay_streaks
        from datetime import date, timedelta

        yesterday = (date.today() - timedelta(days=1)).isoformat()
        tmp_db.execute(
            """INSERT INTO persons (entity_id, name, current_streak, last_completion_date)
               VALUES ('person.test', 'Test', 5, ?)""",
            (yesterday,),
        )
        tmp_db.commit()
        affected = decay_streaks()
        assert affected == 0
        row = tmp_db.execute("SELECT current_streak FROM persons WHERE entity_id='person.test'").fetchone()
        assert row[0] == 5  # unchanged

    def test_decay_bottoms_at_zero(self, tmp_db):
        """Streak bottoms at 0 after enough accumulated missed days."""
        from gamification import decay_streaks
        from datetime import date, timedelta

        # Simulate: decay last ran 8 days ago, person last completed 10 days ago
        eight_days_ago = (date.today() - timedelta(days=8)).isoformat()
        ten_days_ago = (date.today() - timedelta(days=10)).isoformat()
        tmp_db.execute(
            """INSERT INTO persons (entity_id, name, current_streak, last_completion_date)
               VALUES ('person.test', 'Test', 5, ?)""",
            (ten_days_ago,),
        )
        tmp_db.execute(
            "INSERT INTO config (key, value) VALUES ('last_streak_decay_date', ?)",
            (eight_days_ago,),
        )
        tmp_db.commit()
        affected = decay_streaks()
        assert affected == 1
        row = tmp_db.execute("SELECT current_streak FROM persons WHERE entity_id='person.test'").fetchone()
        # days_to_process = 7 (8_days_ago+1 through yesterday), person missed all 7 → max(0, 5-7) = 0
        assert row[0] == 0

    def test_decay_idempotent_when_called_twice(self, tmp_db):
        from gamification import decay_streaks
        from datetime import date, timedelta

        two_days_ago = (date.today() - timedelta(days=2)).isoformat()
        tmp_db.execute(
            """INSERT INTO persons (entity_id, name, current_streak, last_completion_date)
               VALUES ('person.test', 'Test', 5, ?)""",
            (two_days_ago,),
        )
        tmp_db.commit()
        decay_streaks()
        affected2 = decay_streaks()
        assert affected2 == 0  # second call is a no-op


class TestBadges:
    def test_first_chore_badge(self, tmp_db):
        from gamification import check_and_award_badges

        tmp_db.execute(
            "INSERT INTO persons (entity_id, name, current_streak, level) VALUES ('person.test', 'Test', 1, 1)"
        )
        tmp_db.execute(
            "INSERT INTO chores (id, name) VALUES (1, 'Test Chore')"
        )
        tmp_db.execute(
            """INSERT INTO chore_instances (chore_id, due_date, completed_by, status, completed_at)
               VALUES (1, '2025-01-01', 'person.test', 'completed', '2025-01-01T12:00:00')"""
        )
        tmp_db.commit()

        badges = check_and_award_badges("person.test")
        badge_ids = [b["id"] for b in badges]
        assert "first_chore" in badge_ids

    def test_no_duplicate_badges(self, tmp_db):
        from gamification import check_and_award_badges

        tmp_db.execute(
            "INSERT INTO persons (entity_id, name, current_streak, level) VALUES ('person.test', 'Test', 1, 1)"
        )
        tmp_db.execute("INSERT INTO chores (id, name) VALUES (1, 'Test Chore')")
        tmp_db.execute(
            """INSERT INTO chore_instances (chore_id, due_date, completed_by, status, completed_at)
               VALUES (1, '2025-01-01', 'person.test', 'completed', '2025-01-01T12:00:00')"""
        )
        tmp_db.commit()

        badges1 = check_and_award_badges("person.test")
        badges2 = check_and_award_badges("person.test")
        assert len(badges1) > 0
        assert len(badges2) == 0  # Already awarded


class TestAddXP:
    def test_add_xp_updates_level(self, tmp_db):
        from gamification import add_xp

        tmp_db.execute(
            "INSERT INTO persons (entity_id, name, xp_total, level) VALUES ('person.test', 'Test', 45, 1)"
        )
        tmp_db.commit()

        new_total, new_level, leveled_up = add_xp("person.test", 10)
        assert new_total == 55
        assert new_level == 2
        assert leveled_up is True


class TestPowerUps:
    def test_award_levelup_powerup_returns_row(self, tmp_db):
        from gamification import award_levelup_powerup

        tmp_db.execute("INSERT INTO persons (entity_id, name) VALUES ('person.tester', 'Tester')")
        tmp_db.commit()

        pu = award_levelup_powerup("person.tester", 2)
        assert pu is not None
        assert pu["person_id"] == "person.tester"
        assert pu["uses_remaining"] >= 1
        assert pu["multiplier"] >= 1.0

    def test_get_active_powerups_returns_awarded(self, tmp_db):
        from gamification import award_levelup_powerup, get_active_powerups

        tmp_db.execute("INSERT INTO persons (entity_id, name) VALUES ('person.tester', 'Tester')")
        tmp_db.commit()

        award_levelup_powerup("person.tester", 2)
        powerups = get_active_powerups("person.tester")
        assert len(powerups) >= 1

    def test_apply_powerup_to_xp_consumes_use(self, tmp_db):
        from gamification import get_active_powerups, apply_powerup_to_xp
        from datetime import datetime, timedelta

        expires_at = (datetime.now() + timedelta(days=7)).isoformat()
        tmp_db.execute("INSERT INTO persons (entity_id, name) VALUES ('person.tester', 'Tester')")
        tmp_db.execute(
            """INSERT INTO person_powerups
               (person_id, powerup_type, name, icon, description, applies_to, multiplier, uses_remaining, expires_at)
               VALUES ('person.tester', 'xp_double_hard', 'Hard Bonus', '💥', 'test', 'hard', 2.0, 1, ?)""",
            (expires_at,),
        )
        tmp_db.commit()

        multiplier, consumed = apply_powerup_to_xp("person.tester", "hard")
        assert multiplier == 2.0
        assert consumed is not None
        assert consumed["powerup_type"] == "xp_double_hard"
        # After consuming single use, power-up should be gone
        remaining = get_active_powerups("person.tester")
        assert len(remaining) == 0

    def test_apply_powerup_no_match_returns_one(self, tmp_db):
        from gamification import apply_powerup_to_xp
        from datetime import datetime, timedelta

        expires_at = (datetime.now() + timedelta(days=7)).isoformat()
        tmp_db.execute("INSERT INTO persons (entity_id, name) VALUES ('person.tester', 'Tester')")
        tmp_db.execute(
            """INSERT INTO person_powerups
               (person_id, powerup_type, name, icon, description, applies_to, multiplier, uses_remaining, expires_at)
               VALUES ('person.tester', 'xp_double_hard', 'Hard Bonus', '💥', 'test', 'hard', 2.0, 1, ?)""",
            (expires_at,),
        )
        tmp_db.commit()

        multiplier, consumed = apply_powerup_to_xp("person.tester", "easy")
        assert multiplier == 1.0
        assert consumed is None

    def test_streak_shield_not_applied_as_xp_multiplier(self, tmp_db):
        from gamification import apply_powerup_to_xp
        from datetime import datetime, timedelta

        expires_at = (datetime.now() + timedelta(days=14)).isoformat()
        tmp_db.execute("INSERT INTO persons (entity_id, name) VALUES ('person.tester', 'Tester')")
        tmp_db.execute(
            """INSERT INTO person_powerups
               (person_id, powerup_type, name, icon, description, applies_to, multiplier, uses_remaining, expires_at)
               VALUES ('person.tester', 'streak_shield', 'Shield', '🛡️', 'test', NULL, 1.0, 1, ?)""",
            (expires_at,),
        )
        tmp_db.commit()

        multiplier, consumed = apply_powerup_to_xp("person.tester", "easy")
        assert multiplier == 1.0
        assert consumed is None
