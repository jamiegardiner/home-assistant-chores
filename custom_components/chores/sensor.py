"""Sensor platform for the Chores integration.

One sensor entity per configured chore. State is ``done`` or ``overdue``,
sourced from the coordinator. ``last_completed`` and ``next_due`` are exposed
as extra state attributes.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.entity_platform import (
    AddEntitiesCallback,
    async_get_current_platform,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

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


# ---------------------------------------------------------------------------
# Entity service handlers — called once per matched entity by HA's platform
# machinery, which handles all target resolution (entity, area, device, label).
# ---------------------------------------------------------------------------


async def _handle_complete(entity: ChoreSensor, call: ServiceCall) -> None:
    await entity.coordinator.async_complete(entity._chore_id)


async def _handle_snooze(entity: ChoreSensor, call: ServiceCall) -> None:
    snooze_until = _parse_snooze_until(call.data)
    await entity.coordinator.async_snooze(entity._chore_id, snooze_until)


async def _handle_unsnooze(entity: ChoreSensor, call: ServiceCall) -> None:
    await entity.coordinator.async_unsnooze(entity._chore_id)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Chores sensor platform from a config entry."""
    coordinator = entry.runtime_data
    async_add_entities(
        ChoreSensor(coordinator, entry, chore_id) for chore_id in coordinator.chore_ids
    )

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
    """Sensor entity representing a single chore.

    State is ``done`` or ``overdue`` as derived by the coordinator.
    """

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ChoresCoordinator,
        entry: ConfigEntry,
        chore_id: str,
    ) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, context=chore_id)
        self._chore_id = chore_id
        self._attr_unique_id = f"{entry.entry_id}_{chore_id}"
        # Capture the chore display name once; it does not change at runtime.
        state = self._chore_state()
        self._attr_name = state.get("name", chore_id)

    @property
    def suggested_object_id(self) -> str:
        return f"chore_{slugify(self._attr_name)}"

    def _chore_state(self) -> dict[str, Any]:
        """Return the coordinator's current state dict for this chore."""
        return self.coordinator.chore_state(self._chore_id)

    @property
    def native_value(self) -> str:
        """Return ``done`` or ``overdue``."""
        return self._chore_state().get("status", "unknown")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return last_completed, next_due, and snooze_until as ISO strings (or None)."""
        state = self._chore_state()
        return {
            "last_completed": _iso(state.get("last_completed")),
            "next_due": _iso(state.get("next_due")),
            "snooze_until": _iso(state.get("snooze_until")),
        }
