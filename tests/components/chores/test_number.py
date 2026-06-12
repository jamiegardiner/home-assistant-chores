"""Unit tests for custom_components/chores/number.py."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from homeassistant.const import EntityCategory
from homeassistant.exceptions import HomeAssistantError

from custom_components.chores.number import (
    ChoreDefaultSnoozeValueNumber,
    ChoreIntervalNumber,
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


def _make_interval_number(coordinator=None, entry=None):
    if coordinator is None:
        coordinator = FakeCoordinator()
    if entry is None:
        entry = _make_entry()
    return ChoreIntervalNumber(coordinator, entry)


def _make_snooze_value_number(coordinator=None, entry=None):
    if coordinator is None:
        coordinator = FakeCoordinator()
    if entry is None:
        entry = _make_entry()
    return ChoreDefaultSnoozeValueNumber(coordinator, entry)


# ---------------------------------------------------------------------------
# async_setup_entry
# ---------------------------------------------------------------------------


class TestAsyncSetupEntry:
    async def test_two_number_entities_per_entry(self):
        """async_setup_entry must add exactly two number entities."""
        coordinator = FakeCoordinator()
        entry = _make_entry()
        entry.runtime_data = coordinator

        added: list = []
        await async_setup_entry(MagicMock(), entry, lambda e, **_: added.extend(e))

        assert len(added) == 2

    async def test_entity_types(self):
        """Both number entity classes are created."""
        coordinator = FakeCoordinator()
        entry = _make_entry()
        entry.runtime_data = coordinator

        added: list = []
        await async_setup_entry(MagicMock(), entry, lambda e, **_: added.extend(e))

        types = {type(e) for e in added}
        assert types == {ChoreIntervalNumber, ChoreDefaultSnoozeValueNumber}


# ---------------------------------------------------------------------------
# ChoreIntervalNumber
# ---------------------------------------------------------------------------


class TestChoreIntervalNumber:
    def test_native_value(self):
        entity = _make_interval_number()
        assert entity.native_value == 7

    def test_native_value_custom(self):
        entity = _make_interval_number(
            coordinator=FakeCoordinator({**CHORE_STATE, "interval_days": 14})
        )
        assert entity.native_value == 14

    def test_native_value_none_when_missing(self):
        state = {k: v for k, v in CHORE_STATE.items() if k != "interval_days"}
        entity = _make_interval_number(coordinator=FakeCoordinator(state))
        assert entity.native_value is None

    def test_entity_category_config(self):
        entity = _make_interval_number()
        assert entity.entity_category == EntityCategory.CONFIG

    def test_unique_id_format(self):
        entry = _make_entry(entry_id="abc")
        entity = _make_interval_number(entry=entry)
        assert entity.unique_id == "abc_interval_days"

    def test_translation_key(self):
        entity = _make_interval_number()
        assert entity.translation_key == "interval_days"

    def test_min_value(self):
        entity = _make_interval_number()
        assert entity.native_min_value == 1.0

    def test_step(self):
        entity = _make_interval_number()
        assert entity.native_step == 1.0

    async def test_set_native_value_persists(self):
        coordinator = FakeCoordinator()
        entity = _make_interval_number(coordinator=coordinator)
        await entity.async_set_native_value(14.0)
        assert coordinator._persist_calls == [{"interval_days": 14}]

    async def test_set_native_value_rejects_zero(self):
        entity = _make_interval_number()
        with pytest.raises(HomeAssistantError):
            await entity.async_set_native_value(0.0)

    async def test_set_native_value_rejects_negative(self):
        entity = _make_interval_number()
        with pytest.raises(HomeAssistantError):
            await entity.async_set_native_value(-1.0)

    async def test_set_native_value_no_persist_on_invalid(self):
        coordinator = FakeCoordinator()
        entity = _make_interval_number(coordinator=coordinator)
        with pytest.raises(HomeAssistantError):
            await entity.async_set_native_value(0.0)
        assert coordinator._persist_calls == []


# ---------------------------------------------------------------------------
# ChoreDefaultSnoozeValueNumber
# ---------------------------------------------------------------------------


class TestChoreDefaultSnoozeValueNumber:
    def test_native_value(self):
        entity = _make_snooze_value_number()
        assert entity.native_value == 1

    def test_native_value_custom(self):
        entity = _make_snooze_value_number(
            coordinator=FakeCoordinator({**CHORE_STATE, "default_snooze_value": 5})
        )
        assert entity.native_value == 5

    def test_native_value_none_when_missing(self):
        state = {k: v for k, v in CHORE_STATE.items() if k != "default_snooze_value"}
        entity = _make_snooze_value_number(coordinator=FakeCoordinator(state))
        assert entity.native_value is None

    def test_entity_category_config(self):
        entity = _make_snooze_value_number()
        assert entity.entity_category == EntityCategory.CONFIG

    def test_unique_id_format(self):
        entry = _make_entry(entry_id="abc")
        entity = _make_snooze_value_number(entry=entry)
        assert entity.unique_id == "abc_default_snooze_value"

    def test_translation_key(self):
        entity = _make_snooze_value_number()
        assert entity.translation_key == "default_snooze_value"

    async def test_set_native_value_persists(self):
        coordinator = FakeCoordinator()
        entity = _make_snooze_value_number(coordinator=coordinator)
        await entity.async_set_native_value(3.0)
        assert coordinator._persist_calls == [{"default_snooze_value": 3}]

    async def test_set_native_value_rejects_zero(self):
        entity = _make_snooze_value_number()
        with pytest.raises(HomeAssistantError):
            await entity.async_set_native_value(0.0)

    async def test_set_native_value_no_persist_on_invalid(self):
        coordinator = FakeCoordinator()
        entity = _make_snooze_value_number(coordinator=coordinator)
        with pytest.raises(HomeAssistantError):
            await entity.async_set_native_value(0.0)
        assert coordinator._persist_calls == []
