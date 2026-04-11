"""Chores – Home Assistant Supervisor API client."""

from __future__ import annotations
import os
import logging
import httpx

logger = logging.getLogger(__name__)

SUPERVISOR_TOKEN = os.environ.get("SUPERVISOR_TOKEN", "")
SUPERVISOR_URL = "http://supervisor"
HA_URL = "http://supervisor/core"


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {SUPERVISOR_TOKEN}"}


async def get_persons() -> list[dict]:
    """Fetch all person entities from Home Assistant."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{HA_URL}/api/states",
                headers=_headers(),
            )
            resp.raise_for_status()
            states = resp.json()
            persons = []
            for s in states:
                if s.get("entity_id", "").startswith("person."):
                    attrs = s.get("attributes", {})
                    persons.append({
                        "entity_id": s["entity_id"],
                        "name": attrs.get("friendly_name", s["entity_id"]),
                        "avatar_url": attrs.get("entity_picture", ""),
                    })
            return persons
    except Exception as e:
        logger.error("Failed to fetch persons from HA: %s", e)
        return []


async def send_notification(
    person_entity_id: str,
    title: str,
    message: str,
    data: dict | None = None,
) -> bool:
    """Send a notification to a person's mobile device.

    Maps person entity_id to their mobile_app notification target by
    looking up the device_trackers associated with the person.
    """
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # Get person state to find device trackers
            resp = await client.get(
                f"{HA_URL}/api/states/{person_entity_id}",
                headers=_headers(),
            )
            resp.raise_for_status()
            person_state = resp.json()
            device_trackers = person_state.get("attributes", {}).get(
                "device_trackers", []
            )

            # Try to find a mobile_app device tracker
            notified = False
            for tracker in device_trackers:
                if "mobile_app" in tracker:
                    # Extract device name: device_tracker.mobile_app_xxx -> xxx
                    device_name = tracker.replace("device_tracker.", "")
                    service_target = f"mobile_app_{device_name.replace('mobile_app_', '')}"

                    payload: dict = {
                        "title": title,
                        "message": message,
                    }
                    if data:
                        payload["data"] = data

                    notify_resp = await client.post(
                        f"{HA_URL}/api/services/notify/{service_target}",
                        headers=_headers(),
                        json=payload,
                    )
                    if notify_resp.status_code < 300:
                        notified = True
                        logger.info(
                            "Notification sent to %s via %s",
                            person_entity_id,
                            service_target,
                        )

            if not notified:
                logger.warning(
                    "No mobile_app device found for %s (trackers: %s)",
                    person_entity_id,
                    device_trackers,
                )
            return notified
    except Exception as e:
        logger.error("Failed to send notification to %s: %s", person_entity_id, e)
        return False


async def get_calendar_events(
    calendar_entity: str, start: str, end: str
) -> list[dict]:
    """Fetch calendar events for conflict detection."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{HA_URL}/api/calendars/{calendar_entity}",
                headers=_headers(),
                params={"start": start, "end": end},
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error("Failed to fetch calendar events: %s", e)
        return []


async def create_todo_item(todo_entity: str, summary: str) -> bool:
    """Create a todo item in a HA todo list."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{HA_URL}/api/services/todo/add_item",
                headers=_headers(),
                json={
                    "entity_id": todo_entity,
                    "item": summary,
                },
            )
            return resp.status_code < 300
    except Exception as e:
        logger.error("Failed to create todo item: %s", e)
        return False


async def complete_todo_item(todo_entity: str, summary: str) -> bool:
    """Mark a todo item as complete in HA."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{HA_URL}/api/services/todo/update_item",
                headers=_headers(),
                json={
                    "entity_id": todo_entity,
                    "item": summary,
                    "status": "completed",
                },
            )
            return resp.status_code < 300
    except Exception as e:
        logger.error("Failed to complete todo item: %s", e)
        return False
