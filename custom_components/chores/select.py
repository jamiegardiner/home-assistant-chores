"""Select platform for the Chores integration.

One CONFIG select entity per config entry: Default Snooze Unit.
"""

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SNOOZE_UNITS
from .coordinator import ChoresCoordinator, _ChoreDeviceMixin

PARALLEL_UPDATES = 0

_SNOOZE_UNIT_OPTIONS: list[str] = list(SNOOZE_UNITS)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Default Snooze Unit select entity for this config entry."""
    coordinator = entry.runtime_data
    async_add_entities([ChoreDefaultSnoozeUnitSelect(coordinator, entry)])


class ChoreDefaultSnoozeUnitSelect(
    _ChoreDeviceMixin, CoordinatorEntity[ChoresCoordinator], SelectEntity
):
    """CONFIG select entity for default_snooze_unit."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "default_snooze_unit"
    _attr_options = _SNOOZE_UNIT_OPTIONS

    def __init__(self, coordinator: ChoresCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_default_snooze_unit"
        self._entry_id = entry.entry_id

    @property
    def current_option(self) -> str | None:
        return (self.coordinator.data or {}).get("default_snooze_unit")

    async def async_select_option(self, option: str) -> None:
        if option not in SNOOZE_UNITS:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="invalid_snooze_unit",
                translation_placeholders={"option": option},
            )
        self.coordinator.set_option("default_snooze_unit", option)
