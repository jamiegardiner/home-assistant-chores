"""Shared helper functions for chores coordinator tests."""

from datetime import timedelta
from typing import Any

from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.chores.const import DOMAIN
from custom_components.chores.coordinator import ChoresCoordinator


def make_entry(
    name: str = "Bins",
    interval_value: int = 7,
    interval_unit: str = "days",
    default_snooze_value: int = 1,
    default_snooze_unit: str = "days",
    notification_time: str = "00:00",
    days_ago: int = 0,
    snooze_until: str | None = None,
    next_due: str | None = None,
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
        "interval_value": interval_value,
        "interval_unit": interval_unit,
        "default_snooze_value": default_snooze_value,
        "default_snooze_unit": default_snooze_unit,
        "notification_time": notification_time,
        "last_completed": last_completed,
        "snooze_until": snooze_until,
        "next_due": next_due,
    }
    return MockConfigEntry(domain=DOMAIN, entry_id=entry_id, options=opts)


async def setup_coord(hass: Any, entry: MockConfigEntry) -> ChoresCoordinator:
    """Create and initialize a coordinator (entry must already be added to hass)."""
    coord = ChoresCoordinator(hass, entry)
    await coord.async_initialize()
    return coord
