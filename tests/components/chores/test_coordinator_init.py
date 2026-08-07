"""Tests for coordinator initialization, status computation, and async_update_config."""

from datetime import UTC, date, datetime, timedelta
from typing import Any, cast
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.exceptions import ConfigEntryError
from homeassistant.helpers import issue_registry as ir
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.chores.const import (
    DOMAIN,
    REPAIR_ISSUE_CORRUPT_CONFIG,
    REPAIR_ISSUE_CORRUPT_LAST_COMPLETED,
    REPAIR_ISSUE_CORRUPT_NEXT_DUE,
    REPAIR_ISSUE_CORRUPT_SNOOZE_UNTIL,
)
from custom_components.chores.coordinator import (
    ChoresCoordinator,
    _parse_aware_datetime,
)
from tests.components.chores.helpers import make_entry, setup_coord

# ---------------------------------------------------------------------------
# Coordinator initialization / status computation tests
# ---------------------------------------------------------------------------


async def test_initial_status_overdue(hass: Any) -> None:
    """Chore last completed 30 days ago with 7-day interval is overdue."""
    entry = make_entry(days_ago=30, interval_value=7)
    entry.add_to_hass(hass)
    coord = await setup_coord(hass, entry)
    assert coord.data["status"] == "overdue"


async def test_initial_status_done(hass: Any) -> None:
    """Chore last completed today with 7-day interval is done."""
    entry = make_entry(days_ago=0, interval_value=7)
    entry.add_to_hass(hass)
    coord = await setup_coord(hass, entry)
    assert coord.data["status"] == "done"


async def test_next_due_computed_correctly(hass: Any) -> None:
    """next_due is last_completed + interval, expressed as start of that local day."""
    entry = make_entry(days_ago=0, interval_value=7)
    entry.add_to_hass(hass)
    coord = await setup_coord(hass, entry)
    expected_date = dt_util.now().date() + timedelta(days=7)
    assert coord.data["next_due"].date() == expected_date


async def test_timer_fires_overdue_transition(
    hass: Any, fake_track: dict[str, Any]
) -> None:
    """When the scheduled timer fires, status transitions to overdue."""
    entry = make_entry(days_ago=0, interval_value=7)
    entry.add_to_hass(hass)
    coord = await setup_coord(hass, entry)

    assert coord.data["status"] == "done"
    assert "cb" in fake_track

    future = datetime.now(tz=UTC) + timedelta(days=8)
    with patch("custom_components.chores.coordinator.dt_util.now", return_value=future):
        fake_track["cb"](future)

    assert coord.data["status"] == "overdue"


async def test_last_completed_survives_restart(hass: Any) -> None:
    """After completing, a new coordinator reads last_completed from entry.options."""
    entry = make_entry(days_ago=30, interval_value=7)
    entry.add_to_hass(hass)
    coord = await setup_coord(hass, entry)
    await coord.async_complete()
    completion_date = coord.data["last_completed"]

    coord2 = await setup_coord(hass, entry)

    assert coord2.data["last_completed"] == completion_date
    assert coord2.data["status"] == "done"


async def test_next_due_persisted_to_entry_options(hass: Any) -> None:
    """A normal load persists the recomputed next_due into entry.options."""
    entry = make_entry(days_ago=0, interval_value=7)
    entry.add_to_hass(hass)
    coord = await setup_coord(hass, entry)

    persisted = entry.options["next_due"]
    assert persisted is not None
    assert datetime.fromisoformat(persisted) == coord.data["next_due"]


async def test_unload_cancels_timers(hass: Any, patch_track: MagicMock) -> None:
    """async_shutdown_timers cancels all scheduled callbacks."""
    cancel_mocks: list[MagicMock] = []

    def _fake_track(hass_: Any, cb: Any, point_in_time: Any) -> MagicMock:
        cancel = MagicMock()
        cancel_mocks.append(cancel)
        return cancel

    patch_track.side_effect = _fake_track

    entry = make_entry(days_ago=0, interval_value=7)
    entry.add_to_hass(hass)
    coord = await setup_coord(hass, entry)

    assert len(cancel_mocks) >= 1
    coord.async_shutdown_timers()
    for mock in cancel_mocks:
        mock.assert_called_once()


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


# ---------------------------------------------------------------------------
# async_update_config tests
# ---------------------------------------------------------------------------


async def test_update_config_recomputes_from_preserved_last_completed(
    hass: Any,
) -> None:
    """Changing interval recomputes next_due from the existing last_completed, not today."""
    last_completed_date = dt_util.now().date() - timedelta(days=7)
    entry = make_entry(days_ago=7, interval_value=7)
    entry.add_to_hass(hass)
    coord = await setup_coord(hass, entry)

    assert coord.data["status"] == "overdue"

    new_opts = {
        **dict(entry.options),
        "interval_value": 14,
    }
    await coord.async_update_config(new_opts)

    assert coord.data["last_completed"].date() == last_completed_date
    expected_next_due = last_completed_date + timedelta(days=14)
    assert coord.data["next_due"].date() == expected_next_due
    assert coord.data["status"] == "done"
    assert datetime.fromisoformat(entry.options["next_due"]) == coord.data["next_due"]


async def test_update_config_name_change_no_status_change(hass: Any) -> None:
    """Editing the name does not change status or next_due."""
    entry = make_entry(name="Bins", days_ago=0, interval_value=7)
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
    entry = make_entry(
        days_ago=30, interval_value=7, snooze_until=snooze_dt.isoformat()
    )
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
    entry = make_entry(days_ago=30, interval_value=7)
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
    entry = make_entry(days_ago=0, interval_value=7)
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
        interval_value=7,
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


# ---------------------------------------------------------------------------
# _parse_aware_datetime tests
# ---------------------------------------------------------------------------


def test_parse_aware_datetime_type_error_returns_none() -> None:
    """A non-string value triggers TypeError in fromisoformat and returns None."""
    result = _parse_aware_datetime(cast(str, 42))
    assert result is None


# ---------------------------------------------------------------------------
# Timer callback guard tests
# ---------------------------------------------------------------------------


async def test_overdue_callback_noop_after_shutdown(
    hass: Any, fake_track: dict[str, Any]
) -> None:
    """Timer callback is a no-op when coordinator runtime is torn down."""
    entry = make_entry(days_ago=0, interval_value=7)
    entry.add_to_hass(hass)
    coord = await setup_coord(hass, entry)
    cb = fake_track["cb"]

    coord._runtime = None
    cb(datetime.now(tz=UTC))  # must not raise


# ---------------------------------------------------------------------------
# Repair issue tests
# ---------------------------------------------------------------------------


async def test_naive_last_completed_gracefully_recovered(hass: Any) -> None:
    """A naive last_completed is cleared to None and a repair issue is raised."""
    entry = make_entry(interval_value=7, last_completed="2020-01-01")
    entry.add_to_hass(hass)

    coord = await setup_coord(hass, entry)

    assert coord.data["last_completed"] is None
    assert entry.options["last_completed"] is None
    issue = ir.async_get(hass).async_get_issue(
        DOMAIN, f"{REPAIR_ISSUE_CORRUPT_LAST_COMPLETED}_{entry.entry_id}"
    )
    assert issue is not None
    assert issue.severity == ir.IssueSeverity.WARNING


async def test_invalid_interval_value_raises_config_entry_error(hass: Any) -> None:
    """An invalid interval_value raises ConfigEntryError and surfaces an ERROR repair issue."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        entry_id="test_entry_id",
        options={
            "name": "Bins",
            "interval_value": 0,
            "default_snooze_value": 1,
            "default_snooze_unit": "days",
            "notification_time": "08:00",
            "last_completed": None,
            "snooze_until": None,
        },
    )
    entry.add_to_hass(hass)

    with pytest.raises(ConfigEntryError):
        coord = ChoresCoordinator(hass, entry)
        await coord.async_initialize()

    issue = ir.async_get(hass).async_get_issue(
        DOMAIN, f"{REPAIR_ISSUE_CORRUPT_CONFIG}_{entry.entry_id}"
    )
    assert issue is not None
    assert issue.severity == ir.IssueSeverity.ERROR


async def test_garbage_snooze_until_gracefully_recovered(hass: Any) -> None:
    """A totally unparseable snooze_until (not just naive) also triggers a repair issue."""
    entry = make_entry(days_ago=30, interval_value=7, snooze_until="not-a-date")
    entry.add_to_hass(hass)

    coord = await setup_coord(hass, entry)

    assert coord.data["snooze_until"] is None
    assert entry.options["snooze_until"] is None
    issue = ir.async_get(hass).async_get_issue(
        DOMAIN, f"{REPAIR_ISSUE_CORRUPT_SNOOZE_UNTIL}_{entry.entry_id}"
    )
    assert issue is not None
    assert issue.severity == ir.IssueSeverity.WARNING


async def test_garbage_next_due_gracefully_recovered(hass: Any) -> None:
    """A totally unparseable next_due is sanitised and recomputed, with a repair issue raised."""
    entry = make_entry(days_ago=30, interval_value=7, next_due="not-a-date")
    entry.add_to_hass(hass)

    coord = await setup_coord(hass, entry)

    expected_next_due = dt_util.now().date() - timedelta(days=23)
    assert coord.data["next_due"].date() == expected_next_due
    assert datetime.fromisoformat(entry.options["next_due"]).date() == expected_next_due
    issue = ir.async_get(hass).async_get_issue(
        DOMAIN, f"{REPAIR_ISSUE_CORRUPT_NEXT_DUE}_{entry.entry_id}"
    )
    assert issue is not None
    assert issue.severity == ir.IssueSeverity.WARNING


async def test_valid_options_no_repair_issue(hass: Any) -> None:
    """A clean load produces no repair issues."""
    entry = make_entry(days_ago=3, interval_value=7)
    entry.add_to_hass(hass)

    await setup_coord(hass, entry)

    issue_reg = ir.async_get(hass)
    assert (
        issue_reg.async_get_issue(
            DOMAIN, f"{REPAIR_ISSUE_CORRUPT_LAST_COMPLETED}_{entry.entry_id}"
        )
        is None
    )
    assert (
        issue_reg.async_get_issue(
            DOMAIN, f"{REPAIR_ISSUE_CORRUPT_SNOOZE_UNTIL}_{entry.entry_id}"
        )
        is None
    )
    assert (
        issue_reg.async_get_issue(
            DOMAIN, f"{REPAIR_ISSUE_CORRUPT_NEXT_DUE}_{entry.entry_id}"
        )
        is None
    )
    assert (
        issue_reg.async_get_issue(
            DOMAIN, f"{REPAIR_ISSUE_CORRUPT_CONFIG}_{entry.entry_id}"
        )
        is None
    )


async def test_clean_load_deletes_stale_repair_issues(hass: Any) -> None:
    """A clean load deletes any repair issues left over from a prior corrupt boot."""
    entry = make_entry(days_ago=3, interval_value=7)
    entry.add_to_hass(hass)

    ir.async_create_issue(
        hass,
        DOMAIN,
        f"{REPAIR_ISSUE_CORRUPT_LAST_COMPLETED}_{entry.entry_id}",
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key=REPAIR_ISSUE_CORRUPT_LAST_COMPLETED,
        translation_placeholders={"name": "Bins"},
    )
    ir.async_create_issue(
        hass,
        DOMAIN,
        f"{REPAIR_ISSUE_CORRUPT_SNOOZE_UNTIL}_{entry.entry_id}",
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key=REPAIR_ISSUE_CORRUPT_SNOOZE_UNTIL,
        translation_placeholders={"name": "Bins"},
    )
    ir.async_create_issue(
        hass,
        DOMAIN,
        f"{REPAIR_ISSUE_CORRUPT_NEXT_DUE}_{entry.entry_id}",
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key=REPAIR_ISSUE_CORRUPT_NEXT_DUE,
        translation_placeholders={"name": "Bins"},
    )
    ir.async_create_issue(
        hass,
        DOMAIN,
        f"{REPAIR_ISSUE_CORRUPT_CONFIG}_{entry.entry_id}",
        is_fixable=False,
        severity=ir.IssueSeverity.ERROR,
        translation_key=REPAIR_ISSUE_CORRUPT_CONFIG,
        translation_placeholders={"name": "Bins", "error": "bad"},
    )

    await setup_coord(hass, entry)

    issue_reg = ir.async_get(hass)
    assert (
        issue_reg.async_get_issue(
            DOMAIN, f"{REPAIR_ISSUE_CORRUPT_LAST_COMPLETED}_{entry.entry_id}"
        )
        is None
    )
    assert (
        issue_reg.async_get_issue(
            DOMAIN, f"{REPAIR_ISSUE_CORRUPT_SNOOZE_UNTIL}_{entry.entry_id}"
        )
        is None
    )
    assert (
        issue_reg.async_get_issue(
            DOMAIN, f"{REPAIR_ISSUE_CORRUPT_NEXT_DUE}_{entry.entry_id}"
        )
        is None
    )
    assert (
        issue_reg.async_get_issue(
            DOMAIN, f"{REPAIR_ISSUE_CORRUPT_CONFIG}_{entry.entry_id}"
        )
        is None
    )
