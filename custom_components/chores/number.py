"""Number platform for the Chores integration.

Two CONFIG number entities per config entry: Interval and Default Snooze Value.
"""

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import _ChoreDeviceMixin
from .const import MAX_NUMBER_VALUE, MIN_NUMBER_VALUE
from .coordinator import ChoresCoordinator

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Interval and Default Snooze Value number entities for this config entry."""
    coordinator = entry.runtime_data
    async_add_entities(
        [
            ChoreIntervalNumber(coordinator, entry),
            ChoreDefaultSnoozeValueNumber(coordinator, entry),
        ]
    )


class _ChoreNumberBase(
    _ChoreDeviceMixin, CoordinatorEntity[ChoresCoordinator], NumberEntity
):
    """Shared base for chore CONFIG number entities."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = MIN_NUMBER_VALUE
    _attr_native_max_value = MAX_NUMBER_VALUE
    _attr_native_step = 1.0

    def __init__(self, coordinator: ChoresCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry_id = entry.entry_id


class ChoreIntervalNumber(_ChoreNumberBase):
    """CONFIG number entity for interval_value."""

    _attr_translation_key = "interval_value"

    def __init__(self, coordinator: ChoresCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_interval_value"

    @property
    def native_value(self) -> float | None:
        return (self.coordinator.data or {}).get("interval_value")

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.set_option("interval_value", int(value))


class ChoreDefaultSnoozeValueNumber(_ChoreNumberBase):
    """CONFIG number entity for default_snooze_value."""

    _attr_translation_key = "default_snooze_value"

    def __init__(self, coordinator: ChoresCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_default_snooze_value"

    @property
    def native_value(self) -> float | None:
        return (self.coordinator.data or {}).get("default_snooze_value")

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.set_option("default_snooze_value", int(value))
