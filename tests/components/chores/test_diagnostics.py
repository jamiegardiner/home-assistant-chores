"""Unit tests for custom_components/chores/diagnostics.py."""

from typing import Any

import pytest

from custom_components.chores.diagnostics import async_get_config_entry_diagnostics
from tests.components.chores.helpers import make_entry, setup_coord


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: Any) -> None:
    pass


async def test_returns_coordinator_snapshot(hass: Any) -> None:
    """Diagnostics output matches the live coordinator snapshot keys exactly."""
    entry = make_entry(days_ago=0, interval_value=7, notification_time="08:00")
    entry.add_to_hass(hass)
    coord = await setup_coord(hass, entry)
    entry.runtime_data = coord

    result = await async_get_config_entry_diagnostics(hass, entry)
    data = result["coordinator_data"]

    assert set(data.keys()) == {
        "name",
        "status",
        "last_completed",
        "next_due",
        "snooze_until",
        "interval_value",
        "interval_unit",
        "default_snooze_value",
        "default_snooze_unit",
        "notification_time",
    }
    assert data["status"] == "done"
    assert data["interval_value"] == 7
    assert data["interval_unit"] == "days"
    assert data["notification_time"] == "08:00"


async def test_returns_empty_dict_when_coordinator_data_is_none(hass: Any) -> None:
    """Returns empty coordinator_data when coordinator.data is None (pre-init state)."""
    entry = make_entry(days_ago=0, interval_value=7, notification_time="08:00")
    entry.add_to_hass(hass)
    coord = await setup_coord(hass, entry)
    coord.data = None
    entry.runtime_data = coord

    result = await async_get_config_entry_diagnostics(hass, entry)
    assert result == {"coordinator_data": {}}
