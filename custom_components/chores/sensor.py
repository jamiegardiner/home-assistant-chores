"""Sensor platform for the Chores integration.

One sensor entity per configured chore. State is ``done`` or ``overdue``,
sourced from the coordinator. ``last_completed`` and ``next_due`` are exposed
as extra state attributes.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Protocol

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


class ChoresCoordinator(Protocol):
    """Protocol for the Chores coordinator.

    Defines the subset of the coordinator's public API consumed by this platform.
    All coordinator access in this file is gated through this Protocol so that
    a field-name change requires only updating this declaration.
    """

    chore_ids: list[str]

    def chore_state(self, chore_id: str) -> dict[str, Any]:
        """Return runtime state dict for a single chore."""
        ...

    def register_entity(self, entity_id: str, chore_id: str) -> None:
        """Register a sensor entity_id -> chore_id mapping."""
        ...


def _iso(value: date | datetime | None | Any) -> str | None | Any:
    """Convert date/datetime to ISO-8601 string; pass through everything else."""
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Chores sensor platform from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        ChoreSensor(coordinator, entry, chore_id) for chore_id in coordinator.chore_ids
    )


class ChoreSensor(CoordinatorEntity, SensorEntity):
    """Sensor entity representing a single chore.

    State is ``done`` or ``overdue`` as derived by the coordinator.
    """

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: Any,
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

    async def async_added_to_hass(self) -> None:
        """Register the entity_id -> chore_id mapping with the coordinator.

        ``entity_id`` is not assigned at ``__init__`` time, so the registration
        must happen in this lifecycle hook.
        """
        await super().async_added_to_hass()
        self._chores_coordinator.register_entity(self.entity_id, self._chore_id)

    @property
    def _chores_coordinator(self) -> ChoresCoordinator:
        """Return the coordinator typed as ChoresCoordinator."""
        return self.coordinator  # type: ignore[return-value]

    def _chore_state(self) -> dict[str, Any]:
        """Return the coordinator's current state dict for this chore.

        All coordinator access is funnelled through this single helper so that
        field-name changes on merge with issue #4 require only a 1-line edit.

        Expected keys: ``status``, ``last_completed``, ``next_due``, ``name``.
        """
        return self._chores_coordinator.chore_state(self._chore_id)

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
