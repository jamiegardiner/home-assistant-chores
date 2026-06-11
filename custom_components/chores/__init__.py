"""The Chores integration."""

from __future__ import annotations

import logging

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import ChoresConfigEntry, ChoresCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.BUTTON, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ChoresConfigEntry) -> bool:
    """Set up a single Chores entry (one per chore)."""
    coordinator = ChoresCoordinator(hass, entry)
    await coordinator.async_initialize()

    entry.runtime_data = coordinator
    entry.async_on_unload(coordinator.async_shutdown_timers)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ChoresConfigEntry) -> bool:
    """Unload a Chores config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_update_listener(hass: HomeAssistant, entry: ChoresConfigEntry) -> None:
    """Reconcile coordinator runtime state when options change (no reload)."""
    await entry.runtime_data.async_update_config(dict(entry.options))
