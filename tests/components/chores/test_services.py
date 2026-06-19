"""Tests for the Chores service helpers and entity service handlers."""

from datetime import timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.chores.const import DOMAIN, SNOOZE_UNITS
from custom_components.chores.sensor import (
    _handle_complete,
    _handle_snooze,
    _handle_snooze_exact,
    _handle_unsnooze,
)
from custom_components.chores.services import _parse_snooze_datetime
from tests.components.chores.helpers import make_entry

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
    entity.coordinator.async_snooze_default = AsyncMock()
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

    async def test_no_params_calls_async_snooze_default(self) -> None:
        entity = _make_entity()
        await _handle_snooze(entity, _make_call({}))
        entity.coordinator.async_snooze_default.assert_called_once_with()
        entity.coordinator.async_snooze.assert_not_called()


class TestHandleSnoozeValidation:
    async def test_out_of_range_value_raises_service_validation_error(self) -> None:
        entity = _make_entity()
        with pytest.raises(ServiceValidationError) as exc_info:
            await _handle_snooze(entity, _make_call({"value": 500, "unit": "days"}))
        assert exc_info.value.translation_key == "snooze_value_out_of_range"

    async def test_zero_value_raises_service_validation_error(self) -> None:
        entity = _make_entity()
        with pytest.raises(ServiceValidationError):
            await _handle_snooze(entity, _make_call({"value": 0, "unit": "days"}))

    async def test_invalid_unit_raises_service_validation_error(self) -> None:
        entity = _make_entity()
        with pytest.raises(ServiceValidationError) as exc_info:
            await _handle_snooze(entity, _make_call({"value": 3, "unit": "fortnights"}))
        assert exc_info.value.translation_key == "invalid_snooze_unit"

    async def test_no_coordinator_call_on_validation_error(self) -> None:
        entity = _make_entity()
        with pytest.raises(ServiceValidationError):
            await _handle_snooze(entity, _make_call({"value": 500, "unit": "days"}))
        entity.coordinator.async_snooze.assert_not_called()

    async def test_value_only_raises_partial_params_error(self) -> None:
        entity = _make_entity()
        with pytest.raises(ServiceValidationError) as exc_info:
            await _handle_snooze(entity, _make_call({"value": 3}))
        assert exc_info.value.translation_key == "snooze_partial_params"
        entity.coordinator.async_snooze.assert_not_called()
        entity.coordinator.async_snooze_default.assert_not_called()

    async def test_unit_only_raises_partial_params_error(self) -> None:
        entity = _make_entity()
        with pytest.raises(ServiceValidationError) as exc_info:
            await _handle_snooze(entity, _make_call({"unit": "days"}))
        assert exc_info.value.translation_key == "snooze_partial_params"
        entity.coordinator.async_snooze.assert_not_called()
        entity.coordinator.async_snooze_default.assert_not_called()


class TestHandleSnoozeExact:
    async def test_naive_datetime_converted_to_aware(self) -> None:
        entity = _make_entity()
        naive = dt_util.now().replace(tzinfo=None)
        await _handle_snooze_exact(entity, _make_call({"snooze_until": naive}))
        entity.coordinator.async_snooze.assert_called_once()
        passed = entity.coordinator.async_snooze.call_args[0][0]
        assert passed.tzinfo is not None

    async def test_aware_datetime_passed_directly(self) -> None:
        entity = _make_entity()
        aware = dt_util.now() + timedelta(hours=3)
        await _handle_snooze_exact(entity, _make_call({"snooze_until": aware}))
        entity.coordinator.async_snooze.assert_called_once_with(aware)


class TestHandleUnsnooze:
    async def test_calls_coordinator_async_unsnooze(self):
        entity = _make_entity()
        await _handle_unsnooze(entity, _make_call({}))
        entity.coordinator.async_unsnooze.assert_called_once_with()


# ---------------------------------------------------------------------------
# End-to-end integration tests — full HA stack via hass.services.async_call
# ---------------------------------------------------------------------------

_TRACK_PATCH = "custom_components.chores.coordinator.async_track_point_in_time"


class TestServiceCallsIntegration:
    @pytest.fixture(autouse=True)
    def auto_enable_custom_integrations(self, enable_custom_integrations: Any) -> None:
        pass

    async def _setup(self, hass: Any) -> tuple[MockConfigEntry, str]:
        entry = make_entry(days_ago=30, interval_value=7)
        entry.add_to_hass(hass)
        with patch(_TRACK_PATCH):
            await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        entity_id = er.async_get(hass).async_get_entity_id(
            "sensor", DOMAIN, entry.entry_id
        )
        return entry, entity_id

    async def test_complete_service_sets_status_done(self, hass: Any) -> None:
        entry, entity_id = await self._setup(hass)
        assert entry.runtime_data.data["status"] == "overdue"

        with patch(_TRACK_PATCH):
            await hass.services.async_call(
                DOMAIN, "complete", {"entity_id": entity_id}, blocking=True
            )

        data = entry.runtime_data.data
        assert data["status"] == "done"
        assert data["last_completed"].date() == dt_util.now().date()

    async def test_complete_service_with_completed_at(self, hass: Any) -> None:
        entry, entity_id = await self._setup(hass)
        past = dt_util.now() - timedelta(hours=2)

        with patch(_TRACK_PATCH):
            await hass.services.async_call(
                DOMAIN,
                "complete",
                {"entity_id": entity_id, "completed_at": past},
                blocking=True,
            )

        last_completed = entry.runtime_data.data["last_completed"]
        assert last_completed is not None
        assert abs((last_completed - past).total_seconds()) < 1

    async def test_snooze_service_default_params(self, hass: Any) -> None:
        entry, entity_id = await self._setup(hass)

        with patch(_TRACK_PATCH):
            await hass.services.async_call(
                DOMAIN, "snooze", {"entity_id": entity_id}, blocking=True
            )

        data = entry.runtime_data.data
        assert data["status"] == "snoozed"
        assert data["snooze_until"] is not None

    async def test_snooze_service_explicit_params(self, hass: Any) -> None:
        entry, entity_id = await self._setup(hass)
        before = dt_util.now()

        with patch(_TRACK_PATCH):
            await hass.services.async_call(
                DOMAIN,
                "snooze",
                {"entity_id": entity_id, "value": 2, "unit": "hours"},
                blocking=True,
            )

        after = dt_util.now()
        snooze_until = entry.runtime_data.data["snooze_until"]
        assert snooze_until is not None
        assert before + timedelta(hours=2) <= snooze_until <= after + timedelta(hours=2)

    async def test_snooze_exact_service(self, hass: Any) -> None:
        entry, entity_id = await self._setup(hass)
        target = dt_util.now() + timedelta(hours=3)

        with patch(_TRACK_PATCH):
            await hass.services.async_call(
                DOMAIN,
                "snooze_exact",
                {"entity_id": entity_id, "snooze_until": target},
                blocking=True,
            )

        snooze_until = entry.runtime_data.data["snooze_until"]
        assert snooze_until is not None
        assert abs((snooze_until - target).total_seconds()) < 1

    async def test_unsnooze_service_clears_snooze(self, hass: Any) -> None:
        snooze_dt = dt_util.now() + timedelta(hours=1)
        entry = make_entry(
            days_ago=30, interval_value=7, snooze_until=snooze_dt.isoformat()
        )
        entry.add_to_hass(hass)
        with patch(_TRACK_PATCH):
            await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        entity_id = er.async_get(hass).async_get_entity_id(
            "sensor", DOMAIN, entry.entry_id
        )

        assert entry.runtime_data.data["status"] == "snoozed"

        with patch(_TRACK_PATCH):
            await hass.services.async_call(
                DOMAIN, "unsnooze", {"entity_id": entity_id}, blocking=True
            )

        data = entry.runtime_data.data
        assert data["snooze_until"] is None
        assert data["status"] == "overdue"
