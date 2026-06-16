"""Tests for coordinator initialization, status computation, and async_update_config."""

from datetime import UTC, date, datetime, timedelta
from typing import Any
from unittest.mock import MagicMock, patch

from homeassistant.util import dt as dt_util

from tests.components.chores.helpers import make_entry, setup_coord

# ---------------------------------------------------------------------------
# Coordinator tests
# ---------------------------------------------------------------------------


async def test_initial_status_overdue(hass: Any) -> None:
    """Chore last completed 30 days ago with 7-day interval is overdue."""
    entry = make_entry(days_ago=30, interval_days=7)
    entry.add_to_hass(hass)
    coord = await setup_coord(hass, entry)
    assert coord.data["status"] == "overdue"


async def test_initial_status_done(hass: Any) -> None:
    """Chore last completed today with 7-day interval is done."""
    entry = make_entry(days_ago=0, interval_days=7)
    entry.add_to_hass(hass)
    coord = await setup_coord(hass, entry)
    assert coord.data["status"] == "done"


async def test_next_due_computed_correctly(hass: Any) -> None:
    """next_due is last_completed + interval, expressed as start of that local day."""
    entry = make_entry(days_ago=0, interval_days=7)
    entry.add_to_hass(hass)
    coord = await setup_coord(hass, entry)
    expected_date = dt_util.now().date() + timedelta(days=7)
    assert coord.data["next_due"].date() == expected_date


async def test_timer_fires_overdue_transition(
    hass: Any, fake_track: dict[str, Any]
) -> None:
    """When the scheduled timer fires, status transitions to overdue."""
    entry = make_entry(days_ago=0, interval_days=7)
    entry.add_to_hass(hass)
    coord = await setup_coord(hass, entry)

    assert coord.data["status"] == "done"
    assert "cb" in fake_track

    future = datetime.now(tz=UTC) + timedelta(days=8)
    with patch("custom_components.chores.coordinator.dt_util.now", return_value=future):
        fake_track["cb"](future)

    assert coord.data["status"] == "overdue"


async def test_complete_resets_to_done(hass: Any) -> None:
    """async_complete sets last_completed to today, status to done."""
    entry = make_entry(days_ago=30, interval_days=7)
    entry.add_to_hass(hass)
    coord = await setup_coord(hass, entry)

    assert coord.data["status"] == "overdue"
    await coord.async_complete()

    assert coord.data["status"] == "done"
    assert coord.data["last_completed"].date() == dt_util.now().date()
    assert coord.data["next_due"] > datetime.now(tz=UTC)


async def test_complete_persists_to_entry_options(hass: Any) -> None:
    """async_complete writes last_completed to entry.options."""
    entry = make_entry(days_ago=30, interval_days=7)
    entry.add_to_hass(hass)
    coord = await setup_coord(hass, entry)
    await coord.async_complete()

    persisted = entry.options["last_completed"]
    assert datetime.fromisoformat(persisted).tzinfo is not None
    assert datetime.fromisoformat(persisted).date() == dt_util.now().date()
    assert entry.options["snooze_until"] is None


async def test_last_completed_survives_restart(hass: Any) -> None:
    """After completing, a new coordinator reads last_completed from entry.options."""
    entry = make_entry(days_ago=30, interval_days=7)
    entry.add_to_hass(hass)
    coord = await setup_coord(hass, entry)
    await coord.async_complete()
    completion_date = coord.data["last_completed"]

    coord2 = await setup_coord(hass, entry)

    assert coord2.data["last_completed"] == completion_date
    assert coord2.data["status"] == "done"


async def test_unload_cancels_timers(hass: Any, patch_track: MagicMock) -> None:
    """async_shutdown_timers cancels all scheduled callbacks."""
    cancel_mocks: list[MagicMock] = []

    def _fake_track(hass_: Any, cb: Any, point_in_time: Any) -> MagicMock:
        cancel = MagicMock()
        cancel_mocks.append(cancel)
        return cancel

    patch_track.side_effect = _fake_track

    entry = make_entry(days_ago=0, interval_days=7)
    entry.add_to_hass(hass)
    coord = await setup_coord(hass, entry)

    assert len(cancel_mocks) >= 1
    coord.async_shutdown_timers()
    for mock in cancel_mocks:
        mock.assert_called_once()


# ---------------------------------------------------------------------------
# async_update_config tests
# ---------------------------------------------------------------------------


async def test_update_config_recomputes_from_preserved_last_completed(
    hass: Any,
) -> None:
    """Changing interval recomputes next_due from the existing last_completed, not today."""
    last_completed_date = dt_util.now().date() - timedelta(days=7)
    entry = make_entry(days_ago=7, interval_days=7)
    entry.add_to_hass(hass)
    coord = await setup_coord(hass, entry)

    assert coord.data["status"] == "overdue"

    new_opts = {
        **dict(entry.options),
        "interval_days": 14,
    }
    await coord.async_update_config(new_opts)

    assert coord.data["last_completed"].date() == last_completed_date
    expected_next_due = last_completed_date + timedelta(days=14)
    assert coord.data["next_due"].date() == expected_next_due
    assert coord.data["status"] == "done"


async def test_update_config_name_change_no_status_change(hass: Any) -> None:
    """Editing the name does not change status or next_due."""
    entry = make_entry(name="Bins", days_ago=0, interval_days=7)
    entry.add_to_hass(hass)
    coord = await setup_coord(hass, entry)

    original_status = coord.data["status"]
    original_next_due = coord.data["next_due"]

    new_opts = {**dict(entry.options), "name": "Wheelie Bins"}
    await coord.async_update_config(new_opts)

    assert coord.data["name"] == "Wheelie Bins"
    assert coord.data["status"] == original_status
    assert coord.data["next_due"] == original_next_due


async def test_update_config_preserves_snooze(hass: Any) -> None:
    """async_update_config preserves snooze_until when options still carry it."""
    snooze_dt = dt_util.now() + timedelta(days=3)
    entry = make_entry(days_ago=30, interval_days=7, snooze_until=snooze_dt.isoformat())
    entry.add_to_hass(hass)
    coord = await setup_coord(hass, entry)

    assert coord.data["status"] == "snoozed"

    new_opts = {**dict(entry.options), "name": "Renamed Chore"}
    await coord.async_update_config(new_opts)

    assert coord.data["status"] == "snoozed"
    assert coord.data["snooze_until"] == snooze_dt


async def test_update_config_expired_snooze_cleared_from_entry_options(
    hass: Any,
) -> None:
    """An expired snooze_until is cleared from entry.options during async_update_config.

    The expired snooze is injected after async_initialize so that async_initialize's
    own issue-114 guard does not pre-clear it before async_update_config runs.
    """
    entry = make_entry(days_ago=30, interval_days=7)
    entry.add_to_hass(hass)
    coord = await setup_coord(hass, entry)

    expired_dt = dt_util.now() - timedelta(hours=1)
    hass.config_entries.async_update_entry(
        entry,
        options={**dict(entry.options), "snooze_until": expired_dt.isoformat()},
    )

    new_opts = {**dict(entry.options), "name": "Renamed Chore"}
    await coord.async_update_config(new_opts)

    assert coord.data["snooze_until"] is None
    assert entry.options["snooze_until"] is None


async def test_update_config_noop_when_options_match_runtime(
    hass: Any, patch_track: MagicMock
) -> None:
    """async_update_config early-returns when options already match runtime state."""
    entry = make_entry(days_ago=0, interval_days=7)
    entry.add_to_hass(hass)
    coord = await setup_coord(hass, entry)
    call_count_after_init = patch_track.call_count

    await coord.async_update_config(dict(entry.options))

    assert patch_track.call_count == call_count_after_init


async def test_next_due_dst_spring_forward(hass: Any) -> None:
    """next_due is correctly offset-aware when it falls on a DST spring-forward day.

    America/New_York springs forward on 2024-03-10 (2am -> 3am, EST -> EDT).
    last_completed 7 days prior places next_due exactly on the transition date.
    """
    await hass.config.async_set_time_zone("America/New_York")

    last_completed_dt = datetime(2024, 3, 3, 12, 0, 0, tzinfo=UTC)
    entry = make_entry(
        interval_days=7,
        notification_time="08:00",
        last_completed=last_completed_dt.isoformat(),
    )
    entry.add_to_hass(hass)
    coord = await setup_coord(hass, entry)

    next_due = coord.data["next_due"]
    assert next_due is not None
    assert next_due.tzinfo is not None
    local_next_due = dt_util.as_local(next_due)
    assert local_next_due.date() == date(2024, 3, 10)
    assert local_next_due.hour == 8
    assert local_next_due.minute == 0
