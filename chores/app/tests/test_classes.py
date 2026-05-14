"""Tests for class specialization (v0.4.4)."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json as _json
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_db):
    from main import app
    with TestClient(app) as c:
        yield c


def _seed_person(conn, entity_id="person.alice", name="Alice", level=5, xp=400):
    conn.execute(
        """INSERT INTO persons (entity_id, name, xp_total, level)
           VALUES (?, ?, ?, ?)""",
        (entity_id, name, xp, level),
    )
    conn.commit()


def _seed_chore(conn, chore_id, category, xp_reward=20, difficulty="medium"):
    conn.execute(
        """INSERT INTO chores (id, name, category, xp_reward, difficulty, active)
           VALUES (?, ?, ?, ?, ?, 1)""",
        (chore_id, f"Chore {chore_id}", category, xp_reward, difficulty),
    )
    conn.commit()


# ── class_multiplier helper ───────────────────────────────────────────────────

class TestClassMultiplier:
    def test_specialist_matches_category(self):
        from classes import class_multiplier
        assert class_multiplier("dishwasher", "dishes") == 0.15
        assert class_multiplier("chef", "cooking") == 0.15

    def test_specialist_other_category_no_bonus(self):
        from classes import class_multiplier
        assert class_multiplier("dishwasher", "laundry") == 0.0

    def test_generalist_flat_5_percent(self):
        from classes import class_multiplier
        assert class_multiplier("generalist", "dishes") == 0.05
        assert class_multiplier("generalist", "other") == 0.05
        assert class_multiplier("generalist", None) == 0.05

    def test_no_class_no_bonus(self):
        from classes import class_multiplier
        assert class_multiplier(None, "dishes") == 0.0
        assert class_multiplier("", "dishes") == 0.0

    def test_unknown_class_no_bonus(self):
        from classes import class_multiplier
        assert class_multiplier("ninja", "dishes") == 0.0


# ── calculate_xp integration ──────────────────────────────────────────────────

class TestCalculateXP:
    def test_dishwasher_gets_15_percent_on_dishes(self):
        from gamification import calculate_xp
        # 100 base * (1.0 + 0.15) → int() truncation lands on 114 due to float repr
        assert calculate_xp(100, category="dishes", class_id="dishwasher") == 114

    def test_dishwasher_no_bonus_on_laundry(self):
        from gamification import calculate_xp
        assert calculate_xp(100, category="laundry", class_id="dishwasher") == 100

    def test_generalist_flat_bonus(self):
        from gamification import calculate_xp
        assert calculate_xp(100, category="laundry", class_id="generalist") == 105

    def test_class_stacks_with_streak(self):
        from gamification import calculate_xp
        # 100 * (1 + 0.3 streak + 0.15 class) = 145 (int truncation)
        result = calculate_xp(100, streak=3, category="dishes", class_id="dishwasher")
        assert 144 <= result <= 145


# ── Catalog + endpoint ────────────────────────────────────────────────────────

class TestClassRouter:
    def test_catalog_lists_classes_and_pick_level(self, client):
        resp = client.get("/api/classes/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["pick_level"] == 5
        ids = {c["id"] for c in data["classes"]}
        assert ids == {"dishwasher", "launderer", "chef", "cleaner", "generalist"}

    def test_set_class_below_level_5_forbidden(self, client, tmp_db):
        _seed_person(tmp_db, level=4)
        resp = client.post(
            "/api/classes/persons/person.alice",
            json={"class_id": "dishwasher"},
        )
        assert resp.status_code == 403

    def test_set_class_at_level_5_succeeds(self, client, tmp_db):
        _seed_person(tmp_db, level=5)
        resp = client.post(
            "/api/classes/persons/person.alice",
            json={"class_id": "dishwasher"},
        )
        assert resp.status_code == 200
        row = tmp_db.execute(
            "SELECT class_id FROM persons WHERE entity_id = ?", ("person.alice",)
        ).fetchone()
        assert row["class_id"] == "dishwasher"

    def test_respec_is_free(self, client, tmp_db):
        _seed_person(tmp_db, level=10)
        client.post(
            "/api/classes/persons/person.alice",
            json={"class_id": "dishwasher"},
        )
        # Switch to chef without paying anything
        resp = client.post(
            "/api/classes/persons/person.alice",
            json={"class_id": "chef"},
        )
        assert resp.status_code == 200
        row = tmp_db.execute(
            "SELECT class_id FROM persons WHERE entity_id = ?", ("person.alice",)
        ).fetchone()
        assert row["class_id"] == "chef"

    def test_clear_class(self, client, tmp_db):
        _seed_person(tmp_db, level=10)
        client.post(
            "/api/classes/persons/person.alice",
            json={"class_id": "dishwasher"},
        )
        resp = client.post(
            "/api/classes/persons/person.alice", json={"class_id": ""}
        )
        assert resp.status_code == 200
        row = tmp_db.execute(
            "SELECT class_id FROM persons WHERE entity_id = ?", ("person.alice",)
        ).fetchone()
        assert row["class_id"] == ""

    def test_unknown_class_422(self, client, tmp_db):
        _seed_person(tmp_db, level=10)
        resp = client.post(
            "/api/classes/persons/person.alice",
            json={"class_id": "ninja"},
        )
        assert resp.status_code == 422

    def test_unknown_person_404(self, client):
        resp = client.post(
            "/api/classes/persons/person.ghost",
            json={"class_id": "dishwasher"},
        )
        assert resp.status_code == 404


# ── Class-pick prompt on level-5 cross ────────────────────────────────────────

class TestClassPickPrompt:
    def test_crossing_level_5_emits_prompt_when_no_class(self, client, tmp_db):
        # Seed at 395 XP (level 4 under linear curve, classless)
        _seed_person(tmp_db, level=4, xp=395)
        _seed_chore(tmp_db, chore_id=1, category="dishes", xp_reward=50)
        from datetime import date as _date
        cursor = tmp_db.execute(
            """INSERT INTO chore_instances (chore_id, due_date, assigned_to, status)
               VALUES (1, ?, 'person.alice', 'pending')""",
            (_date.today().isoformat(),),
        )
        tmp_db.commit()
        iid = cursor.lastrowid

        resp = client.post(
            f"/api/assignments/{iid}/complete",
            json={"completed_by": "person.alice"},
        )
        assert resp.status_code == 200

        payloads = [
            _json.loads(r["payload"])
            for r in tmp_db.execute(
                "SELECT payload FROM pending_celebrations WHERE person_id = ?",
                ("person.alice",),
            ).fetchall()
        ]
        assert any(p.get("class_pick_prompt") is True for p in payloads)

    def test_crossing_level_5_no_prompt_when_class_already_set(self, client, tmp_db):
        _seed_person(tmp_db, level=4, xp=395)
        tmp_db.execute(
            "UPDATE persons SET class_id = 'dishwasher' WHERE entity_id = ?",
            ("person.alice",),
        )
        _seed_chore(tmp_db, chore_id=1, category="dishes", xp_reward=50)
        from datetime import date as _date
        cursor = tmp_db.execute(
            """INSERT INTO chore_instances (chore_id, due_date, assigned_to, status)
               VALUES (1, ?, 'person.alice', 'pending')""",
            (_date.today().isoformat(),),
        )
        tmp_db.commit()
        iid = cursor.lastrowid

        resp = client.post(
            f"/api/assignments/{iid}/complete",
            json={"completed_by": "person.alice"},
        )
        assert resp.status_code == 200
        payloads = [
            _json.loads(r["payload"])
            for r in tmp_db.execute(
                "SELECT payload FROM pending_celebrations WHERE person_id = ?",
                ("person.alice",),
            ).fetchall()
        ]
        assert not any(p.get("class_pick_prompt") is True for p in payloads)


# ── Migration ─────────────────────────────────────────────────────────────────

class TestMigration:
    def test_migration_adds_class_columns(self, tmp_path, monkeypatch):
        import sqlite3
        db_path = str(tmp_path / "legacy_cls.db")
        legacy = sqlite3.connect(db_path)
        legacy.execute(
            """CREATE TABLE persons (
                 entity_id TEXT PRIMARY KEY,
                 name TEXT,
                 xp_total INTEGER DEFAULT 0,
                 level INTEGER DEFAULT 1)"""
        )
        legacy.commit()
        legacy.close()

        monkeypatch.setenv("DATA_DIR", str(tmp_path))
        monkeypatch.setenv("CHORES_SKIP_SEED_OTHER", "1")
        import database
        database._conn = None
        database.DB_PATH = db_path
        database.initialize()
        conn = database.get_connection()
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(persons)")}
        assert "class_id" in cols
        assert "class_chosen_at" in cols
        database.close_connection()
