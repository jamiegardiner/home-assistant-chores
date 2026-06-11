"""Tests for the Chores service helpers and entity service handlers."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util

from custom_components.chores.sensor import (
    _handle_complete,
    _handle_snooze,
    _handle_unsnooze,
)
from custom_components.chores.services import _parse_snooze_until

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
# _parse_snooze_until
# ---------------------------------------------------------------------------


class TestParseSnoozeUntil:
    def test_snooze_days(self):
        today = dt_util.now().date()
        result = _parse_snooze_until({"snooze_days": 3})
        assert result == today + timedelta(days=3)

    def test_snooze_weeks(self):
        today = dt_util.now().date()
        result = _parse_snooze_until({"snooze_weeks": 2})
        assert result == today + timedelta(weeks=2)

    def test_snooze_until_iso(self):
        future = (dt_util.now().date() + timedelta(days=5)).isoformat()
        result = _parse_snooze_until({"snooze_until": future})
        assert result == dt_util.now().date() + timedelta(days=5)

    def test_raises_when_no_param_provided(self):
        with pytest.raises(HomeAssistantError, match="Exactly one"):
            _parse_snooze_until({})

    def test_raises_when_two_params_provided(self):
        with pytest.raises(HomeAssistantError, match="Exactly one"):
            _parse_snooze_until({"snooze_days": 1, "snooze_weeks": 1})

    def test_raises_on_invalid_date_string(self):
        with pytest.raises(HomeAssistantError, match="Invalid snooze_until"):
            _parse_snooze_until({"snooze_until": "not-a-date"})


# ---------------------------------------------------------------------------
# Entity service handlers
# ---------------------------------------------------------------------------


class TestHandleComplete:
    async def test_calls_coordinator_async_complete(self):
        entity = _make_entity()
        await _handle_complete(entity, _make_call({}))
        entity.coordinator.async_complete.assert_called_once_with()

    async def test_complete_second_entity_also_works(self):
        entity = _make_entity()
        await _handle_complete(entity, _make_call({}))
        entity.coordinator.async_complete.assert_called_once_with()


class TestHandleSnooze:
    async def test_calls_coordinator_async_snooze_with_days(self):
        entity = _make_entity()
        today = dt_util.now().date()
        await _handle_snooze(entity, _make_call({"snooze_days": 3}))
        entity.coordinator.async_snooze.assert_called_once_with(
            today + timedelta(days=3)
        )

    async def test_calls_coordinator_async_snooze_with_weeks(self):
        entity = _make_entity()
        today = dt_util.now().date()
        await _handle_snooze(entity, _make_call({"snooze_weeks": 1}))
        entity.coordinator.async_snooze.assert_called_once_with(
            today + timedelta(weeks=1)
        )

    async def test_propagates_validation_error(self):
        entity = _make_entity()
        with pytest.raises(HomeAssistantError):
            await _handle_snooze(entity, _make_call({}))
        entity.coordinator.async_snooze.assert_not_called()


class TestHandleUnsnooze:
    async def test_calls_coordinator_async_unsnooze(self):
        entity = _make_entity()
        await _handle_unsnooze(entity, _make_call({}))
        entity.coordinator.async_unsnooze.assert_called_once_with()
