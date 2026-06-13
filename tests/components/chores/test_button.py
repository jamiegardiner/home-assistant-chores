"""Unit tests for custom_components/chores/button.py."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

from custom_components.chores.button import (
    ChoreCompleteButton,
    ChoreSnoozeButton,
    ChoreUnsnoozeButton,
    async_setup_entry,
)
from custom_components.chores.const import DOMAIN

CHORE_STATE = {
    "name": "Dishes",
    "status": "overdue",
    "last_completed": date(2026, 6, 1),
    "next_due": date(2026, 6, 8),
    "snooze_until": None,
    "default_snooze_value": 1,
    "default_snooze_unit": "days",
}


class FakeCoordinator:
    def __init__(self, state: dict | None = None):
        self.data = state if state is not None else dict(CHORE_STATE)
        self.async_complete = AsyncMock()
        self.async_snooze_default = AsyncMock()
        self.async_unsnooze = AsyncMock()

    def async_add_listener(self, *_args, **_kwargs):
        return lambda: None

    def async_remove_listener(self, *_args, **_kwargs):
        pass


def _make_entry(entry_id: str = "test_entry_id") -> MagicMock:
    entry = MagicMock()
    entry.entry_id = entry_id
    return entry


def _make_complete_button(coordinator=None, entry=None):
    if coordinator is None:
        coordinator = FakeCoordinator()
    if entry is None:
        entry = _make_entry()
    return ChoreCompleteButton(coordinator, entry)


def _make_snooze_button(coordinator=None, entry=None):
    if coordinator is None:
        coordinator = FakeCoordinator()
    if entry is None:
        entry = _make_entry()
    return ChoreSnoozeButton(coordinator, entry)


def _make_unsnooze_button(coordinator=None, entry=None):
    if coordinator is None:
        coordinator = FakeCoordinator()
    if entry is None:
        entry = _make_entry()
    return ChoreUnsnoozeButton(coordinator, entry)


class TestAsyncSetupEntry:
    async def test_creates_three_buttons(self):
        coordinator = FakeCoordinator()
        entry = _make_entry()
        entry.runtime_data = coordinator

        added: list = []
        await async_setup_entry(
            MagicMock(), entry, lambda entities, **_: added.extend(entities)
        )

        assert len(added) == 3

    async def test_buttons_are_distinct_types(self):
        coordinator = FakeCoordinator()
        entry = _make_entry()
        entry.runtime_data = coordinator

        added: list = []
        await async_setup_entry(
            MagicMock(), entry, lambda entities, **_: added.extend(entities)
        )

        types = {type(e) for e in added}
        assert types == {ChoreCompleteButton, ChoreSnoozeButton, ChoreUnsnoozeButton}


class TestChoreCompleteButton:
    async def test_press_calls_async_complete(self):
        coordinator = FakeCoordinator()
        button = _make_complete_button(coordinator=coordinator)
        await button.async_press()
        coordinator.async_complete.assert_called_once()

    def test_unique_id_format(self):
        button = _make_complete_button(entry=_make_entry(entry_id="abc"))
        assert button.unique_id == "abc_complete"

    def test_translation_key(self):
        assert _make_complete_button().translation_key == "complete"

    def test_has_entity_name(self):
        assert _make_complete_button().has_entity_name is True


class TestChoreSnoozeButton:
    async def test_press_calls_async_snooze_default(self):
        coordinator = FakeCoordinator()
        button = _make_snooze_button(coordinator=coordinator)
        await button.async_press()
        coordinator.async_snooze_default.assert_called_once()

    def test_unique_id_format(self):
        button = _make_snooze_button(entry=_make_entry(entry_id="abc"))
        assert button.unique_id == "abc_snooze"

    def test_translation_key(self):
        assert _make_snooze_button().translation_key == "snooze"


class TestChoreUnsnoozeButton:
    async def test_press_calls_async_unsnooze(self):
        coordinator = FakeCoordinator()
        button = _make_unsnooze_button(coordinator=coordinator)
        await button.async_press()
        coordinator.async_unsnooze.assert_called_once()

    def test_unique_id_format(self):
        button = _make_unsnooze_button(entry=_make_entry(entry_id="abc"))
        assert button.unique_id == "abc_unsnooze"

    def test_translation_key(self):
        assert _make_unsnooze_button().translation_key == "unsnooze"


class TestButtonDeviceInfo:
    def test_device_info_name_from_coordinator_data(self):
        button = _make_complete_button()
        assert button.device_info["name"] == "Dishes"

    def test_device_info_identifiers_contain_entry_id(self):
        entry = _make_entry(entry_id="my_entry")
        button = _make_complete_button(entry=entry)
        assert (DOMAIN, "my_entry") in button.device_info["identifiers"]

    def test_device_info_matches_across_buttons(self):
        entry = _make_entry(entry_id="shared_entry")
        coordinator = FakeCoordinator()
        complete = _make_complete_button(coordinator=coordinator, entry=entry)
        snooze = _make_snooze_button(coordinator=coordinator, entry=entry)
        unsnooze = _make_unsnooze_button(coordinator=coordinator, entry=entry)
        assert complete.device_info["identifiers"] == snooze.device_info["identifiers"]
        assert snooze.device_info["identifiers"] == unsnooze.device_info["identifiers"]


class TestUniqueIdsDistinct:
    def test_all_three_unique_ids_are_distinct(self):
        entry = _make_entry(entry_id="same_entry")
        coordinator = FakeCoordinator()
        ids = {
            _make_complete_button(coordinator=coordinator, entry=entry).unique_id,
            _make_snooze_button(coordinator=coordinator, entry=entry).unique_id,
            _make_unsnooze_button(coordinator=coordinator, entry=entry).unique_id,
        }
        assert len(ids) == 3
