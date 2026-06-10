"""Tests for the Chores coordinator."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.chores.const import CONF_CHORES, DOMAIN
from custom_components.chores.coordinator import (
    ChoresCoordinator,
    _interval_to_timedelta,
    _unique_slug,
)
from custom_components.chores.models import ChoreConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _chore_dict(
    name: str, interval_value: int, interval_unit: str, days_ago: int
) -> dict:
    last_completed = (date.today() - timedelta(days=days_ago)).isoformat()
    return {
        "name": name,
        "interval_value": interval_value,
        "interval_unit": interval_unit,
        "last_completed": last_completed,
    }


def _make_entry(
    chore_dicts: list[dict], entry_id: str = "test_entry_id"
) -> MockConfigEntry:
    """Return a MockConfigEntry with the given chore dicts in entry.data."""
    return MockConfigEntry(
        domain=DOMAIN,
        entry_id=entry_id,
        data={CONF_CHORES: chore_dicts},
    )


# ---------------------------------------------------------------------------
# Unit tests: helpers (no HA required)
# ---------------------------------------------------------------------------


def test_unique_slug_no_collision() -> None:
    slug = _unique_slug("Vacuum Living Room", set())
    assert slug == "vacuum_living_room"


def test_unique_slug_collision() -> None:
    existing = {"vacuum_living_room"}
    slug = _unique_slug("Vacuum Living Room", existing)
    assert slug == "vacuum_living_room_1"


def test_interval_to_timedelta_days() -> None:
    config = ChoreConfig(
        name="test",
        interval_value=14,
        interval_unit="days",
        last_completed=date.today(),
    )
    assert _interval_to_timedelta(config) == timedelta(days=14)


def test_interval_to_timedelta_weeks() -> None:
    config = ChoreConfig(
        name="test",
        interval_value=2,
        interval_unit="weeks",
        last_completed=date.today(),
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
                "Chore A", 7, "days", 30
            ),  # last_completed 30 days ago, 7d interval -> overdue
            _chore_dict(
                "Chore B", 7, "days", 0
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
    assert data["chore_a"]["status"] == "overdue"
    # Chore B: today, 7d interval -> done
    assert data["chore_b"]["status"] == "done"
    # next_due for B should be roughly today + 7 days
    next_due_b: datetime = data["chore_b"]["next_due"]
    expected_date = date.today() + timedelta(days=7)
    assert next_due_b.date() == expected_date


async def test_timer_fires_overdue_transition(
    hass: Any, two_chore_entry: MockConfigEntry
) -> None:
    """When the scheduled timer fires, status transitions to overdue."""
    captured_callback: dict[str, Any] = {}

    def _fake_track(hass_, callback, point_in_time):  # noqa: ARG001
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
    assert coord.data["chore_b"]["status"] == "done"
    assert "cb" in captured_callback

    # Simulate time passing: next_due has elapsed
    future = datetime.now(tz=timezone.utc) + timedelta(days=8)
    with patch("custom_components.chores.coordinator.dt_util.now", return_value=future):
        captured_callback["cb"](future)

    assert coord.data["chore_b"]["status"] == "overdue"


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
        assert coord.data["chore_a"]["status"] == "overdue"

        await coord.async_complete("chore_a")

    data = coord.data
    assert data["chore_a"]["status"] == "done"
    assert data["chore_a"]["last_completed"] == date.today()
    # next_due should now be in the future
    assert data["chore_a"]["next_due"] > datetime.now(tz=timezone.utc)


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
        await coord.async_complete("chore_a")
        completion_date = coord.data["chore_a"]["last_completed"]

        # Simulate restart: create new coordinator with same entry
        coord2 = ChoresCoordinator(hass, two_chore_entry)
        await coord2.async_initialize()

    assert coord2.data["chore_a"]["last_completed"] == completion_date
    assert coord2.data["chore_a"]["status"] == "done"


async def test_unload_cancels_timers(
    hass: Any, two_chore_entry: MockConfigEntry
) -> None:
    """async_shutdown_timers cancels all scheduled callbacks."""
    cancel_mocks: list[MagicMock] = []

    def _fake_track(hass_, callback, point_in_time):  # noqa: ARG001
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

        snooze_date = date.today() + timedelta(days=3)
        await coord.async_snooze("chore_a", snooze_date)

    data = coord.data
    assert data["chore_a"]["status"] == "snoozed"
    assert data["chore_a"]["snooze_until"] == snooze_date


async def test_snooze_expiry_recomputes_state(
    hass: Any, two_chore_entry: MockConfigEntry
) -> None:
    """When the snooze timer fires, status is recalculated."""
    captured_snooze_cb: dict[str, Any] = {}

    def _fake_track(hass_, cb, point_in_time):  # noqa: ARG001
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
        snooze_date = date.today() + timedelta(days=3)
        await coord.async_snooze("chore_a", snooze_date)

    assert coord.data["chore_a"]["status"] == "snoozed"
    assert "cb" in captured_snooze_cb

    # Simulate snooze expiry — chore_a was overdue before snooze
    future = datetime.now(tz=timezone.utc) + timedelta(days=4)
    with patch("custom_components.chores.coordinator.dt_util.now", return_value=future):
        captured_snooze_cb["cb"](future)

    assert coord.data["chore_a"]["status"] == "overdue"
    assert coord.data["chore_a"]["snooze_until"] is None


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

        snooze_date = date.today() + timedelta(days=3)
        await coord.async_snooze("chore_a", snooze_date)
        assert coord.data["chore_a"]["status"] == "snoozed"

        await coord.async_complete("chore_a")

    data = coord.data
    assert data["chore_a"]["status"] == "done"
    assert data["chore_a"]["snooze_until"] is None


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

        snooze_date = date.today() + timedelta(days=5)
        await coord.async_snooze("chore_a", snooze_date)

        # Simulate restart
        coord2 = ChoresCoordinator(hass, two_chore_entry)
        await coord2.async_initialize()

    assert coord2.data["chore_a"]["status"] == "snoozed"
    assert coord2.data["chore_a"]["snooze_until"] == snooze_date


async def test_expired_snooze_not_restored_on_restart(
    hass: Any, two_chore_entry: MockConfigEntry
) -> None:
    """An expired snooze_until is discarded on restart, not restored."""
    snooze_date = date.today() - timedelta(days=1)  # already past
    stored = {
        "chore_a": {
            "last_completed": (date.today() - timedelta(days=30)).isoformat(),
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

    assert coord.data["chore_a"]["status"] == "overdue"
    assert coord.data["chore_a"]["snooze_until"] is None


@pytest.mark.asyncio
async def test_unsnooze_clears_snooze_and_recalculates(
    hass: Any, two_chore_entry: MockConfigEntry
) -> None:
    """Unsnooze on a snoozed overdue chore: snooze_until cleared, status returns to overdue."""
    snooze_date = date.today() + timedelta(days=3)
    stored = {
        "chore_a": {
            "last_completed": (date.today() - timedelta(days=30)).isoformat(),
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

        assert coord.data["chore_a"]["status"] == "snoozed"
        assert coord.data["chore_a"]["snooze_until"] == snooze_date

        await coord.async_unsnooze("chore_a")

    assert coord.data["chore_a"]["snooze_until"] is None
    assert coord.data["chore_a"]["status"] == "overdue"


@pytest.mark.asyncio
async def test_unsnooze_done_chore_reschedules_timer(
    hass: Any, two_chore_entry: MockConfigEntry
) -> None:
    """Unsnooze on a snoozed done chore: status returns to done."""
    snooze_date = date.today() + timedelta(days=3)
    # last_completed yesterday, interval 7d -> not yet overdue
    stored = {
        "chore_a": {
            "last_completed": (date.today() - timedelta(days=1)).isoformat(),
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

        assert coord.data["chore_a"]["status"] == "snoozed"

        await coord.async_unsnooze("chore_a")

    assert coord.data["chore_a"]["snooze_until"] is None
    assert coord.data["chore_a"]["status"] == "done"


@pytest.mark.asyncio
async def test_unsnooze_on_non_snoozed_is_noop(
    hass: Any, two_chore_entry: MockConfigEntry
) -> None:
    """Calling async_unsnooze on a chore not in snoozed state is a no-op."""
    stored = {
        "chore_a": {
            "last_completed": (date.today() - timedelta(days=30)).isoformat(),
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

        status_before = coord.data["chore_a"]["status"]
        await coord.async_unsnooze("chore_a")

    assert coord.data["chore_a"]["status"] == status_before
    assert coord.data["chore_a"]["snooze_until"] is None
    save_mock.assert_not_called()
