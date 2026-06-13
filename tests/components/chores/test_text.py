"""Unit tests for custom_components/chores/text.py."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from homeassistant.const import EntityCategory
from homeassistant.exceptions import HomeAssistantError

from custom_components.chores.text import ChoreNameTextEntity, async_setup_entry

# ---------------------------------------------------------------------------
# Fake coordinator
# ---------------------------------------------------------------------------

CHORE_STATE = {
    "name": "Bins",
    "status": "overdue",
    "interval_days": 7,
    "default_snooze_value": 1,
    "default_snooze_unit": "days",
    "notification_time": "08:00",
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


def _make_text_entity(coordinator=None, entry=None):
    if coordinator is None:
        coordinator = FakeCoordinator()
    if entry is None:
        entry = _make_entry()
    return ChoreNameTextEntity(coordinator, entry)


# ---------------------------------------------------------------------------
# async_setup_entry
# ---------------------------------------------------------------------------


class TestAsyncSetupEntry:
    async def test_one_text_entity_per_entry(self):
        """async_setup_entry must add exactly one text entity."""
        coordinator = FakeCoordinator()
        entry = _make_entry()
        entry.runtime_data = coordinator

        added: list = []
        await async_setup_entry(MagicMock(), entry, lambda e, **_: added.extend(e))

        assert len(added) == 1
        assert isinstance(added[0], ChoreNameTextEntity)


# ---------------------------------------------------------------------------
# ChoreNameTextEntity
# ---------------------------------------------------------------------------


class TestChoreNameTextEntity:
    def test_native_value(self):
        entity = _make_text_entity()
        assert entity.native_value == "Bins"

    def test_native_value_none_when_data_is_none(self):
        coordinator = FakeCoordinator()
        coordinator.data = None
        entity = _make_text_entity(coordinator=coordinator)
        assert entity.native_value is None

    def test_entity_category_config(self):
        entity = _make_text_entity()
        assert entity.entity_category == EntityCategory.CONFIG

    def test_unique_id_format(self):
        entry = _make_entry(entry_id="abc")
        entity = _make_text_entity(entry=entry)
        assert entity.unique_id == "abc_name"

    def test_translation_key(self):
        entity = _make_text_entity()
        assert entity.translation_key == "name"

    def test_min_is_1(self):
        entity = _make_text_entity()
        assert entity.native_min == 1

    async def test_set_value_persists(self):
        coordinator = FakeCoordinator()
        entity = _make_text_entity(coordinator=coordinator)
        await entity.async_set_value("Wheelie Bins")
        assert coordinator._persist_calls == [{"name": "Wheelie Bins"}]

    async def test_set_value_strips_whitespace(self):
        coordinator = FakeCoordinator()
        entity = _make_text_entity(coordinator=coordinator)
        await entity.async_set_value("  Bins  ")
        assert coordinator._persist_calls == [{"name": "Bins"}]

    async def test_set_value_whitespace_only_raises(self):
        coordinator = FakeCoordinator()
        entity = _make_text_entity(coordinator=coordinator)
        with pytest.raises(HomeAssistantError):
            await entity.async_set_value("   ")
        assert coordinator._persist_calls == []

    async def test_set_value_empty_raises(self):
        coordinator = FakeCoordinator()
        entity = _make_text_entity(coordinator=coordinator)
        with pytest.raises(HomeAssistantError):
            await entity.async_set_value("")
        assert coordinator._persist_calls == []
