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

    def test_streak_decrements_after_gap(self, tmp_db):
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
        # 3-day gap = 2 missed days: max(0, 5-2) + 1 = 4
        assert streak == 4
        assert longest == 10

    def test_streak_bottoms_at_zero(self, tmp_db):
        from gamification import update_streak
        from datetime import date, timedelta

        ten_days_ago = (date.today() - timedelta(days=10)).isoformat()
        tmp_db.execute(
            """INSERT INTO persons (entity_id, name, current_streak, longest_streak, last_completion_date)
               VALUES ('person.test', 'Test', 3, 10, ?)""",
            (ten_days_ago,),
        )
        tmp_db.commit()
        streak, longest = update_streak("person.test")
        # 10-day gap = 9 missed days: max(0, 3-9) + 1 = 1
        assert streak == 1
        assert longest == 10


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
