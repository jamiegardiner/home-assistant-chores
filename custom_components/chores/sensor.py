"""Sensor platform for the Chores integration.

Five sensor entities per config entry: primary status sensor plus four diagnostics.
"""

from __future__ import annotations

from datetime import date, datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import (
    AddEntitiesCallback,
    async_get_current_platform,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .const import CHORE_SERVICE_FEATURE, DOMAIN, STATUS_OPTIONS
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
    """Set up all sensor entities for this config entry."""
    coordinator = entry.runtime_data
    async_add_entities(
        [
            ChoreSensor(coordinator, entry),
            ChoreLastCompletedSensor(coordinator, entry),
            ChoreNextDueSensor(coordinator, entry),
            ChoreSnoozeUntilSensor(coordinator, entry),
            ChoreDefaultSnoozeDaysSensor(coordinator, entry),
        ]
    )

    platform = async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_COMPLETE,
        COMPLETE_SCHEMA,
        _handle_complete,
        required_features=[CHORE_SERVICE_FEATURE],
    )
    platform.async_register_entity_service(
        SERVICE_SNOOZE,
        SNOOZE_SCHEMA,
        _handle_snooze,
        required_features=[CHORE_SERVICE_FEATURE],
    )
    platform.async_register_entity_service(
        SERVICE_UNSNOOZE,
        UNSNOOZE_SCHEMA,
        _handle_unsnooze,
        required_features=[CHORE_SERVICE_FEATURE],
    )


class ChoreSensor(CoordinatorEntity[ChoresCoordinator], SensorEntity):
    """Primary sensor entity representing a single chore (one per config entry)."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_has_entity_name = True
    _attr_translation_key = "chore"
    _attr_options = STATUS_OPTIONS
    _attr_supported_features = CHORE_SERVICE_FEATURE

    def __init__(self, coordinator: ChoresCoordinator, entry: ConfigEntry) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = entry.entry_id
        self._entry_id = entry.entry_id

    @property
    def device_info(self) -> DeviceInfo:
        name = (self.coordinator.data or {}).get("name", "Chore")
        return DeviceInfo(identifiers={(DOMAIN, self._entry_id)}, name=name)

    @property
    def suggested_object_id(self) -> str:
        name = (self.coordinator.data or {}).get("name", "Chore")
        return f"chore_{slugify(name)}"

    @property
    def native_value(self) -> str | None:
        """Return ``done``, ``overdue``, ``snoozed``, or None when unknown."""
        return (self.coordinator.data or {}).get("status")


class _ChoreDateSensor(CoordinatorEntity[ChoresCoordinator], SensorEntity):
    """Base class for diagnostic date sensors on a chore device."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: ChoresCoordinator,
        entry: ConfigEntry,
        data_key: str,
        unique_suffix: str,
    ) -> None:
        super().__init__(coordinator)
        self._data_key = data_key
        self._attr_unique_id = f"{entry.entry_id}_{unique_suffix}"
        self._entry_id = entry.entry_id

    @property
    def device_info(self) -> DeviceInfo:
        name = (self.coordinator.data or {}).get("name", "Chore")
        return DeviceInfo(identifiers={(DOMAIN, self._entry_id)}, name=name)

    @property
    def native_value(self) -> str | None:
        return _iso((self.coordinator.data or {}).get(self._data_key))


class ChoreLastCompletedSensor(_ChoreDateSensor):
    """Diagnostic sensor surfacing the last completed date."""

    _attr_translation_key = "last_completed"

    def __init__(self, coordinator: ChoresCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "last_completed", "last_completed")


class ChoreNextDueSensor(_ChoreDateSensor):
    """Diagnostic sensor surfacing the next due date."""

    _attr_translation_key = "next_due"

    def __init__(self, coordinator: ChoresCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "next_due", "next_due")


class ChoreSnoozeUntilSensor(_ChoreDateSensor):
    """Diagnostic sensor surfacing snooze_until (unavailable when not snoozed)."""

    _attr_translation_key = "snooze_until"

    def __init__(self, coordinator: ChoresCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "snooze_until", "snooze_until")


class ChoreDefaultSnoozeDaysSensor(CoordinatorEntity[ChoresCoordinator], SensorEntity):
    """Diagnostic sensor surfacing the default snooze duration in days."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "default_snooze_days"

    def __init__(self, coordinator: ChoresCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_default_snooze_days"
        self._entry_id = entry.entry_id

    @property
    def device_info(self) -> DeviceInfo:
        name = (self.coordinator.data or {}).get("name", "Chore")
        return DeviceInfo(identifiers={(DOMAIN, self._entry_id)}, name=name)

    @property
    def native_value(self) -> int | None:
        return (self.coordinator.data or {}).get("default_snooze_days")
