"""Chores – DataUpdateCoordinator for polling the add-on API."""

from __future__ import annotations
import logging
from datetime import timedelta

import httpx
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(minutes=5)


class ChoresCoordinator(DataUpdateCoordinator):
    """Fetch data from the Chores add-on API."""

    def __init__(self, hass: HomeAssistant, addon_url: str) -> None:
        super().__init__(hass, _LOGGER, name="Chores", update_interval=SCAN_INTERVAL)
        self.addon_url = addon_url.rstrip("/")

    async def _async_update_data(self) -> dict:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                # Fetch all needed data in parallel
                health_resp, persons_resp, leaderboard_resp, instances_resp = (
                    await client.get(f"{self.addon_url}/api/health"),
                    await client.get(f"{self.addon_url}/api/persons/"),
                    await client.get(f"{self.addon_url}/api/gamification/leaderboard"),
                    await client.get(
                        f"{self.addon_url}/api/assignments/",
                        params={"status": "pending,claimed,overdue"},
                    ),
                )

                health = health_resp.json()
                persons = persons_resp.json()
                leaderboard = leaderboard_resp.json()
                instances = instances_resp.json()

                # Count overdue
                overdue_count = sum(1 for i in instances if i.get("status") == "overdue")

                return {
                    "health": health,
                    "persons": persons,
                    "leaderboard": leaderboard,
                    "instances": instances,
                    "overdue_count": overdue_count,
                }
        except Exception as exc:
            raise UpdateFailed(f"Error fetching chores data: {exc}") from exc
