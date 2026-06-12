"""Unit tests for custom_components/chores/sensor.py."""

from __future__ import annotations

from datetime import UTC, date, datetime
from unittest.mock import MagicMock, patch

from homeassistant.const import EntityCategory

# ---------------------------------------------------------------------------
# Fake coordinator — single-chore flat-dict model
# ---------------------------------------------------------------------------

CHORE_STATE = {
    "name": "Dishes",
    "status": "overdue",
    "last_completed": date(2026, 6, 1),
    "next_due": date(2026, 6, 8),
    "snooze_until": None,
    "default_snooze_value": 1,
    "default_snooze_unit": "days",
}

CHORE_STATE_B = {
    "name": "Vacuum",
    "status": "done",
    "last_completed": date(2026, 6, 5),
    "next_due": date(2026, 6, 12),
    "snooze_until": None,
    "default_snooze_value": 2,
    "default_snooze_unit": "hours",
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


def _make_last_completed_sensor(coordinator=None, entry=None):
    from custom_components.chores.sensor import ChoreLastCompletedSensor

    if coordinator is None:
        coordinator = FakeCoordinator()
    if entry is None:
        entry = _make_entry()
    return ChoreLastCompletedSensor(coordinator, entry)


def _make_next_due_sensor(coordinator=None, entry=None):
    from custom_components.chores.sensor import ChoreNextDueSensor

    if coordinator is None:
        coordinator = FakeCoordinator()
    if entry is None:
        entry = _make_entry()
    return ChoreNextDueSensor(coordinator, entry)


def _make_snooze_until_sensor(coordinator=None, entry=None):
    from custom_components.chores.sensor import ChoreSnoozeUntilSensor

    if coordinator is None:
        coordinator = FakeCoordinator()
    if entry is None:
        entry = _make_entry()
    return ChoreSnoozeUntilSensor(coordinator, entry)


def _make_default_snooze_value_sensor(coordinator=None, entry=None):
    from custom_components.chores.sensor import ChoreDefaultSnoozeValueSensor

    if coordinator is None:
        coordinator = FakeCoordinator()
    if entry is None:
        entry = _make_entry()
    return ChoreDefaultSnoozeValueSensor(coordinator, entry)


def _make_default_snooze_unit_sensor(coordinator=None, entry=None):
    from custom_components.chores.sensor import ChoreDefaultSnoozeUnitSensor

    if coordinator is None:
        coordinator = FakeCoordinator()
    if entry is None:
        entry = _make_entry()
    return ChoreDefaultSnoozeUnitSensor(coordinator, entry)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAsyncSetupEntry:
    """Tests for async_setup_entry."""

    async def test_six_sensors_per_entry(self):
        """async_setup_entry must add exactly six entities per config entry."""
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

        assert len(added) == 6

    async def test_setup_entry_entity_types(self):
        """Six distinct entity classes are created."""
        from custom_components.chores.sensor import (
            ChoreDefaultSnoozeUnitSensor,
            ChoreDefaultSnoozeValueSensor,
            ChoreLastCompletedSensor,
            ChoreNextDueSensor,
            ChoreSensor,
            ChoreSnoozeUntilSensor,
            async_setup_entry,
        )

        coordinator = FakeCoordinator()
        entry = _make_entry()
        entry.runtime_data = coordinator

        added: list = []

        with patch("custom_components.chores.sensor.async_get_current_platform"):
            await async_setup_entry(MagicMock(), entry, lambda e, **_: added.extend(e))

        types = {type(e) for e in added}
        assert types == {
            ChoreSensor,
            ChoreLastCompletedSensor,
            ChoreNextDueSensor,
            ChoreSnoozeUntilSensor,
            ChoreDefaultSnoozeValueSensor,
            ChoreDefaultSnoozeUnitSensor,
        }


class TestChoreSensorState:
    """Tests for ChoreSensor.native_value."""

    def test_state_overdue(self):
        sensor = _make_sensor()
        assert sensor.native_value == "overdue"

    def test_state_done(self):
        sensor = _make_sensor(coordinator=FakeCoordinator(dict(CHORE_STATE_B)))
        assert sensor.native_value == "done"


class TestChoreSensorDeviceInfo:
    """Tests for ChoreSensor.device_info and entity naming (has_entity_name=True)."""

    def test_device_info_name_from_coordinator_data(self):
        sensor = _make_sensor()
        assert sensor.device_info["name"] == "Dishes"

    def test_device_info_name_updates_when_data_changes(self):
        coordinator = FakeCoordinator()
        sensor = _make_sensor(coordinator=coordinator)
        coordinator.data = {**CHORE_STATE, "name": "Plates"}
        assert sensor.device_info["name"] == "Plates"

    def test_device_info_identifiers_contain_entry_id(self):
        from custom_components.chores.const import DOMAIN

        entry = _make_entry(entry_id="my_entry_id")
        sensor = _make_sensor(entry=entry)
        assert (DOMAIN, "my_entry_id") in sensor.device_info["identifiers"]

    def test_has_entity_name_is_true(self):
        sensor = _make_sensor()
        assert sensor.has_entity_name is True


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


class TestChoreLastCompletedSensor:
    def test_native_value(self):
        sensor = _make_last_completed_sensor()
        assert sensor.native_value == date(2026, 6, 1)

    def test_device_class_date(self):
        from homeassistant.components.sensor import SensorDeviceClass

        sensor = _make_last_completed_sensor()
        assert sensor.device_class == SensorDeviceClass.DATE

    def test_entity_category_diagnostic(self):
        sensor = _make_last_completed_sensor()
        assert sensor.entity_category == EntityCategory.DIAGNOSTIC

    def test_unique_id_format(self):
        entry = _make_entry(entry_id="abc")
        sensor = _make_last_completed_sensor(entry=entry)
        assert sensor.unique_id == "abc_last_completed"

    def test_translation_key(self):
        sensor = _make_last_completed_sensor()
        assert sensor.translation_key == "last_completed"

    def test_native_value_none_when_missing(self):
        coordinator = FakeCoordinator({**CHORE_STATE, "last_completed": None})
        sensor = _make_last_completed_sensor(coordinator=coordinator)
        assert sensor.native_value is None


class TestChoreNextDueSensor:
    def test_native_value(self):
        sensor = _make_next_due_sensor()
        assert sensor.native_value == date(2026, 6, 8)

    def test_device_class_timestamp(self):
        from homeassistant.components.sensor import SensorDeviceClass

        sensor = _make_next_due_sensor()
        assert sensor.device_class == SensorDeviceClass.TIMESTAMP

    def test_entity_category_diagnostic(self):
        sensor = _make_next_due_sensor()
        assert sensor.entity_category == EntityCategory.DIAGNOSTIC

    def test_unique_id_format(self):
        entry = _make_entry(entry_id="abc")
        sensor = _make_next_due_sensor(entry=entry)
        assert sensor.unique_id == "abc_next_due"

    def test_translation_key(self):
        sensor = _make_next_due_sensor()
        assert sensor.translation_key == "next_due"


_SNOOZE_DT = datetime(2026, 6, 15, 12, 0, tzinfo=UTC)


class TestChoreSnoozeUntilSensor:
    def test_native_value_none_when_not_snoozed(self):
        sensor = _make_snooze_until_sensor()
        assert sensor.native_value is None

    def test_native_value_when_snoozed(self):
        coordinator = FakeCoordinator({**CHORE_STATE, "snooze_until": _SNOOZE_DT})
        sensor = _make_snooze_until_sensor(coordinator=coordinator)
        assert sensor.native_value == _SNOOZE_DT

    def test_device_class_timestamp(self):
        from homeassistant.components.sensor import SensorDeviceClass

        sensor = _make_snooze_until_sensor()
        assert sensor.device_class == SensorDeviceClass.TIMESTAMP

    def test_entity_category_diagnostic(self):
        sensor = _make_snooze_until_sensor()
        assert sensor.entity_category == EntityCategory.DIAGNOSTIC

    def test_unique_id_format(self):
        entry = _make_entry(entry_id="abc")
        sensor = _make_snooze_until_sensor(entry=entry)
        assert sensor.unique_id == "abc_snooze_until"

    def test_translation_key(self):
        sensor = _make_snooze_until_sensor()
        assert sensor.translation_key == "snooze_until"


class TestChoreDefaultSnoozeValueSensor:
    def test_native_value(self):
        sensor = _make_default_snooze_value_sensor()
        assert sensor.native_value == 1

    def test_native_value_custom(self):
        coordinator = FakeCoordinator({**CHORE_STATE, "default_snooze_value": 5})
        sensor = _make_default_snooze_value_sensor(coordinator=coordinator)
        assert sensor.native_value == 5

    def test_entity_category_diagnostic(self):
        sensor = _make_default_snooze_value_sensor()
        assert sensor.entity_category == EntityCategory.DIAGNOSTIC

    def test_unique_id_format(self):
        entry = _make_entry(entry_id="abc")
        sensor = _make_default_snooze_value_sensor(entry=entry)
        assert sensor.unique_id == "abc_default_snooze_value"

    def test_translation_key(self):
        sensor = _make_default_snooze_value_sensor()
        assert sensor.translation_key == "default_snooze_value"

    def test_native_value_none_when_missing(self):
        coordinator = FakeCoordinator(
            {k: v for k, v in CHORE_STATE.items() if k != "default_snooze_value"}
        )
        sensor = _make_default_snooze_value_sensor(coordinator=coordinator)
        assert sensor.native_value is None


class TestChoreDefaultSnoozeUnitSensor:
    def test_native_value(self):
        sensor = _make_default_snooze_unit_sensor()
        assert sensor.native_value == "days"

    def test_native_value_hours(self):
        coordinator = FakeCoordinator({**CHORE_STATE, "default_snooze_unit": "hours"})
        sensor = _make_default_snooze_unit_sensor(coordinator=coordinator)
        assert sensor.native_value == "hours"

    def test_entity_category_diagnostic(self):
        sensor = _make_default_snooze_unit_sensor()
        assert sensor.entity_category == EntityCategory.DIAGNOSTIC

    def test_unique_id_format(self):
        entry = _make_entry(entry_id="abc")
        sensor = _make_default_snooze_unit_sensor(entry=entry)
        assert sensor.unique_id == "abc_default_snooze_unit"

    def test_translation_key(self):
        sensor = _make_default_snooze_unit_sensor()
        assert sensor.translation_key == "default_snooze_unit"

    def test_native_value_none_when_missing(self):
        coordinator = FakeCoordinator(
            {k: v for k, v in CHORE_STATE.items() if k != "default_snooze_unit"}
        )
        sensor = _make_default_snooze_unit_sensor(coordinator=coordinator)
        assert sensor.native_value is None


class TestDiagnosticSensorDeviceInfo:
    """All diagnostic sensors share the same device as the primary sensor."""

    def test_device_info_matches_primary(self):
        coordinator = FakeCoordinator()
        entry = _make_entry(entry_id="shared")
        primary = _make_sensor(coordinator=coordinator, entry=entry)
        diag = _make_last_completed_sensor(coordinator=coordinator, entry=entry)
        assert primary.device_info["identifiers"] == diag.device_info["identifiers"]
