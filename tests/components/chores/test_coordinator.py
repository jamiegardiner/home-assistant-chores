"""Tests for the Chores coordinator (single-chore-per-entry model)."""

from __future__ import annotations

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
    default_snooze_days: int = 1,
    days_ago: int = 0,
    snooze_until: str | None = None,
    entry_id: str = "test_entry_id",
) -> MockConfigEntry:
    """Return a single-chore MockConfigEntry."""
    last_completed = (dt_util.now().date() - timedelta(days=days_ago)).isoformat()
    opts: dict[str, Any] = {
        "name": name,
        "interval_days": interval_days,
        "default_snooze_days": default_snooze_days,
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
    assert coord.data["last_completed"] == dt_util.now().date()
    assert coord.data["next_due"] > datetime.now(tz=UTC)


async def test_complete_persists_to_entry_options(hass: Any) -> None:
    """async_complete writes last_completed to entry.options."""
    entry = _make_entry(days_ago=30, interval_days=7)
    entry.add_to_hass(hass)

    with patch("custom_components.chores.coordinator.async_track_point_in_time"):
        coord = ChoresCoordinator(hass, entry)
        await coord.async_initialize()
        await coord.async_complete()

    assert entry.options["last_completed"] == dt_util.now().date().isoformat()
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

    assert coord.data["last_completed"] == last_completed_date
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


async def test_snooze_default_uses_default_snooze_days(hass: Any) -> None:
    """async_snooze_default snoozes for default_snooze_days from now."""
    entry = _make_entry(days_ago=30, interval_days=14, default_snooze_days=3)
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
