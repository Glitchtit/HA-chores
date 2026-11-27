"""Undo of a completion puts back what it changed; undo of a fresh
schedule deletes it."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
from datetime import date, datetime, timedelta

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
    listed = client.get("/api/assignments/", params={"status": "completed"}).json()
    assert [ci["can_undo"] for ci in listed if ci["id"] == inst] == [True]
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


def _complete_wash(client):
    chore = client.post("/api/chores/", json={"name": "Wash", "xp_reward": 50}).json()
    inst = _schedule(client, chore["id"])
    assert client.post(f"/api/assignments/{inst}/complete", json={"completed_by": "person.a"}).status_code == 200
    return inst


def _shop_item(conn):
    return conn.execute(
        "SELECT id, cost_tokens FROM cosmetics WHERE unlock_type = 'shop'"
        " AND cost_tokens > 0 ORDER BY cost_tokens LIMIT 1"
    ).fetchone()


def test_undo_leaves_someone_elses_purchase_alone(client, tmp_db):
    tmp_db.execute("INSERT INTO persons (entity_id, name, tokens) VALUES ('person.b', 'B', 500)")
    tmp_db.commit()
    a_before = tuple(tmp_db.execute("SELECT xp_total, level, tokens FROM persons WHERE entity_id = 'person.a'").fetchone())
    inst = _complete_wash(client)
    assert tmp_db.execute("SELECT xp_total FROM persons WHERE entity_id = 'person.a'").fetchone()[0] > 0
    item = _shop_item(tmp_db)
    assert client.post("/api/cosmetics/person.b/purchase", json={"cosmetic_id": item["id"]}).json()["status"] == "purchased"

    assert client.post(f"/api/assignments/{inst}/undo", json={}).status_code == 200
    assert tmp_db.execute("SELECT tokens FROM persons WHERE entity_id = 'person.b'").fetchone()[0] == 500 - item["cost_tokens"]
    assert tmp_db.execute("SELECT 1 FROM person_cosmetics WHERE person_id = 'person.b' AND cosmetic_id = ?",
                          (item["id"],)).fetchone()
    assert tuple(tmp_db.execute("SELECT xp_total, level, tokens FROM persons WHERE entity_id = 'person.a'").fetchone()) == a_before


def test_undo_keeps_celebrations_seen_since(client, tmp_db):
    tmp_db.execute("INSERT INTO persons (entity_id, name, ha_user_id) VALUES ('person.b', 'B', 'user-b')")
    tmp_db.execute("INSERT INTO pending_celebrations (person_id, payload) VALUES ('person.b', '{}')")
    tmp_db.commit()
    cel = tmp_db.execute("SELECT id FROM pending_celebrations WHERE person_id = 'person.b'").fetchone()[0]
    inst = _complete_wash(client)
    ack = client.post("/api/persons/me/pending-celebrations/ack", json={"ids": [cel]},
                      headers={"X-Remote-User-Id": "user-b"})
    assert ack.json()["acked"] == 1

    assert client.post(f"/api/assignments/{inst}/undo", json={}).status_code == 200
    assert tmp_db.execute("SELECT seen_at FROM pending_celebrations WHERE id = ?", (cel,)).fetchone()[0] is not None


def test_undo_refused_when_its_changes_changed_again(client, tmp_db):
    item = _shop_item(tmp_db)
    tmp_db.execute("UPDATE persons SET tokens = ? WHERE entity_id = 'person.a'", (item["cost_tokens"] - 1,))
    tmp_db.commit()
    inst = _complete_wash(client)  # earns the missing token(s)
    assert client.post("/api/cosmetics/person.a/purchase", json={"cosmetic_id": item["id"]}).json()["status"] == "purchased"
    after_purchase = _state(tmp_db)

    resp = client.post(f"/api/assignments/{inst}/undo", json={})
    assert resp.status_code == 400 and "cannot undo" in resp.json()["detail"]
    assert _state(tmp_db) == after_purchase
    assert tmp_db.execute("SELECT status FROM chore_instances WHERE id = ?", (inst,)).fetchone()[0] == "completed"


def test_undo_snapshot_skips_seen_celebrations(client, tmp_db):
    for _ in range(50):
        tmp_db.execute(
            "INSERT INTO pending_celebrations (person_id, payload, seen_at) VALUES ('person.a', ?, ?)",
            ('{"old": true}', "2026-01-01T00:00:00"),
        )
    tmp_db.execute(
        "INSERT INTO pending_celebrations (person_id, payload) VALUES ('person.a', ?)",
        ('{"fresh": true}',),
    )
    tmp_db.commit()

    inst = _complete_wash(client)
    snap = json.loads(tmp_db.execute("SELECT undo FROM chore_instances WHERE id = ?", (inst,)).fetchone()[0])
    for key in ("tables", "after"):
        rows = snap[key]["pending_celebrations"]
        assert all(r["seen_at"] is None for r in rows), key
        assert any(r["payload"] == '{"fresh": true}' for r in rows), key

    assert client.post(f"/api/assignments/{inst}/undo", json={}).status_code == 200
    seen = tmp_db.execute(
        "SELECT count(*) FROM pending_celebrations WHERE person_id = 'person.a' AND seen_at IS NOT NULL"
    ).fetchone()[0]
    assert seen == 50


def test_expired_undo_cleared_on_next_completion(client, tmp_db):
    first = _complete_wash(client)
    backdate = (datetime.now() - timedelta(minutes=61)).isoformat()
    tmp_db.execute("UPDATE chore_instances SET completed_at = ? WHERE id = ?", (backdate, first))
    tmp_db.commit()

    second = _complete_wash(client)

    assert tmp_db.execute("SELECT undo FROM chore_instances WHERE id = ?", (first,)).fetchone()[0] is None
    assert tmp_db.execute("SELECT undo FROM chore_instances WHERE id = ?", (second,)).fetchone()[0] is not None
    listed = client.get("/api/assignments/", params={"status": "completed"}).json()
    assert [ci["can_undo"] for ci in listed if ci["id"] == first] == [False]


def test_expired_undo_cleared_at_startup(client, tmp_db):
    inst = _complete_wash(client)
    backdate = (datetime.now() - timedelta(minutes=61)).isoformat()
    tmp_db.execute("UPDATE chore_instances SET completed_at = ? WHERE id = ?", (backdate, inst))
    tmp_db.commit()

    from main import app
    with TestClient(app):
        pass
    import database
    assert database.get_connection().execute(
        "SELECT undo FROM chore_instances WHERE id = ?", (inst,)).fetchone()[0] is None


def test_undo_removes_own_celebration_even_if_seen(client, tmp_db):
    before_ids = {r[0] for r in tmp_db.execute("SELECT id FROM pending_celebrations").fetchall()}
    inst = _complete_wash(client)
    new_ids = [r[0] for r in tmp_db.execute("SELECT id FROM pending_celebrations").fetchall() if r[0] not in before_ids]
    assert new_ids  # the first completion earns the first-chore badge, so it queued a celebration
    for cel_id in new_ids:
        tmp_db.execute("UPDATE pending_celebrations SET seen_at = '2026-01-01T00:00:00' WHERE id = ?", (cel_id,))
    tmp_db.commit()

    resp = client.post(f"/api/assignments/{inst}/undo", json={})
    assert resp.status_code == 200, resp.text
    placeholders = ",".join("?" * len(new_ids))
    left = tmp_db.execute(
        f"SELECT count(*) FROM pending_celebrations WHERE id IN ({placeholders})", new_ids
    ).fetchone()[0]
    assert left == 0


def test_undo_refuses_snapshot_without_after_state(client, tmp_db):
    inst = _complete_wash(client)
    snap = json.loads(tmp_db.execute("SELECT undo FROM chore_instances WHERE id = ?", (inst,)).fetchone()[0])
    del snap["after"]
    tmp_db.execute("UPDATE chore_instances SET undo = ? WHERE id = ?", (json.dumps(snap), inst))
    tmp_db.commit()
    listed = client.get("/api/assignments/", params={"status": "completed"}).json()
    assert [ci["can_undo"] for ci in listed if ci["id"] == inst] == [False]
    resp = client.post(f"/api/assignments/{inst}/undo", json={})
    assert resp.status_code == 400 and "older version" in resp.json()["detail"]
