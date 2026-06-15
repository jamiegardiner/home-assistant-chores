"""Tests for the Chores service helpers and entity service handlers."""

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.util import dt as dt_util

from custom_components.chores.const import SNOOZE_UNITS
from custom_components.chores.sensor import (
    _handle_complete,
    _handle_snooze,
    _handle_unsnooze,
)
from custom_components.chores.services import _parse_snooze_datetime

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
    @pytest.mark.parametrize(
        ("value", "unit"),
        [
            (30, "minutes"),
            (2, "hours"),
            (3, "days"),
            (2, "weeks"),
        ],
    )
    def test_parse_snooze_datetime(self, value: int, unit: str) -> None:
        before = dt_util.now()
        result = _parse_snooze_datetime({"value": value, "unit": unit})
        after = dt_util.now()
        assert (
            before + timedelta(**{unit: value})
            <= result
            <= after + timedelta(**{unit: value})
        )

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
    @pytest.mark.parametrize(
        ("value", "unit"),
        [
            (3, "days"),
            (4, "hours"),
            (1, "weeks"),
        ],
    )
    async def test_calls_coordinator_async_snooze(self, value: int, unit: str) -> None:
        entity = _make_entity()
        before = dt_util.now()
        await _handle_snooze(entity, _make_call({"value": value, "unit": unit}))
        after = dt_util.now()
        entity.coordinator.async_snooze.assert_called_once()
        passed_dt = entity.coordinator.async_snooze.call_args[0][0]
        assert (
            before + timedelta(**{unit: value})
            <= passed_dt
            <= after + timedelta(**{unit: value})
        )


class TestHandleUnsnooze:
    async def test_calls_coordinator_async_unsnooze(self):
        entity = _make_entity()
        await _handle_unsnooze(entity, _make_call({}))
        entity.coordinator.async_unsnooze.assert_called_once_with()
