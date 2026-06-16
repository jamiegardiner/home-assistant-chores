"""Diagnostics support for the Chores integration."""

from typing import Any

from homeassistant.core import HomeAssistant

from .coordinator import ChoresConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ChoresConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    return {"coordinator_data": dict(coordinator.data)}
