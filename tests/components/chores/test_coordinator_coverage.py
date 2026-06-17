"""Tests for timer-reschedule guard branches, _parse_aware_datetime, and repair issues."""

from datetime import UTC, datetime, timedelta
from typing import Any, cast
from unittest.mock import MagicMock

import pytest
from homeassistant.exceptions import ConfigEntryError
from homeassistant.helpers import issue_registry as ir
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.chores.const import (
    DOMAIN,
    REPAIR_ISSUE_CORRUPT_CONFIG,
    REPAIR_ISSUE_CORRUPT_LAST_COMPLETED,
    REPAIR_ISSUE_CORRUPT_SNOOZE_UNTIL,
)
from custom_components.chores.coordinator import (
    ChoresCoordinator,
    _parse_aware_datetime,
)
from tests.components.chores.helpers import make_entry, setup_coord

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

    entry = make_entry(days_ago=0, interval_value=7)
    entry.add_to_hass(hass)
    coord = await setup_coord(hass, entry)
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

    entry = make_entry(days_ago=0, interval_value=7)
    entry.add_to_hass(hass)
    coord = await setup_coord(hass, entry)
    first_cancel = cancel_mocks[0]

    await coord.async_snooze(dt_util.now() + timedelta(days=1))

    first_cancel.assert_called_once()


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

    entry = make_entry(days_ago=30, interval_value=7)
    entry.add_to_hass(hass)
    coord = await setup_coord(hass, entry)

    await coord.async_snooze(dt_util.now() + timedelta(days=1))
    first_snooze_cancel = cancel_mocks[-1]

    await coord.async_snooze(dt_util.now() + timedelta(days=2))

    first_snooze_cancel.assert_called_once()


async def test_snooze_expiry_callback_noop_after_shutdown(
    hass: Any, fake_track: dict[str, Any]
) -> None:
    """Snooze expiry callback is a no-op when coordinator runtime is torn down."""
    entry = make_entry(days_ago=30, interval_value=7)
    entry.add_to_hass(hass)
    coord = await setup_coord(hass, entry)

    await coord.async_snooze(dt_util.now() + timedelta(days=1))
    cb = fake_track["cb"]

    coord._runtime = None
    cb(datetime.now(tz=UTC))  # must not raise


async def test_schedule_snooze_returns_early_when_snooze_until_is_none(
    hass: Any,
) -> None:
    """_schedule_snooze is a no-op when snooze_until is None."""
    entry = make_entry(days_ago=30, interval_value=7)
    entry.add_to_hass(hass)
    coord = await setup_coord(hass, entry)
    assert coord._runtime is not None
    coord._runtime.snooze_until = None
    coord._schedule_snooze(
        coord._runtime
    )  # must not raise and must not schedule a timer


async def test_schedule_snooze_returns_early_when_snooze_until_in_past(
    hass: Any,
) -> None:
    """_schedule_snooze is a no-op when snooze_until is already in the past."""
    entry = make_entry(days_ago=30, interval_value=7)
    entry.add_to_hass(hass)
    coord = await setup_coord(hass, entry)
    assert coord._runtime is not None
    coord._runtime.snooze_until = dt_util.now() - timedelta(hours=1)
    coord._schedule_snooze(
        coord._runtime
    )  # must not raise and must not schedule a timer


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
            DOMAIN, f"{REPAIR_ISSUE_CORRUPT_CONFIG}_{entry.entry_id}"
        )
        is None
    )
