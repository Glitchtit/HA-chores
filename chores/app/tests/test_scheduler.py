"""Tests for the scheduler module."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import date
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


class TestMarkOverdue:
    def test_marks_past_due(self, tmp_db):
        from scheduler import mark_overdue

        tmp_db.execute("INSERT INTO chores (id, name) VALUES (1, 'Test')")
        tmp_db.execute(
            """INSERT INTO chore_instances (chore_id, due_date, status)
               VALUES (1, '2020-01-01', 'pending')"""
        )
        tmp_db.commit()

        count = mark_overdue()
        assert count == 1

        row = tmp_db.execute("SELECT status FROM chore_instances WHERE chore_id = 1").fetchone()
        assert row["status"] == "overdue"
