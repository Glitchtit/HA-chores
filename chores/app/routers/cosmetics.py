"""Chores – Cosmetics shop and wardrobe endpoints (v0.4.3).

Cosmetics are catalog-seeded items the user can purchase with tokens
(1 token per 10 XP earned) or unlock via boss-defeat / level milestones.
Each person can equip one cosmetic per slot at a time.
"""

from __future__ import annotations
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from database import get_connection
from gamification import spend_tokens

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/cosmetics", tags=["cosmetics"])

ALL_SLOTS = ("hat", "background", "particle", "nameplate", "evolution")


class PurchaseBody(BaseModel):
    cosmetic_id: str


class EquipBody(BaseModel):
    cosmetic_id: str


class UnequipBody(BaseModel):
    slot: str


def _cosmetic_row(conn, cosmetic_id: str):
    return conn.execute(
        "SELECT * FROM cosmetics WHERE id = ?", (cosmetic_id,)
    ).fetchone()


def _person_row(conn, person_id: str):
    return conn.execute(
        "SELECT * FROM persons WHERE entity_id = ?", (person_id,)
    ).fetchone()


def _qualifies_for_level_unlock(person_level: int, cosmetic) -> bool:
    """A level-unlock cosmetic becomes purchasable (for 0 tokens) once the
    owner has reached the threshold stored in ``unlock_value``."""
    if cosmetic["unlock_type"] != "level":
        return False
    try:
        required = int(cosmetic["unlock_value"])
    except (TypeError, ValueError):
        return False
    return person_level >= required


@router.get("/")
def list_catalog(include_hidden: bool = False):
    """Return the full cosmetics catalog. Hidden boss-rewards are excluded by default."""
    conn = get_connection()
    if include_hidden:
        rows = conn.execute("SELECT * FROM cosmetics ORDER BY slot, cost_tokens, name").fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM cosmetics WHERE hidden = 0 ORDER BY slot, cost_tokens, name"
        ).fetchall()
    return [dict(r) for r in rows]


@router.get("/{person_id}")
def list_for_person(person_id: str):
    """Return the cosmetics catalog annotated with this person's ownership / equipped state.

    Also includes the person's current token balance for convenience.
    """
    conn = get_connection()
    person = _person_row(conn, person_id)
    if not person:
        raise HTTPException(404, "Person not found")

    catalog = conn.execute(
        "SELECT * FROM cosmetics WHERE hidden = 0 OR id IN (SELECT cosmetic_id FROM person_cosmetics WHERE person_id = ?) ORDER BY slot, cost_tokens, name",
        (person_id,),
    ).fetchall()
    owned = {
        r["cosmetic_id"]: r
        for r in conn.execute(
            "SELECT cosmetic_id, equipped, acquired_at FROM person_cosmetics WHERE person_id = ?",
            (person_id,),
        ).fetchall()
    }

    items = []
    for c in catalog:
        own = owned.get(c["id"])
        items.append({
            **dict(c),
            "owned": own is not None,
            "equipped": bool(own["equipped"]) if own else False,
            "acquired_at": own["acquired_at"] if own else None,
            "unlocked": (
                own is not None
                or c["unlock_type"] == "shop"
                or _qualifies_for_level_unlock(person["level"], c)
            ),
        })

    return {
        "person_id": person_id,
        "tokens": person["tokens"] or 0,
        "items": items,
    }


@router.post("/{person_id}/purchase")
def purchase(person_id: str, body: PurchaseBody):
    """Purchase a cosmetic. Deducts tokens; idempotent if already owned."""
    conn = get_connection()
    person = _person_row(conn, person_id)
    if not person:
        raise HTTPException(404, "Person not found")
    cosmetic = _cosmetic_row(conn, body.cosmetic_id)
    if not cosmetic:
        raise HTTPException(404, "Cosmetic not found")

    already_owned = conn.execute(
        "SELECT 1 FROM person_cosmetics WHERE person_id = ? AND cosmetic_id = ?",
        (person_id, body.cosmetic_id),
    ).fetchone()
    if already_owned:
        return {"status": "already_owned", "tokens": person["tokens"] or 0}

    utype = cosmetic["unlock_type"]
    if utype == "boss":
        raise HTTPException(403, "This cosmetic must be earned by defeating its boss event")
    if utype == "level" and not _qualifies_for_level_unlock(person["level"], cosmetic):
        raise HTTPException(403, "Reach the required level to unlock this cosmetic")
    if utype == "gift":
        raise HTTPException(403, "Gifted cosmetics cannot be purchased directly")

    cost = cosmetic["cost_tokens"] or 0
    if cost > 0 and not spend_tokens(person_id, cost):
        raise HTTPException(402, "Not enough tokens")

    conn.execute(
        "INSERT INTO person_cosmetics (person_id, cosmetic_id, equipped) VALUES (?, ?, 0)",
        (person_id, body.cosmetic_id),
    )
    conn.commit()
    new_balance = conn.execute(
        "SELECT tokens FROM persons WHERE entity_id = ?", (person_id,)
    ).fetchone()["tokens"]
    logger.info("Person %s purchased cosmetic %s for %d tokens", person_id, body.cosmetic_id, cost)
    return {"status": "purchased", "tokens": new_balance or 0}


@router.post("/{person_id}/equip")
def equip(person_id: str, body: EquipBody):
    """Equip a cosmetic. Automatically unequips any other cosmetic in the same slot."""
    conn = get_connection()
    if not _person_row(conn, person_id):
        raise HTTPException(404, "Person not found")
    cosmetic = _cosmetic_row(conn, body.cosmetic_id)
    if not cosmetic:
        raise HTTPException(404, "Cosmetic not found")
    owned = conn.execute(
        "SELECT 1 FROM person_cosmetics WHERE person_id = ? AND cosmetic_id = ?",
        (person_id, body.cosmetic_id),
    ).fetchone()
    if not owned:
        raise HTTPException(403, "You don't own this cosmetic")

    conn.execute(
        """UPDATE person_cosmetics
           SET equipped = 0
           WHERE person_id = ? AND cosmetic_id IN (
               SELECT id FROM cosmetics WHERE slot = ?
           )""",
        (person_id, cosmetic["slot"]),
    )
    conn.execute(
        "UPDATE person_cosmetics SET equipped = 1 WHERE person_id = ? AND cosmetic_id = ?",
        (person_id, body.cosmetic_id),
    )
    conn.commit()
    return {"status": "equipped", "slot": cosmetic["slot"], "cosmetic_id": body.cosmetic_id}


@router.post("/{person_id}/unequip")
def unequip(person_id: str, body: UnequipBody):
    """Unequip any cosmetic in the given slot."""
    if body.slot not in ALL_SLOTS:
        raise HTTPException(422, f"Unknown slot: {body.slot}")
    conn = get_connection()
    if not _person_row(conn, person_id):
        raise HTTPException(404, "Person not found")
    conn.execute(
        """UPDATE person_cosmetics
           SET equipped = 0
           WHERE person_id = ? AND cosmetic_id IN (
               SELECT id FROM cosmetics WHERE slot = ?
           )""",
        (person_id, body.slot),
    )
    conn.commit()
    return {"status": "unequipped", "slot": body.slot}


def get_equipped_for_person(conn, person_id: str) -> dict[str, dict]:
    """Helper used by other modules (pets view, integration) to enrich responses
    with the currently-equipped cosmetic per slot."""
    rows = conn.execute(
        """SELECT c.* FROM cosmetics c
           JOIN person_cosmetics pc ON pc.cosmetic_id = c.id
           WHERE pc.person_id = ? AND pc.equipped = 1""",
        (person_id,),
    ).fetchall()
    return {r["slot"]: dict(r) for r in rows}
