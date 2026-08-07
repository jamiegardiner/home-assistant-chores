"""Tests for coordinator async_complete and notification_time behaviour."""

from datetime import datetime, timedelta
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util

from tests.components.chores.helpers import make_entry, setup_coord

# ---------------------------------------------------------------------------
# async_complete tests
# ---------------------------------------------------------------------------


async def test_complete_resets_to_done(hass: Any) -> None:
    """async_complete sets last_completed to today, status to done."""
    entry = make_entry(days_ago=30, interval_value=7)
    entry.add_to_hass(hass)
    coord = await setup_coord(hass, entry)

    assert coord.data["status"] == "overdue"
    await coord.async_complete()

    assert coord.data["status"] == "done"
    assert coord.data["last_completed"].date() == dt_util.now().date()
    assert coord.data["next_due"] > datetime.now(tz=dt_util.now().tzinfo)


async def test_complete_persists_to_entry_options(hass: Any) -> None:
    """async_complete writes last_completed to entry.options."""
    entry = make_entry(days_ago=30, interval_value=7)
    entry.add_to_hass(hass)
    coord = await setup_coord(hass, entry)
    await coord.async_complete()

    persisted = entry.options["last_completed"]
    assert datetime.fromisoformat(persisted).tzinfo is not None
    assert datetime.fromisoformat(persisted).date() == dt_util.now().date()
    assert entry.options["snooze_until"] is None

    persisted_next_due = entry.options["next_due"]
    assert datetime.fromisoformat(persisted_next_due) == coord.data["next_due"]


async def test_completing_never_completed_chore_starts_cycle(hass: Any) -> None:
    """Completing a never-completed chore sets last_completed, next_due, and status done."""
    entry = make_entry(last_completed=None, interval_value=7)
    entry.add_to_hass(hass)
    coord = await setup_coord(hass, entry)

    assert coord.data["status"] == "overdue"
    await coord.async_complete()

    assert coord.data["status"] == "done"
    assert coord.data["last_completed"] is not None
    assert coord.data["last_completed"].date() == dt_util.now().date()
    expected_next_due = dt_util.now().date() + timedelta(days=7)
    assert coord.data["next_due"].date() == expected_next_due


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

    entry = make_entry(days_ago=0, interval_value=7)
    entry.add_to_hass(hass)
    coord = await setup_coord(hass, entry)
    assert len(cancel_mocks) == 1
    first_cancel = cancel_mocks[0]

    await coord.async_complete()

    first_cancel.assert_called_once()


# ---------------------------------------------------------------------------
# async_complete with completed_at tests
# ---------------------------------------------------------------------------


async def test_complete_with_explicit_completed_at(hass: Any) -> None:
    """async_complete with a past datetime stores that datetime."""
    entry = make_entry(days_ago=30, interval_value=7)
    entry.add_to_hass(hass)
    coord = await setup_coord(hass, entry)

    past_dt = dt_util.now() - timedelta(hours=3)
    await coord.async_complete(past_dt)

    assert coord.data["last_completed"] == past_dt
    assert coord.data["status"] == "done"


async def test_complete_future_completed_at_raises(hass: Any) -> None:
    """async_complete with a future datetime raises HomeAssistantError."""
    entry = make_entry(days_ago=30, interval_value=7)
    entry.add_to_hass(hass)
    coord = await setup_coord(hass, entry)

    original_last = coord.data["last_completed"]
    future_dt = dt_util.now() + timedelta(hours=1)

    with pytest.raises(HomeAssistantError) as exc_info:
        await coord.async_complete(future_dt)

    assert exc_info.value.translation_key == "completed_at_in_future"
    assert coord.data["last_completed"] == original_last


async def test_last_completed_is_datetime_not_date(hass: Any) -> None:
    """Snapshot last_completed is a datetime, not a date."""
    entry = make_entry(days_ago=0, interval_value=7)
    entry.add_to_hass(hass)
    coord = await setup_coord(hass, entry)
    assert isinstance(coord.data["last_completed"], datetime)


async def test_complete_persists_tz_aware_datetime(hass: Any) -> None:
    """async_complete stores a tz-aware ISO datetime string in entry.options."""
    entry = make_entry(days_ago=30, interval_value=7)
    entry.add_to_hass(hass)
    coord = await setup_coord(hass, entry)
    await coord.async_complete()

    stored = entry.options["last_completed"]
    parsed = datetime.fromisoformat(stored)
    assert parsed.tzinfo is not None


# ---------------------------------------------------------------------------
# notification_time tests
# ---------------------------------------------------------------------------


async def test_next_due_at_notification_time(hass: Any) -> None:
    """next_due is at notification_time on the due date, not midnight."""
    entry = make_entry(days_ago=0, interval_value=7, notification_time="08:00")
    entry.add_to_hass(hass)
    coord = await setup_coord(hass, entry)

    next_due = coord.data["next_due"]
    assert next_due.hour == 8
    assert next_due.minute == 0
    expected_date = dt_util.now().date() + timedelta(days=7)
    assert next_due.date() == expected_date


async def test_next_due_default_notification_time_is_midnight(hass: Any) -> None:
    """notification_time 00:00 gives midnight next_due."""
    entry = make_entry(days_ago=0, interval_value=7, notification_time="00:00")
    entry.add_to_hass(hass)
    coord = await setup_coord(hass, entry)

    next_due = coord.data["next_due"]
    assert next_due.hour == 0
    assert next_due.minute == 0


async def test_ha_starts_before_notification_time_is_done(hass: Any) -> None:
    """Chore is done when HA starts before notification_time on the due date."""
    # Compute times in local tz so the test is timezone-independent.
    today_midnight = dt_util.start_of_local_day(dt_util.now())
    last_completed = (today_midnight - timedelta(days=7)).isoformat()
    before_notification = today_midnight + timedelta(hours=7)  # 07:00 local < 08:00

    entry = make_entry(last_completed=last_completed, notification_time="08:00")
    entry.add_to_hass(hass)

    with patch(
        "custom_components.chores.coordinator.dt_util.now",
        return_value=before_notification,
    ):
        coord = await setup_coord(hass, entry)

    assert coord.data["status"] == "done"


async def test_ha_starts_after_notification_time_is_overdue(hass: Any) -> None:
    """Chore is overdue when HA starts after notification_time on the due date."""
    today_midnight = dt_util.start_of_local_day(dt_util.now())
    last_completed = (today_midnight - timedelta(days=7)).isoformat()
    after_notification = today_midnight + timedelta(hours=9)  # 09:00 local > 08:00

    entry = make_entry(last_completed=last_completed, notification_time="08:00")
    entry.add_to_hass(hass)

    with patch(
        "custom_components.chores.coordinator.dt_util.now",
        return_value=after_notification,
    ):
        coord = await setup_coord(hass, entry)

    assert coord.data["status"] == "overdue"


async def test_snooze_timer_fires_at_snooze_until_regardless_of_notification_time(
    hass: Any, patch_track: MagicMock
) -> None:
    """The snooze-expiry timer fires at snooze_until, not at notification_time."""
    timer_points: list[datetime] = []

    def _fake_track(hass_: Any, cb: Any, point_in_time: Any) -> MagicMock:
        timer_points.append(point_in_time)
        return MagicMock()

    patch_track.side_effect = _fake_track

    entry = make_entry(days_ago=30, interval_value=7, notification_time="08:00")
    entry.add_to_hass(hass)
    coord = await setup_coord(hass, entry)

    snooze_dt = dt_util.now() + timedelta(minutes=30)
    await coord.async_snooze(snooze_dt)

    assert timer_points[-1] == snooze_dt


async def test_notification_time_in_snapshot(hass: Any) -> None:
    """notification_time is included in the coordinator snapshot."""
    entry = make_entry(days_ago=0, interval_value=7, notification_time="08:30")
    entry.add_to_hass(hass)
    coord = await setup_coord(hass, entry)
    assert coord.data["notification_time"] == "08:30"
