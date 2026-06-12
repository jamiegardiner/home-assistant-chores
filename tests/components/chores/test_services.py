"""Tests for the Chores service helpers and entity service handlers."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock

from homeassistant.util import dt as dt_util

from custom_components.chores.sensor import (
    _handle_complete,
    _handle_snooze,
    _handle_unsnooze,
)
from custom_components.chores.services import SNOOZE_UNITS, _parse_snooze_datetime

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_call(data: dict) -> MagicMock:
    call = MagicMock()
    call.data = data
    return call


def _make_entity() -> MagicMock:
    entity = MagicMock()
    entity.coordinator = MagicMock()
    entity.coordinator.async_complete = AsyncMock()
    entity.coordinator.async_snooze = AsyncMock()
    entity.coordinator.async_unsnooze = AsyncMock()
    return entity


# ---------------------------------------------------------------------------
# _parse_snooze_datetime
# ---------------------------------------------------------------------------


class TestParseSnoozeDateTime:
    def test_minutes(self):
        before = dt_util.now()
        result = _parse_snooze_datetime({"value": 30, "unit": "minutes"})
        after = dt_util.now()
        assert before + timedelta(minutes=30) <= result <= after + timedelta(minutes=30)

    def test_hours(self):
        before = dt_util.now()
        result = _parse_snooze_datetime({"value": 2, "unit": "hours"})
        after = dt_util.now()
        assert before + timedelta(hours=2) <= result <= after + timedelta(hours=2)

    def test_days(self):
        before = dt_util.now()
        result = _parse_snooze_datetime({"value": 3, "unit": "days"})
        after = dt_util.now()
        assert before + timedelta(days=3) <= result <= after + timedelta(days=3)

    def test_weeks(self):
        before = dt_util.now()
        result = _parse_snooze_datetime({"value": 2, "unit": "weeks"})
        after = dt_util.now()
        assert before + timedelta(weeks=2) <= result <= after + timedelta(weeks=2)

    def test_all_units_are_covered(self):
        """Every unit in SNOOZE_UNITS must produce a valid future datetime."""
        for unit in SNOOZE_UNITS:
            result = _parse_snooze_datetime({"value": 1, "unit": unit})
            assert result > dt_util.now()


# ---------------------------------------------------------------------------
# Entity service handlers
# ---------------------------------------------------------------------------


class TestHandleComplete:
    async def test_calls_coordinator_async_complete_no_completed_at(self):
        """Calling complete without completed_at passes None to the coordinator."""
        entity = _make_entity()
        await _handle_complete(entity, _make_call({}))
        entity.coordinator.async_complete.assert_called_once_with(None)

    async def test_calls_coordinator_async_complete_with_completed_at(self):
        """Calling complete with a past completed_at passes the datetime to the coordinator.

        cv.datetime in the schema converts the string before the handler fires,
        so the handler receives a datetime object (possibly naive from YAML automations).
        """
        entity = _make_entity()
        past = dt_util.now() - timedelta(hours=2)
        await _handle_complete(entity, _make_call({"completed_at": past}))
        entity.coordinator.async_complete.assert_called_once()
        passed = entity.coordinator.async_complete.call_args[0][0]
        assert passed is not None
        assert passed.tzinfo is not None
        assert abs((passed - past).total_seconds()) < 1

    async def test_complete_second_entity_also_works(self):
        entity = _make_entity()
        await _handle_complete(entity, _make_call({}))
        entity.coordinator.async_complete.assert_called_once_with(None)


class TestHandleSnooze:
    async def test_calls_coordinator_async_snooze_with_days(self):
        entity = _make_entity()
        before = dt_util.now()
        await _handle_snooze(entity, _make_call({"value": 3, "unit": "days"}))
        after = dt_util.now()
        entity.coordinator.async_snooze.assert_called_once()
        passed_dt = entity.coordinator.async_snooze.call_args[0][0]
        assert before + timedelta(days=3) <= passed_dt <= after + timedelta(days=3)

    async def test_calls_coordinator_async_snooze_with_hours(self):
        entity = _make_entity()
        before = dt_util.now()
        await _handle_snooze(entity, _make_call({"value": 4, "unit": "hours"}))
        after = dt_util.now()
        entity.coordinator.async_snooze.assert_called_once()
        passed_dt = entity.coordinator.async_snooze.call_args[0][0]
        assert before + timedelta(hours=4) <= passed_dt <= after + timedelta(hours=4)

    async def test_calls_coordinator_async_snooze_with_weeks(self):
        entity = _make_entity()
        before = dt_util.now()
        await _handle_snooze(entity, _make_call({"value": 1, "unit": "weeks"}))
        after = dt_util.now()
        entity.coordinator.async_snooze.assert_called_once()
        passed_dt = entity.coordinator.async_snooze.call_args[0][0]
        assert before + timedelta(weeks=1) <= passed_dt <= after + timedelta(weeks=1)


class TestHandleUnsnooze:
    async def test_calls_coordinator_async_unsnooze(self):
        entity = _make_entity()
        await _handle_unsnooze(entity, _make_call({}))
        entity.coordinator.async_unsnooze.assert_called_once_with()
