"""The Chores integration."""

from __future__ import annotations

import logging

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .coordinator import (
    STORAGE_VERSION,
    ChoresConfigEntry,
    ChoresCoordinator,
    storage_key,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ChoresConfigEntry) -> bool:
    """Set up Chores from a config entry."""
    coordinator = ChoresCoordinator(hass, entry)
    await coordinator.async_initialize()

    # Store coordinator for access by platform and service handlers
    entry.runtime_data = coordinator

    # Register timer teardown on unload
    entry.async_on_unload(coordinator.async_shutdown_timers)

    # Forward to sensor platform (entity services are registered during platform setup)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Re-initialize coordinator when options change
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ChoresConfigEntry) -> bool:
    """Unload a Chores config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: ChoresConfigEntry) -> None:
    """Delete the storage file when the config entry is removed."""
    store: Store = Store(hass, STORAGE_VERSION, storage_key(entry.entry_id))
    await store.async_remove()


async def _async_update_listener(hass: HomeAssistant, entry: ChoresConfigEntry) -> None:
    """Handle options/data update by reloading the entry."""
    await hass.config_entries.async_reload(entry.entry_id)
