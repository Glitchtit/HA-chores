"""Undo of a completion writes every gamification row back; undo of a fresh
schedule deletes it."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import date

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_db):
    from main import app
    with TestClient(app) as c:
        tmp_db.execute("INSERT INTO persons (entity_id, name) VALUES ('person.a', 'A')")
        tmp_db.commit()
        yield c


def _state(conn):
    tables = ["persons", "person_badges", "person_powerups", "pet_states",
              "pending_celebrations", "daily_quests", "daily_quest_bundles"]
    return {t: [tuple(r) for r in conn.execute(f"SELECT * FROM {t} ORDER BY 1, 2")] for t in tables}


def _schedule(client, chore_id):
    return client.post("/api/assignments/", json={
        "chore_id": chore_id, "due_date": date.today().isoformat(),
        "assigned_to": "person.a", "created_by": "person.a",
    }).json()["id"]


def test_undo_completion_restores_everything(client, tmp_db):
    followup = client.post("/api/chores/", json={"name": "Dry"}).json()
    chore = client.post("/api/chores/", json={"name": "Wash", "xp_reward": 50}).json()
    tmp_db.execute("UPDATE chores SET followup_chore_id = ? WHERE id = ?", (followup["id"], chore["id"]))
    tmp_db.commit()
    inst = _schedule(client, chore["id"])
    before = _state(tmp_db)
    instances_before = tmp_db.execute("SELECT count(*) FROM chore_instances").fetchone()[0]

    done = client.post(f"/api/assignments/{inst}/complete", json={"completed_by": "person.a"})
    assert done.status_code == 200 and done.json()["xp_awarded"] > 0
    assert _state(tmp_db) != before  # XP, first-chore badge, pet...

    resp = client.post(f"/api/assignments/{inst}/undo", json={})
    assert resp.status_code == 200, resp.text
    assert _state(tmp_db) == before
    row = tmp_db.execute("SELECT status, undo FROM chore_instances WHERE id = ?", (inst,)).fetchone()
    assert row["status"] == "pending" and row["undo"] is None
    assert tmp_db.execute("SELECT count(*) FROM chore_instances").fetchone()[0] == instances_before

    # Undone once means not completed any more.
    assert client.post(f"/api/assignments/{inst}/undo", json={}).json()["undone"] == "schedule"


def test_undo_with_remove_deletes_quick_logged_instance(client, tmp_db):
    chore = client.post("/api/chores/", json={"name": "Vacuum"}).json()
    inst = _schedule(client, chore["id"])
    client.post(f"/api/assignments/{inst}/complete", json={"completed_by": "person.a", "remove_on_undo": True})
    resp = client.post(f"/api/assignments/{inst}/undo", json={})
    assert resp.status_code == 200
    assert tmp_db.execute("SELECT 1 FROM chore_instances WHERE id = ?", (inst,)).fetchone() is None
    assert tmp_db.execute("SELECT xp_total FROM persons").fetchone()[0] == 0


def test_undo_refused_after_a_later_completion(client, tmp_db):
    chore = client.post("/api/chores/", json={"name": "Vacuum"}).json()
    first, second = _schedule(client, chore["id"]), _schedule(client, chore["id"])
    client.post(f"/api/assignments/{first}/complete", json={"completed_by": "person.a"})
    client.post(f"/api/assignments/{second}/complete", json={"completed_by": "person.a"})
    resp = client.post(f"/api/assignments/{first}/undo", json={})
    assert resp.status_code == 400 and "undo that first" in resp.json()["detail"]


def test_undo_schedule_deletes_fresh_instance_only(client, tmp_db):
    chore = client.post("/api/chores/", json={"name": "Trash"}).json()
    inst = _schedule(client, chore["id"])
    assert client.post(f"/api/assignments/{inst}/undo", json={}).json()["undone"] == "schedule"
    assert tmp_db.execute("SELECT 1 FROM chore_instances WHERE id = ?", (inst,)).fetchone() is None

    old = _schedule(client, chore["id"])
    tmp_db.execute("UPDATE chore_instances SET created_at = datetime('now', '-2 hours') WHERE id = ?", (old,))
    tmp_db.commit()
    assert client.post(f"/api/assignments/{old}/undo", json={}).status_code == 400


def test_undo_last_picks_newest_completion(client, tmp_db):
    chore = client.post("/api/chores/", json={"name": "Vacuum"}).json()
    first, second = _schedule(client, chore["id"]), _schedule(client, chore["id"])
    client.post(f"/api/assignments/{first}/complete", json={"completed_by": "person.a"})
    client.post(f"/api/assignments/{second}/complete", json={"completed_by": "person.a"})
    assert client.post("/api/assignments/undo-last").json()["instance_id"] == second
    assert client.post("/api/assignments/undo-last").json()["instance_id"] == first
    assert client.post("/api/assignments/undo-last").status_code == 400
