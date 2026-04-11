"""Chores – Configuration endpoints."""

from __future__ import annotations
from fastapi import APIRouter
from models import ConfigEntry
from database import get_connection

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("/", response_model=list[ConfigEntry])
async def list_config():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM config ORDER BY key").fetchall()
    return [dict(r) for r in rows]


@router.get("/{key}")
async def get_config(key: str):
    conn = get_connection()
    row = conn.execute("SELECT value FROM config WHERE key = ?", (key,)).fetchone()
    if row:
        return {"key": key, "value": row["value"]}
    return {"key": key, "value": None}


@router.put("/{key}", response_model=ConfigEntry)
async def set_config(key: str, body: ConfigEntry):
    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
        (key, body.value),
    )
    conn.commit()
    return {"key": key, "value": body.value}
