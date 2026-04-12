"""Tests for the Chores API endpoints."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_db):
    """Create a test client with a temporary database."""
    import database as db_module
    # Patch main to use the tmp db
    from main import app
    with TestClient(app) as c:
        yield c


class TestHealth:
    def test_health_returns_ok(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["db_tables"] > 0


class TestChores:
    def test_create_chore(self, client):
        resp = client.post("/api/chores/", json={
            "name": "Vacuum Living Room",
            "difficulty": "medium",
            "xp_reward": 15,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Vacuum Living Room"
        assert data["xp_reward"] == 15
        assert data["active"] is True

    def test_list_chores(self, client):
        client.post("/api/chores/", json={"name": "Chore A"})
        client.post("/api/chores/", json={"name": "Chore B"})
        resp = client.get("/api/chores/")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_update_chore(self, client):
        create_resp = client.post("/api/chores/", json={"name": "Old Name"})
        chore_id = create_resp.json()["id"]
        resp = client.put(f"/api/chores/{chore_id}", json={"name": "New Name"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "New Name"

    def test_delete_chore(self, client):
        create_resp = client.post("/api/chores/", json={"name": "Delete Me"})
        chore_id = create_resp.json()["id"]
        resp = client.delete(f"/api/chores/{chore_id}")
        assert resp.status_code == 204

    def test_get_nonexistent_chore(self, client):
        resp = client.get("/api/chores/99999")
        assert resp.status_code == 404


class TestAssignments:
    def test_create_instance(self, client, tmp_db):
        tmp_db.execute("INSERT INTO persons (entity_id, name) VALUES ('person.test', 'Test')")
        tmp_db.commit()

        chore = client.post("/api/chores/", json={"name": "Test Chore"}).json()
        resp = client.post("/api/assignments/", json={
            "chore_id": chore["id"],
            "due_date": "2025-06-01",
            "assigned_to": "person.test",
        })
        assert resp.status_code == 201
        assert resp.json()["assigned_to"] == "person.test"

    def test_complete_instance(self, client, tmp_db):
        tmp_db.execute("INSERT INTO persons (entity_id, name) VALUES ('person.test', 'Test')")
        tmp_db.commit()

        chore = client.post("/api/chores/", json={"name": "Test Chore", "xp_reward": 10}).json()
        instance = client.post("/api/assignments/", json={
            "chore_id": chore["id"],
            "due_date": "2025-06-01",
        }).json()

        resp = client.post(f"/api/assignments/{instance['id']}/complete", json={
            "completed_by": "person.test",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["instance"]["status"] == "completed"
        assert data["xp_awarded"] > 0

    def test_claim_instance(self, client, tmp_db):
        tmp_db.execute("INSERT INTO persons (entity_id, name) VALUES ('person.test', 'Test')")
        tmp_db.commit()

        chore = client.post("/api/chores/", json={"name": "Claimable", "assignment_mode": "claim"}).json()
        instance = client.post("/api/assignments/", json={
            "chore_id": chore["id"],
            "due_date": "2025-06-01",
        }).json()

        resp = client.post(f"/api/assignments/{instance['id']}/claim", json={
            "person_id": "person.test",
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "claimed"
        assert resp.json()["assigned_to"] == "person.test"


class TestGamification:
    def test_leaderboard(self, client, tmp_db):
        tmp_db.execute("INSERT INTO persons (entity_id, name, xp_total, level) VALUES ('person.a', 'Alice', 100, 2)")
        tmp_db.execute("INSERT INTO persons (entity_id, name, xp_total, level) VALUES ('person.b', 'Bob', 50, 1)")
        tmp_db.commit()

        resp = client.get("/api/gamification/leaderboard")
        assert resp.status_code == 200
        data = resp.json()
        assert data["entries"][0]["name"] == "Alice"
        assert data["entries"][0]["rank"] == 1
        assert data["entries"][1]["name"] == "Bob"
        assert data["entries"][1]["rank"] == 2

    def test_badges_list(self, client):
        resp = client.get("/api/gamification/badges")
        assert resp.status_code == 200
        badges = resp.json()
        assert len(badges) > 0
        assert any(b["id"] == "first_chore" for b in badges)
