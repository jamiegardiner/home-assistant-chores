"""Tests for the Chores coordinator (single-chore-per-entry model)."""

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.chores.const import DOMAIN
from custom_components.chores.coordinator import ChoresCoordinator

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_entry(
    name: str = "Bins",
    interval_days: int = 7,
    default_snooze_value: int = 1,
    default_snooze_unit: str = "days",
    notification_time: str = "00:00",
    days_ago: int = 0,
    snooze_until: str | None = None,
    entry_id: str = "test_entry_id",
    last_completed: str | None = "auto",
) -> MockConfigEntry:
    """Return a single-chore MockConfigEntry.

    Pass last_completed=None for a never-completed chore; omit (default "auto") to
    derive last_completed from days_ago.
    """
    if last_completed == "auto":
        last_completed = (dt_util.now() - timedelta(days=days_ago)).isoformat()
    opts: dict[str, Any] = {
        "name": name,
        "interval_days": interval_days,
        "default_snooze_value": default_snooze_value,
        "default_snooze_unit": default_snooze_unit,
        "notification_time": notification_time,
        "last_completed": last_completed,
        "snooze_until": snooze_until,
    }
    return MockConfigEntry(domain=DOMAIN, entry_id=entry_id, options=opts)


# ---------------------------------------------------------------------------
# Coordinator tests
# ---------------------------------------------------------------------------


async def test_initial_status_overdue(hass: Any) -> None:
    """Chore last completed 30 days ago with 7-day interval is overdue."""
    entry = _make_entry(days_ago=30, interval_days=7)
    entry.add_to_hass(hass)

    with patch("custom_components.chores.coordinator.async_track_point_in_time"):
        coord = ChoresCoordinator(hass, entry)
        await coord.async_initialize()

    assert coord.data["status"] == "overdue"


async def test_initial_status_done(hass: Any) -> None:
    """Chore last completed today with 7-day interval is done."""
    entry = _make_entry(days_ago=0, interval_days=7)
    entry.add_to_hass(hass)

    with patch("custom_components.chores.coordinator.async_track_point_in_time"):
        coord = ChoresCoordinator(hass, entry)
        await coord.async_initialize()

    assert coord.data["status"] == "done"


async def test_next_due_computed_correctly(hass: Any) -> None:
    """next_due is last_completed + interval, expressed as start of that local day."""
    entry = _make_entry(days_ago=0, interval_days=7)
    entry.add_to_hass(hass)

    with patch("custom_components.chores.coordinator.async_track_point_in_time"):
        coord = ChoresCoordinator(hass, entry)
        await coord.async_initialize()

    expected_date = dt_util.now().date() + timedelta(days=7)
    assert coord.data["next_due"].date() == expected_date


async def test_timer_fires_overdue_transition(hass: Any) -> None:
    """When the scheduled timer fires, status transitions to overdue."""
    captured: dict[str, Any] = {}

    def _fake_track(hass_, cb, point_in_time):
        captured["cb"] = cb
        return MagicMock()

    entry = _make_entry(days_ago=0, interval_days=7)
    entry.add_to_hass(hass)

    with patch(
        "custom_components.chores.coordinator.async_track_point_in_time",
        side_effect=_fake_track,
    ):
        coord = ChoresCoordinator(hass, entry)
        await coord.async_initialize()

    assert coord.data["status"] == "done"
    assert "cb" in captured

    future = datetime.now(tz=UTC) + timedelta(days=8)
    with patch("custom_components.chores.coordinator.dt_util.now", return_value=future):
        captured["cb"](future)

    assert coord.data["status"] == "overdue"


async def test_complete_resets_to_done(hass: Any) -> None:
    """async_complete sets last_completed to today, status to done."""
    entry = _make_entry(days_ago=30, interval_days=7)
    entry.add_to_hass(hass)

    with patch("custom_components.chores.coordinator.async_track_point_in_time"):
        coord = ChoresCoordinator(hass, entry)
        await coord.async_initialize()

        assert coord.data["status"] == "overdue"
        await coord.async_complete()

    assert coord.data["status"] == "done"
    assert coord.data["last_completed"].date() == dt_util.now().date()
    assert coord.data["next_due"] > datetime.now(tz=UTC)


async def test_complete_persists_to_entry_options(hass: Any) -> None:
    """async_complete writes last_completed to entry.options."""
    entry = _make_entry(days_ago=30, interval_days=7)
    entry.add_to_hass(hass)

    with patch("custom_components.chores.coordinator.async_track_point_in_time"):
        coord = ChoresCoordinator(hass, entry)
        await coord.async_initialize()
        await coord.async_complete()

    persisted = entry.options["last_completed"]
    assert datetime.fromisoformat(persisted).tzinfo is not None
    assert datetime.fromisoformat(persisted).date() == dt_util.now().date()
    assert entry.options["snooze_until"] is None


async def test_last_completed_survives_restart(hass: Any) -> None:
    """After completing, a new coordinator reads last_completed from entry.options."""
    entry = _make_entry(days_ago=30, interval_days=7)
    entry.add_to_hass(hass)

    with patch("custom_components.chores.coordinator.async_track_point_in_time"):
        coord = ChoresCoordinator(hass, entry)
        await coord.async_initialize()
        await coord.async_complete()
        completion_date = coord.data["last_completed"]

        coord2 = ChoresCoordinator(hass, entry)
        await coord2.async_initialize()

    assert coord2.data["last_completed"] == completion_date
    assert coord2.data["status"] == "done"


async def test_unload_cancels_timers(hass: Any) -> None:
    """async_shutdown_timers cancels all scheduled callbacks."""
    cancel_mocks: list[MagicMock] = []

    def _fake_track(hass_, cb, point_in_time):
        cancel = MagicMock()
        cancel_mocks.append(cancel)
        return cancel

    entry = _make_entry(days_ago=0, interval_days=7)
    entry.add_to_hass(hass)

    with patch(
        "custom_components.chores.coordinator.async_track_point_in_time",
        side_effect=_fake_track,
    ):
        coord = ChoresCoordinator(hass, entry)
        await coord.async_initialize()

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
    entry = _make_entry(days_ago=7, interval_days=7)
    entry.add_to_hass(hass)

    with patch("custom_components.chores.coordinator.async_track_point_in_time"):
        coord = ChoresCoordinator(hass, entry)
        await coord.async_initialize()

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
    entry = _make_entry(name="Bins", days_ago=0, interval_days=7)
    entry.add_to_hass(hass)

    with patch("custom_components.chores.coordinator.async_track_point_in_time"):
        coord = ChoresCoordinator(hass, entry)
        await coord.async_initialize()

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
    entry = _make_entry(
        days_ago=30, interval_days=7, snooze_until=snooze_dt.isoformat()
    )
    entry.add_to_hass(hass)

    with patch("custom_components.chores.coordinator.async_track_point_in_time"):
        coord = ChoresCoordinator(hass, entry)
        await coord.async_initialize()

        assert coord.data["status"] == "snoozed"

        new_opts = {**dict(entry.options), "name": "Renamed Chore"}
        await coord.async_update_config(new_opts)

    assert coord.data["status"] == "snoozed"
    assert coord.data["snooze_until"] == snooze_dt


async def test_update_config_noop_when_options_match_runtime(hass: Any) -> None:
    """async_update_config early-returns when options already match runtime state."""
    entry = _make_entry(days_ago=0, interval_days=7)
    entry.add_to_hass(hass)

    with patch(
        "custom_components.chores.coordinator.async_track_point_in_time"
    ) as mock_track:
        coord = ChoresCoordinator(hass, entry)
        await coord.async_initialize()
        call_count_after_init = mock_track.call_count

        await coord.async_update_config(dict(entry.options))

    assert mock_track.call_count == call_count_after_init


# ---------------------------------------------------------------------------
# Snooze tests
# ---------------------------------------------------------------------------


async def test_snooze_transitions_to_snoozed(hass: Any) -> None:
    entry = _make_entry(days_ago=30, interval_days=7)
    entry.add_to_hass(hass)

    with patch("custom_components.chores.coordinator.async_track_point_in_time"):
        coord = ChoresCoordinator(hass, entry)
        await coord.async_initialize()

        snooze_dt = dt_util.now() + timedelta(days=3)
        await coord.async_snooze(snooze_dt)

    assert coord.data["status"] == "snoozed"
    assert coord.data["snooze_until"] == snooze_dt


async def test_snooze_persists_to_entry_options(hass: Any) -> None:
    entry = _make_entry(days_ago=30, interval_days=7)
    entry.add_to_hass(hass)

    with patch("custom_components.chores.coordinator.async_track_point_in_time"):
        coord = ChoresCoordinator(hass, entry)
        await coord.async_initialize()

        snooze_dt = dt_util.now() + timedelta(days=3)
        await coord.async_snooze(snooze_dt)

    assert entry.options["snooze_until"] == snooze_dt.isoformat()


async def test_snooze_survives_restart(hass: Any) -> None:
    """snooze_until in entry.options is restored on a new coordinator."""
    entry = _make_entry(days_ago=30, interval_days=7)
    entry.add_to_hass(hass)

    with patch("custom_components.chores.coordinator.async_track_point_in_time"):
        coord = ChoresCoordinator(hass, entry)
        await coord.async_initialize()

        snooze_dt = dt_util.now() + timedelta(days=5)
        await coord.async_snooze(snooze_dt)

        coord2 = ChoresCoordinator(hass, entry)
        await coord2.async_initialize()

    assert coord2.data["status"] == "snoozed"
    assert coord2.data["snooze_until"] == snooze_dt


async def test_snooze_expiry_recomputes_state(hass: Any) -> None:
    """When the snooze timer fires, status is recalculated."""
    captured: dict[str, Any] = {}

    def _fake_track(hass_, cb, point_in_time):
        captured["cb"] = cb
        return MagicMock()

    entry = _make_entry(days_ago=30, interval_days=7)
    entry.add_to_hass(hass)

    with patch(
        "custom_components.chores.coordinator.async_track_point_in_time",
        side_effect=_fake_track,
    ):
        coord = ChoresCoordinator(hass, entry)
        await coord.async_initialize()

        snooze_dt = dt_util.now() + timedelta(days=3)
        await coord.async_snooze(snooze_dt)

    assert coord.data["status"] == "snoozed"
    assert "cb" in captured

    future = datetime.now(tz=UTC) + timedelta(days=4)
    with patch("custom_components.chores.coordinator.dt_util.now", return_value=future):
        captured["cb"](future)

    assert coord.data["status"] == "overdue"
    assert coord.data["snooze_until"] is None


@pytest.mark.parametrize(
    "bad_dt",
    [
        pytest.param(datetime(2026, 6, 12, 11, 0, tzinfo=UTC), id="one_hour_before"),
        pytest.param(datetime(2026, 6, 12, 12, 0, tzinfo=UTC), id="exactly_now"),
    ],
)
async def test_snooze_non_future_datetime_raises(hass: Any, bad_dt: datetime) -> None:
    """async_snooze with a past or present datetime raises HomeAssistantError."""
    entry = _make_entry(days_ago=30, interval_days=7)
    entry.add_to_hass(hass)

    fixed_now = datetime(2026, 6, 12, 12, 0, tzinfo=UTC)
    with (
        patch("custom_components.chores.coordinator.async_track_point_in_time"),
        patch(
            "custom_components.chores.coordinator.dt_util.now",
            return_value=fixed_now,
        ),
    ):
        coord = ChoresCoordinator(hass, entry)
        await coord.async_initialize()

        with pytest.raises(HomeAssistantError):
            await coord.async_snooze(bad_dt)

    assert coord.data["status"] != "snoozed"
    assert coord.data["snooze_until"] is None


async def test_complete_clears_snooze(hass: Any) -> None:
    """Completing a snoozed chore clears the snooze and marks it done."""
    entry = _make_entry(days_ago=30, interval_days=7)
    entry.add_to_hass(hass)

    with patch("custom_components.chores.coordinator.async_track_point_in_time"):
        coord = ChoresCoordinator(hass, entry)
        await coord.async_initialize()

        snooze_dt = dt_util.now() + timedelta(days=3)
        await coord.async_snooze(snooze_dt)
        assert coord.data["status"] == "snoozed"

        await coord.async_complete()

    assert coord.data["status"] == "done"
    assert coord.data["snooze_until"] is None


async def test_expired_snooze_not_restored_on_restart(hass: Any) -> None:
    """An expired snooze_until is discarded on restart."""
    expired_dt = (dt_util.now() - timedelta(hours=1)).isoformat()
    entry = _make_entry(days_ago=30, interval_days=7, snooze_until=expired_dt)
    entry.add_to_hass(hass)

    with patch("custom_components.chores.coordinator.async_track_point_in_time"):
        coord = ChoresCoordinator(hass, entry)
        await coord.async_initialize()

    assert coord.data["status"] == "overdue"
    assert coord.data["snooze_until"] is None


async def test_naive_snooze_raises_on_load(hass: Any) -> None:
    """A naive snooze_until string raises ValueError on load (indicates a storage bug)."""
    entry = _make_entry(days_ago=30, interval_days=7, snooze_until="2099-12-31")
    entry.add_to_hass(hass)

    with (
        patch("custom_components.chores.coordinator.async_track_point_in_time"),
        pytest.raises(ValueError, match="got naive"),
    ):
        coord = ChoresCoordinator(hass, entry)
        await coord.async_initialize()


async def test_unsnooze_clears_snooze_and_recalculates(hass: Any) -> None:
    """Unsnoozed overdue chore returns to overdue."""
    snooze_dt = dt_util.now() + timedelta(days=3)
    entry = _make_entry(
        days_ago=30, interval_days=7, snooze_until=snooze_dt.isoformat()
    )
    entry.add_to_hass(hass)

    with patch("custom_components.chores.coordinator.async_track_point_in_time"):
        coord = ChoresCoordinator(hass, entry)
        await coord.async_initialize()

        assert coord.data["status"] == "snoozed"
        await coord.async_unsnooze()

    assert coord.data["snooze_until"] is None
    assert coord.data["status"] == "overdue"


async def test_unsnooze_done_chore(hass: Any) -> None:
    """Unsnoozed done chore (not yet overdue) returns to done."""
    snooze_dt = dt_util.now() + timedelta(days=3)
    entry = _make_entry(days_ago=1, interval_days=7, snooze_until=snooze_dt.isoformat())
    entry.add_to_hass(hass)

    with patch("custom_components.chores.coordinator.async_track_point_in_time"):
        coord = ChoresCoordinator(hass, entry)
        await coord.async_initialize()

        assert coord.data["status"] == "snoozed"
        await coord.async_unsnooze()

    assert coord.data["snooze_until"] is None
    assert coord.data["status"] == "done"


async def test_snooze_default_uses_default_snooze_value_and_unit(hass: Any) -> None:
    """async_snooze_default snoozes for default_snooze_value + default_snooze_unit from now."""
    entry = _make_entry(
        days_ago=30,
        interval_days=14,
        default_snooze_value=2,
        default_snooze_unit="hours",
    )
    entry.add_to_hass(hass)

    with patch("custom_components.chores.coordinator.async_track_point_in_time"):
        coord = ChoresCoordinator(hass, entry)
        await coord.async_initialize()
        before = dt_util.now()
        await coord.async_snooze_default()
        after = dt_util.now()

    snooze_until = coord.data["snooze_until"]
    assert before + timedelta(hours=2) <= snooze_until <= after + timedelta(hours=2)
    assert coord.data["status"] == "snoozed"


async def test_snooze_default_days_unit(hass: Any) -> None:
    """async_snooze_default with unit=days defers by the configured number of days."""
    entry = _make_entry(
        days_ago=30,
        interval_days=14,
        default_snooze_value=3,
        default_snooze_unit="days",
    )
    entry.add_to_hass(hass)

    with patch("custom_components.chores.coordinator.async_track_point_in_time"):
        coord = ChoresCoordinator(hass, entry)
        await coord.async_initialize()
        before = dt_util.now()
        await coord.async_snooze_default()
        after = dt_util.now()

    snooze_until = coord.data["snooze_until"]
    assert before + timedelta(days=3) <= snooze_until <= after + timedelta(days=3)
    assert coord.data["status"] == "snoozed"


async def test_unsnooze_on_non_snoozed_is_noop(hass: Any) -> None:
    """Calling async_unsnooze on a non-snoozed chore is a no-op."""
    entry = _make_entry(days_ago=30, interval_days=7)
    entry.add_to_hass(hass)

    with patch("custom_components.chores.coordinator.async_track_point_in_time"):
        coord = ChoresCoordinator(hass, entry)
        await coord.async_initialize()

        status_before = coord.data["status"]
        initial_options = dict(entry.options)
        await coord.async_unsnooze()

    assert coord.data["status"] == status_before
    assert coord.data["snooze_until"] is None
    # Options unchanged since it was a no-op
    assert dict(entry.options) == initial_options


# ---------------------------------------------------------------------------
# async_complete with completed_at tests
# ---------------------------------------------------------------------------


async def test_complete_with_explicit_completed_at(hass: Any) -> None:
    """async_complete with a past datetime stores that datetime."""
    entry = _make_entry(days_ago=30, interval_days=7)
    entry.add_to_hass(hass)

    with patch("custom_components.chores.coordinator.async_track_point_in_time"):
        coord = ChoresCoordinator(hass, entry)
        await coord.async_initialize()

        past_dt = dt_util.now() - timedelta(hours=3)
        await coord.async_complete(past_dt)

    assert coord.data["last_completed"] == past_dt
    assert coord.data["status"] == "done"


async def test_complete_future_completed_at_raises(hass: Any) -> None:
    """async_complete with a future datetime raises HomeAssistantError."""
    entry = _make_entry(days_ago=30, interval_days=7)
    entry.add_to_hass(hass)

    with patch("custom_components.chores.coordinator.async_track_point_in_time"):
        coord = ChoresCoordinator(hass, entry)
        await coord.async_initialize()

        original_last = coord.data["last_completed"]
        future_dt = dt_util.now() + timedelta(hours=1)

        with pytest.raises(HomeAssistantError):
            await coord.async_complete(future_dt)

    assert coord.data["last_completed"] == original_last


async def test_last_completed_is_datetime_not_date(hass: Any) -> None:
    """Snapshot last_completed is a datetime, not a date."""
    entry = _make_entry(days_ago=0, interval_days=7)
    entry.add_to_hass(hass)

    with patch("custom_components.chores.coordinator.async_track_point_in_time"):
        coord = ChoresCoordinator(hass, entry)
        await coord.async_initialize()

    assert isinstance(coord.data["last_completed"], datetime)


async def test_complete_persists_tz_aware_datetime(hass: Any) -> None:
    """async_complete stores a tz-aware ISO datetime string in entry.options."""
    entry = _make_entry(days_ago=30, interval_days=7)
    entry.add_to_hass(hass)

    with patch("custom_components.chores.coordinator.async_track_point_in_time"):
        coord = ChoresCoordinator(hass, entry)
        await coord.async_initialize()
        await coord.async_complete()

    stored = entry.options["last_completed"]
    parsed = datetime.fromisoformat(stored)
    assert parsed.tzinfo is not None


# ---------------------------------------------------------------------------
# notification_time tests
# ---------------------------------------------------------------------------


async def test_next_due_at_notification_time(hass: Any) -> None:
    """next_due is at notification_time on the due date, not midnight."""
    entry = _make_entry(days_ago=0, interval_days=7, notification_time="08:00")
    entry.add_to_hass(hass)

    with patch("custom_components.chores.coordinator.async_track_point_in_time"):
        coord = ChoresCoordinator(hass, entry)
        await coord.async_initialize()

    next_due = coord.data["next_due"]
    assert next_due.hour == 8
    assert next_due.minute == 0
    expected_date = dt_util.now().date() + timedelta(days=7)
    assert next_due.date() == expected_date


async def test_next_due_default_notification_time_is_midnight(hass: Any) -> None:
    """notification_time 00:00 gives midnight next_due."""
    entry = _make_entry(days_ago=0, interval_days=7, notification_time="00:00")
    entry.add_to_hass(hass)

    with patch("custom_components.chores.coordinator.async_track_point_in_time"):
        coord = ChoresCoordinator(hass, entry)
        await coord.async_initialize()

    next_due = coord.data["next_due"]
    assert next_due.hour == 0
    assert next_due.minute == 0


async def test_ha_starts_before_notification_time_is_done(hass: Any) -> None:
    """Chore is done when HA starts before notification_time on the due date."""
    # Compute times in local tz so the test is timezone-independent.
    today_midnight = dt_util.start_of_local_day(dt_util.now())
    last_completed = (today_midnight - timedelta(days=7)).isoformat()
    before_notification = today_midnight + timedelta(hours=7)  # 07:00 local < 08:00

    opts: dict[str, Any] = {
        "name": "Bins",
        "interval_days": 7,
        "default_snooze_value": 1,
        "default_snooze_unit": "days",
        "notification_time": "08:00",
        "last_completed": last_completed,
        "snooze_until": None,
    }
    entry = MockConfigEntry(domain=DOMAIN, options=opts)
    entry.add_to_hass(hass)

    with (
        patch("custom_components.chores.coordinator.async_track_point_in_time"),
        patch(
            "custom_components.chores.coordinator.dt_util.now",
            return_value=before_notification,
        ),
    ):
        coord = ChoresCoordinator(hass, entry)
        await coord.async_initialize()

    assert coord.data["status"] == "done"


async def test_ha_starts_after_notification_time_is_overdue(hass: Any) -> None:
    """Chore is overdue when HA starts after notification_time on the due date."""
    today_midnight = dt_util.start_of_local_day(dt_util.now())
    last_completed = (today_midnight - timedelta(days=7)).isoformat()
    after_notification = today_midnight + timedelta(hours=9)  # 09:00 local > 08:00

    opts: dict[str, Any] = {
        "name": "Bins",
        "interval_days": 7,
        "default_snooze_value": 1,
        "default_snooze_unit": "days",
        "notification_time": "08:00",
        "last_completed": last_completed,
        "snooze_until": None,
    }
    entry = MockConfigEntry(domain=DOMAIN, options=opts)
    entry.add_to_hass(hass)

    with (
        patch("custom_components.chores.coordinator.async_track_point_in_time"),
        patch(
            "custom_components.chores.coordinator.dt_util.now",
            return_value=after_notification,
        ),
    ):
        coord = ChoresCoordinator(hass, entry)
        await coord.async_initialize()

    assert coord.data["status"] == "overdue"


async def test_snooze_timer_fires_at_snooze_until_regardless_of_notification_time(
    hass: Any,
) -> None:
    """The snooze-expiry timer fires at snooze_until, not at notification_time."""
    timer_points: list[datetime] = []

    def _fake_track(hass_, cb, point_in_time):
        timer_points.append(point_in_time)
        return MagicMock()

    entry = _make_entry(days_ago=30, interval_days=7, notification_time="08:00")
    entry.add_to_hass(hass)

    with patch(
        "custom_components.chores.coordinator.async_track_point_in_time",
        side_effect=_fake_track,
    ):
        coord = ChoresCoordinator(hass, entry)
        await coord.async_initialize()

        snooze_dt = dt_util.now() + timedelta(minutes=30)
        await coord.async_snooze(snooze_dt)

    assert timer_points[-1] == snooze_dt


async def test_snooze_expiry_transitions_to_overdue(hass: Any) -> None:
    """When the snooze-expiry timer fires, status transitions to overdue."""
    captured: dict[str, Any] = {}

    def _fake_track(hass_, cb, point_in_time):
        captured["cb"] = cb
        return MagicMock()

    entry = _make_entry(days_ago=30, interval_days=7, notification_time="08:00")
    entry.add_to_hass(hass)

    with patch(
        "custom_components.chores.coordinator.async_track_point_in_time",
        side_effect=_fake_track,
    ):
        coord = ChoresCoordinator(hass, entry)
        await coord.async_initialize()

        snooze_dt = dt_util.now() + timedelta(days=3)
        await coord.async_snooze(snooze_dt)

    assert coord.data["status"] == "snoozed"
    assert "cb" in captured

    future = datetime.now(tz=UTC) + timedelta(days=4)
    with patch("custom_components.chores.coordinator.dt_util.now", return_value=future):
        captured["cb"](future)

    assert coord.data["status"] == "overdue"
    assert coord.data["snooze_until"] is None


async def test_notification_time_in_snapshot(hass: Any) -> None:
    """notification_time is included in the coordinator snapshot."""
    entry = _make_entry(days_ago=0, interval_days=7, notification_time="08:30")
    entry.add_to_hass(hass)

    with patch("custom_components.chores.coordinator.async_track_point_in_time"):
        coord = ChoresCoordinator(hass, entry)
        await coord.async_initialize()

    assert coord.data["notification_time"] == "08:30"


# ---------------------------------------------------------------------------
# Never-completed chore tests
# ---------------------------------------------------------------------------


async def test_never_completed_is_overdue(hass: Any) -> None:
    """A chore with no last_completed starts overdue."""
    entry = _make_entry(last_completed=None)
    entry.add_to_hass(hass)

    with patch("custom_components.chores.coordinator.async_track_point_in_time"):
        coord = ChoresCoordinator(hass, entry)
        await coord.async_initialize()

    assert coord.data["status"] == "overdue"


async def test_never_completed_next_due_is_none(hass: Any) -> None:
    """A chore with no last_completed has next_due=None."""
    entry = _make_entry(last_completed=None)
    entry.add_to_hass(hass)

    with patch("custom_components.chores.coordinator.async_track_point_in_time"):
        coord = ChoresCoordinator(hass, entry)
        await coord.async_initialize()

    assert coord.data["next_due"] is None


async def test_never_completed_last_completed_is_none_in_snapshot(hass: Any) -> None:
    """Snapshot carries last_completed=None for a never-completed chore."""
    entry = _make_entry(last_completed=None)
    entry.add_to_hass(hass)

    with patch("custom_components.chores.coordinator.async_track_point_in_time"):
        coord = ChoresCoordinator(hass, entry)
        await coord.async_initialize()

    assert coord.data["last_completed"] is None


async def test_completing_never_completed_chore_starts_cycle(hass: Any) -> None:
    """Completing a never-completed chore sets last_completed, next_due, and status done."""
    entry = _make_entry(last_completed=None, interval_days=7)
    entry.add_to_hass(hass)

    with patch("custom_components.chores.coordinator.async_track_point_in_time"):
        coord = ChoresCoordinator(hass, entry)
        await coord.async_initialize()

        assert coord.data["status"] == "overdue"
        await coord.async_complete()

    assert coord.data["status"] == "done"
    assert coord.data["last_completed"] is not None
    assert coord.data["last_completed"].date() == dt_util.now().date()
    expected_next_due = dt_util.now().date() + timedelta(days=7)
    assert coord.data["next_due"].date() == expected_next_due


async def test_snooze_on_never_completed_chore(hass: Any) -> None:
    """Snoozing a never-completed chore transitions to snoozed; expiry returns to overdue."""
    captured: dict[str, Any] = {}

    def _fake_track(hass_, cb, point_in_time):
        captured["cb"] = cb
        return MagicMock()

    entry = _make_entry(last_completed=None)
    entry.add_to_hass(hass)

    with patch(
        "custom_components.chores.coordinator.async_track_point_in_time",
        side_effect=_fake_track,
    ):
        coord = ChoresCoordinator(hass, entry)
        await coord.async_initialize()

        assert coord.data["status"] == "overdue"

        snooze_dt = dt_util.now() + timedelta(days=3)
        await coord.async_snooze(snooze_dt)

    assert coord.data["status"] == "snoozed"

    future = datetime.now(tz=UTC) + timedelta(days=4)
    with patch("custom_components.chores.coordinator.dt_util.now", return_value=future):
        captured["cb"](future)

    assert coord.data["status"] == "overdue"
    assert coord.data["last_completed"] is None
