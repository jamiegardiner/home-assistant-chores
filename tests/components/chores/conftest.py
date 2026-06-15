"""Shared fixtures and helpers for chores coordinator tests."""

from datetime import timedelta
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.chores.const import DOMAIN
from custom_components.chores.coordinator import ChoresCoordinator

_TRACK_PATCH = "custom_components.chores.coordinator.async_track_point_in_time"


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


async def _setup_coord(hass: Any, entry: MockConfigEntry) -> ChoresCoordinator:
    """Create and initialize a coordinator (entry must already be added to hass)."""
    coord = ChoresCoordinator(hass, entry)
    await coord.async_initialize()
    return coord


@pytest.fixture(autouse=True)
def patch_track():
    with patch(_TRACK_PATCH) as mock_track:
        yield mock_track


@pytest.fixture
def fake_track(patch_track: MagicMock) -> dict[str, Any]:
    """Override the autouse timer patch to capture the scheduled callback."""
    captured: dict[str, Any] = {}

    def _side_effect(hass_: Any, cb: Any, point_in_time: Any) -> MagicMock:
        captured["cb"] = cb
        return MagicMock()

    patch_track.side_effect = _side_effect
    return captured
