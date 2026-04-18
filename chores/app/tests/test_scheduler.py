"""Tests for the scheduler module."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import date, timedelta
from scheduler import parse_recurrence, should_schedule_on, get_next_assignee


class TestParseRecurrence:
    def test_daily(self):
        assert parse_recurrence("daily") == {"type": "daily"}

    def test_weekly(self):
        result = parse_recurrence("weekly:mon,thu")
        assert result["type"] == "weekly"
        assert "mon" in result["days"]
        assert "thu" in result["days"]

    def test_monthly(self):
        result = parse_recurrence("monthly:1,15")
        assert result["type"] == "monthly"
        assert 1 in result["days_of_month"]
        assert 15 in result["days_of_month"]

    def test_empty(self):
        assert parse_recurrence("")["type"] == "none"
        assert parse_recurrence(None)["type"] == "none"

    def test_every(self):
        result = parse_recurrence("every:3")
        assert result["type"] == "every"
        assert result["interval"] == 3


class TestShouldScheduleOn:
    def test_daily_always_true(self):
        assert should_schedule_on("daily", date(2025, 1, 6)) is True  # Monday
        assert should_schedule_on("daily", date(2025, 1, 11)) is True  # Saturday

    def test_weekly_correct_day(self):
        # 2025-01-06 is a Monday
        assert should_schedule_on("weekly:mon", date(2025, 1, 6)) is True
        assert should_schedule_on("weekly:mon", date(2025, 1, 7)) is False  # Tuesday

    def test_monthly_correct_day(self):
        assert should_schedule_on("monthly:15", date(2025, 1, 15)) is True
        assert should_schedule_on("monthly:15", date(2025, 1, 14)) is False

    def test_none_returns_false(self):
        assert should_schedule_on("", date(2025, 1, 1)) is False


class TestGetNextAssignee:
    def test_first_assignment(self, tmp_db):
        order = ["person.alice", "person.bob", "person.charlie"]
        result = get_next_assignee(999, order)
        assert result == "person.alice"

    def test_rotation(self, tmp_db):
        order = ["person.alice", "person.bob", "person.charlie"]
        tmp_db.execute("INSERT INTO chores (id, name) VALUES (1, 'Test')")
        tmp_db.execute(
            """INSERT INTO chore_instances (chore_id, due_date, assigned_to, status)
               VALUES (1, '2025-01-01', 'person.alice', 'completed')"""
        )
        tmp_db.commit()
        result = get_next_assignee(1, order)
        assert result == "person.bob"

    def test_rotation_wraps(self, tmp_db):
        order = ["person.alice", "person.bob"]
        tmp_db.execute("INSERT INTO chores (id, name) VALUES (1, 'Test')")
        tmp_db.execute(
            """INSERT INTO chore_instances (chore_id, due_date, assigned_to, status)
               VALUES (1, '2025-01-01', 'person.bob', 'completed')"""
        )
        tmp_db.commit()
        result = get_next_assignee(1, order)
        assert result == "person.alice"

    def test_empty_rotation(self):
        result = get_next_assignee(1, [])
        assert result is None


class TestGenerateInstances:
    def test_generates_daily_instances(self, tmp_db):
        from scheduler import generate_instances

        tmp_db.execute(
            """INSERT INTO chores (id, name, recurrence, active)
               VALUES (1, 'Daily Clean', 'daily', 1)"""
        )
        tmp_db.commit()

        count = generate_instances(days_ahead=3)
        assert count == 3

        rows = tmp_db.execute("SELECT * FROM chore_instances WHERE chore_id = 1").fetchall()
        assert len(rows) == 3

    def test_skips_existing_instances(self, tmp_db):
        from scheduler import generate_instances
        from datetime import date as d

        today = d.today().isoformat()
        tmp_db.execute(
            """INSERT INTO chores (id, name, recurrence, active)
               VALUES (1, 'Daily Clean', 'daily', 1)"""
        )
        tmp_db.execute(
            """INSERT INTO chore_instances (chore_id, due_date, status)
               VALUES (1, ?, 'pending')""",
            (today,),
        )
        tmp_db.commit()

        count = generate_instances(days_ahead=3)
        assert count == 2  # Today already exists

    def test_rotation_advances_across_days(self, tmp_db):
        from scheduler import generate_instances

        tmp_db.execute(
            """INSERT INTO chores (id, name, recurrence, active, assignment_mode, rotation_order)
               VALUES (1, 'Rotation Chore', 'daily', 1, 'rotation', '["person.alice", "person.bob"]')"""
        )
        tmp_db.commit()

        count = generate_instances(days_ahead=4)
        assert count == 4

        rows = tmp_db.execute(
            "SELECT due_date, assigned_to FROM chore_instances WHERE chore_id = 1 ORDER BY due_date"
        ).fetchall()
        assignees = [r["assigned_to"] for r in rows]
        assert assignees == ["person.alice", "person.bob", "person.alice", "person.bob"]


class TestMarkOverdue:
    def test_marks_past_due(self, tmp_db):
        from scheduler import mark_overdue

        tmp_db.execute("INSERT INTO chores (id, name) VALUES (1, 'Test')")
        tmp_db.execute(
            """INSERT INTO chore_instances (chore_id, due_date, status)
               VALUES (1, '2020-01-01', 'pending')"""
        )
        tmp_db.commit()

        count, targets = mark_overdue()
        assert count == 1
        # No assigned_to, so no notification targets
        assert len(targets) == 0

        row = tmp_db.execute("SELECT status FROM chore_instances WHERE chore_id = 1").fetchone()
        assert row["status"] == "overdue"

    def test_marks_overdue_with_notification_target(self, tmp_db):
        from scheduler import mark_overdue

        tmp_db.execute("INSERT INTO chores (id, name) VALUES (1, 'Dishes')")
        tmp_db.execute("INSERT INTO persons (entity_id, name) VALUES ('person.alice', 'Alice')")
        tmp_db.execute(
            """INSERT INTO chore_instances (chore_id, due_date, status, assigned_to)
               VALUES (1, '2020-01-01', 'pending', 'person.alice')"""
        )
        tmp_db.commit()

        count, targets = mark_overdue()
        assert count == 1
        assert len(targets) == 1
        assert targets[0]["person"] == "person.alice"
        assert targets[0]["chore_name"] == "Dishes"


class TestStreakAtRisk:
    def test_returns_at_risk_persons(self, tmp_db):
        from scheduler import get_streak_at_risk_persons

        yesterday = (date.today() - timedelta(days=1)).isoformat()
        tmp_db.execute(
            """INSERT INTO persons (entity_id, name, current_streak, last_completion_date)
               VALUES ('person.alice', 'Alice', 5, ?)""",
            (yesterday,),
        )
        tmp_db.commit()

        at_risk = get_streak_at_risk_persons()
        assert len(at_risk) == 1
        assert at_risk[0]["entity_id"] == "person.alice"
        assert at_risk[0]["streak"] == 5

    def test_excludes_zero_streak(self, tmp_db):
        from scheduler import get_streak_at_risk_persons

        tmp_db.execute(
            "INSERT INTO persons (entity_id, name, current_streak) VALUES ('person.bob', 'Bob', 0)"
        )
        tmp_db.commit()
        assert len(get_streak_at_risk_persons()) == 0

    def test_excludes_completed_today(self, tmp_db):
        from scheduler import get_streak_at_risk_persons

        today = date.today().isoformat()
        tmp_db.execute(
            """INSERT INTO persons (entity_id, name, current_streak, last_completion_date)
               VALUES ('person.alice', 'Alice', 5, ?)""",
            (today,),
        )
        tmp_db.commit()
        assert len(get_streak_at_risk_persons()) == 0


class TestWeeklySummary:
    def test_returns_summary_for_persons(self, tmp_db):
        from scheduler import get_weekly_summary_data

        tmp_db.execute(
            "INSERT INTO persons (entity_id, name, xp_total) VALUES ('person.alice', 'Alice', 100)"
        )
        tmp_db.execute("INSERT INTO chores (id, name) VALUES (1, 'Test')")
        tmp_db.execute(
            """INSERT INTO chore_instances (chore_id, due_date, completed_by, status, completed_at, xp_awarded)
               VALUES (1, ?, 'person.alice', 'completed', ?, 10)""",
            (date.today().isoformat(), date.today().isoformat()),
        )
        tmp_db.commit()

        summaries = get_weekly_summary_data()
        assert len(summaries) == 1
        assert summaries[0]["completed"] == 1
        assert summaries[0]["xp_earned"] == 10


class TestPerfectWeek:
    def test_perfect_week_true(self, tmp_db):
        from scheduler import check_perfect_week

        tmp_db.execute("INSERT INTO persons (entity_id, name) VALUES ('person.alice', 'Alice')")
        tmp_db.execute("INSERT INTO chores (id, name) VALUES (1, 'Test')")

        for i in range(1, 8):
            d = (date.today() - timedelta(days=i)).isoformat()
            tmp_db.execute(
                """INSERT INTO chore_instances (chore_id, due_date, assigned_to, status, completed_by)
                   VALUES (1, ?, 'person.alice', 'completed', 'person.alice')""",
                (d,),
            )
        tmp_db.commit()

        assert check_perfect_week("person.alice") is True

    def test_perfect_week_false_with_missed(self, tmp_db):
        from scheduler import check_perfect_week

        tmp_db.execute("INSERT INTO persons (entity_id, name) VALUES ('person.alice', 'Alice')")
        tmp_db.execute("INSERT INTO chores (id, name) VALUES (1, 'Test')")

        for i in range(1, 8):
            d = (date.today() - timedelta(days=i)).isoformat()
            status = "completed" if i <= 5 else "pending"
            tmp_db.execute(
                """INSERT INTO chore_instances (chore_id, due_date, assigned_to, status)
                   VALUES (1, ?, 'person.alice', ?)""",
                (d, status),
            )
        tmp_db.commit()

        assert check_perfect_week("person.alice") is False
