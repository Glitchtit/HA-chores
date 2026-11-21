"""Chores – HA service handlers (agent-facing)."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Optional

import httpx
import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.util import dt as dt_util
from homeassistant.util.ssl import get_default_context

from .const import DOMAIN
from .coordinator import ChoresCoordinator

_LOGGER = logging.getLogger(__name__)

SERVICE_CREATE_CHORE = "create_chore"
SERVICE_SCHEDULE_CHORE = "schedule_chore"
SERVICE_ASSIGN_CHORE = "assign_chore"
SERVICE_CLAIM_CHORE = "claim_chore"
SERVICE_COMPLETE_CHORE = "complete_chore"
SERVICE_LIST_CHORES = "list_chores"
SERVICE_LEADERBOARD = "leaderboard"
SERVICE_UNDO = "undo"

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
        vol.Required("due_date"): cv.date,
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

_CLAIM_SCHEMA = vol.Schema(
    {
        vol.Required("instance_id"): vol.Coerce(int),
        vol.Required("person"): cv.string,
    }
)

_COMPLETE_SCHEMA = vol.Schema(
    {
        vol.Required("chore"): cv.string,
        vol.Required("completed_by"): cv.string,
        vol.Optional("notes", default=""): cv.string,
    }
)

_UNDO_SCHEMA = vol.Schema(
    {
        vol.Optional("instance_id"): vol.Coerce(int),
        vol.Optional("chore_id"): vol.Coerce(int),
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


def unknown_chore_message(name: str, chores: list[dict]) -> str:
    """Error text for a name that matched no chore.

    Lists the real names so an assistant can retry with one of them
    ("vacuumed" -> "Vacuum a bit").
    """
    names = ", ".join(str(c.get("name", "")).strip() for c in chores)
    return f"No chore named '{name}'. Use one of these exact names: {names}"


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


def _require_coordinators(hass: HomeAssistant) -> list[ChoresCoordinator]:
    """The coordinators, or an error: an empty loop must never read as done."""
    coords = _coordinators(hass)
    if not coords:
        raise HomeAssistantError("Chores is not set up.")
    return coords


def _failure(err: httpx.HTTPError) -> HomeAssistantError:
    """The add-on's own reason ("Already completed") when it gave one."""
    detail = None
    if isinstance(err, httpx.HTTPStatusError):
        try:
            detail = err.response.json().get("detail")
        except (ValueError, AttributeError):
            detail = None
    return HomeAssistantError(f"Chores add-on request failed: {detail or err}")


async def _post(coordinator: ChoresCoordinator, path: str, payload: dict) -> dict:
    async with httpx.AsyncClient(verify=get_default_context(), timeout=15) as client:
        try:
            resp = await client.post(f"{coordinator.addon_url}{path}", json=payload)
            resp.raise_for_status()
        except httpx.HTTPError as err:
            # Only a HomeAssistantError reaches a voice assistant as text.
            raise _failure(err) from err
        try:
            return resp.json()
        except ValueError:
            return {}


async def _get(coordinator: ChoresCoordinator, path: str, params: dict | None = None) -> dict | list:
    async with httpx.AsyncClient(verify=get_default_context(), timeout=15) as client:
        try:
            resp = await client.get(f"{coordinator.addon_url}{path}", params=params or {})
            resp.raise_for_status()
        except httpx.HTTPError as err:
            raise _failure(err) from err
        return resp.json()


# ── Registration ─────────────────────────────────────────────────────────────

def async_register_services(hass: HomeAssistant) -> None:
    """Register integration services. Idempotent."""
    if hass.services.has_service(DOMAIN, SERVICE_CREATE_CHORE):
        return

    async def handle_create_chore(call: ServiceCall) -> dict:
        payload = {k: v for k, v in call.data.items() if v is not None}
        result: dict = {}
        for coord in _require_coordinators(hass):
            result = await _post(coord, "/api/chores/", payload)
            await coord.async_request_refresh()
        return result

    async def handle_schedule_chore(call: ServiceCall) -> dict:
        result: dict = {}
        for coord in _require_coordinators(hass):
            chores = await _get(coord, "/api/chores/", {"active_only": "true"})
            chore_id = resolve_chore_id(call.data["chore"], chores)
            if chore_id is None:
                raise ServiceValidationError(
                    unknown_chore_message(call.data["chore"], chores)
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
                "due_date": call.data["due_date"].isoformat(),
                "assigned_to": person,
                "created_by": created_by,
            }
            payload = {k: v for k, v in payload.items() if v is not None}
            result = await _post(coord, "/api/assignments/", payload)
            await coord.async_request_refresh()
        return result

    async def handle_assign_chore(call: ServiceCall) -> dict:
        result: dict = {}
        for coord in _require_coordinators(hass):
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

    async def handle_claim_chore(call: ServiceCall) -> dict:
        result: dict = {}
        for coord in _require_coordinators(hass):
            persons = await _get(coord, "/api/persons/")
            person = resolve_person(call.data["person"], persons)
            if person is None:
                raise ServiceValidationError(
                    f"No person named '{call.data['person']}' found."
                )
            result = await _post(
                coord, f"/api/assignments/{call.data['instance_id']}/claim", {"person_id": person}
            )
            await coord.async_request_refresh()
        return result

    async def handle_complete_chore(call: ServiceCall) -> dict:
        result: dict = {}
        for coord in _require_coordinators(hass):
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
                    unknown_chore_message(call.data["chore"], chores)
                )
            instances = await _get(
                coord,
                "/api/assignments/",
                {"status": "pending,claimed,overdue", "person": person},
            )
            instance_id = find_open_instance(chore_id, person, instances)
            created_here = instance_id is None
            if created_here:
                # Nothing was scheduled: log it as done today, the way the
                # app's quick-done tile does (self-assigned, so no notification).
                created = await _post(
                    coord,
                    "/api/assignments/",
                    {
                        "chore_id": chore_id,
                        "due_date": dt_util.now().date().isoformat(),
                        "assigned_to": person,
                        "created_by": person,
                    },
                )
                instance_id = created["id"]
            payload = {
                "completed_by": person,
                "notes": call.data.get("notes") or "",
                # Undo then removes the instance instead of leaving it on the plate.
                "remove_on_undo": created_here,
            }
            result = await _post(
                coord, f"/api/assignments/{instance_id}/complete", payload
            )
            await coord.async_request_refresh()
        return result

    async def handle_undo(call: ServiceCall) -> dict:
        """Take back a recent completion, scheduling or new chore.

        No id means the newest completion. Each add-on refuses what it can no
        longer undo safely (older than an hour, a later completion exists).
        """
        coord = _require_coordinators(hass)[0]
        chore_id = call.data.get("chore_id")
        if chore_id is not None:
            chore = await _get(coord, f"/api/chores/{chore_id}")
            created = dt_util.parse_datetime(str(chore.get("created_at") or ""))
            if created is None or dt_util.utcnow() - created.replace(
                tzinfo=created.tzinfo or dt_util.UTC
            ) > timedelta(hours=1):
                raise ServiceValidationError(
                    "Only chores created in the last hour can be undone."
                )
            async with httpx.AsyncClient(verify=get_default_context(), timeout=15) as client:
                try:
                    (await client.delete(f"{coord.addon_url}/api/chores/{chore_id}")).raise_for_status()
                except httpx.HTTPError as err:
                    raise _failure(err) from err
            result = {"undone": "create_chore", "chore_id": chore_id, "chore": chore.get("name")}
        elif call.data.get("instance_id") is not None:
            result = await _post(coord, f"/api/assignments/{call.data['instance_id']}/undo", {})
        else:
            result = await _post(coord, "/api/assignments/undo-last", {})
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
        SERVICE_CLAIM_CHORE,
        handle_claim_chore,
        schema=_CLAIM_SCHEMA,
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
        SERVICE_UNDO,
        handle_undo,
        schema=_UNDO_SCHEMA,
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
        SERVICE_CLAIM_CHORE,
        SERVICE_COMPLETE_CHORE,
        SERVICE_LIST_CHORES,
        SERVICE_LEADERBOARD,
        SERVICE_UNDO,
    ):
        if hass.services.has_service(DOMAIN, svc):
            hass.services.async_remove(DOMAIN, svc)
