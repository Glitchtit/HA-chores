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
    # Active household challenge (v0.4.6)
    entities.append(ChoresChallengeProgressSensor(coordinator, entry))
    # Active seasonal boss (v0.5.0)
    entities.append(ChoresActiveBossSensor(coordinator, entry))

    # Per-person sensors
    for person in coordinator.data.get("persons", []):
        entities.append(ChoresPersonXPSensor(coordinator, entry, person))
        entities.append(ChoresPersonLevelSensor(coordinator, entry, person))
        entities.append(ChoresPersonStreakSensor(coordinator, entry, person))
        entities.append(ChoresPersonTokensSensor(coordinator, entry, person))

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


class ChoresPersonTokensSensor(CoordinatorEntity, SensorEntity):
    """Cosmetic-shop tokens balance (1 token per 10 XP earned) — v0.4.3."""

    _attr_icon = "mdi:circle-multiple"
    _attr_native_unit_of_measurement = "tokens"

    def __init__(self, coordinator, entry, person):
        super().__init__(coordinator)
        self._person_id = person["entity_id"]
        name_slug = person["name"].lower().replace(" ", "_")
        self._attr_unique_id = f"{entry.entry_id}_{name_slug}_tokens"
        self._attr_name = f"Chores {person['name']} Tokens"

    @property
    def native_value(self):
        for p in self.coordinator.data.get("persons", []):
            if p["entity_id"] == self._person_id:
                return p.get("tokens", 0)
        return 0


class ChoresChallengeProgressSensor(CoordinatorEntity, SensorEntity):
    """Active household challenge — state is "name (progress/goal)", attributes
    expose the raw fields. v0.4.6."""

    _attr_icon = "mdi:trophy-variant"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_active_challenge"
        self._attr_name = "Chores Active Challenge"

    @property
    def native_value(self):
        c = self.coordinator.data.get("active_challenge")
        if not c:
            return "none"
        return f"{c['name']} ({c['progress']}/{c['goal_value']})"

    @property
    def extra_state_attributes(self):
        c = self.coordinator.data.get("active_challenge")
        if not c:
            return {}
        return {
            "name": c.get("name"),
            "description": c.get("description"),
            "progress": c.get("progress"),
            "goal_value": c.get("goal_value"),
            "goal_type": c.get("goal_type"),
            "target_category": c.get("target_category"),
            "period_start": c.get("period_start"),
            "period_end": c.get("period_end"),
            "status": c.get("status"),
            "reward_multiplier": c.get("reward_multiplier"),
            "reward_hours": c.get("reward_hours"),
        }


class ChoresActiveBossSensor(CoordinatorEntity, SensorEntity):
    """Active seasonal boss event — state is the boss name (or "none").
    Attributes expose progress %, end date, and the objectives list. v0.5.0."""

    _attr_icon = "mdi:sword-cross"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_active_boss"
        self._attr_name = "Chores Active Boss"

    @property
    def native_value(self):
        b = self.coordinator.data.get("active_boss")
        if not b:
            return "none"
        return b.get("name", "boss")

    @property
    def extra_state_attributes(self):
        b = self.coordinator.data.get("active_boss")
        if not b:
            return {}
        objectives = b.get("objectives", []) or []
        total = sum(o.get("target_count", 0) for o in objectives)
        progress = sum(o.get("progress", 0) for o in objectives)
        pct = (progress / total * 100) if total else 0
        return {
            "name": b.get("name"),
            "description": b.get("description"),
            "icon": b.get("icon"),
            "status": b.get("status"),
            "start_date": b.get("start_date"),
            "end_date": b.get("end_date"),
            "progress": progress,
            "total": total,
            "progress_pct": round(pct, 1),
            "objectives": [
                {
                    "chore_name": o.get("chore_name"),
                    "progress": o.get("progress"),
                    "target": o.get("target_count"),
                }
                for o in objectives
            ],
        }
