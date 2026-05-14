"""Tests for tokens + cosmetics shop (v0.4.3)."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_db):
    from main import app
    with TestClient(app) as c:
        yield c


def _seed_person(conn, entity_id="person.alice", name="Alice", level=1, xp=0, tokens=0):
    conn.execute(
        """INSERT INTO persons (entity_id, name, xp_total, level, tokens)
           VALUES (?, ?, ?, ?, ?)""",
        (entity_id, name, xp, level, tokens),
    )
    conn.commit()


# ── Token accrual ─────────────────────────────────────────────────────────────

class TestTokenAccrual:
    def test_add_xp_mints_one_token_per_ten_xp(self, tmp_db):
        from gamification import add_xp
        _seed_person(tmp_db, "person.alice", xp=0, tokens=0)
        add_xp("person.alice", 25)
        tokens = tmp_db.execute(
            "SELECT tokens FROM persons WHERE entity_id = ?", ("person.alice",)
        ).fetchone()["tokens"]
        assert tokens == 2  # 25 // 10 = 2

    def test_add_xp_accumulates_tokens(self, tmp_db):
        from gamification import add_xp
        _seed_person(tmp_db, "person.alice", xp=0, tokens=5)
        add_xp("person.alice", 100)
        tokens = tmp_db.execute(
            "SELECT tokens FROM persons WHERE entity_id = ?", ("person.alice",)
        ).fetchone()["tokens"]
        assert tokens == 15  # 5 + 10

    def test_add_xp_zero_mints_no_tokens(self, tmp_db):
        from gamification import add_xp
        _seed_person(tmp_db, "person.alice", xp=50, tokens=3)
        add_xp("person.alice", 0)
        tokens = tmp_db.execute(
            "SELECT tokens FROM persons WHERE entity_id = ?", ("person.alice",)
        ).fetchone()["tokens"]
        assert tokens == 3

    def test_award_tokens_helper(self, tmp_db):
        from gamification import award_tokens
        _seed_person(tmp_db, "person.alice", tokens=10)
        balance = award_tokens("person.alice", 25, reason="challenge reward")
        assert balance == 35

    def test_spend_tokens_succeeds_when_enough(self, tmp_db):
        from gamification import spend_tokens
        _seed_person(tmp_db, "person.alice", tokens=100)
        assert spend_tokens("person.alice", 60) is True
        tokens = tmp_db.execute(
            "SELECT tokens FROM persons WHERE entity_id = ?", ("person.alice",)
        ).fetchone()["tokens"]
        assert tokens == 40

    def test_spend_tokens_fails_when_insufficient(self, tmp_db):
        from gamification import spend_tokens
        _seed_person(tmp_db, "person.alice", tokens=5)
        assert spend_tokens("person.alice", 50) is False
        tokens = tmp_db.execute(
            "SELECT tokens FROM persons WHERE entity_id = ?", ("person.alice",)
        ).fetchone()["tokens"]
        assert tokens == 5  # unchanged


# ── Catalog ──────────────────────────────────────────────────────────────────

class TestCatalog:
    def test_catalog_excludes_hidden_by_default(self, client):
        resp = client.get("/api/cosmetics/")
        assert resp.status_code == 200
        items = resp.json()
        assert all(c["hidden"] == 0 for c in items)
        ids = {c["id"] for c in items}
        assert "hat_party" in ids
        assert "hat_laurel" not in ids  # boss-locked, hidden

    def test_catalog_includes_hidden_with_flag(self, client):
        resp = client.get("/api/cosmetics/?include_hidden=true")
        ids = {c["id"] for c in resp.json()}
        assert "hat_laurel" in ids


# ── Purchase / equip / unequip ───────────────────────────────────────────────

class TestPurchase:
    def test_purchase_deducts_tokens_and_grants_item(self, client, tmp_db):
        _seed_person(tmp_db, "person.alice", tokens=100)
        resp = client.post(
            "/api/cosmetics/person.alice/purchase",
            json={"cosmetic_id": "hat_party"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "purchased"
        assert resp.json()["tokens"] == 50  # 100 - 50 cost

    def test_purchase_insufficient_tokens_returns_402(self, client, tmp_db):
        _seed_person(tmp_db, "person.alice", tokens=10)
        resp = client.post(
            "/api/cosmetics/person.alice/purchase",
            json={"cosmetic_id": "hat_party"},
        )
        assert resp.status_code == 402

    def test_purchase_already_owned_is_idempotent(self, client, tmp_db):
        _seed_person(tmp_db, "person.alice", tokens=200)
        client.post(
            "/api/cosmetics/person.alice/purchase",
            json={"cosmetic_id": "hat_party"},
        )
        resp = client.post(
            "/api/cosmetics/person.alice/purchase",
            json={"cosmetic_id": "hat_party"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "already_owned"

    def test_purchase_boss_locked_forbidden(self, client, tmp_db):
        _seed_person(tmp_db, "person.alice", tokens=10_000)
        resp = client.post(
            "/api/cosmetics/person.alice/purchase",
            json={"cosmetic_id": "hat_laurel"},
        )
        assert resp.status_code == 403

    def test_purchase_level_locked_requires_level(self, client, tmp_db):
        _seed_person(tmp_db, "person.alice", level=5, tokens=10)
        resp = client.post(
            "/api/cosmetics/person.alice/purchase",
            json={"cosmetic_id": "hat_graduate"},  # requires level 10
        )
        assert resp.status_code == 403

    def test_purchase_level_locked_succeeds_at_threshold(self, client, tmp_db):
        _seed_person(tmp_db, "person.alice", level=10, tokens=0)
        resp = client.post(
            "/api/cosmetics/person.alice/purchase",
            json={"cosmetic_id": "hat_graduate"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "purchased"


class TestEquip:
    def test_equip_after_purchase(self, client, tmp_db):
        _seed_person(tmp_db, "person.alice", tokens=200)
        client.post(
            "/api/cosmetics/person.alice/purchase",
            json={"cosmetic_id": "hat_party"},
        )
        resp = client.post(
            "/api/cosmetics/person.alice/equip",
            json={"cosmetic_id": "hat_party"},
        )
        assert resp.status_code == 200
        # Verify equipped state
        row = tmp_db.execute(
            "SELECT equipped FROM person_cosmetics WHERE person_id = ? AND cosmetic_id = ?",
            ("person.alice", "hat_party"),
        ).fetchone()
        assert row["equipped"] == 1

    def test_equip_unequips_other_in_same_slot(self, client, tmp_db):
        _seed_person(tmp_db, "person.alice", tokens=500)
        client.post("/api/cosmetics/person.alice/purchase", json={"cosmetic_id": "hat_party"})
        client.post("/api/cosmetics/person.alice/purchase", json={"cosmetic_id": "hat_chef"})
        client.post("/api/cosmetics/person.alice/equip", json={"cosmetic_id": "hat_party"})
        client.post("/api/cosmetics/person.alice/equip", json={"cosmetic_id": "hat_chef"})

        equipped = {
            r["cosmetic_id"]: r["equipped"]
            for r in tmp_db.execute(
                "SELECT cosmetic_id, equipped FROM person_cosmetics WHERE person_id = ?",
                ("person.alice",),
            ).fetchall()
        }
        assert equipped["hat_chef"] == 1
        assert equipped["hat_party"] == 0

    def test_equip_unowned_forbidden(self, client, tmp_db):
        _seed_person(tmp_db, "person.alice", tokens=0)
        resp = client.post(
            "/api/cosmetics/person.alice/equip",
            json={"cosmetic_id": "hat_party"},
        )
        assert resp.status_code == 403

    def test_unequip_clears_slot(self, client, tmp_db):
        _seed_person(tmp_db, "person.alice", tokens=200)
        client.post("/api/cosmetics/person.alice/purchase", json={"cosmetic_id": "hat_party"})
        client.post("/api/cosmetics/person.alice/equip", json={"cosmetic_id": "hat_party"})
        resp = client.post(
            "/api/cosmetics/person.alice/unequip", json={"slot": "hat"}
        )
        assert resp.status_code == 200
        row = tmp_db.execute(
            "SELECT equipped FROM person_cosmetics WHERE person_id = ? AND cosmetic_id = ?",
            ("person.alice", "hat_party"),
        ).fetchone()
        assert row["equipped"] == 0

    def test_unequip_unknown_slot_422(self, client, tmp_db):
        _seed_person(tmp_db, "person.alice")
        resp = client.post(
            "/api/cosmetics/person.alice/unequip", json={"slot": "shoes"}
        )
        assert resp.status_code == 422


# ── Person-scoped catalog view ────────────────────────────────────────────────

class TestPersonView:
    def test_lists_owned_equipped_unlocked_flags(self, client, tmp_db):
        _seed_person(tmp_db, "person.alice", level=12, tokens=300)
        client.post(
            "/api/cosmetics/person.alice/purchase",
            json={"cosmetic_id": "hat_party"},
        )
        resp = client.get("/api/cosmetics/person.alice")
        assert resp.status_code == 200
        data = resp.json()
        assert data["tokens"] == 250  # 300 - 50
        by_id = {c["id"]: c for c in data["items"]}
        assert by_id["hat_party"]["owned"] is True
        assert by_id["hat_chef"]["owned"] is False
        # Level-unlocked item should report `unlocked: True` for level 12
        assert by_id["hat_graduate"]["unlocked"] is True
        # Higher-level unlock not yet available
        assert by_id["hat_halo"]["unlocked"] is False

    def test_unknown_person_404(self, client):
        resp = client.get("/api/cosmetics/person.ghost")
        assert resp.status_code == 404


# ── Pet view surfaces tokens + equipped ───────────────────────────────────────

class TestPetViewIntegration:
    def test_pet_view_includes_tokens_and_equipped(self, client, tmp_db):
        _seed_person(tmp_db, "person.alice", tokens=80)
        # Purchase + equip
        client.post(
            "/api/cosmetics/person.alice/purchase",
            json={"cosmetic_id": "hat_party"},
        )
        client.post(
            "/api/cosmetics/person.alice/equip",
            json={"cosmetic_id": "hat_party"},
        )
        resp = client.get("/api/pets/me?person_id=person.alice")
        data = resp.json()
        assert data["tokens"] == 30
        assert "hat" in data["equipped"]
        assert data["equipped"]["hat"]["id"] == "hat_party"


# ── Placed nameplates (v0.7.0) ───────────────────────────────────────────────

class TestPlacedNameplates:
    def _setup_owner(self, client, tmp_db, entity_id="person.alice", plate_id="plate_gold"):
        _seed_person(tmp_db, entity_id, tokens=1000)
        # Buy the nameplate so the person owns it
        resp = client.post(
            f"/api/cosmetics/{entity_id}/purchase",
            json={"cosmetic_id": plate_id},
        )
        assert resp.status_code == 200, resp.text
        return entity_id, plate_id

    def test_place_writes_row(self, client, tmp_db):
        eid, plate = self._setup_owner(client, tmp_db)
        resp = client.put(
            f"/api/cosmetics/nameplates/placed/{eid}",
            json={"cosmetic_id": plate, "x": 25.0, "y": 60.0},
        )
        assert resp.status_code == 200
        assert resp.json()["x"] == 25.0
        row = tmp_db.execute(
            "SELECT cosmetic_id, x, y FROM placed_nameplates WHERE person_id = ?", (eid,)
        ).fetchone()
        assert row["cosmetic_id"] == plate
        assert row["x"] == 25.0
        assert row["y"] == 60.0

    def test_place_clamps_coordinates(self, client, tmp_db):
        eid, plate = self._setup_owner(client, tmp_db)
        resp = client.put(
            f"/api/cosmetics/nameplates/placed/{eid}",
            json={"cosmetic_id": plate, "x": -50.0, "y": 9999.0},
        )
        assert resp.status_code == 200
        assert resp.json()["x"] == 0.0
        assert resp.json()["y"] == 100.0

    def test_place_is_idempotent_overwrite(self, client, tmp_db):
        eid, plate = self._setup_owner(client, tmp_db)
        client.put(
            f"/api/cosmetics/nameplates/placed/{eid}",
            json={"cosmetic_id": plate, "x": 10.0, "y": 10.0},
        )
        client.put(
            f"/api/cosmetics/nameplates/placed/{eid}",
            json={"cosmetic_id": plate, "x": 80.0, "y": 80.0},
        )
        count = tmp_db.execute(
            "SELECT COUNT(*) AS c FROM placed_nameplates WHERE person_id = ?", (eid,)
        ).fetchone()["c"]
        row = tmp_db.execute(
            "SELECT x, y FROM placed_nameplates WHERE person_id = ?", (eid,)
        ).fetchone()
        assert count == 1
        assert row["x"] == 80.0

    def test_place_requires_ownership(self, client, tmp_db):
        _seed_person(tmp_db, "person.bob", tokens=0)
        resp = client.put(
            "/api/cosmetics/nameplates/placed/person.bob",
            json={"cosmetic_id": "plate_gold", "x": 50, "y": 50},
        )
        assert resp.status_code == 403

    def test_place_rejects_non_nameplate(self, client, tmp_db):
        _seed_person(tmp_db, "person.alice", tokens=1000)
        client.post(
            "/api/cosmetics/person.alice/purchase",
            json={"cosmetic_id": "hat_party"},
        )
        resp = client.put(
            "/api/cosmetics/nameplates/placed/person.alice",
            json={"cosmetic_id": "hat_party", "x": 50, "y": 50},
        )
        assert resp.status_code == 422

    def test_list_includes_pet_name(self, client, tmp_db):
        eid, plate = self._setup_owner(client, tmp_db)
        # Give the pet a custom name so we can verify it surfaces
        tmp_db.execute(
            "INSERT OR REPLACE INTO pet_states (person_id, pet_name) VALUES (?, ?)",
            (eid, "Squiggle"),
        )
        tmp_db.commit()
        client.put(
            f"/api/cosmetics/nameplates/placed/{eid}",
            json={"cosmetic_id": plate, "x": 33, "y": 66},
        )
        resp = client.get("/api/cosmetics/nameplates/placed")
        assert resp.status_code == 200
        rows = resp.json()
        assert len(rows) == 1
        assert rows[0]["person_id"] == eid
        assert rows[0]["display_name"] == "Squiggle"
        assert rows[0]["cosmetic_id"] == plate

    def test_delete_removes_row(self, client, tmp_db):
        eid, plate = self._setup_owner(client, tmp_db)
        client.put(
            f"/api/cosmetics/nameplates/placed/{eid}",
            json={"cosmetic_id": plate, "x": 50, "y": 50},
        )
        resp = client.delete(f"/api/cosmetics/nameplates/placed/{eid}")
        assert resp.status_code == 200
        assert resp.json()["rows"] == 1
        count = tmp_db.execute(
            "SELECT COUNT(*) AS c FROM placed_nameplates WHERE person_id = ?", (eid,)
        ).fetchone()["c"]
        assert count == 0


# ── Migration ────────────────────────────────────────────────────────────────

class TestMigration:
    def test_migration_adds_tokens_column(self, tmp_path, monkeypatch):
        import sqlite3
        db_path = str(tmp_path / "legacy_tokens.db")
        legacy = sqlite3.connect(db_path)
        legacy.execute(
            """CREATE TABLE persons (
                 entity_id TEXT PRIMARY KEY,
                 name TEXT,
                 xp_total INTEGER DEFAULT 0,
                 level INTEGER DEFAULT 1,
                 current_streak INTEGER DEFAULT 0,
                 longest_streak INTEGER DEFAULT 0)"""
        )
        legacy.execute("INSERT INTO persons (entity_id, name) VALUES ('person.old', 'Old')")
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
        assert "tokens" in cols
        row = conn.execute(
            "SELECT tokens FROM persons WHERE entity_id = ?", ("person.old",)
        ).fetchone()
        assert row["tokens"] == 0
        database.close_connection()
