"""Unit tests for custom_components/chores/sensor.py."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Fake coordinator — single-chore flat-dict model
# ---------------------------------------------------------------------------

CHORE_STATE = {
    "name": "Dishes",
    "status": "overdue",
    "last_completed": date(2026, 6, 1),
    "next_due": date(2026, 6, 8),
    "snooze_until": None,
}

CHORE_STATE_B = {
    "name": "Vacuum",
    "status": "done",
    "last_completed": date(2026, 6, 5),
    "next_due": date(2026, 6, 12),
    "snooze_until": None,
}


class FakeCoordinator:
    """Minimal coordinator stub duck-typed against the new single-chore API."""

    def __init__(self, state: dict | None = None):
        self.data = state if state is not None else dict(CHORE_STATE)

    def async_add_listener(self, *_args, **_kwargs):
        return lambda: None

    def async_remove_listener(self, *_args, **_kwargs):
        pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_entry(entry_id: str = "test_entry_id") -> MagicMock:
    entry = MagicMock()
    entry.entry_id = entry_id
    return entry


def _make_sensor(coordinator=None, entry=None):
    """Build a ChoreSensor without going through async_setup_entry."""
    from custom_components.chores.sensor import ChoreSensor

    if coordinator is None:
        coordinator = FakeCoordinator()
    if entry is None:
        entry = _make_entry()
    return ChoreSensor(coordinator, entry)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAsyncSetupEntry:
    """Tests for async_setup_entry."""

    async def test_one_sensor_per_entry(self):
        """async_setup_entry must add exactly one entity per config entry."""
        from custom_components.chores.sensor import async_setup_entry

        coordinator = FakeCoordinator()
        entry = _make_entry()
        entry.runtime_data = coordinator

        hass = MagicMock()
        added: list = []

        def sync_add(entities, **_kwargs):
            added.extend(list(entities))

        with patch("custom_components.chores.sensor.async_get_current_platform"):
            await async_setup_entry(hass, entry, sync_add)

        assert len(added) == 1

    async def test_setup_entry_reads_coordinator_from_runtime_data(self):
        """Coordinator is read from entry.runtime_data."""
        from custom_components.chores.sensor import async_setup_entry

        coordinator = FakeCoordinator()
        entry = _make_entry(entry_id="my_entry")
        entry.runtime_data = coordinator

        hass = MagicMock()
        added: list = []

        def sync_add(entities, **_kwargs):
            added.extend(list(entities))

        with patch("custom_components.chores.sensor.async_get_current_platform"):
            await async_setup_entry(hass, entry, sync_add)

        assert len(added) == 1


class TestChoreSensorState:
    """Tests for ChoreSensor.native_value."""

    def test_state_overdue(self):
        sensor = _make_sensor()
        assert sensor.native_value == "overdue"

    def test_state_done(self):
        sensor = _make_sensor(coordinator=FakeCoordinator(dict(CHORE_STATE_B)))
        assert sensor.native_value == "done"


class TestChoreSensorName:
    """Tests for ChoreSensor.name."""

    def test_name_from_coordinator_data(self):
        sensor = _make_sensor()
        assert sensor.name == "Dishes"

    def test_name_updates_when_data_changes(self):
        coordinator = FakeCoordinator()
        sensor = _make_sensor(coordinator=coordinator)
        coordinator.data = {**CHORE_STATE, "name": "Plates"}
        assert sensor.name == "Plates"


class TestChoreSensorAttributes:
    """Tests for ChoreSensor.extra_state_attributes."""

    def test_attributes_last_completed_iso(self):
        sensor = _make_sensor()
        assert sensor.extra_state_attributes["last_completed"] == "2026-06-01"

    def test_attributes_next_due_iso(self):
        sensor = _make_sensor()
        assert sensor.extra_state_attributes["next_due"] == "2026-06-08"

    def test_attributes_none_snooze_until(self):
        sensor = _make_sensor()
        assert sensor.extra_state_attributes["snooze_until"] is None

    def test_attributes_none_last_completed(self):
        coordinator = FakeCoordinator({**CHORE_STATE, "last_completed": None})
        sensor = _make_sensor(coordinator=coordinator)
        assert sensor.extra_state_attributes["last_completed"] is None


class TestChoreSensorUniqueId:
    """Tests for stable unique_id (= entry.entry_id)."""

    def test_unique_id_equals_entry_id(self):
        entry = _make_entry(entry_id="cfg_entry_abc")
        sensor = _make_sensor(entry=entry)
        assert sensor.unique_id == "cfg_entry_abc"

    def test_unique_id_stable_across_instances(self):
        entry = _make_entry(entry_id="stable_entry")
        s1 = _make_sensor(entry=entry)
        s2 = _make_sensor(entry=entry)
        assert s1.unique_id == s2.unique_id

    def test_unique_id_differs_per_entry(self):
        s1 = _make_sensor(entry=_make_entry(entry_id="entry_1"))
        s2 = _make_sensor(entry=_make_entry(entry_id="entry_2"))
        assert s1.unique_id != s2.unique_id


class TestChoreSensorSuggestedObjectId:
    """Tests for suggested_object_id."""

    def test_suggested_object_id_format(self):
        sensor = _make_sensor()
        assert sensor.suggested_object_id == "chore_dishes"

    def test_suggested_object_id_tracks_name(self):
        coordinator = FakeCoordinator({**CHORE_STATE, "name": "Vacuum"})
        sensor = _make_sensor(coordinator=coordinator)
        assert sensor.suggested_object_id == "chore_vacuum"


class TestChoreSensorConventions:
    """Tests for HA entity conventions: enum device class, options, translation_key."""

    def test_device_class_is_enum(self):
        from homeassistant.components.sensor import SensorDeviceClass

        sensor = _make_sensor()
        assert sensor.device_class == SensorDeviceClass.ENUM

    def test_options_covers_all_states(self):
        sensor = _make_sensor()
        assert sensor.options == ["done", "overdue", "snoozed"]

    def test_translation_key(self):
        sensor = _make_sensor()
        assert sensor.translation_key == "chore"

    def test_native_value_none_when_data_is_none(self):
        coordinator = FakeCoordinator()
        coordinator.data = None
        sensor = _make_sensor(coordinator=coordinator)
        assert sensor.native_value is None

    def test_native_value_none_when_status_missing(self):
        coordinator = FakeCoordinator({**CHORE_STATE})
        del coordinator.data["status"]
        sensor = _make_sensor(coordinator=coordinator)
        assert sensor.native_value is None


class TestIsoHelper:
    """Tests for the _iso date-formatting helper."""

    def test_date_converted_to_iso(self):
        from custom_components.chores.sensor import _iso

        assert _iso(date(2026, 1, 15)) == "2026-01-15"

    def test_none_passed_through(self):
        from custom_components.chores.sensor import _iso

        assert _iso(None) is None

    def test_string_passed_through(self):
        from custom_components.chores.sensor import _iso

        assert _iso("already-a-string") == "already-a-string"
