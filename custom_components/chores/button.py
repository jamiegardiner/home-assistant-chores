"""Button platform for the Chores integration.

Three button entities per config entry: Complete, Snooze, Unsnooze.
All share the same device as the chore sensor.
"""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ChoresCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Complete, Snooze, and Unsnooze buttons for this config entry."""
    coordinator = entry.runtime_data
    async_add_entities(
        [
            ChoreCompleteButton(coordinator, entry),
            ChoreSnoozeButton(coordinator, entry),
            ChoreUnsnoozeButton(coordinator, entry),
        ]
    )


class _ChoreButtonBase(CoordinatorEntity[ChoresCoordinator], ButtonEntity):
    """Shared base for all chore button entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: ChoresCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry_id = entry.entry_id

    @property
    def device_info(self) -> DeviceInfo:
        name = (self.coordinator.data or {}).get("name", "Chore")
        return DeviceInfo(identifiers={(DOMAIN, self._entry_id)}, name=name)


class ChoreCompleteButton(_ChoreButtonBase):
    """Button that marks a chore as completed."""

    _attr_translation_key = "complete"

    def __init__(self, coordinator: ChoresCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_complete"

    async def async_press(self) -> None:
        await self.coordinator.async_complete()


class ChoreSnoozeButton(_ChoreButtonBase):
    """Button that snoozes a chore by default_snooze_days."""

    _attr_translation_key = "snooze"

    def __init__(self, coordinator: ChoresCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_snooze"

    async def async_press(self) -> None:
        await self.coordinator.async_snooze_default()


class ChoreUnsnoozeButton(_ChoreButtonBase):
    """Button that cancels an active snooze (no-op when not snoozed)."""

    _attr_translation_key = "unsnooze"

    def __init__(self, coordinator: ChoresCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_unsnooze"

    async def async_press(self) -> None:
        await self.coordinator.async_unsnooze()
