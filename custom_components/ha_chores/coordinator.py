"""Chores – DataUpdateCoordinator for polling the add-on API."""

from __future__ import annotations
import asyncio
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
                results = await asyncio.gather(
                    client.get(f"{self.addon_url}/api/health"),
                    client.get(f"{self.addon_url}/api/persons/"),
                    client.get(f"{self.addon_url}/api/gamification/leaderboard"),
                    client.get(
                        f"{self.addon_url}/api/assignments/",
                        params={"status": "pending,claimed,overdue"},
                    ),
                    return_exceptions=True,
                )

                # Check for connection errors
                for r in results:
                    if isinstance(r, Exception):
                        raise r

                health_resp, persons_resp, leaderboard_resp, instances_resp = results

                persons = persons_resp.json() if persons_resp.status_code == 200 else []
                leaderboard = leaderboard_resp.json() if leaderboard_resp.status_code == 200 else {}
                instances = instances_resp.json() if instances_resp.status_code == 200 else []
                health = health_resp.json() if health_resp.status_code == 200 else {}

                overdue_count = sum(1 for i in instances if i.get("status") == "overdue")

                return {
                    "health": health,
                    "persons": persons,
                    "leaderboard": leaderboard,
                    "instances": instances,
                    "overdue_count": overdue_count,
                }
        except (httpx.ConnectError, httpx.TimeoutException, OSError) as exc:
            raise UpdateFailed(
                f"Cannot connect to Chores add-on at {self.addon_url}. "
                f"Check the URL in the integration settings. Error: {exc}"
            ) from exc
        except Exception as exc:
            raise UpdateFailed(f"Error fetching chores data: {exc}") from exc
