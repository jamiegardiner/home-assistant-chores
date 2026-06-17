"""Unit tests for custom_components/chores/select.py."""

from typing import Any
from unittest.mock import MagicMock

import pytest
from homeassistant.const import EntityCategory

from custom_components.chores.const import INTERVAL_UNITS, SNOOZE_UNITS
from custom_components.chores.select import (
    ChoreDefaultSnoozeUnitSelect,
    ChoreIntervalUnitSelect,
    async_setup_entry,
)
from tests.components.chores.helpers import make_entry, setup_coord

# ---------------------------------------------------------------------------
# Fake coordinator
# ---------------------------------------------------------------------------

CHORE_STATE = {
    "name": "Dishes",
    "status": "overdue",
    "interval_value": 7,
    "interval_unit": "days",
    "default_snooze_value": 1,
    "default_snooze_unit": "days",
}


class FakeCoordinator:
    def __init__(self, state: dict | None = None):
        self.data = state if state is not None else dict(CHORE_STATE)
        self.config_entry = MagicMock()
        self.config_entry.options = dict(CHORE_STATE)
        self._persist_calls: list[dict] = []

    def async_add_listener(self, *_args, **_kwargs):
        return lambda: None

    def async_remove_listener(self, *_args, **_kwargs):
        pass

    def set_option(self, key: str, value: object) -> None:
        self._persist({key: value})

    def _persist(self, fields: dict) -> None:
        self._persist_calls.append(fields)
        self.config_entry.options = {**self.config_entry.options, **fields}


def _make_entry(entry_id: str = "test_entry_id") -> MagicMock:
    entry = MagicMock()
    entry.entry_id = entry_id
    return entry


def _make_interval_unit_select(coordinator=None, entry=None):
    if coordinator is None:
        coordinator = FakeCoordinator()
    if entry is None:
        entry = _make_entry()
    return ChoreIntervalUnitSelect(coordinator, entry)


def _make_snooze_unit_select(coordinator=None, entry=None):
    if coordinator is None:
        coordinator = FakeCoordinator()
    if entry is None:
        entry = _make_entry()
    return ChoreDefaultSnoozeUnitSelect(coordinator, entry)


# ---------------------------------------------------------------------------
# async_setup_entry
# ---------------------------------------------------------------------------


class TestAsyncSetupEntry:
    async def test_two_select_entities_per_entry(self):
        """async_setup_entry must add exactly two select entities."""
        coordinator = FakeCoordinator()
        entry = _make_entry()
        entry.runtime_data = coordinator

        added: list = []
        await async_setup_entry(MagicMock(), entry, lambda e, **_: added.extend(e))

        assert len(added) == 2

    async def test_entity_types(self):
        """Both select entity classes are created."""
        coordinator = FakeCoordinator()
        entry = _make_entry()
        entry.runtime_data = coordinator

        added: list = []
        await async_setup_entry(MagicMock(), entry, lambda e, **_: added.extend(e))

        types = {type(e) for e in added}
        assert types == {ChoreIntervalUnitSelect, ChoreDefaultSnoozeUnitSelect}


# ---------------------------------------------------------------------------
# ChoreIntervalUnitSelect
# ---------------------------------------------------------------------------


class TestChoreIntervalUnitSelect:
    def test_current_option(self):
        entity = _make_interval_unit_select()
        assert entity.current_option == "days"

    def test_current_option_custom(self):
        entity = _make_interval_unit_select(
            coordinator=FakeCoordinator({**CHORE_STATE, "interval_unit": "weeks"})
        )
        assert entity.current_option == "weeks"

    def test_current_option_none_when_missing(self):
        state = {k: v for k, v in CHORE_STATE.items() if k != "interval_unit"}
        entity = _make_interval_unit_select(coordinator=FakeCoordinator(state))
        assert entity.current_option is None

    def test_entity_category_config(self):
        entity = _make_interval_unit_select()
        assert entity.entity_category == EntityCategory.CONFIG

    def test_unique_id_format(self):
        entry = _make_entry(entry_id="abc")
        entity = _make_interval_unit_select(entry=entry)
        assert entity.unique_id == "abc_interval_unit"

    def test_translation_key(self):
        entity = _make_interval_unit_select()
        assert entity.translation_key == "interval_unit"

    def test_options_are_interval_units(self):
        entity = _make_interval_unit_select()
        assert entity.options == list(INTERVAL_UNITS)

    @pytest.mark.parametrize("unit", INTERVAL_UNITS)
    async def test_select_option_persists_all_valid_units(self, unit):
        coordinator = FakeCoordinator()
        entity = _make_interval_unit_select(coordinator=coordinator)
        await entity.async_select_option(unit)
        assert coordinator._persist_calls == [{"interval_unit": unit}]


# ---------------------------------------------------------------------------
# ChoreDefaultSnoozeUnitSelect
# ---------------------------------------------------------------------------


class TestChoreDefaultSnoozeUnitSelect:
    def test_current_option(self):
        entity = _make_snooze_unit_select()
        assert entity.current_option == "days"

    def test_current_option_custom(self):
        entity = _make_snooze_unit_select(
            coordinator=FakeCoordinator({**CHORE_STATE, "default_snooze_unit": "hours"})
        )
        assert entity.current_option == "hours"

    def test_current_option_none_when_missing(self):
        state = {k: v for k, v in CHORE_STATE.items() if k != "default_snooze_unit"}
        entity = _make_snooze_unit_select(coordinator=FakeCoordinator(state))
        assert entity.current_option is None

    def test_entity_category_config(self):
        entity = _make_snooze_unit_select()
        assert entity.entity_category == EntityCategory.CONFIG

    def test_unique_id_format(self):
        entry = _make_entry(entry_id="abc")
        entity = _make_snooze_unit_select(entry=entry)
        assert entity.unique_id == "abc_default_snooze_unit"

    def test_translation_key(self):
        entity = _make_snooze_unit_select()
        assert entity.translation_key == "default_snooze_unit"

    def test_options_are_snooze_units(self):
        entity = _make_snooze_unit_select()
        assert entity.options == list(SNOOZE_UNITS)

    @pytest.mark.parametrize("unit", SNOOZE_UNITS)
    async def test_select_option_persists_all_valid_units(self, unit):
        coordinator = FakeCoordinator()
        entity = _make_snooze_unit_select(coordinator=coordinator)
        await entity.async_select_option(unit)
        assert coordinator._persist_calls == [{"default_snooze_unit": unit}]


# ---------------------------------------------------------------------------
# Integration tests — real ChoresCoordinator
# ---------------------------------------------------------------------------


class TestIntervalUnitSelectIntegration:
    async def test_select_option_updates_coordinator_data(self, hass: Any) -> None:
        """Interval unit select updates coordinator.data via the real set_option → _persist path."""
        entry = make_entry(interval_unit="days")
        entry.add_to_hass(hass)
        coord = await setup_coord(hass, entry)
        entity = ChoreIntervalUnitSelect(coord, entry)

        await entity.async_select_option("weeks")
        await coord.async_update_config(dict(entry.options))

        assert coord.data["interval_unit"] == "weeks"


class TestSnoozeUnitSelectIntegration:
    async def test_select_option_updates_coordinator_data(self, hass: Any) -> None:
        """Snooze unit select updates coordinator.data via the real set_option → _persist path."""
        entry = make_entry(default_snooze_unit="days")
        entry.add_to_hass(hass)
        coord = await setup_coord(hass, entry)
        entity = ChoreDefaultSnoozeUnitSelect(coord, entry)

        await entity.async_select_option("hours")
        await coord.async_update_config(dict(entry.options))

        assert coord.data["default_snooze_unit"] == "hours"
