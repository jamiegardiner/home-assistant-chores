"""Unit tests for custom_components/chores/time.py."""

from datetime import time
from unittest.mock import MagicMock

from homeassistant.const import EntityCategory

from custom_components.chores.time import (
    ChoreNotificationTimeEntity,
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
    "notification_time": "00:00",
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


def _make_time_entity(coordinator=None, entry=None):
    if coordinator is None:
        coordinator = FakeCoordinator()
    if entry is None:
        entry = _make_entry()
    return ChoreNotificationTimeEntity(coordinator, entry)


# ---------------------------------------------------------------------------
# async_setup_entry
# ---------------------------------------------------------------------------


class TestAsyncSetupEntry:
    async def test_one_time_entity_per_entry(self):
        """async_setup_entry must add exactly one time entity."""
        coordinator = FakeCoordinator()
        entry = _make_entry()
        entry.runtime_data = coordinator

        added: list = []
        await async_setup_entry(MagicMock(), entry, lambda e, **_: added.extend(e))

        assert len(added) == 1
        assert isinstance(added[0], ChoreNotificationTimeEntity)


# ---------------------------------------------------------------------------
# ChoreNotificationTimeEntity
# ---------------------------------------------------------------------------


class TestChoreNotificationTimeEntity:
    def test_native_value_default(self):
        entity = _make_time_entity()
        assert entity.native_value == time(0, 0)

    def test_native_value_custom(self):
        entity = _make_time_entity(
            coordinator=FakeCoordinator({**CHORE_STATE, "notification_time": "08:00"})
        )
        assert entity.native_value == time(8, 0)

    def test_native_value_custom_with_minutes(self):
        entity = _make_time_entity(
            coordinator=FakeCoordinator({**CHORE_STATE, "notification_time": "08:30"})
        )
        assert entity.native_value == time(8, 30)

    def test_native_value_none_when_missing(self):
        state = {k: v for k, v in CHORE_STATE.items() if k != "notification_time"}
        entity = _make_time_entity(coordinator=FakeCoordinator(state))
        assert entity.native_value is None

    def test_entity_category_config(self):
        entity = _make_time_entity()
        assert entity.entity_category == EntityCategory.CONFIG

    def test_unique_id_format(self):
        entry = _make_entry(entry_id="abc")
        entity = _make_time_entity(entry=entry)
        assert entity.unique_id == "abc_notification_time"

    def test_translation_key(self):
        entity = _make_time_entity()
        assert entity.translation_key == "notification_time"

    async def test_set_value_persists(self):
        coordinator = FakeCoordinator()
        entity = _make_time_entity(coordinator=coordinator)
        await entity.async_set_value(time(8, 30))
        assert coordinator._persist_calls == [{"notification_time": "08:30"}]

    async def test_set_value_midnight(self):
        coordinator = FakeCoordinator()
        entity = _make_time_entity(coordinator=coordinator)
        await entity.async_set_value(time(0, 0))
        assert coordinator._persist_calls == [{"notification_time": "00:00"}]

    async def test_set_value_end_of_day(self):
        coordinator = FakeCoordinator()
        entity = _make_time_entity(coordinator=coordinator)
        await entity.async_set_value(time(23, 59))
        assert coordinator._persist_calls == [{"notification_time": "23:59"}]
