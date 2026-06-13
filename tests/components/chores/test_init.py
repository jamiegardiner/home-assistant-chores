"""Tests for the Chores integration entry lifecycle."""

from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.chores.const import DOMAIN


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    pass


def _make_entry(entry_id: str = "test_entry_id") -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        entry_id=entry_id,
        options={
            "name": "Bins",
            "interval_days": 7,
            "default_snooze_value": 1,
            "default_snooze_unit": "days",
            "notification_time": "08:00",
            "last_completed": None,
            "snooze_until": None,
        },
    )


async def test_setup_entry_creates_coordinator(hass) -> None:
    """async_setup_entry creates a coordinator and stores it in runtime_data."""
    entry = _make_entry()
    entry.add_to_hass(hass)

    with patch("custom_components.chores.coordinator.async_track_point_in_time"):
        assert await hass.config_entries.async_setup(entry.entry_id)

    assert entry.runtime_data is not None


async def test_unload_entry_succeeds(hass) -> None:
    """async_unload_entry succeeds and removes runtime_data."""
    entry = _make_entry()
    entry.add_to_hass(hass)

    with patch("custom_components.chores.coordinator.async_track_point_in_time"):
        await hass.config_entries.async_setup(entry.entry_id)
        assert await hass.config_entries.async_unload(entry.entry_id)


async def test_update_listener_calls_async_update_config(hass) -> None:
    """Options update triggers async_update_config, not async_reload."""
    entry = _make_entry()
    entry.add_to_hass(hass)

    with patch("custom_components.chores.coordinator.async_track_point_in_time"):
        await hass.config_entries.async_setup(entry.entry_id)

    coordinator = entry.runtime_data
    update_config_mock = AsyncMock()
    coordinator.async_update_config = update_config_mock

    new_opts = {**dict(entry.options), "name": "Wheelie Bins"}
    hass.config_entries.async_update_entry(entry, options=new_opts)
    await hass.async_block_till_done()

    update_config_mock.assert_awaited_once_with(new_opts)
