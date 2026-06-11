"""Tests for the Chores coordinator."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.chores.const import CONF_CHORES, DOMAIN
from custom_components.chores.coordinator import (
    ChoresCoordinator,
    _interval_to_timedelta,
)
from custom_components.chores.models import ChoreConfig

# ---------------------------------------------------------------------------
# Test chore IDs (deterministic 32-char hex strings)
# ---------------------------------------------------------------------------

CHORE_A_ID = "a" * 32
CHORE_B_ID = "b" * 32

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _chore_dict(
    name: str,
    interval_value: int,
    interval_unit: str,
    days_ago: int,
    chore_id: str = "",
) -> dict:
    last_completed = (dt_util.now().date() - timedelta(days=days_ago)).isoformat()
    return {
        "id": chore_id,
        "name": name,
        "interval_value": interval_value,
        "interval_unit": interval_unit,
        "last_completed": last_completed,
    }


def _make_entry(
    chore_dicts: list[dict], entry_id: str = "test_entry_id"
) -> MockConfigEntry:
    """Return a MockConfigEntry with the given chore dicts in entry.options."""
    return MockConfigEntry(
        domain=DOMAIN,
        entry_id=entry_id,
        options={CONF_CHORES: chore_dicts},
    )


# ---------------------------------------------------------------------------
# Unit tests: helpers (no HA required)
# ---------------------------------------------------------------------------


def test_interval_to_timedelta_days() -> None:
    config = ChoreConfig(
        name="test",
        interval_value=14,
        interval_unit="days",
        last_completed=dt_util.now().date(),
    )
    assert _interval_to_timedelta(config) == timedelta(days=14)


def test_interval_to_timedelta_weeks() -> None:
    config = ChoreConfig(
        name="test",
        interval_value=2,
        interval_unit="weeks",
        last_completed=dt_util.now().date(),
    )
    assert _interval_to_timedelta(config) == timedelta(days=14)


# ---------------------------------------------------------------------------
# Coordinator tests (uses real hass fixture)
# ---------------------------------------------------------------------------


@pytest.fixture
def two_chore_entry() -> MockConfigEntry:
    """A MockConfigEntry with chore A (overdue) and chore B (done)."""
    return _make_entry(
        [
            _chore_dict(
                "Chore A", 7, "days", 30, CHORE_A_ID
            ),  # last_completed 30 days ago, 7d interval -> overdue
            _chore_dict(
                "Chore B", 7, "days", 0, CHORE_B_ID
            ),  # last_completed today, 7d interval -> done
        ]
    )


async def test_initial_status_and_next_due(
    hass: Any, two_chore_entry: MockConfigEntry
) -> None:
    """Coordinator correctly derives done/overdue on first refresh."""
    with (
        patch(
            "custom_components.chores.coordinator.Store.async_load",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch("custom_components.chores.coordinator.async_track_point_in_time"),
    ):
        coord = ChoresCoordinator(hass, two_chore_entry)
        await coord.async_initialize()

    data = coord.data
    # Chore A: 30 days ago, 7d interval -> overdue
    assert data[CHORE_A_ID]["status"] == "overdue"
    # Chore B: today, 7d interval -> done
    assert data[CHORE_B_ID]["status"] == "done"
    # next_due for B should be roughly today + 7 days
    next_due_b: datetime = data[CHORE_B_ID]["next_due"]
    expected_date = dt_util.now().date() + timedelta(days=7)
    assert next_due_b.date() == expected_date


async def test_timer_fires_overdue_transition(
    hass: Any, two_chore_entry: MockConfigEntry
) -> None:
    """When the scheduled timer fires, status transitions to overdue."""
    captured_callback: dict[str, Any] = {}

    def _fake_track(hass_, callback, point_in_time):
        captured_callback["cb"] = callback
        return MagicMock()  # cancel handle

    with (
        patch(
            "custom_components.chores.coordinator.Store.async_load",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "custom_components.chores.coordinator.async_track_point_in_time",
            side_effect=_fake_track,
        ),
    ):
        coord = ChoresCoordinator(hass, two_chore_entry)
        await coord.async_initialize()

    # Chore B starts as "done"; fire its timer
    assert coord.data[CHORE_B_ID]["status"] == "done"
    assert "cb" in captured_callback

    # Simulate time passing: next_due has elapsed
    future = datetime.now(tz=UTC) + timedelta(days=8)
    with patch("custom_components.chores.coordinator.dt_util.now", return_value=future):
        captured_callback["cb"](future)

    assert coord.data[CHORE_B_ID]["status"] == "overdue"


async def test_complete_resets_to_done(
    hass: Any, two_chore_entry: MockConfigEntry
) -> None:
    """async_complete sets last_completed to today, status to done, and recomputes next_due."""
    with (
        patch(
            "custom_components.chores.coordinator.Store.async_load",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "custom_components.chores.coordinator.Store.async_save",
            new_callable=AsyncMock,
        ),
        patch("custom_components.chores.coordinator.async_track_point_in_time"),
    ):
        coord = ChoresCoordinator(hass, two_chore_entry)
        await coord.async_initialize()

        # Chore A starts overdue
        assert coord.data[CHORE_A_ID]["status"] == "overdue"

        await coord.async_complete(CHORE_A_ID)

    data = coord.data
    assert data[CHORE_A_ID]["status"] == "done"
    assert data[CHORE_A_ID]["last_completed"] == dt_util.now().date()
    # next_due should now be in the future
    assert data[CHORE_A_ID]["next_due"] > datetime.now(tz=UTC)


async def test_last_completed_survives_restart(
    hass: Any, two_chore_entry: MockConfigEntry
) -> None:
    """After completing a chore, a reload reads from the store and retains state."""
    saved_payload: dict[str, str] = {}

    async def fake_save(data: dict) -> None:
        saved_payload.update(data)

    async def fake_load() -> dict | None:
        return saved_payload if saved_payload else None

    with (
        patch(
            "custom_components.chores.coordinator.Store.async_load",
            new_callable=AsyncMock,
            side_effect=fake_load,
        ),
        patch(
            "custom_components.chores.coordinator.Store.async_save",
            new_callable=AsyncMock,
            side_effect=fake_save,
        ),
        patch("custom_components.chores.coordinator.async_track_point_in_time"),
    ):
        # First load and complete chore A
        coord = ChoresCoordinator(hass, two_chore_entry)
        await coord.async_initialize()
        await coord.async_complete(CHORE_A_ID)
        completion_date = coord.data[CHORE_A_ID]["last_completed"]

        # Simulate restart: create new coordinator with same entry
        coord2 = ChoresCoordinator(hass, two_chore_entry)
        await coord2.async_initialize()

    assert coord2.data[CHORE_A_ID]["last_completed"] == completion_date
    assert coord2.data[CHORE_A_ID]["status"] == "done"


async def test_unload_cancels_timers(
    hass: Any, two_chore_entry: MockConfigEntry
) -> None:
    """async_shutdown_timers cancels all scheduled callbacks."""
    cancel_mocks: list[MagicMock] = []

    def _fake_track(hass_, callback, point_in_time):
        cancel = MagicMock()
        cancel_mocks.append(cancel)
        return cancel

    with (
        patch(
            "custom_components.chores.coordinator.Store.async_load",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "custom_components.chores.coordinator.async_track_point_in_time",
            side_effect=_fake_track,
        ),
    ):
        coord = ChoresCoordinator(hass, two_chore_entry)
        await coord.async_initialize()

    # There should be a timer for chore B (the "done" chore with a future next_due)
    assert len(cancel_mocks) >= 1

    coord.async_shutdown_timers()

    for mock in cancel_mocks:
        mock.assert_called_once()


# ---------------------------------------------------------------------------
# Snooze tests
# ---------------------------------------------------------------------------


async def test_snooze_transitions_to_snoozed(
    hass: Any, two_chore_entry: MockConfigEntry
) -> None:
    """async_snooze sets status to snoozed and exposes snooze_until."""
    with (
        patch(
            "custom_components.chores.coordinator.Store.async_load",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "custom_components.chores.coordinator.Store.async_save",
            new_callable=AsyncMock,
        ),
        patch("custom_components.chores.coordinator.async_track_point_in_time"),
    ):
        coord = ChoresCoordinator(hass, two_chore_entry)
        await coord.async_initialize()

        snooze_date = dt_util.now().date() + timedelta(days=3)
        await coord.async_snooze(CHORE_A_ID, snooze_date)

    data = coord.data
    assert data[CHORE_A_ID]["status"] == "snoozed"
    assert data[CHORE_A_ID]["snooze_until"] == snooze_date


async def test_snooze_expiry_recomputes_state(
    hass: Any, two_chore_entry: MockConfigEntry
) -> None:
    """When the snooze timer fires, status is recalculated."""
    captured_snooze_cb: dict[str, Any] = {}

    def _fake_track(hass_, cb, point_in_time):
        captured_snooze_cb["cb"] = cb
        return MagicMock()

    with (
        patch(
            "custom_components.chores.coordinator.Store.async_load",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "custom_components.chores.coordinator.Store.async_save",
            new_callable=AsyncMock,
        ),
        patch(
            "custom_components.chores.coordinator.async_track_point_in_time",
            side_effect=_fake_track,
        ),
    ):
        coord = ChoresCoordinator(hass, two_chore_entry)
        await coord.async_initialize()

        # Snooze an overdue chore (no overdue timer, so snooze timer is first)
        snooze_date = dt_util.now().date() + timedelta(days=3)
        await coord.async_snooze(CHORE_A_ID, snooze_date)

    assert coord.data[CHORE_A_ID]["status"] == "snoozed"
    assert "cb" in captured_snooze_cb

    # Simulate snooze expiry — chore_a was overdue before snooze
    future = datetime.now(tz=UTC) + timedelta(days=4)
    with patch("custom_components.chores.coordinator.dt_util.now", return_value=future):
        captured_snooze_cb["cb"](future)

    assert coord.data[CHORE_A_ID]["status"] == "overdue"
    assert coord.data[CHORE_A_ID]["snooze_until"] is None


@pytest.mark.parametrize(
    "bad_date",
    [
        pytest.param(dt_util.now().date() - timedelta(days=1), id="yesterday"),
        pytest.param(dt_util.now().date(), id="today"),
    ],
)
async def test_snooze_non_future_date_raises(
    hass: Any, two_chore_entry: MockConfigEntry, bad_date: date
) -> None:
    """async_snooze with today or a past date raises HomeAssistantError without mutating state."""
    with (
        patch(
            "custom_components.chores.coordinator.Store.async_load",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "custom_components.chores.coordinator.Store.async_save",
            new_callable=AsyncMock,
        ),
        patch("custom_components.chores.coordinator.async_track_point_in_time"),
    ):
        coord = ChoresCoordinator(hass, two_chore_entry)
        await coord.async_initialize()

        with pytest.raises(HomeAssistantError):
            await coord.async_snooze(CHORE_A_ID, bad_date)

    assert coord.data[CHORE_A_ID]["status"] != "snoozed"
    assert coord.data[CHORE_A_ID]["snooze_until"] is None


async def test_complete_clears_snooze(
    hass: Any, two_chore_entry: MockConfigEntry
) -> None:
    """Completing a snoozed chore clears the snooze and marks it done."""
    with (
        patch(
            "custom_components.chores.coordinator.Store.async_load",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "custom_components.chores.coordinator.Store.async_save",
            new_callable=AsyncMock,
        ),
        patch("custom_components.chores.coordinator.async_track_point_in_time"),
    ):
        coord = ChoresCoordinator(hass, two_chore_entry)
        await coord.async_initialize()

        snooze_date = dt_util.now().date() + timedelta(days=3)
        await coord.async_snooze(CHORE_A_ID, snooze_date)
        assert coord.data[CHORE_A_ID]["status"] == "snoozed"

        await coord.async_complete(CHORE_A_ID)

    data = coord.data
    assert data[CHORE_A_ID]["status"] == "done"
    assert data[CHORE_A_ID]["snooze_until"] is None


async def test_snooze_survives_restart(
    hass: Any, two_chore_entry: MockConfigEntry
) -> None:
    """snooze_until is persisted to the store and restored on restart."""
    saved_payload: dict[str, Any] = {}

    async def fake_save(data: dict) -> None:
        saved_payload.update(data)

    async def fake_load() -> dict | None:
        return saved_payload if saved_payload else None

    with (
        patch(
            "custom_components.chores.coordinator.Store.async_load",
            new_callable=AsyncMock,
            side_effect=fake_load,
        ),
        patch(
            "custom_components.chores.coordinator.Store.async_save",
            new_callable=AsyncMock,
            side_effect=fake_save,
        ),
        patch("custom_components.chores.coordinator.async_track_point_in_time"),
    ):
        coord = ChoresCoordinator(hass, two_chore_entry)
        await coord.async_initialize()

        snooze_date = dt_util.now().date() + timedelta(days=5)
        await coord.async_snooze(CHORE_A_ID, snooze_date)

        # Simulate restart
        coord2 = ChoresCoordinator(hass, two_chore_entry)
        await coord2.async_initialize()

    assert coord2.data[CHORE_A_ID]["status"] == "snoozed"
    assert coord2.data[CHORE_A_ID]["snooze_until"] == snooze_date


async def test_expired_snooze_not_restored_on_restart(
    hass: Any, two_chore_entry: MockConfigEntry
) -> None:
    """An expired snooze_until is discarded on restart, not restored."""
    snooze_date = dt_util.now().date() - timedelta(days=1)  # already past
    stored = {
        CHORE_A_ID: {
            "last_completed": (dt_util.now().date() - timedelta(days=30)).isoformat(),
            "snooze_until": snooze_date.isoformat(),
        }
    }

    with (
        patch(
            "custom_components.chores.coordinator.Store.async_load",
            new_callable=AsyncMock,
            return_value=stored,
        ),
        patch("custom_components.chores.coordinator.async_track_point_in_time"),
    ):
        coord = ChoresCoordinator(hass, two_chore_entry)
        await coord.async_initialize()

    assert coord.data[CHORE_A_ID]["status"] == "overdue"
    assert coord.data[CHORE_A_ID]["snooze_until"] is None


async def test_unsnooze_clears_snooze_and_recalculates(
    hass: Any, two_chore_entry: MockConfigEntry
) -> None:
    """Unsnooze on a snoozed overdue chore: snooze_until cleared, status returns to overdue."""
    snooze_date = dt_util.now().date() + timedelta(days=3)
    stored = {
        CHORE_A_ID: {
            "last_completed": (dt_util.now().date() - timedelta(days=30)).isoformat(),
            "snooze_until": snooze_date.isoformat(),
        }
    }

    with (
        patch(
            "custom_components.chores.coordinator.Store.async_load",
            new_callable=AsyncMock,
            return_value=stored,
        ),
        patch(
            "custom_components.chores.coordinator.Store.async_save",
            new_callable=AsyncMock,
        ),
        patch("custom_components.chores.coordinator.async_track_point_in_time"),
    ):
        coord = ChoresCoordinator(hass, two_chore_entry)
        await coord.async_initialize()

        assert coord.data[CHORE_A_ID]["status"] == "snoozed"
        assert coord.data[CHORE_A_ID]["snooze_until"] == snooze_date

        await coord.async_unsnooze(CHORE_A_ID)

    assert coord.data[CHORE_A_ID]["snooze_until"] is None
    assert coord.data[CHORE_A_ID]["status"] == "overdue"


async def test_unsnooze_done_chore_reschedules_timer(
    hass: Any, two_chore_entry: MockConfigEntry
) -> None:
    """Unsnooze on a snoozed done chore: status returns to done."""
    snooze_date = dt_util.now().date() + timedelta(days=3)
    # last_completed yesterday, interval 7d -> not yet overdue
    stored = {
        CHORE_A_ID: {
            "last_completed": (dt_util.now().date() - timedelta(days=1)).isoformat(),
            "snooze_until": snooze_date.isoformat(),
        }
    }

    cancel_mock = MagicMock()
    with (
        patch(
            "custom_components.chores.coordinator.Store.async_load",
            new_callable=AsyncMock,
            return_value=stored,
        ),
        patch(
            "custom_components.chores.coordinator.Store.async_save",
            new_callable=AsyncMock,
        ),
        patch(
            "custom_components.chores.coordinator.async_track_point_in_time",
            return_value=cancel_mock,
        ),
    ):
        coord = ChoresCoordinator(hass, two_chore_entry)
        await coord.async_initialize()

        assert coord.data[CHORE_A_ID]["status"] == "snoozed"

        await coord.async_unsnooze(CHORE_A_ID)

    assert coord.data[CHORE_A_ID]["snooze_until"] is None
    assert coord.data[CHORE_A_ID]["status"] == "done"


async def test_unsnooze_on_non_snoozed_is_noop(
    hass: Any, two_chore_entry: MockConfigEntry
) -> None:
    """Calling async_unsnooze on a chore not in snoozed state is a no-op."""
    stored = {
        CHORE_A_ID: {
            "last_completed": (dt_util.now().date() - timedelta(days=30)).isoformat(),
            "snooze_until": None,
        }
    }

    save_mock = AsyncMock()
    with (
        patch(
            "custom_components.chores.coordinator.Store.async_load",
            new_callable=AsyncMock,
            return_value=stored,
        ),
        patch(
            "custom_components.chores.coordinator.Store.async_save",
            save_mock,
        ),
        patch("custom_components.chores.coordinator.async_track_point_in_time"),
    ):
        coord = ChoresCoordinator(hass, two_chore_entry)
        await coord.async_initialize()

        status_before = coord.data[CHORE_A_ID]["status"]
        await coord.async_unsnooze(CHORE_A_ID)

    assert coord.data[CHORE_A_ID]["status"] == status_before
    assert coord.data[CHORE_A_ID]["snooze_until"] is None
    save_mock.assert_not_called()


# ---------------------------------------------------------------------------
# UUID identity tests
# ---------------------------------------------------------------------------


async def test_re_added_chore_does_not_inherit_stale_state(hass: Any) -> None:
    """A new chore with the same name as a removed one does not inherit stored state."""
    removed_id = "dead" * 8  # 32-char hex
    new_id = "cafe" * 8
    stale_date = (dt_util.now().date() - timedelta(days=5)).isoformat()

    # Store has data for the removed chore under its old UUID
    stored = {
        removed_id: {"last_completed": stale_date, "snooze_until": None},
    }

    config_last_completed = (dt_util.now().date() - timedelta(days=1)).isoformat()
    entry = _make_entry(
        [
            {
                "id": new_id,
                "name": "Bins",
                "interval_value": 7,
                "interval_unit": "days",
                "last_completed": config_last_completed,
            }
        ]
    )

    with (
        patch(
            "custom_components.chores.coordinator.Store.async_load",
            new_callable=AsyncMock,
            return_value=stored,
        ),
        patch(
            "custom_components.chores.coordinator.Store.async_save",
            new_callable=AsyncMock,
        ),
        patch("custom_components.chores.coordinator.async_track_point_in_time"),
    ):
        coord = ChoresCoordinator(hass, entry)
        await coord.async_initialize()

    # The new chore uses its own config's last_completed, not the stale stored value
    assert coord.data[new_id]["last_completed"].isoformat() == config_last_completed


async def test_removed_chore_pruned_from_storage(hass: Any) -> None:
    """A stale store key left by a removed chore is pruned on async_initialize."""
    stale_id = "dead" * 8

    stored = {
        CHORE_A_ID: {
            "last_completed": (dt_util.now().date() - timedelta(days=1)).isoformat(),
            "snooze_until": None,
        },
        stale_id: {
            "last_completed": (dt_util.now().date() - timedelta(days=30)).isoformat(),
            "snooze_until": None,
        },
    }

    saved_payload: dict[str, Any] = {}

    async def fake_save(data: dict) -> None:
        saved_payload.clear()
        saved_payload.update(data)

    entry = _make_entry([_chore_dict("Chore A", 7, "days", 1, CHORE_A_ID)])

    with (
        patch(
            "custom_components.chores.coordinator.Store.async_load",
            new_callable=AsyncMock,
            return_value=stored,
        ),
        patch(
            "custom_components.chores.coordinator.Store.async_save",
            new_callable=AsyncMock,
            side_effect=fake_save,
        ),
        patch("custom_components.chores.coordinator.async_track_point_in_time"),
    ):
        coord = ChoresCoordinator(hass, entry)
        await coord.async_initialize()

    # Stale key must be absent from what was saved
    assert stale_id not in saved_payload
    assert CHORE_A_ID in saved_payload
