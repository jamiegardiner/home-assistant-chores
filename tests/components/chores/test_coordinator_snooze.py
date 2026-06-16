"""Tests for coordinator snooze, unsnooze, and never-completed chore behaviour."""

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import patch

import pytest
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import issue_registry as ir
from homeassistant.util import dt as dt_util

from custom_components.chores.const import DOMAIN, REPAIR_ISSUE_CORRUPT_FIELD
from tests.components.chores.helpers import make_entry, setup_coord

# ---------------------------------------------------------------------------
# Snooze tests
# ---------------------------------------------------------------------------


async def test_snooze_transitions_to_snoozed(hass: Any) -> None:
    entry = make_entry(days_ago=30, interval_days=7)
    entry.add_to_hass(hass)
    coord = await setup_coord(hass, entry)

    snooze_dt = dt_util.now() + timedelta(days=3)
    await coord.async_snooze(snooze_dt)

    assert coord.data["status"] == "snoozed"
    assert coord.data["snooze_until"] == snooze_dt


async def test_snooze_persists_to_entry_options(hass: Any) -> None:
    entry = make_entry(days_ago=30, interval_days=7)
    entry.add_to_hass(hass)
    coord = await setup_coord(hass, entry)

    snooze_dt = dt_util.now() + timedelta(days=3)
    await coord.async_snooze(snooze_dt)

    assert entry.options["snooze_until"] == snooze_dt.isoformat()


async def test_snooze_survives_restart(hass: Any) -> None:
    """snooze_until in entry.options is restored on a new coordinator."""
    entry = make_entry(days_ago=30, interval_days=7)
    entry.add_to_hass(hass)
    coord = await setup_coord(hass, entry)

    snooze_dt = dt_util.now() + timedelta(days=5)
    await coord.async_snooze(snooze_dt)

    coord2 = await setup_coord(hass, entry)

    assert coord2.data["status"] == "snoozed"
    assert coord2.data["snooze_until"] == snooze_dt


@pytest.mark.parametrize(
    "notification_time",
    ["00:00", "08:00"],
    ids=["midnight", "eight_am"],
)
async def test_snooze_expiry_transitions_to_overdue(
    hass: Any, notification_time: str, fake_track: dict[str, Any]
) -> None:
    """When the snooze-expiry timer fires, status transitions to overdue."""
    entry = make_entry(
        days_ago=30, interval_days=7, notification_time=notification_time
    )
    entry.add_to_hass(hass)
    coord = await setup_coord(hass, entry)
    snooze_dt = dt_util.now() + timedelta(days=3)
    await coord.async_snooze(snooze_dt)

    assert coord.data["status"] == "snoozed"
    assert "cb" in fake_track

    future = datetime.now(tz=UTC) + timedelta(days=4)
    with patch("custom_components.chores.coordinator.dt_util.now", return_value=future):
        fake_track["cb"](future)

    assert coord.data["status"] == "overdue"
    assert coord.data["snooze_until"] is None
    assert entry.options["snooze_until"] is None


@pytest.mark.parametrize(
    "bad_dt",
    [
        pytest.param(datetime(2026, 6, 12, 11, 0, tzinfo=UTC), id="one_hour_before"),
        pytest.param(datetime(2026, 6, 12, 12, 0, tzinfo=UTC), id="exactly_now"),
    ],
)
async def test_snooze_non_future_datetime_raises(hass: Any, bad_dt: datetime) -> None:
    """async_snooze with a past or present datetime raises HomeAssistantError."""
    entry = make_entry(days_ago=30, interval_days=7)
    entry.add_to_hass(hass)

    fixed_now = datetime(2026, 6, 12, 12, 0, tzinfo=UTC)
    with patch(
        "custom_components.chores.coordinator.dt_util.now",
        return_value=fixed_now,
    ):
        coord = await setup_coord(hass, entry)

        with pytest.raises(HomeAssistantError):
            await coord.async_snooze(bad_dt)

    assert coord.data["status"] != "snoozed"
    assert coord.data["snooze_until"] is None


async def test_complete_clears_snooze(hass: Any) -> None:
    """Completing a snoozed chore clears the snooze and marks it done."""
    entry = make_entry(days_ago=30, interval_days=7)
    entry.add_to_hass(hass)
    coord = await setup_coord(hass, entry)

    snooze_dt = dt_util.now() + timedelta(days=3)
    await coord.async_snooze(snooze_dt)
    assert coord.data["status"] == "snoozed"

    await coord.async_complete()

    assert coord.data["status"] == "done"
    assert coord.data["snooze_until"] is None


async def test_expired_snooze_not_restored_on_restart(hass: Any) -> None:
    """An expired snooze_until is discarded on restart and cleared from entry.options."""
    expired_dt = (dt_util.now() - timedelta(hours=1)).isoformat()
    entry = make_entry(days_ago=30, interval_days=7, snooze_until=expired_dt)
    entry.add_to_hass(hass)
    coord = await setup_coord(hass, entry)

    assert coord.data["status"] == "overdue"
    assert coord.data["snooze_until"] is None
    assert entry.options["snooze_until"] is None


async def test_naive_snooze_gracefully_recovered(hass: Any) -> None:
    """A naive snooze_until is cleared to None and a repair issue is raised."""
    entry = make_entry(days_ago=30, interval_days=7, snooze_until="2099-12-31")
    entry.add_to_hass(hass)

    coord = await setup_coord(hass, entry)

    assert coord.data["snooze_until"] is None
    assert entry.options["snooze_until"] is None
    issue = ir.async_get(hass).async_get_issue(
        DOMAIN, f"{REPAIR_ISSUE_CORRUPT_FIELD}_{entry.entry_id}"
    )
    assert issue is not None
    assert issue.severity == ir.IssueSeverity.WARNING


async def test_unsnooze_clears_snooze_and_recalculates(hass: Any) -> None:
    """Unsnoozed overdue chore returns to overdue."""
    snooze_dt = dt_util.now() + timedelta(days=3)
    entry = make_entry(days_ago=30, interval_days=7, snooze_until=snooze_dt.isoformat())
    entry.add_to_hass(hass)
    coord = await setup_coord(hass, entry)

    assert coord.data["status"] == "snoozed"
    await coord.async_unsnooze()

    assert coord.data["snooze_until"] is None
    assert coord.data["status"] == "overdue"


async def test_unsnooze_done_chore(hass: Any) -> None:
    """Unsnoozed done chore (not yet overdue) returns to done."""
    snooze_dt = dt_util.now() + timedelta(days=3)
    entry = make_entry(days_ago=1, interval_days=7, snooze_until=snooze_dt.isoformat())
    entry.add_to_hass(hass)
    coord = await setup_coord(hass, entry)

    assert coord.data["status"] == "snoozed"
    await coord.async_unsnooze()

    assert coord.data["snooze_until"] is None
    assert coord.data["status"] == "done"


async def test_snooze_default_uses_default_snooze_value_and_unit(hass: Any) -> None:
    """async_snooze_default snoozes for default_snooze_value + default_snooze_unit from now."""
    entry = make_entry(
        days_ago=30,
        interval_days=14,
        default_snooze_value=2,
        default_snooze_unit="hours",
    )
    entry.add_to_hass(hass)
    coord = await setup_coord(hass, entry)
    before = dt_util.now()
    await coord.async_snooze_default()
    after = dt_util.now()

    snooze_until = coord.data["snooze_until"]
    assert before + timedelta(hours=2) <= snooze_until <= after + timedelta(hours=2)
    assert coord.data["status"] == "snoozed"


async def test_snooze_default_days_unit(hass: Any) -> None:
    """async_snooze_default with unit=days defers by the configured number of days."""
    entry = make_entry(
        days_ago=30,
        interval_days=14,
        default_snooze_value=3,
        default_snooze_unit="days",
    )
    entry.add_to_hass(hass)
    coord = await setup_coord(hass, entry)
    before = dt_util.now()
    await coord.async_snooze_default()
    after = dt_util.now()

    snooze_until = coord.data["snooze_until"]
    assert before + timedelta(days=3) <= snooze_until <= after + timedelta(days=3)
    assert coord.data["status"] == "snoozed"


async def test_unsnooze_on_non_snoozed_is_noop(hass: Any) -> None:
    """Calling async_unsnooze on a non-snoozed chore is a no-op."""
    entry = make_entry(days_ago=30, interval_days=7)
    entry.add_to_hass(hass)
    coord = await setup_coord(hass, entry)

    status_before = coord.data["status"]
    initial_options = dict(entry.options)
    await coord.async_unsnooze()

    assert coord.data["status"] == status_before
    assert coord.data["snooze_until"] is None
    # Options unchanged since it was a no-op
    assert dict(entry.options) == initial_options


# ---------------------------------------------------------------------------
# Never-completed chore tests
# ---------------------------------------------------------------------------


async def test_never_completed_is_overdue(hass: Any) -> None:
    """A chore with no last_completed starts overdue."""
    entry = make_entry(last_completed=None)
    entry.add_to_hass(hass)
    coord = await setup_coord(hass, entry)
    assert coord.data["status"] == "overdue"


async def test_never_completed_next_due_is_none(hass: Any) -> None:
    """A chore with no last_completed has next_due=None."""
    entry = make_entry(last_completed=None)
    entry.add_to_hass(hass)
    coord = await setup_coord(hass, entry)
    assert coord.data["next_due"] is None


async def test_never_completed_last_completed_is_none_in_snapshot(hass: Any) -> None:
    """Snapshot carries last_completed=None for a never-completed chore."""
    entry = make_entry(last_completed=None)
    entry.add_to_hass(hass)
    coord = await setup_coord(hass, entry)
    assert coord.data["last_completed"] is None


async def test_completing_never_completed_chore_starts_cycle(hass: Any) -> None:
    """Completing a never-completed chore sets last_completed, next_due, and status done."""
    entry = make_entry(last_completed=None, interval_days=7)
    entry.add_to_hass(hass)
    coord = await setup_coord(hass, entry)

    assert coord.data["status"] == "overdue"
    await coord.async_complete()

    assert coord.data["status"] == "done"
    assert coord.data["last_completed"] is not None
    assert coord.data["last_completed"].date() == dt_util.now().date()
    expected_next_due = dt_util.now().date() + timedelta(days=7)
    assert coord.data["next_due"].date() == expected_next_due


async def test_snooze_on_never_completed_chore(
    hass: Any, fake_track: dict[str, Any]
) -> None:
    """Snoozing a never-completed chore transitions to snoozed; expiry returns to overdue."""
    entry = make_entry(last_completed=None)
    entry.add_to_hass(hass)
    coord = await setup_coord(hass, entry)

    assert coord.data["status"] == "overdue"

    snooze_dt = dt_util.now() + timedelta(days=3)
    await coord.async_snooze(snooze_dt)

    assert coord.data["status"] == "snoozed"

    future = datetime.now(tz=UTC) + timedelta(days=4)
    with patch("custom_components.chores.coordinator.dt_util.now", return_value=future):
        fake_track["cb"](future)

    assert coord.data["status"] == "overdue"
    assert coord.data["last_completed"] is None


async def test_never_completed_snoozed_restores_on_load(hass: Any) -> None:
    """Coordinator restores to snoozed when last_completed is None but snooze_until is active."""
    snooze_dt = dt_util.now() + timedelta(days=2)
    entry = make_entry(last_completed=None, snooze_until=snooze_dt.isoformat())
    entry.add_to_hass(hass)
    coord = await setup_coord(hass, entry)

    assert coord.data["status"] == "snoozed"
    assert coord.data["snooze_until"] == snooze_dt
    assert coord.data["last_completed"] is None
