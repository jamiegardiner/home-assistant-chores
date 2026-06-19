"""Time platform for the Chores integration.

One CONFIG time entity per config entry: Notification Time.
"""

from datetime import time

from homeassistant.components.time import TimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import _ChoreDeviceMixin
from .coordinator import ChoresCoordinator

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Notification Time entity for this config entry."""
    coordinator = entry.runtime_data
    async_add_entities([ChoreNotificationTimeEntity(coordinator, entry)])


class ChoreNotificationTimeEntity(
    _ChoreDeviceMixin, CoordinatorEntity[ChoresCoordinator], TimeEntity
):
    """CONFIG time entity for notification_time."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "notification_time"

    def __init__(self, coordinator: ChoresCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_notification_time"
        self._entry_id = entry.entry_id

    @property
    def native_value(self) -> time | None:
        time_str = (self.coordinator.data or {}).get("notification_time")
        if not time_str:
            return None
        try:
            h, m = map(int, time_str.split(":"))
            return time(h, m)
        except ValueError, AttributeError:
            return None

    async def async_set_value(self, value: time) -> None:
        self.coordinator.set_option(
            "notification_time", f"{value.hour:02d}:{value.minute:02d}"
        )
