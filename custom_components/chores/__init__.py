"""The Chores integration."""

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DEFAULT_INTERVAL_UNIT, DOMAIN
from .coordinator import (
    ChoresConfigEntry,
    ChoresCoordinator,
    compute_next_due,
    parse_aware_datetime,
)
from .models import ChoreConfig


class _ChoreDeviceMixin:
    """Shared device_info property for all chore entity classes."""

    _entry_id: str
    coordinator: ChoresCoordinator

    @property
    def device_info(self) -> DeviceInfo:
        name = (self.coordinator.data or {}).get("name", "Chore")
        return DeviceInfo(identifiers={(DOMAIN, self._entry_id)}, name=name)


PLATFORMS: list[Platform] = [
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.TIME,
]


async def async_migrate_entry(hass: HomeAssistant, entry: ChoresConfigEntry) -> bool:
    """Migrate old config entry versions to the current version."""
    if entry.version == 1:
        options = dict(entry.options)
        options["interval_value"] = options.pop(
            "interval_days", options.get("interval_value", 1)
        )
        options.setdefault("interval_unit", DEFAULT_INTERVAL_UNIT)

        ent_reg = er.async_get(hass)
        old_entity_id = ent_reg.async_get_entity_id(
            "number", DOMAIN, f"{entry.entry_id}_interval_days"
        )
        if old_entity_id:
            ent_reg.async_remove(old_entity_id)

        hass.config_entries.async_update_entry(entry, options=options, version=2)

    if entry.version == 2:
        options = dict(entry.options)
        try:
            last_completed = parse_aware_datetime(options.get("last_completed"))
        except ValueError:
            last_completed = None

        try:
            config = ChoreConfig.from_dict(options)
            next_due = compute_next_due(last_completed, config)
        except ValueError:
            next_due = None
        options["next_due"] = next_due.isoformat() if next_due else None

        hass.config_entries.async_update_entry(entry, options=options, version=3)

    return True


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
