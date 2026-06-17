"""Select platform for the Chores integration.

Two CONFIG select entities per config entry: Interval Unit and Default Snooze Unit.
"""

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import INTERVAL_UNITS, SNOOZE_UNITS
from .coordinator import ChoresCoordinator, _ChoreDeviceMixin

PARALLEL_UPDATES = 0

_INTERVAL_UNIT_OPTIONS: list[str] = list(INTERVAL_UNITS)
_SNOOZE_UNIT_OPTIONS: list[str] = list(SNOOZE_UNITS)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Interval Unit and Default Snooze Unit select entities for this config entry."""
    coordinator = entry.runtime_data
    async_add_entities(
        [
            ChoreIntervalUnitSelect(coordinator, entry),
            ChoreDefaultSnoozeUnitSelect(coordinator, entry),
        ]
    )


class _ChoreSelectBase(
    _ChoreDeviceMixin, CoordinatorEntity[ChoresCoordinator], SelectEntity
):
    """Shared base for chore CONFIG select entities."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: ChoresCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry_id = entry.entry_id


class ChoreIntervalUnitSelect(_ChoreSelectBase):
    """CONFIG select entity for interval_unit."""

    _attr_translation_key = "interval_unit"
    _attr_options = _INTERVAL_UNIT_OPTIONS

    def __init__(self, coordinator: ChoresCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_interval_unit"

    @property
    def current_option(self) -> str | None:
        return (self.coordinator.data or {}).get("interval_unit")

    async def async_select_option(self, option: str) -> None:
        self.coordinator.set_option("interval_unit", option)


class ChoreDefaultSnoozeUnitSelect(_ChoreSelectBase):
    """CONFIG select entity for default_snooze_unit."""

    _attr_translation_key = "default_snooze_unit"
    _attr_options = _SNOOZE_UNIT_OPTIONS

    def __init__(self, coordinator: ChoresCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_default_snooze_unit"

    @property
    def current_option(self) -> str | None:
        return (self.coordinator.data or {}).get("default_snooze_unit")

    async def async_select_option(self, option: str) -> None:
        self.coordinator.set_option("default_snooze_unit", option)
