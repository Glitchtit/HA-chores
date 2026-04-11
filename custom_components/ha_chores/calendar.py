"""Chores – Calendar entity showing chore schedule."""

from __future__ import annotations
from datetime import datetime, date
from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ChoresCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: ChoresCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ChoresCalendar(coordinator, entry)])


class ChoresCalendar(CoordinatorEntity, CalendarEntity):
    _attr_icon = "mdi:calendar-check"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_calendar"
        self._attr_name = "Chores"

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming chore event."""
        today = date.today().isoformat()
        for inst in self.coordinator.data.get("instances", []):
            if inst.get("due_date", "") >= today and inst.get("status") != "completed":
                return CalendarEvent(
                    summary=f"{inst.get('chore_icon', '🧹')} {inst.get('chore_name', 'Chore')}",
                    start=date.fromisoformat(inst["due_date"]),
                    end=date.fromisoformat(inst["due_date"]),
                )
        return None

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Return chore events in the given date range."""
        events = []
        start_str = start_date.date().isoformat() if isinstance(start_date, datetime) else start_date.isoformat()
        end_str = end_date.date().isoformat() if isinstance(end_date, datetime) else end_date.isoformat()

        for inst in self.coordinator.data.get("instances", []):
            due = inst.get("due_date", "")
            if start_str <= due <= end_str:
                events.append(CalendarEvent(
                    summary=f"{inst.get('chore_icon', '🧹')} {inst.get('chore_name', 'Chore')}",
                    start=date.fromisoformat(due),
                    end=date.fromisoformat(due),
                    description=f"Status: {inst.get('status', 'unknown')}, Assigned: {inst.get('assigned_to', 'unassigned')}",
                ))
        return events
