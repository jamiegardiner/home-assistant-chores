"""Text platform for the Chores integration.

One CONFIG text entity per config entry: Name.
"""

from __future__ import annotations

from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import ChoresCoordinator, _ChoreDeviceMixin


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Name text entity for this config entry."""
    coordinator = entry.runtime_data
    async_add_entities([ChoreNameTextEntity(coordinator, entry)])


class ChoreNameTextEntity(
    _ChoreDeviceMixin, CoordinatorEntity[ChoresCoordinator], TextEntity
):
    """CONFIG text entity for the chore name."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "name"
    _attr_native_min = 1

    def __init__(self, coordinator: ChoresCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_name"
        self._entry_id = entry.entry_id

    @property
    def native_value(self) -> str | None:
        return (self.coordinator.data or {}).get("name")

    async def async_set_value(self, value: str) -> None:
        stripped = value.strip()
        if not stripped:
            raise HomeAssistantError("Name cannot be empty")
        self.coordinator._persist({"name": stripped})
