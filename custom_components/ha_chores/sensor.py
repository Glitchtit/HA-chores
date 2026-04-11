"""Chores – Sensor entities for HA."""

from __future__ import annotations
from homeassistant.components.sensor import SensorEntity
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
    entities = []

    # Global overdue sensor
    entities.append(ChoresOverdueSensor(coordinator, entry))

    # Per-person sensors
    for person in coordinator.data.get("persons", []):
        entities.append(ChoresPersonXPSensor(coordinator, entry, person))
        entities.append(ChoresPersonLevelSensor(coordinator, entry, person))
        entities.append(ChoresPersonStreakSensor(coordinator, entry, person))

    async_add_entities(entities)


class ChoresOverdueSensor(CoordinatorEntity, SensorEntity):
    _attr_icon = "mdi:alert-circle"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_overdue_count"
        self._attr_name = "Chores Overdue"

    @property
    def native_value(self):
        return self.coordinator.data.get("overdue_count", 0)


class ChoresPersonXPSensor(CoordinatorEntity, SensorEntity):
    _attr_icon = "mdi:star"
    _attr_native_unit_of_measurement = "XP"

    def __init__(self, coordinator, entry, person):
        super().__init__(coordinator)
        self._person_id = person["entity_id"]
        name_slug = person["name"].lower().replace(" ", "_")
        self._attr_unique_id = f"{entry.entry_id}_{name_slug}_xp"
        self._attr_name = f"Chores {person['name']} XP"

    @property
    def native_value(self):
        for p in self.coordinator.data.get("persons", []):
            if p["entity_id"] == self._person_id:
                return p.get("xp_total", 0)
        return 0

    @property
    def extra_state_attributes(self):
        for p in self.coordinator.data.get("persons", []):
            if p["entity_id"] == self._person_id:
                return {"level": p.get("level", 1), "streak": p.get("current_streak", 0)}
        return {}


class ChoresPersonLevelSensor(CoordinatorEntity, SensorEntity):
    _attr_icon = "mdi:arrow-up-bold-circle"

    def __init__(self, coordinator, entry, person):
        super().__init__(coordinator)
        self._person_id = person["entity_id"]
        name_slug = person["name"].lower().replace(" ", "_")
        self._attr_unique_id = f"{entry.entry_id}_{name_slug}_level"
        self._attr_name = f"Chores {person['name']} Level"

    @property
    def native_value(self):
        for p in self.coordinator.data.get("persons", []):
            if p["entity_id"] == self._person_id:
                return p.get("level", 1)
        return 1


class ChoresPersonStreakSensor(CoordinatorEntity, SensorEntity):
    _attr_icon = "mdi:fire"
    _attr_native_unit_of_measurement = "days"

    def __init__(self, coordinator, entry, person):
        super().__init__(coordinator)
        self._person_id = person["entity_id"]
        name_slug = person["name"].lower().replace(" ", "_")
        self._attr_unique_id = f"{entry.entry_id}_{name_slug}_streak"
        self._attr_name = f"Chores {person['name']} Streak"

    @property
    def native_value(self):
        for p in self.coordinator.data.get("persons", []):
            if p["entity_id"] == self._person_id:
                return p.get("current_streak", 0)
        return 0
