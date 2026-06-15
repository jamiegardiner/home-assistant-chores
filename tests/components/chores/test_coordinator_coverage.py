"""Tests for timer-reschedule guard branches and _parse_aware_datetime."""

from datetime import UTC, datetime, timedelta
from typing import Any, cast
from unittest.mock import MagicMock

from homeassistant.util import dt as dt_util

from custom_components.chores.coordinator import _parse_aware_datetime
from tests.components.chores.conftest import _make_entry, _setup_coord

# ---------------------------------------------------------------------------
# _parse_aware_datetime tests
# ---------------------------------------------------------------------------


def test_parse_aware_datetime_type_error_returns_none() -> None:
    """A non-string value triggers TypeError in fromisoformat and returns None."""
    result = _parse_aware_datetime(cast(str, 42))
    assert result is None


# ---------------------------------------------------------------------------
# Timer-reschedule branch tests
# ---------------------------------------------------------------------------


async def test_complete_while_timer_live_cancels_prior_timer(
    hass: Any, patch_track: MagicMock
) -> None:
    """Completing a done chore cancels the existing overdue timer before scheduling a new one."""
    cancel_mocks: list[MagicMock] = []

    def _side_effect(hass_: Any, cb: Any, point_in_time: Any) -> MagicMock:
        cancel = MagicMock()
        cancel_mocks.append(cancel)
        return cancel

    patch_track.side_effect = _side_effect

    entry = _make_entry(days_ago=0, interval_days=7)
    entry.add_to_hass(hass)
    coord = await _setup_coord(hass, entry)
    assert len(cancel_mocks) == 1
    first_cancel = cancel_mocks[0]

    await coord.async_complete()

    first_cancel.assert_called_once()


async def test_snooze_while_timer_live_cancels_overdue_timer(
    hass: Any, patch_track: MagicMock
) -> None:
    """Snoozing a done chore cancels the live overdue timer before scheduling the snooze timer."""
    cancel_mocks: list[MagicMock] = []

    def _side_effect(hass_: Any, cb: Any, point_in_time: Any) -> MagicMock:
        cancel = MagicMock()
        cancel_mocks.append(cancel)
        return cancel

    patch_track.side_effect = _side_effect

    entry = _make_entry(days_ago=0, interval_days=7)
    entry.add_to_hass(hass)
    coord = await _setup_coord(hass, entry)
    first_cancel = cancel_mocks[0]

    await coord.async_snooze(dt_util.now() + timedelta(days=1))

    first_cancel.assert_called_once()


async def test_overdue_callback_noop_after_shutdown(
    hass: Any, fake_track: dict[str, Any]
) -> None:
    """Timer callback is a no-op when coordinator runtime is torn down."""
    entry = _make_entry(days_ago=0, interval_days=7)
    entry.add_to_hass(hass)
    coord = await _setup_coord(hass, entry)
    cb = fake_track["cb"]

    coord._runtime = None
    cb(datetime.now(tz=UTC))  # must not raise


# ---------------------------------------------------------------------------
# Snooze-reschedule branch tests
# ---------------------------------------------------------------------------


async def test_snooze_reschedule_cancels_prior_snooze_timer(
    hass: Any, patch_track: MagicMock
) -> None:
    """Snoozing twice cancels the first snooze timer before scheduling the replacement."""
    cancel_mocks: list[MagicMock] = []

    def _side_effect(hass_: Any, cb: Any, point_in_time: Any) -> MagicMock:
        cancel = MagicMock()
        cancel_mocks.append(cancel)
        return cancel

    patch_track.side_effect = _side_effect

    entry = _make_entry(days_ago=30, interval_days=7)
    entry.add_to_hass(hass)
    coord = await _setup_coord(hass, entry)

    await coord.async_snooze(dt_util.now() + timedelta(days=1))
    first_snooze_cancel = cancel_mocks[-1]

    await coord.async_snooze(dt_util.now() + timedelta(days=2))

    first_snooze_cancel.assert_called_once()


async def test_snooze_expiry_callback_noop_after_shutdown(
    hass: Any, fake_track: dict[str, Any]
) -> None:
    """Snooze expiry callback is a no-op when coordinator runtime is torn down."""
    entry = _make_entry(days_ago=30, interval_days=7)
    entry.add_to_hass(hass)
    coord = await _setup_coord(hass, entry)

    await coord.async_snooze(dt_util.now() + timedelta(days=1))
    cb = fake_track["cb"]

    coord._runtime = None
    cb(datetime.now(tz=UTC))  # must not raise


async def test_schedule_snooze_returns_early_when_snooze_until_is_none(
    hass: Any,
) -> None:
    """_schedule_snooze is a no-op when snooze_until is None."""
    entry = _make_entry(days_ago=30, interval_days=7)
    entry.add_to_hass(hass)
    coord = await _setup_coord(hass, entry)
    assert coord._runtime is not None
    coord._runtime.snooze_until = None
    coord._schedule_snooze(
        coord._runtime
    )  # must not raise and must not schedule a timer


async def test_schedule_snooze_returns_early_when_snooze_until_in_past(
    hass: Any,
) -> None:
    """_schedule_snooze is a no-op when snooze_until is already in the past."""
    entry = _make_entry(days_ago=30, interval_days=7)
    entry.add_to_hass(hass)
    coord = await _setup_coord(hass, entry)
    assert coord._runtime is not None
    coord._runtime.snooze_until = dt_util.now() - timedelta(hours=1)
    coord._schedule_snooze(
        coord._runtime
    )  # must not raise and must not schedule a timer
