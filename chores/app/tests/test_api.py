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
        from datetime import date
        this_month = date.today().strftime("%Y-%m")
        tmp_db.execute("INSERT INTO persons (entity_id, name, xp_total, level) VALUES ('person.a', 'Alice', 100, 2)")
        tmp_db.execute("INSERT INTO persons (entity_id, name, xp_total, level) VALUES ('person.b', 'Bob', 50, 1)")
        # Insert a chore so we can create instances
        tmp_db.execute("INSERT INTO chores (name, xp_reward, difficulty, assignment_mode) VALUES ('T', 5, 'easy', 'manual')")
        chore_id = tmp_db.execute("SELECT last_insert_rowid()").fetchone()[0]
        tmp_db.execute(
            "INSERT INTO chore_instances (chore_id, due_date, status, completed_by, completed_at, xp_awarded) VALUES (?, ?, 'completed', 'person.a', ?, 100)",
            (chore_id, f"{this_month}-01", f"{this_month}-01 10:00:00"),
        )
        tmp_db.execute(
            "INSERT INTO chore_instances (chore_id, due_date, status, completed_by, completed_at, xp_awarded) VALUES (?, ?, 'completed', 'person.b', ?, 50)",
            (chore_id, f"{this_month}-01", f"{this_month}-01 11:00:00"),
        )
        tmp_db.commit()

        resp = client.get("/api/gamification/leaderboard")
        assert resp.status_code == 200
        data = resp.json()
        assert data["entries"][0]["name"] == "Alice"
        assert data["entries"][0]["rank"] == 1
        assert data["entries"][0]["xp_month"] == 100
        assert data["entries"][1]["name"] == "Bob"
        assert data["entries"][1]["rank"] == 2
        assert data["entries"][1]["xp_month"] == 50

    def test_badges_list(self, client):
        resp = client.get("/api/gamification/badges")
        assert resp.status_code == 200
        badges = resp.json()
        assert len(badges) > 0
        assert any(b["id"] == "first_chore" for b in badges)


class TestPendingCelebrationsSchema:
    def test_table_exists_after_initialize(self, tmp_db):
        row = tmp_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='pending_celebrations'"
        ).fetchone()
        assert row is not None

    def test_table_columns(self, tmp_db):
        cols = {r["name"] for r in tmp_db.execute(
            "PRAGMA table_info(pending_celebrations)"
        ).fetchall()}
        assert cols == {"id", "person_id", "payload", "created_at", "seen_at"}


class TestPendingCelebrationsWrite:
    def _seed_person_at_threshold(self, tmp_db, xp_total=95, level=1):
        tmp_db.execute(
            "INSERT INTO persons (entity_id, name, xp_total, level) VALUES (?, ?, ?, ?)",
            ("person.lvltest", "LevelTest", xp_total, level),
        )
        tmp_db.commit()

    def _seed_chore_and_instance(self, tmp_db, xp_reward=10):
        tmp_db.execute(
            "INSERT INTO chores (name, xp_reward, difficulty, assignment_mode) VALUES (?, ?, 'medium', 'manual')",
            ("LevelUp Chore", xp_reward),
        )
        chore_id = tmp_db.execute("SELECT last_insert_rowid()").fetchone()[0]
        from datetime import date
        tmp_db.execute(
            "INSERT INTO chore_instances (chore_id, due_date, status) VALUES (?, ?, 'pending')",
            (chore_id, date.today().isoformat()),
        )
        inst_id = tmp_db.execute("SELECT last_insert_rowid()").fetchone()[0]
        tmp_db.commit()
        return chore_id, inst_id

    def test_levelup_writes_pending_celebration(self, client, tmp_db):
        self._seed_person_at_threshold(tmp_db, xp_total=95, level=1)
        _, inst_id = self._seed_chore_and_instance(tmp_db, xp_reward=10)
        resp = client.post(f"/api/assignments/{inst_id}/complete",
                           json={"completed_by": "person.lvltest"})
        assert resp.status_code == 200
        assert resp.json()["leveled_up"] is True
        rows = tmp_db.execute(
            "SELECT payload FROM pending_celebrations WHERE person_id = ?",
            ("person.lvltest",),
        ).fetchall()
        assert len(rows) == 1
        import json
        payload = json.loads(rows[0]["payload"])
        assert payload["leveled_up"] is True
        assert payload["new_level"] == 2

    def test_no_celebration_when_nothing_earned(self, client, tmp_db):
        self._seed_person_at_threshold(tmp_db, xp_total=0, level=1)
        # Pre-award all existing badges so check_and_award_badges returns nothing new.
        badge_ids = [r[0] for r in tmp_db.execute("SELECT id FROM badges").fetchall()]
        for bid in badge_ids:
            tmp_db.execute(
                "INSERT OR IGNORE INTO person_badges (person_id, badge_id) VALUES (?, ?)",
                ("person.lvltest", bid),
            )
        tmp_db.commit()
        _, inst_id = self._seed_chore_and_instance(tmp_db, xp_reward=5)
        resp = client.post(f"/api/assignments/{inst_id}/complete",
                           json={"completed_by": "person.lvltest"})
        assert resp.status_code == 200
        assert resp.json()["leveled_up"] is False
        rows = tmp_db.execute(
            "SELECT 1 FROM pending_celebrations WHERE person_id = ?",
            ("person.lvltest",),
        ).fetchall()
        assert rows == []


class TestShoppingHook:
    def _seed_basic(self, tmp_db):
        tmp_db.execute(
            "INSERT INTO persons (entity_id, name) VALUES ('person.shopper', 'Shopper')"
        )
        tmp_db.execute(
            "INSERT INTO chores (name, xp_reward, difficulty, assignment_mode) VALUES ('Shopping', 10, 'medium', 'manual')"
        )
        shop_id = tmp_db.execute("SELECT id FROM chores WHERE name='Shopping'").fetchone()["id"]
        tmp_db.execute(
            "INSERT INTO chores (name, xp_reward, difficulty, assignment_mode) VALUES ('Unpack', 5, 'easy', 'manual')"
        )
        scan_id = tmp_db.execute("SELECT id FROM chores WHERE name='Unpack'").fetchone()["id"]
        tmp_db.execute("UPDATE chores SET followup_chore_id = ? WHERE id = ?", (scan_id, shop_id))
        tmp_db.commit()
        return shop_id, scan_id

    def test_hook_creates_instance_when_missing(self, client, tmp_db):
        shop_id, _ = self._seed_basic(tmp_db)
        resp = client.post("/api/shopping-hook/complete", json={
            "chore_id": shop_id,
            "person": "person.shopper",
            "suppress_followup": False,
        })
        assert resp.status_code == 200
        from datetime import date
        rows = tmp_db.execute(
            "SELECT * FROM chore_instances WHERE chore_id = ? AND due_date = ?",
            (shop_id, date.today().isoformat()),
        ).fetchall()
        assert len(rows) == 1
        assert rows[0]["status"] == "completed"
        assert rows[0]["completed_by"] == "person.shopper"

    def test_hook_completes_existing_pending_instance(self, client, tmp_db):
        shop_id, _ = self._seed_basic(tmp_db)
        from datetime import date
        tmp_db.execute(
            "INSERT INTO chore_instances (chore_id, due_date, status) VALUES (?, ?, 'pending')",
            (shop_id, date.today().isoformat()),
        )
        existing_id = tmp_db.execute("SELECT last_insert_rowid()").fetchone()[0]
        tmp_db.commit()
        resp = client.post("/api/shopping-hook/complete", json={
            "chore_id": shop_id,
            "person": "person.shopper",
            "suppress_followup": False,
        })
        assert resp.status_code == 200
        row = tmp_db.execute(
            "SELECT * FROM chore_instances WHERE id = ?", (existing_id,)
        ).fetchone()
        assert row["status"] == "completed"
        # Should NOT have created a duplicate
        count = tmp_db.execute(
            "SELECT COUNT(*) FROM chore_instances WHERE chore_id = ? AND due_date = ?",
            (shop_id, date.today().isoformat()),
        ).fetchone()[0]
        assert count == 1

    def test_hook_suppress_followup_blocks_spawn(self, client, tmp_db):
        shop_id, scan_id = self._seed_basic(tmp_db)
        resp = client.post("/api/shopping-hook/complete", json={
            "chore_id": shop_id,
            "person": "person.shopper",
            "suppress_followup": True,
        })
        assert resp.status_code == 200
        from datetime import date
        followups = tmp_db.execute(
            "SELECT * FROM chore_instances WHERE chore_id = ? AND due_date = ?",
            (scan_id, date.today().isoformat()),
        ).fetchall()
        assert followups == []

    def test_hook_spawns_followup_when_not_suppressed(self, client, tmp_db):
        shop_id, scan_id = self._seed_basic(tmp_db)
        resp = client.post("/api/shopping-hook/complete", json={
            "chore_id": shop_id,
            "person": "person.shopper",
            "suppress_followup": False,
        })
        assert resp.status_code == 200
        from datetime import date
        followups = tmp_db.execute(
            "SELECT * FROM chore_instances WHERE chore_id = ? AND due_date = ?",
            (scan_id, date.today().isoformat()),
        ).fetchall()
        assert len(followups) == 1
        assert followups[0]["status"] == "pending"

    def test_hook_unknown_chore_returns_404(self, client, tmp_db):
        tmp_db.execute(
            "INSERT INTO persons (entity_id, name) VALUES ('person.x', 'X')"
        )
        tmp_db.commit()
        resp = client.post("/api/shopping-hook/complete", json={
            "chore_id": 99999,
            "person": "person.x",
            "suppress_followup": False,
        })
        assert resp.status_code == 404


class TestPendingCelebrationsAPI:
    def _seed_person_with_ha_user(self, tmp_db, entity_id="person.cele",
                                  ha_user_id="ha-user-1"):
        tmp_db.execute(
            "INSERT INTO persons (entity_id, name, ha_user_id) VALUES (?, ?, ?)",
            (entity_id, "Cele", ha_user_id),
        )
        tmp_db.commit()

    def _insert_celebration(self, tmp_db, person_id, payload='{"leveled_up":true}',
                            seen_at=None):
        tmp_db.execute(
            "INSERT INTO pending_celebrations (person_id, payload, seen_at) VALUES (?, ?, ?)",
            (person_id, payload, seen_at),
        )
        tmp_db.commit()
        return tmp_db.execute("SELECT last_insert_rowid()").fetchone()[0]

    def test_get_returns_unseen_only(self, client, tmp_db):
        self._seed_person_with_ha_user(tmp_db)
        unseen_id = self._insert_celebration(tmp_db, "person.cele")
        self._insert_celebration(tmp_db, "person.cele", seen_at="2025-01-01T00:00:00")
        resp = client.get(
            "/api/persons/me/pending-celebrations",
            headers={"X-Remote-User-Id": "ha-user-1"},
        )
        assert resp.status_code == 200
        rows = resp.json()
        assert len(rows) == 1
        assert rows[0]["id"] == unseen_id

    def test_get_returns_empty_when_no_user_header(self, client, tmp_db):
        self._seed_person_with_ha_user(tmp_db)
        self._insert_celebration(tmp_db, "person.cele")
        resp = client.get("/api/persons/me/pending-celebrations")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_payload_is_parsed_as_json(self, client, tmp_db):
        self._seed_person_with_ha_user(tmp_db)
        self._insert_celebration(tmp_db, "person.cele",
                                 payload='{"leveled_up":true,"new_level":5}')
        resp = client.get(
            "/api/persons/me/pending-celebrations",
            headers={"X-Remote-User-Id": "ha-user-1"},
        )
        rows = resp.json()
        assert rows[0]["payload"]["new_level"] == 5
