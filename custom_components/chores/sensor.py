"""Sensor platform for the Chores integration.

Six sensor entities per config entry: primary status sensor plus five diagnostics.
"""

from __future__ import annotations

from datetime import date, datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.entity_platform import (
    AddEntitiesCallback,
    async_get_current_platform,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util
from homeassistant.util import slugify

from .const import STATUS_OPTIONS, ChoreSensorEntityFeature
from .coordinator import ChoresCoordinator, _ChoreDeviceMixin
from .services import (
    COMPLETE_SCHEMA,
    SERVICE_COMPLETE,
    SERVICE_SNOOZE,
    SERVICE_UNSNOOZE,
    SNOOZE_SCHEMA,
    UNSNOOZE_SCHEMA,
    _parse_snooze_datetime,
)


async def _handle_complete(entity: ChoreSensor, call: ServiceCall) -> None:
    completed_at = None
    raw = call.data.get("completed_at")
    if raw is not None:
        parsed = dt_util.parse_datetime(str(raw))
        if parsed is not None:
            completed_at = (
                parsed if parsed.tzinfo is not None else dt_util.as_local(parsed)
            )
    await entity.coordinator.async_complete(completed_at)


async def _handle_snooze(entity: ChoreSensor, call: ServiceCall) -> None:
    snooze_until = _parse_snooze_datetime(call.data)
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
            ChoreDefaultSnoozeValueSensor(coordinator, entry),
            ChoreDefaultSnoozeUnitSensor(coordinator, entry),
        ]
    )

    platform = async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_COMPLETE,
        COMPLETE_SCHEMA,
        _handle_complete,
        required_features=[ChoreSensorEntityFeature.TARGETABLE],
    )
    platform.async_register_entity_service(
        SERVICE_SNOOZE,
        SNOOZE_SCHEMA,
        _handle_snooze,
        required_features=[ChoreSensorEntityFeature.TARGETABLE],
    )
    platform.async_register_entity_service(
        SERVICE_UNSNOOZE,
        UNSNOOZE_SCHEMA,
        _handle_unsnooze,
        required_features=[ChoreSensorEntityFeature.TARGETABLE],
    )


class ChoreSensor(
    _ChoreDeviceMixin, CoordinatorEntity[ChoresCoordinator], SensorEntity
):
    """Primary sensor entity representing a single chore (one per config entry)."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_has_entity_name = True
    _attr_translation_key = "chore"
    _attr_options = STATUS_OPTIONS
    _attr_supported_features = ChoreSensorEntityFeature.TARGETABLE

    def __init__(self, coordinator: ChoresCoordinator, entry: ConfigEntry) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = entry.entry_id
        self._entry_id = entry.entry_id

    @property
    def suggested_object_id(self) -> str:
        name = (self.coordinator.data or {}).get("name", "Chore")
        return f"chore_{slugify(name)}"

    @property
    def native_value(self) -> str | None:
        """Return ``done``, ``overdue``, ``snoozed``, or None when unknown."""
        return (self.coordinator.data or {}).get("status")


class _ChoreDateSensor(
    _ChoreDeviceMixin, CoordinatorEntity[ChoresCoordinator], SensorEntity
):
    """Base class for diagnostic date/datetime sensors on a chore device."""

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
    def native_value(self) -> date | datetime | None:
        return (self.coordinator.data or {}).get(self._data_key)


class ChoreLastCompletedSensor(_ChoreDateSensor):
    """Diagnostic sensor surfacing the last completed datetime."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_translation_key = "last_completed"

    def __init__(self, coordinator: ChoresCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "last_completed", "last_completed")


class ChoreNextDueSensor(_ChoreDateSensor):
    """Diagnostic sensor surfacing the next due datetime."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_translation_key = "next_due"

    def __init__(self, coordinator: ChoresCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "next_due", "next_due")


class ChoreSnoozeUntilSensor(_ChoreDateSensor):
    """Diagnostic sensor surfacing snooze_until (unavailable when not snoozed)."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_translation_key = "snooze_until"

    def __init__(self, coordinator: ChoresCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "snooze_until", "snooze_until")


class ChoreDefaultSnoozeValueSensor(
    _ChoreDeviceMixin, CoordinatorEntity[ChoresCoordinator], SensorEntity
):
    """Diagnostic sensor surfacing the default snooze value (count)."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "default_snooze_value"

    def __init__(self, coordinator: ChoresCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_default_snooze_value"
        self._entry_id = entry.entry_id

    @property
    def native_value(self) -> int | None:
        return (self.coordinator.data or {}).get("default_snooze_value")


class ChoreDefaultSnoozeUnitSensor(
    _ChoreDeviceMixin, CoordinatorEntity[ChoresCoordinator], SensorEntity
):
    """Diagnostic sensor surfacing the default snooze unit (e.g. hours, days)."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "default_snooze_unit"

    def __init__(self, coordinator: ChoresCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_default_snooze_unit"
        self._entry_id = entry.entry_id

    @property
    def native_value(self) -> str | None:
        return (self.coordinator.data or {}).get("default_snooze_unit")
