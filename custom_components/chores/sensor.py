"""Sensor platform for the Chores integration.

Four sensor entities per config entry: primary status sensor, two primary date sensors,
and one diagnostic sensor (snooze expiry, disabled by default).
"""

from datetime import date, datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import (
    AddEntitiesCallback,
    async_get_current_platform,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    MAX_NUMBER_VALUE,
    MIN_NUMBER_VALUE,
    SERVICE_COMPLETE,
    SERVICE_SNOOZE,
    SERVICE_UNSNOOZE,
    SNOOZE_UNITS,
    STATUS_OPTIONS,
    ChoreSensorEntityFeature,
)
from .coordinator import ChoresCoordinator, _ChoreDeviceMixin
from .services import (
    COMPLETE_SCHEMA,
    SNOOZE_SCHEMA,
    UNSNOOZE_SCHEMA,
    _parse_snooze_datetime,
)

PARALLEL_UPDATES = 0


async def _handle_complete(entity: ChoreSensor, call: ServiceCall) -> None:
    completed_at: datetime | None = call.data.get("completed_at")
    if completed_at is not None and completed_at.tzinfo is None:
        completed_at = dt_util.as_local(completed_at)
    await entity.coordinator.async_complete(completed_at)


async def _handle_snooze(entity: ChoreSensor, call: ServiceCall) -> None:
    value: int = call.data["value"]
    unit: str = call.data["unit"]
    if not MIN_NUMBER_VALUE <= value <= MAX_NUMBER_VALUE:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="snooze_value_out_of_range",
            translation_placeholders={
                "min": str(MIN_NUMBER_VALUE),
                "max": str(MAX_NUMBER_VALUE),
            },
        )
    if unit not in SNOOZE_UNITS:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="invalid_snooze_unit",
            translation_placeholders={"option": unit, "units": ", ".join(SNOOZE_UNITS)},
        )
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
    def native_value(self) -> str | None:
        """Return ``done``, ``overdue``, ``snoozed``, or None when unknown."""
        return (self.coordinator.data or {}).get("status")


class _ChoreDateSensor(
    _ChoreDeviceMixin, CoordinatorEntity[ChoresCoordinator], SensorEntity
):
    """Base class for diagnostic date/datetime sensors on a chore device."""

    _attr_has_entity_name = True

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
    def available(self) -> bool:
        return (
            super().available
            and (self.coordinator.data or {}).get(self._data_key) is not None
        )

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
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: ChoresCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "snooze_until", "snooze_until")
