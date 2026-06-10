"""The Chores integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import ChoresCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Chores from a config entry."""
    coordinator = ChoresCoordinator(hass, entry)
    await coordinator.async_initialize()

    # Store coordinator for access by platform and service handler
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # Register timer teardown on unload
    entry.async_on_unload(coordinator.async_shutdown_timers)

    # Forward to sensor platform (entity services are registered during platform setup)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Re-initialize coordinator when options change
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Chores config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unloaded:
        domain_data: dict[str, Any] = hass.data.get(DOMAIN, {})
        domain_data.pop(entry.entry_id, None)

    return unloaded


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options/data update by reloading the entry."""
    await hass.config_entries.async_reload(entry.entry_id)
