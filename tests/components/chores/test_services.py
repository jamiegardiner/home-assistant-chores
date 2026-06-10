"""Tests for the Chores service helpers and entity service handlers."""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.exceptions import HomeAssistantError

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


def _make_entity(chore_id: str) -> MagicMock:
    entity = MagicMock()
    entity._chore_id = chore_id
    entity._chores_coordinator = MagicMock()
    entity._chores_coordinator.async_complete = AsyncMock()
    entity._chores_coordinator.async_snooze = AsyncMock()
    entity._chores_coordinator.async_unsnooze = AsyncMock()
    return entity


# ---------------------------------------------------------------------------
# _parse_snooze_until
# ---------------------------------------------------------------------------


class TestParseSnoozeUntil:
    def test_snooze_days(self):
        today = date.today()
        result = _parse_snooze_until({"snooze_days": 3})
        assert result == today + timedelta(days=3)

    def test_snooze_weeks(self):
        today = date.today()
        result = _parse_snooze_until({"snooze_weeks": 2})
        assert result == today + timedelta(weeks=2)

    def test_snooze_until_iso(self):
        future = (date.today() + timedelta(days=5)).isoformat()
        result = _parse_snooze_until({"snooze_until": future})
        assert result == date.fromisoformat(future)

    def test_raises_when_no_param_provided(self):
        with pytest.raises(HomeAssistantError, match="Exactly one"):
            _parse_snooze_until({})

    def test_raises_when_two_params_provided(self):
        with pytest.raises(HomeAssistantError, match="Exactly one"):
            _parse_snooze_until({"snooze_days": 1, "snooze_weeks": 1})

    def test_raises_when_snooze_until_is_today(self):
        today = date.today().isoformat()
        with pytest.raises(HomeAssistantError, match="future date"):
            _parse_snooze_until({"snooze_until": today})

    def test_raises_when_snooze_until_is_past(self):
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        with pytest.raises(HomeAssistantError, match="future date"):
            _parse_snooze_until({"snooze_until": yesterday})

    def test_raises_on_invalid_date_string(self):
        with pytest.raises(HomeAssistantError, match="Invalid snooze_until"):
            _parse_snooze_until({"snooze_until": "not-a-date"})


# ---------------------------------------------------------------------------
# Entity service handlers
# ---------------------------------------------------------------------------


class TestHandleComplete:
    @pytest.mark.asyncio
    async def test_calls_coordinator_async_complete(self):
        entity = _make_entity("dishes")
        await _handle_complete(entity, _make_call({}))
        entity._chores_coordinator.async_complete.assert_called_once_with("dishes")

    @pytest.mark.asyncio
    async def test_uses_entity_chore_id(self):
        entity = _make_entity("vacuum")
        await _handle_complete(entity, _make_call({}))
        entity._chores_coordinator.async_complete.assert_called_once_with("vacuum")


class TestHandleSnooze:
    @pytest.mark.asyncio
    async def test_calls_coordinator_async_snooze_with_days(self):
        entity = _make_entity("dishes")
        today = date.today()
        await _handle_snooze(entity, _make_call({"snooze_days": 3}))
        entity._chores_coordinator.async_snooze.assert_called_once_with(
            "dishes", today + timedelta(days=3)
        )

    @pytest.mark.asyncio
    async def test_calls_coordinator_async_snooze_with_weeks(self):
        entity = _make_entity("vacuum")
        today = date.today()
        await _handle_snooze(entity, _make_call({"snooze_weeks": 1}))
        entity._chores_coordinator.async_snooze.assert_called_once_with(
            "vacuum", today + timedelta(weeks=1)
        )

    @pytest.mark.asyncio
    async def test_propagates_validation_error(self):
        entity = _make_entity("dishes")
        with pytest.raises(HomeAssistantError):
            await _handle_snooze(entity, _make_call({}))
        entity._chores_coordinator.async_snooze.assert_not_called()


class TestHandleUnsnooze:
    @pytest.mark.asyncio
    async def test_calls_coordinator_async_unsnooze(self):
        entity = _make_entity("dishes")
        await _handle_unsnooze(entity, _make_call({}))
        entity._chores_coordinator.async_unsnooze.assert_called_once_with("dishes")

    @pytest.mark.asyncio
    async def test_uses_entity_chore_id(self):
        entity = _make_entity("vacuum")
        await _handle_unsnooze(entity, _make_call({}))
        entity._chores_coordinator.async_unsnooze.assert_called_once_with("vacuum")
