"""Chores – Todo list entities for HA (per-person chore lists)."""

from __future__ import annotations
import httpx
from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util.ssl import get_default_context

from .const import DOMAIN
from .coordinator import ChoresCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: ChoresCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for person in coordinator.data.get("persons", []):
        entities.append(ChoresPersonTodo(coordinator, entry, person))
    async_add_entities(entities)


class ChoresPersonTodo(CoordinatorEntity, TodoListEntity):
    """A per-person chore todo list synced from the add-on.

    Checking an item off completes the chore; deleting it skips that occurrence.
    """

    _attr_supported_features = (
        TodoListEntityFeature.UPDATE_TODO_ITEM | TodoListEntityFeature.DELETE_TODO_ITEM
    )

    def __init__(self, coordinator, entry, person):
        super().__init__(coordinator)
        self._person_id = person["entity_id"]
        name_slug = person["name"].lower().replace(" ", "_")
        self._attr_unique_id = f"{entry.entry_id}_{name_slug}_todo"
        self._attr_name = f"Chores {person['name']}"

    @property
    def todo_items(self) -> list[TodoItem]:
        items = []
        for inst in self.coordinator.data.get("instances", []):
            if inst.get("assigned_to") != self._person_id:
                continue
            status = (
                TodoItemStatus.COMPLETED
                if inst.get("status") == "completed"
                else TodoItemStatus.NEEDS_ACTION
            )
            items.append(TodoItem(
                uid=str(inst["id"]),
                summary=f"{inst.get('chore_icon', '🧹')} {inst.get('chore_name', 'Chore')} ({inst.get('due_date', '')})",
                status=status,
            ))
        return items

    async def async_update_todo_item(self, item: TodoItem) -> None:
        """Mark a chore as completed when the todo item is checked off."""
        if item.status != TodoItemStatus.COMPLETED:
            raise HomeAssistantError("Chores can only be checked off here; edit them in the Chores app")
        async with httpx.AsyncClient(verify=get_default_context(), timeout=10) as client:
            resp = await client.post(
                f"{self.coordinator.addon_url}/api/assignments/{item.uid}/complete",
                json={"completed_by": self._person_id, "notes": "Completed via HA Todo"},
            )
            resp.raise_for_status()
        await self.coordinator.async_request_refresh()

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        """Skip chores when deleted from todo list."""
        async with httpx.AsyncClient(verify=get_default_context(), timeout=10) as client:
            for uid in uids:
                resp = await client.post(f"{self.coordinator.addon_url}/api/assignments/{uid}/skip")
                resp.raise_for_status()
        await self.coordinator.async_request_refresh()
