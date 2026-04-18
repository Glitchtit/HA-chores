"""Tests for the pet feature (state logic + API)."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_db):
    from main import app
    with TestClient(app) as c:
        yield c


def _seed_person(conn, entity_id="person.alice", name="Alice", ha_user_id=""):
    conn.execute(
        "INSERT INTO persons (entity_id, name, ha_user_id) VALUES (?, ?, ?)",
        (entity_id, name, ha_user_id),
    )
    conn.commit()
    import pets
    pets.ensure_pet(conn, entity_id)


def _seed_chore(conn, chore_id=1, name="Do Dishes", category="dishes"):
    conn.execute(
        "INSERT INTO chores (id, name, category, active) VALUES (?, ?, ?, 1)",
        (chore_id, name, category),
    )
    conn.commit()


def _seed_overdue(conn, chore_id, assigned_to=None, due_date="2020-01-01", iid=None):
    if iid is None:
        cursor = conn.execute(
            """INSERT INTO chore_instances (chore_id, due_date, assigned_to, status)
               VALUES (?, ?, ?, 'overdue')""",
            (chore_id, due_date, assigned_to),
        )
        conn.commit()
        return cursor.lastrowid
    conn.execute(
        """INSERT INTO chore_instances (id, chore_id, due_date, assigned_to, status)
           VALUES (?, ?, ?, ?, 'overdue')""",
        (iid, chore_id, due_date, assigned_to),
    )
    conn.commit()
    return iid


# ── Unit: state logic ────────────────────────────────────────────────────────

class TestPetStateLogic:
    def test_ensure_pet_idempotent(self, tmp_db):
        import pets
        _seed_person(tmp_db)
        pets.ensure_pet(tmp_db, "person.alice")
        pets.ensure_pet(tmp_db, "person.alice")
        count = tmp_db.execute(
            "SELECT COUNT(*) AS c FROM pet_states WHERE person_id = ?", ("person.alice",)
        ).fetchone()["c"]
        assert count == 1

    def test_bump_happiness_clamps_at_100(self, tmp_db):
        import pets
        _seed_person(tmp_db)
        tmp_db.execute(
            "UPDATE pet_states SET happiness = 98 WHERE person_id = ?", ("person.alice",)
        )
        tmp_db.commit()
        new_val = pets.bump_happiness(tmp_db, "person.alice")
        assert new_val == 100

    def test_bump_overdue_bonus(self, tmp_db):
        import pets
        _seed_person(tmp_db)
        tmp_db.execute(
            "UPDATE pet_states SET happiness = 50 WHERE person_id = ?", ("person.alice",)
        )
        tmp_db.commit()
        new_val = pets.bump_happiness(tmp_db, "person.alice", was_overdue=True)
        # 50 + 5 + 2 = 57
        assert new_val == 57

    def test_decay_all_three_per_day(self, tmp_db):
        import pets
        _seed_person(tmp_db)
        tmp_db.execute(
            """UPDATE pet_states
               SET happiness = 80,
                   last_tick_at = datetime('now', '-3 days')
               WHERE person_id = ?""",
            ("person.alice",),
        )
        tmp_db.commit()
        pets.decay_all(tmp_db)
        new_val = tmp_db.execute(
            "SELECT happiness FROM pet_states WHERE person_id = ?", ("person.alice",)
        ).fetchone()["happiness"]
        assert new_val == 80 - 9

    def test_decay_clamps_at_zero(self, tmp_db):
        import pets
        _seed_person(tmp_db)
        tmp_db.execute(
            """UPDATE pet_states
               SET happiness = 2,
                   last_tick_at = datetime('now', '-10 days')
               WHERE person_id = ?""",
            ("person.alice",),
        )
        tmp_db.commit()
        pets.decay_all(tmp_db)
        new_val = tmp_db.execute(
            "SELECT happiness FROM pet_states WHERE person_id = ?", ("person.alice",)
        ).fetchone()["happiness"]
        assert new_val == 0

    def test_compute_cleanliness_per_person(self, tmp_db):
        import pets
        _seed_person(tmp_db, "person.alice")
        _seed_chore(tmp_db, chore_id=1, name="Dishes", category="dishes")
        _seed_chore(tmp_db, chore_id=2, name="Laundry", category="laundry")
        _seed_overdue(tmp_db, chore_id=1, assigned_to="person.alice")
        _seed_overdue(tmp_db, chore_id=2, assigned_to="person.alice")
        score, counts = pets.compute_cleanliness(tmp_db, "person.alice")
        assert score == 80  # 100 - 2*10
        assert counts["dishes"] == 1
        assert counts["laundry"] == 1
        assert counts["cleaning"] == 0

    def test_compute_household_includes_unassigned(self, tmp_db):
        import pets
        _seed_person(tmp_db, "person.alice")
        _seed_chore(tmp_db, chore_id=1, name="Dishes", category="dishes")
        _seed_overdue(tmp_db, chore_id=1, assigned_to="person.alice")
        _seed_overdue(tmp_db, chore_id=1, assigned_to=None)

        alice_score, alice_counts = pets.compute_cleanliness(tmp_db, "person.alice")
        # Alice has 1 overdue assigned (the unassigned one doesn't count toward her)
        assert alice_counts["dishes"] == 1
        assert alice_score == 90

        shared_score, shared_counts = pets.compute_household_cleanliness(tmp_db)
        # Shared counts both
        assert shared_counts["dishes"] == 2
        assert shared_score == 80


# ── API ──────────────────────────────────────────────────────────────────────

class TestPetsAPI:
    def test_get_me_shape(self, client, tmp_db):
        _seed_person(tmp_db, "person.alice", "Alice", ha_user_id="ha-alice")
        resp = client.get(
            "/api/pets/me", headers={"X-Remote-User-Id": "ha-alice"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["person_id"] == "person.alice"
        assert 0 <= data["happiness"] <= 100
        assert 0 <= data["cleanliness"] <= 100
        assert set(data["mess_counts"].keys()) == {
            "dishes", "laundry", "cleaning", "trash", "cooking", "other",
        }
        assert data["mood"] in {"ecstatic", "happy", "meh", "sad"}

    def test_get_me_fallback_query_param(self, client, tmp_db):
        _seed_person(tmp_db, "person.alice", "Alice")
        resp = client.get("/api/pets/me?person_id=person.alice")
        assert resp.status_code == 200
        assert resp.json()["person_id"] == "person.alice"

    def test_household_aggregates(self, client, tmp_db):
        _seed_person(tmp_db, "person.alice", "Alice")
        _seed_person(tmp_db, "person.bob", "Bob")
        _seed_chore(tmp_db, chore_id=1, name="Dishes", category="dishes")
        _seed_overdue(tmp_db, chore_id=1, assigned_to=None)
        resp = client.get("/api/pets/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["pets"]) == 2
        # Unassigned overdue shows up in shared, not per-person
        assert data["shared"]["mess_counts"]["dishes"] == 1
        for pet in data["pets"]:
            assert pet["mess_counts"]["dishes"] == 0

    def test_put_emoji_valid(self, client, tmp_db):
        _seed_person(tmp_db, "person.alice", "Alice")
        resp = client.put(
            "/api/pets/person.alice/emoji", json={"emoji": "🐱"}
        )
        assert resp.status_code == 200
        assert resp.json()["pet_emoji"] == "🐱"

    def test_put_emoji_empty_rejected(self, client, tmp_db):
        _seed_person(tmp_db, "person.alice", "Alice")
        resp = client.put(
            "/api/pets/person.alice/emoji", json={"emoji": ""}
        )
        assert resp.status_code == 422

    def test_put_emoji_too_long_rejected(self, client, tmp_db):
        _seed_person(tmp_db, "person.alice", "Alice")
        resp = client.put(
            "/api/pets/person.alice/emoji", json={"emoji": "aaaaaaaaa"}
        )
        assert resp.status_code == 422

    def test_complete_bumps_completer_not_assignee(self, client, tmp_db):
        _seed_person(tmp_db, "person.alice", "Alice")
        _seed_person(tmp_db, "person.bob", "Bob")
        _seed_chore(tmp_db, chore_id=1, name="Dishes", category="dishes")
        # Instance assigned to Bob
        cursor = tmp_db.execute(
            """INSERT INTO chore_instances (chore_id, due_date, assigned_to, status)
               VALUES (1, '2025-06-01', 'person.bob', 'pending')"""
        )
        tmp_db.commit()
        iid = cursor.lastrowid

        # Snapshot starting happiness for both
        import pets
        pets.ensure_pet(tmp_db, "person.alice")
        pets.ensure_pet(tmp_db, "person.bob")
        alice_before = tmp_db.execute(
            "SELECT happiness FROM pet_states WHERE person_id = ?", ("person.alice",)
        ).fetchone()["happiness"]
        bob_before = tmp_db.execute(
            "SELECT happiness FROM pet_states WHERE person_id = ?", ("person.bob",)
        ).fetchone()["happiness"]

        # Alice completes Bob's chore
        resp = client.post(
            f"/api/assignments/{iid}/complete",
            json={"completed_by": "person.alice"},
        )
        assert resp.status_code == 200

        alice_after = tmp_db.execute(
            "SELECT happiness FROM pet_states WHERE person_id = ?", ("person.alice",)
        ).fetchone()["happiness"]
        bob_after = tmp_db.execute(
            "SELECT happiness FROM pet_states WHERE person_id = ?", ("person.bob",)
        ).fetchone()["happiness"]

        assert alice_after > alice_before  # Alice got the bump
        assert bob_after == bob_before       # Bob unchanged

    def test_complete_returns_pet_delta(self, client, tmp_db):
        _seed_person(tmp_db, "person.alice", "Alice")
        _seed_chore(tmp_db, chore_id=1, name="Dishes", category="dishes")
        cursor = tmp_db.execute(
            """INSERT INTO chore_instances (chore_id, due_date, assigned_to, status)
               VALUES (1, '2025-06-01', 'person.alice', 'pending')"""
        )
        tmp_db.commit()
        iid = cursor.lastrowid

        resp = client.post(
            f"/api/assignments/{iid}/complete",
            json={"completed_by": "person.alice"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["pet_delta"] is not None
        assert data["pet_happiness"] is not None
        assert data["pet_delta"] >= 5  # HAPPINESS_BUMP minimum


# ── Chore category ───────────────────────────────────────────────────────────

class TestChoreCategory:
    def test_create_with_category(self, client):
        resp = client.post(
            "/api/chores/", json={"name": "Dishwasher", "category": "dishes"}
        )
        assert resp.status_code == 201
        assert resp.json()["category"] == "dishes"

    def test_default_category_other(self, client):
        resp = client.post("/api/chores/", json={"name": "Mystery Task"})
        assert resp.status_code == 201
        assert resp.json()["category"] == "other"

    def test_invalid_category_rejected(self, client):
        resp = client.post(
            "/api/chores/", json={"name": "Bogus", "category": "gardening"}
        )
        assert resp.status_code == 422

    def test_update_category(self, client):
        create = client.post("/api/chores/", json={"name": "Task"}).json()
        resp = client.put(
            f"/api/chores/{create['id']}", json={"category": "laundry"}
        )
        assert resp.status_code == 200
        assert resp.json()["category"] == "laundry"


# ── Scheduler midnight decay ─────────────────────────────────────────────────

class TestSchedulerPetDecay:
    def test_decay_all_from_pets_module(self, tmp_db):
        """Sanity check that decay_all runs idempotently against a fresh db."""
        import pets
        _seed_person(tmp_db, "person.alice", "Alice")
        # Pretend 2 days passed
        tmp_db.execute(
            """UPDATE pet_states
               SET happiness = 70, last_tick_at = datetime('now', '-2 days')
               WHERE person_id = ?""",
            ("person.alice",),
        )
        tmp_db.commit()
        affected = pets.decay_all(tmp_db)
        assert affected == 1
        new_val = tmp_db.execute(
            "SELECT happiness FROM pet_states WHERE person_id = ?", ("person.alice",)
        ).fetchone()["happiness"]
        assert new_val == 70 - 6
