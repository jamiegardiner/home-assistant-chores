"""Sensor platform for the Chores integration.

One sensor entity per config entry (each entry represents one chore).
State is ``done``, ``overdue``, or ``snoozed``, sourced from the coordinator.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.entity_platform import (
    AddEntitiesCallback,
    async_get_current_platform,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .const import STATUS_OPTIONS
from .coordinator import ChoresCoordinator
from .services import (
    COMPLETE_SCHEMA,
    SERVICE_COMPLETE,
    SERVICE_SNOOZE,
    SERVICE_UNSNOOZE,
    SNOOZE_SCHEMA,
    UNSNOOZE_SCHEMA,
    _parse_snooze_until,
)


def _iso(value: date | datetime | None) -> str | None:
    """Convert date/datetime to ISO-8601 string; pass through None unchanged."""
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


async def _handle_complete(entity: ChoreSensor, call: ServiceCall) -> None:
    await entity.coordinator.async_complete()


async def _handle_snooze(entity: ChoreSensor, call: ServiceCall) -> None:
    snooze_until = _parse_snooze_until(call.data)
    await entity.coordinator.async_snooze(snooze_until)


async def _handle_unsnooze(entity: ChoreSensor, call: ServiceCall) -> None:
    await entity.coordinator.async_unsnooze()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a single ChoreSensor for this config entry."""
    coordinator = entry.runtime_data
    async_add_entities([ChoreSensor(coordinator, entry)])

    platform = async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_COMPLETE, COMPLETE_SCHEMA, _handle_complete
    )
    platform.async_register_entity_service(
        SERVICE_SNOOZE, SNOOZE_SCHEMA, _handle_snooze
    )
    platform.async_register_entity_service(
        SERVICE_UNSNOOZE, UNSNOOZE_SCHEMA, _handle_unsnooze
    )


class ChoreSensor(CoordinatorEntity[ChoresCoordinator], SensorEntity):
    """Sensor entity representing a single chore (one per config entry)."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_translation_key = "chore"
    _attr_options = STATUS_OPTIONS

    def __init__(self, coordinator: ChoresCoordinator, entry: ConfigEntry) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = entry.entry_id

    @property
    def name(self) -> str:
        """Return the chore display name."""
        return (self.coordinator.data or {}).get("name", "Chore")

    @property
    def suggested_object_id(self) -> str:
        return f"chore_{slugify(self.name)}"

    @property
    def native_value(self) -> str | None:
        """Return ``done``, ``overdue``, ``snoozed``, or None when unknown."""
        return (self.coordinator.data or {}).get("status")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return last_completed, next_due, and snooze_until as ISO strings (or None)."""
        data = self.coordinator.data or {}
        return {
            "last_completed": _iso(data.get("last_completed")),
            "next_due": _iso(data.get("next_due")),
            "snooze_until": _iso(data.get("snooze_until")),
        }
