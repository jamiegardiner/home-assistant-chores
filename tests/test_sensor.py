"""Unit tests for custom_components/chores/sensor.py.

Uses a fake coordinator so there is no dependency on the real coordinator
(issue #4) or on a running Home Assistant instance.
"""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Fake coordinator
# ---------------------------------------------------------------------------

CHORE_A_ID = "chore_dishes"
CHORE_B_ID = "chore_vacuum"

CHORE_A_STATE = {
    "name": "Dishes",
    "status": "overdue",
    "last_completed": date(2026, 6, 1),
    "next_due": date(2026, 6, 8),
}

CHORE_B_STATE = {
    "name": "Vacuum",
    "status": "done",
    "last_completed": date(2026, 6, 5),
    "next_due": date(2026, 6, 12),
}


class FakeCoordinator:
    """Minimal coordinator stub exposing the contract consumed by sensor.py."""

    chore_ids = [CHORE_A_ID, CHORE_B_ID]

    _states = {
        CHORE_A_ID: CHORE_A_STATE,
        CHORE_B_ID: CHORE_B_STATE,
    }

    def chore_state(self, chore_id: str) -> dict:
        return self._states[chore_id]

    # CoordinatorEntity calls these; provide stubs so the entity can initialise.
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


def _make_sensor(chore_id: str, coordinator=None, entry=None):  # -> ChoreSensor
    """Build a ChoreSensor without going through async_setup_entry."""
    from custom_components.chores.sensor import ChoreSensor

    if coordinator is None:
        coordinator = FakeCoordinator()
    if entry is None:
        entry = _make_entry()
    return ChoreSensor(coordinator, entry, chore_id)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAsyncSetupEntry:
    """Tests for async_setup_entry."""

    @pytest.mark.asyncio
    async def test_one_sensor_per_chore(self):
        """async_setup_entry must add exactly one entity per chore_id."""
        from custom_components.chores.sensor import async_setup_entry

        coordinator = FakeCoordinator()
        entry = _make_entry()

        hass = MagicMock()
        hass.data = {"chores": {entry.entry_id: coordinator}}

        added: list = []

        # async_add_entities is called synchronously with a generator in our impl.
        def sync_add(entities, **_kwargs):
            added.extend(list(entities))

        await async_setup_entry(hass, entry, sync_add)

        assert len(added) == 2  # one per chore_id in FakeCoordinator.chore_ids

    @pytest.mark.asyncio
    async def test_setup_entry_uses_correct_domain_key(self):
        """Coordinator is looked up at hass.data[DOMAIN][entry.entry_id]."""
        from custom_components.chores.sensor import async_setup_entry

        coordinator = FakeCoordinator()
        entry = _make_entry(entry_id="my_entry")

        hass = MagicMock()
        hass.data = {"chores": {"my_entry": coordinator}}

        added: list = []

        def sync_add(entities, **_kwargs):
            added.extend(list(entities))

        await async_setup_entry(hass, entry, sync_add)
        assert len(added) == 2


class TestChoreSensorState:
    """Tests for ChoreSensor.native_value."""

    def test_state_overdue(self):
        sensor = _make_sensor(CHORE_A_ID)
        assert sensor.native_value == "overdue"

    def test_state_done(self):
        sensor = _make_sensor(CHORE_B_ID)
        assert sensor.native_value == "done"


class TestChoreSensorAttributes:
    """Tests for ChoreSensor.extra_state_attributes."""

    def test_attributes_last_completed_iso(self):
        sensor = _make_sensor(CHORE_A_ID)
        attrs = sensor.extra_state_attributes
        assert attrs["last_completed"] == "2026-06-01"

    def test_attributes_next_due_iso(self):
        sensor = _make_sensor(CHORE_A_ID)
        attrs = sensor.extra_state_attributes
        assert attrs["next_due"] == "2026-06-08"

    def test_attributes_none_last_completed(self):
        """Never-completed chore: last_completed=None passes through as None."""

        class NeverCompletedCoordinator(FakeCoordinator):
            def chore_state(self, chore_id):
                state = dict(super().chore_state(chore_id))
                state["last_completed"] = None
                return state

        sensor = _make_sensor(CHORE_A_ID, coordinator=NeverCompletedCoordinator())
        assert sensor.extra_state_attributes["last_completed"] is None

    def test_attributes_none_next_due(self):
        """next_due may be None (no schedule configured)."""

        class NoNextDueCoordinator(FakeCoordinator):
            def chore_state(self, chore_id):
                state = dict(super().chore_state(chore_id))
                state["next_due"] = None
                return state

        sensor = _make_sensor(CHORE_A_ID, coordinator=NoNextDueCoordinator())
        assert sensor.extra_state_attributes["next_due"] is None


class TestChoreSensorUniqueId:
    """Tests for stable unique_id."""

    def test_unique_id_format(self):
        entry = _make_entry(entry_id="cfg_entry_abc")
        sensor = _make_sensor(CHORE_A_ID, entry=entry)
        assert sensor.unique_id == f"cfg_entry_abc_{CHORE_A_ID}"

    def test_unique_id_differs_per_chore(self):
        entry = _make_entry(entry_id="cfg_entry_abc")
        sensor_a = _make_sensor(CHORE_A_ID, entry=entry)
        sensor_b = _make_sensor(CHORE_B_ID, entry=entry)
        assert sensor_a.unique_id != sensor_b.unique_id

    def test_unique_id_stable_across_instances(self):
        """Same entry_id + chore_id must produce the same unique_id."""
        entry = _make_entry(entry_id="stable_entry")
        s1 = _make_sensor(CHORE_A_ID, entry=entry)
        s2 = _make_sensor(CHORE_A_ID, entry=entry)
        assert s1.unique_id == s2.unique_id


class TestChoreSensorSuggestedObjectId:
    """Tests for suggested_object_id (controls HA entity_id on first registration)."""

    def test_suggested_object_id_format(self):
        sensor = _make_sensor(CHORE_A_ID)
        assert sensor.suggested_object_id == f"chore_{CHORE_A_ID}"

    def test_suggested_object_id_differs_per_chore(self):
        sensor_a = _make_sensor(CHORE_A_ID)
        sensor_b = _make_sensor(CHORE_B_ID)
        assert sensor_a.suggested_object_id != sensor_b.suggested_object_id


class TestChoreSensorName:
    """Tests for entity name (set from chore display name)."""

    def test_name_from_coordinator(self):
        sensor = _make_sensor(CHORE_A_ID)
        assert sensor.name == "Dishes"

    def test_name_second_chore(self):
        sensor = _make_sensor(CHORE_B_ID)
        assert sensor.name == "Vacuum"


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
