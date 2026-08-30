"""Tests for the household statistics endpoints."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_db):
    from main import app
    with TestClient(app) as c:
        yield c


def _seed(conn):
    conn.execute("INSERT INTO persons (entity_id, name) VALUES ('person.anna', 'Anna')")
    conn.execute("INSERT INTO persons (entity_id, name) VALUES ('person.ben', 'Ben')")
    conn.execute("INSERT INTO chores (id, name, icon) VALUES (1, 'Dishes', '🍽️')")
    conn.execute("INSERT INTO chores (id, name, icon) VALUES (2, 'Vacuum', '🧹')")
    conn.execute("INSERT INTO chores (id, name, icon, active) VALUES (3, 'Old chore', '🗑️', 0)")
    conn.execute("INSERT INTO chores (id, name, icon, active) VALUES (4, 'Retired never done', '👻', 0)")
    completions = [
        (1, "person.anna", "2026-08-05T10:00:00"),
        (1, "person.anna", "2026-08-12T18:30:00"),
        (1, "person.ben", "2026-08-05T20:00:00"),
        (2, "person.ben", "2026-07-31T09:00:00"),
        (3, "person.anna", "2026-08-01T08:00:00"),
    ]
    for chore_id, person, ts in completions:
        conn.execute(
            """INSERT INTO chore_instances
               (chore_id, due_date, status, completed_by, completed_at)
               VALUES (?, ?, 'completed', ?, ?)""",
            (chore_id, ts[:10], person, ts),
        )
    # A pending instance must never count
    conn.execute(
        "INSERT INTO chore_instances (chore_id, due_date, status) VALUES (2, '2026-08-20', 'pending')"
    )
    conn.commit()


class TestMatrix:
    def test_counts_per_chore_and_person(self, client, tmp_db):
        _seed(tmp_db)
        resp = client.get("/api/stats/matrix")
        assert resp.status_code == 200
        chores = {c["name"]: c for c in resp.json()["chores"]}

        assert chores["Dishes"]["counts"] == {"person.anna": 2, "person.ben": 1}
        assert chores["Dishes"]["total"] == 3
        assert chores["Vacuum"]["counts"] == {"person.ben": 1}

    def test_sorted_by_total_desc(self, client, tmp_db):
        _seed(tmp_db)
        names = [c["name"] for c in client.get("/api/stats/matrix").json()["chores"]]
        assert names[0] == "Dishes"

    def test_includes_inactive_with_history_excludes_without(self, client, tmp_db):
        _seed(tmp_db)
        names = [c["name"] for c in client.get("/api/stats/matrix").json()["chores"]]
        assert "Old chore" in names
        assert "Retired never done" not in names

    def test_active_never_done_shows_zero(self, client, tmp_db):
        tmp_db.execute("INSERT INTO chores (id, name) VALUES (10, 'Fresh chore')")
        tmp_db.commit()
        chores = client.get("/api/stats/matrix").json()["chores"]
        fresh = next(c for c in chores if c["name"] == "Fresh chore")
        assert fresh["counts"] == {}
        assert fresh["total"] == 0


class TestCalendar:
    def test_month_grouped_by_day(self, client, tmp_db):
        _seed(tmp_db)
        resp = client.get("/api/stats/calendar", params={"year": 2026, "month": 8})
        assert resp.status_code == 200
        days = resp.json()["days"]

        assert set(days) == {"2026-08-01", "2026-08-05", "2026-08-12"}
        assert len(days["2026-08-05"]) == 2
        entry = days["2026-08-12"][0]
        assert entry["chore_name"] == "Dishes"
        assert entry["chore_icon"] == "🍽️"
        assert entry["completed_by"] == "person.anna"

    def test_other_month_excluded(self, client, tmp_db):
        _seed(tmp_db)
        days = client.get(
            "/api/stats/calendar", params={"year": 2026, "month": 7}
        ).json()["days"]
        assert set(days) == {"2026-07-31"}

    def test_invalid_month_rejected(self, client):
        resp = client.get("/api/stats/calendar", params={"year": 2026, "month": 13})
        assert resp.status_code == 422
