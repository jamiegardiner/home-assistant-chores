"""Unit tests for custom_components/chores/select.py."""

from unittest.mock import MagicMock

import pytest
from homeassistant.const import EntityCategory
from homeassistant.exceptions import HomeAssistantError

from custom_components.chores.const import SNOOZE_UNITS
from custom_components.chores.select import (
    ChoreDefaultSnoozeUnitSelect,
    async_setup_entry,
)

# ---------------------------------------------------------------------------
# Fake coordinator
# ---------------------------------------------------------------------------

CHORE_STATE = {
    "name": "Dishes",
    "status": "overdue",
    "interval_days": 7,
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

    def _persist(self, fields: dict) -> None:
        self._persist_calls.append(fields)
        self.config_entry.options = {**self.config_entry.options, **fields}


def _make_entry(entry_id: str = "test_entry_id") -> MagicMock:
    entry = MagicMock()
    entry.entry_id = entry_id
    return entry


def _make_select(coordinator=None, entry=None):
    if coordinator is None:
        coordinator = FakeCoordinator()
    if entry is None:
        entry = _make_entry()
    return ChoreDefaultSnoozeUnitSelect(coordinator, entry)


# ---------------------------------------------------------------------------
# async_setup_entry
# ---------------------------------------------------------------------------


class TestAsyncSetupEntry:
    async def test_one_select_entity_per_entry(self):
        """async_setup_entry must add exactly one select entity."""
        coordinator = FakeCoordinator()
        entry = _make_entry()
        entry.runtime_data = coordinator

        added: list = []
        await async_setup_entry(MagicMock(), entry, lambda e, **_: added.extend(e))

        assert len(added) == 1
        assert isinstance(added[0], ChoreDefaultSnoozeUnitSelect)


# ---------------------------------------------------------------------------
# ChoreDefaultSnoozeUnitSelect
# ---------------------------------------------------------------------------


class TestChoreDefaultSnoozeUnitSelect:
    def test_current_option(self):
        entity = _make_select()
        assert entity.current_option == "days"

    def test_current_option_custom(self):
        entity = _make_select(
            coordinator=FakeCoordinator({**CHORE_STATE, "default_snooze_unit": "hours"})
        )
        assert entity.current_option == "hours"

    def test_current_option_none_when_missing(self):
        state = {k: v for k, v in CHORE_STATE.items() if k != "default_snooze_unit"}
        entity = _make_select(coordinator=FakeCoordinator(state))
        assert entity.current_option is None

    def test_entity_category_config(self):
        entity = _make_select()
        assert entity.entity_category == EntityCategory.CONFIG

    def test_unique_id_format(self):
        entry = _make_entry(entry_id="abc")
        entity = _make_select(entry=entry)
        assert entity.unique_id == "abc_default_snooze_unit"

    def test_translation_key(self):
        entity = _make_select()
        assert entity.translation_key == "default_snooze_unit"

    def test_options_are_snooze_units(self):
        entity = _make_select()
        assert entity.options == list(SNOOZE_UNITS)

    @pytest.mark.parametrize("unit", SNOOZE_UNITS)
    async def test_select_option_persists_all_valid_units(self, unit):
        coordinator = FakeCoordinator()
        entity = _make_select(coordinator=coordinator)
        await entity.async_select_option(unit)
        assert coordinator._persist_calls == [{"default_snooze_unit": unit}]

    async def test_select_option_rejects_invalid_unit(self):
        entity = _make_select()
        with pytest.raises(HomeAssistantError):
            await entity.async_select_option("fortnights")

    async def test_select_option_no_persist_on_invalid(self):
        coordinator = FakeCoordinator()
        entity = _make_select(coordinator=coordinator)
        with pytest.raises(HomeAssistantError):
            await entity.async_select_option("fortnights")
        assert coordinator._persist_calls == []
