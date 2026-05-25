"""Chores – HA service handlers (agent-facing)."""

from __future__ import annotations

import logging
from typing import Optional

import httpx
import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN
from .coordinator import ChoresCoordinator

_LOGGER = logging.getLogger(__name__)

SERVICE_CREATE_CHORE = "create_chore"
SERVICE_SCHEDULE_CHORE = "schedule_chore"
SERVICE_ASSIGN_CHORE = "assign_chore"
SERVICE_COMPLETE_CHORE = "complete_chore"
SERVICE_LIST_CHORES = "list_chores"
SERVICE_LEADERBOARD = "leaderboard"

_VALID_CATEGORIES = ["dishes", "laundry", "cleaning", "trash", "cooking", "other"]

_CREATE_CHORE_SCHEMA = vol.Schema(
    {
        vol.Required("name"): cv.string,
        vol.Optional("description", default=""): cv.string,
        vol.Optional("icon", default="🧹"): cv.string,
        vol.Optional("xp_reward", default=10): vol.Coerce(int),
        vol.Optional("difficulty", default="medium"): cv.string,
        vol.Optional("category", default="other"): vol.In(_VALID_CATEGORIES),
        vol.Optional("recurrence"): vol.Any(None, cv.string),
        vol.Optional("estimated_minutes"): vol.Any(None, vol.Coerce(int)),
        vol.Optional("assignment_mode", default="manual"): cv.string,
    }
)

_SCHEDULE_SCHEMA = vol.Schema(
    {
        vol.Required("chore"): cv.string,
        vol.Required("assigned_to"): cv.string,
        vol.Required("due_date"): cv.string,
        vol.Optional("created_by"): vol.Any(None, cv.string),
    }
)

_ASSIGN_SCHEMA = vol.Schema(
    {
        vol.Required("instance_id"): vol.Coerce(int),
        vol.Required("person"): cv.string,
        vol.Optional("assigned_by"): vol.Any(None, cv.string),
    }
)

_COMPLETE_SCHEMA = vol.Schema(
    {
        vol.Required("chore"): cv.string,
        vol.Required("completed_by"): cv.string,
        vol.Optional("notes", default=""): cv.string,
    }
)

_LIST_CHORES_SCHEMA = vol.Schema(
    {
        vol.Optional("active_only", default=True): cv.boolean,
    }
)


# ── Pure resolvers (no I/O — unit-testable) ──────────────────────────────────

def resolve_chore_id(name: str, chores: list[dict]) -> Optional[int]:
    """Return the chore id whose name matches `name` (casefold, trimmed)."""
    target = (name or "").strip().casefold()
    if not target:
        return None
    for chore in chores:
        if str(chore.get("name", "")).strip().casefold() == target:
            return chore.get("id")
    return None


def resolve_person(name: str, persons: list[dict]) -> Optional[str]:
    """Return the person entity_id matching `name`.

    Matches on display name (casefold, trimmed). If `name` is already an
    entity_id present in the list, it is accepted and returned as-is.
    """
    target = (name or "").strip()
    if not target:
        return None
    folded = target.casefold()
    for person in persons:
        if str(person.get("entity_id", "")).strip().casefold() == folded:
            return person.get("entity_id")
    for person in persons:
        if str(person.get("name", "")).strip().casefold() == folded:
            return person.get("entity_id")
    return None


def find_open_instance(chore_id: int, person: str, instances: list[dict]) -> Optional[int]:
    """Pick the best open chore-instance id for (chore_id, person).

    `instances` is the result of GET /api/assignments/?status=...&person=...,
    which returns instances assigned to the person OR unassigned. Prefer an
    instance assigned to the person; fall back to an unassigned one. Among
    candidates, prefer the earliest due_date (overdue/oldest first).
    """
    assigned = [
        i for i in instances
        if i.get("chore_id") == chore_id and i.get("assigned_to") == person
    ]
    unassigned = [
        i for i in instances
        if i.get("chore_id") == chore_id and i.get("assigned_to") in (None, "")
    ]
    candidates = assigned or unassigned
    if not candidates:
        return None
    candidates.sort(key=lambda i: i.get("due_date") or "")
    return candidates[0].get("id")


# ── httpx helpers + coordinator lookup (mirror HA-storage) ───────────────────

def _coordinators(hass: HomeAssistant) -> list[ChoresCoordinator]:
    return [
        v for k, v in hass.data.get(DOMAIN, {}).items()
        if isinstance(v, ChoresCoordinator)
    ]


async def _post(coordinator: ChoresCoordinator, path: str, payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(f"{coordinator.addon_url}{path}", json=payload)
        resp.raise_for_status()
        try:
            return resp.json()
        except ValueError:
            return {}


async def _get(coordinator: ChoresCoordinator, path: str, params: dict | None = None) -> dict | list:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{coordinator.addon_url}{path}", params=params or {})
        resp.raise_for_status()
        return resp.json()


# ── Registration ─────────────────────────────────────────────────────────────

def async_register_services(hass: HomeAssistant) -> None:
    """Register integration services. Idempotent."""
    if hass.services.has_service(DOMAIN, SERVICE_CREATE_CHORE):
        return

    async def handle_create_chore(call: ServiceCall) -> dict:
        payload = {k: v for k, v in call.data.items() if v is not None}
        result: dict = {}
        for coord in _coordinators(hass):
            result = await _post(coord, "/api/chores/", payload)
            await coord.async_request_refresh()
        return result

    async def handle_schedule_chore(call: ServiceCall) -> dict:
        result: dict = {}
        for coord in _coordinators(hass):
            chores = await _get(coord, "/api/chores/", {"active_only": "true"})
            chore_id = resolve_chore_id(call.data["chore"], chores)
            if chore_id is None:
                raise ServiceValidationError(
                    f"No chore named '{call.data['chore']}' found."
                )
            persons = await _get(coord, "/api/persons/")
            person = resolve_person(call.data["assigned_to"], persons)
            if person is None:
                raise ServiceValidationError(
                    f"No person named '{call.data['assigned_to']}' found."
                )
            created_by = call.data.get("created_by")
            if created_by:
                created_by = resolve_person(created_by, persons) or created_by
            payload = {
                "chore_id": chore_id,
                "due_date": call.data["due_date"],
                "assigned_to": person,
                "created_by": created_by,
            }
            payload = {k: v for k, v in payload.items() if v is not None}
            result = await _post(coord, "/api/assignments/", payload)
            await coord.async_request_refresh()
        return result

    async def handle_assign_chore(call: ServiceCall) -> dict:
        result: dict = {}
        for coord in _coordinators(hass):
            persons = await _get(coord, "/api/persons/")
            person = resolve_person(call.data["person"], persons)
            if person is None:
                raise ServiceValidationError(
                    f"No person named '{call.data['person']}' found."
                )
            assigned_by = call.data.get("assigned_by")
            if assigned_by:
                assigned_by = resolve_person(assigned_by, persons) or assigned_by
            payload = {"person_id": person, "assigned_by": assigned_by}
            payload = {k: v for k, v in payload.items() if v is not None}
            result = await _post(
                coord, f"/api/assignments/{call.data['instance_id']}/assign", payload
            )
            await coord.async_request_refresh()
        return result

    async def handle_complete_chore(call: ServiceCall) -> dict:
        result: dict = {}
        for coord in _coordinators(hass):
            persons = await _get(coord, "/api/persons/")
            person = resolve_person(call.data["completed_by"], persons)
            if person is None:
                raise ServiceValidationError(
                    f"No person named '{call.data['completed_by']}' found."
                )
            chores = await _get(coord, "/api/chores/", {"active_only": "true"})
            chore_id = resolve_chore_id(call.data["chore"], chores)
            if chore_id is None:
                raise ServiceValidationError(
                    f"No chore named '{call.data['chore']}' found."
                )
            instances = await _get(
                coord,
                "/api/assignments/",
                {"status": "pending,claimed,overdue", "person": person},
            )
            instance_id = find_open_instance(chore_id, person, instances)
            if instance_id is None:
                raise ServiceValidationError(
                    f"No open '{call.data['chore']}' instance found for "
                    f"{person} to complete."
                )
            payload = {"completed_by": person, "notes": call.data.get("notes") or ""}
            result = await _post(
                coord, f"/api/assignments/{instance_id}/complete", payload
            )
            await coord.async_request_refresh()
        return result

    async def handle_list_chores(call: ServiceCall) -> dict:
        coords = _coordinators(hass)
        if not coords:
            return {"error": "no_coordinator"}
        active_only = "true" if call.data.get("active_only", True) else "false"
        chores = await _get(coords[0], "/api/chores/", {"active_only": active_only})
        return {"chores": chores}

    async def handle_leaderboard(call: ServiceCall) -> dict:
        coords = _coordinators(hass)
        if not coords:
            return {"error": "no_coordinator"}
        return await _get(coords[0], "/api/gamification/leaderboard")

    hass.services.async_register(
        DOMAIN,
        SERVICE_CREATE_CHORE,
        handle_create_chore,
        schema=_CREATE_CHORE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SCHEDULE_CHORE,
        handle_schedule_chore,
        schema=_SCHEDULE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_ASSIGN_CHORE,
        handle_assign_chore,
        schema=_ASSIGN_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_COMPLETE_CHORE,
        handle_complete_chore,
        schema=_COMPLETE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_LIST_CHORES,
        handle_list_chores,
        schema=_LIST_CHORES_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_LEADERBOARD,
        handle_leaderboard,
        supports_response=SupportsResponse.ONLY,
    )


def async_unregister_services(hass: HomeAssistant) -> None:
    """Remove integration services."""
    for svc in (
        SERVICE_CREATE_CHORE,
        SERVICE_SCHEDULE_CHORE,
        SERVICE_ASSIGN_CHORE,
        SERVICE_COMPLETE_CHORE,
        SERVICE_LIST_CHORES,
        SERVICE_LEADERBOARD,
    ):
        if hass.services.has_service(DOMAIN, svc):
            hass.services.async_remove(DOMAIN, svc)
