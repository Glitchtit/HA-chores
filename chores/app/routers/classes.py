"""Chores – Class specialization endpoints (v0.4.4)."""

from __future__ import annotations
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from database import get_connection
from classes import CLASSES, CLASS_PICK_LEVEL

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/classes", tags=["classes"])


class ClassPickBody(BaseModel):
    class_id: str  # "" to clear, otherwise must be a known class id


@router.get("/")
def list_classes():
    """Return the static class catalog with display metadata."""
    return {
        "pick_level": CLASS_PICK_LEVEL,
        "classes": [
            {"id": cid, **info} for cid, info in CLASSES.items()
        ],
    }


@router.post("/persons/{entity_id}")
def set_person_class(entity_id: str, body: ClassPickBody):
    """Set or change a person's class. Free at any time once level threshold met."""
    conn = get_connection()
    person = conn.execute(
        "SELECT entity_id, level, class_id FROM persons WHERE entity_id = ?",
        (entity_id,),
    ).fetchone()
    if not person:
        raise HTTPException(404, "Person not found")
    if person["level"] < CLASS_PICK_LEVEL:
        raise HTTPException(
            403,
            f"Class pick unlocks at level {CLASS_PICK_LEVEL}",
        )

    new_class = body.class_id.strip()
    if new_class and new_class not in CLASSES:
        raise HTTPException(422, f"Unknown class: {new_class}")

    conn.execute(
        "UPDATE persons SET class_id = ?, class_chosen_at = ? WHERE entity_id = ?",
        (new_class, datetime.now().isoformat(), entity_id),
    )
    conn.commit()
    logger.info("Person %s set class to %r", entity_id, new_class or "(none)")
    return {"entity_id": entity_id, "class_id": new_class}
