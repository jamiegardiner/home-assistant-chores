"""Tests for the Chores integration entry lifecycle."""

from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.chores import async_migrate_entry
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
            "interval_value": 7,
            "interval_unit": "days",
            "default_snooze_value": 1,
            "default_snooze_unit": "days",
            "notification_time": "08:00",
            "last_completed": dt_util.now().isoformat(),
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


# ---------------------------------------------------------------------------
# async_migrate_entry tests
# ---------------------------------------------------------------------------


async def test_migrate_entry_v1_renames_interval_days(hass) -> None:
    """v1 entry: interval_days is renamed to interval_value and interval_unit is added."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        entry_id="migrate_test",
        version=1,
        options={
            "name": "Bins",
            "interval_days": 14,
            "default_snooze_value": 1,
            "default_snooze_unit": "days",
            "notification_time": "08:00",
            "last_completed": None,
            "snooze_until": None,
        },
    )
    entry.add_to_hass(hass)

    with patch("custom_components.chores.coordinator.async_track_point_in_time"):
        result = await hass.config_entries.async_setup(entry.entry_id)

    assert result is True
    assert entry.version == 3
    assert "interval_days" not in entry.options
    assert entry.options["interval_value"] == 14
    assert entry.options["interval_unit"] == "days"


async def test_migrate_entry_v1_removes_old_entity(hass) -> None:
    """v1 migration removes the old _interval_days entity from the entity registry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        entry_id="migrate_test",
        version=1,
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
    entry.add_to_hass(hass)

    ent_reg = er.async_get(hass)
    ent_reg.async_get_or_create(
        "number",
        DOMAIN,
        "migrate_test_interval_days",
        config_entry=entry,
    )
    assert (
        ent_reg.async_get_entity_id("number", DOMAIN, "migrate_test_interval_days")
        is not None
    )

    with patch("custom_components.chores.coordinator.async_track_point_in_time"):
        await hass.config_entries.async_setup(entry.entry_id)

    assert (
        ent_reg.async_get_entity_id("number", DOMAIN, "migrate_test_interval_days")
        is None
    )


async def test_migrate_entry_v1_no_old_entity_succeeds(hass) -> None:
    """v1 migration succeeds even when the old _interval_days entity is absent."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        entry_id="migrate_test",
        version=1,
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
    entry.add_to_hass(hass)

    with patch("custom_components.chores.coordinator.async_track_point_in_time"):
        result = await hass.config_entries.async_setup(entry.entry_id)

    assert result is True
    assert entry.version == 3


async def test_migrate_entry_v2_computes_next_due(hass) -> None:
    """v2 entries pass through unchanged apart from a newly computed next_due."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        entry_id="test_entry_id",
        version=2,
        options={
            "name": "Bins",
            "interval_value": 7,
            "interval_unit": "days",
            "default_snooze_value": 1,
            "default_snooze_unit": "days",
            "notification_time": "08:00",
            "last_completed": dt_util.now().isoformat(),
            "snooze_until": None,
        },
    )
    entry.add_to_hass(hass)

    with patch("custom_components.chores.coordinator.async_track_point_in_time"):
        result = await hass.config_entries.async_setup(entry.entry_id)

    assert result is True
    assert entry.version == 3
    assert entry.options["interval_value"] == 7
    assert entry.options["interval_unit"] == "days"

    last_completed = dt_util.parse_datetime(entry.options["last_completed"])
    assert last_completed is not None
    expected_next_due = last_completed.date() + timedelta(days=7)
    next_due = dt_util.parse_datetime(entry.options["next_due"])
    assert next_due is not None
    assert next_due.date() == expected_next_due


async def test_migrate_entry_v2_never_completed_next_due_is_none(hass) -> None:
    """v2 entry with last_completed=None migrates to next_due=None."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        entry_id="migrate_test",
        version=2,
        options={
            "name": "Bins",
            "interval_value": 7,
            "interval_unit": "days",
            "default_snooze_value": 1,
            "default_snooze_unit": "days",
            "notification_time": "08:00",
            "last_completed": None,
            "snooze_until": None,
        },
    )
    entry.add_to_hass(hass)

    with patch("custom_components.chores.coordinator.async_track_point_in_time"):
        result = await hass.config_entries.async_setup(entry.entry_id)

    assert result is True
    assert entry.version == 3
    assert entry.options["next_due"] is None


async def test_migrate_entry_v2_corrupt_last_completed_does_not_crash(hass) -> None:
    """A naive (corrupt) last_completed does not crash migration; next_due ends up None."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        entry_id="migrate_test",
        version=2,
        options={
            "name": "Bins",
            "interval_value": 7,
            "interval_unit": "days",
            "default_snooze_value": 1,
            "default_snooze_unit": "days",
            "notification_time": "08:00",
            "last_completed": "2020-01-01",
            "snooze_until": None,
        },
    )
    entry.add_to_hass(hass)

    with patch("custom_components.chores.coordinator.async_track_point_in_time"):
        result = await hass.config_entries.async_setup(entry.entry_id)

    assert result is True
    assert entry.version == 3
    assert entry.options["next_due"] is None


async def test_migrate_entry_v2_corrupt_config_does_not_crash(hass) -> None:
    """A corrupt v2 config field does not crash migration; next_due ends up None.

    Calls async_migrate_entry directly rather than through the full setup flow,
    since the corrupt config subsequently fails async_initialize's own
    unrecoverable-config handling (a separate, already-tested code path).
    """
    entry = MockConfigEntry(
        domain=DOMAIN,
        entry_id="migrate_test",
        version=2,
        options={
            "name": "Bins",
            "interval_value": 0,
            "interval_unit": "days",
            "default_snooze_value": 1,
            "default_snooze_unit": "days",
            "notification_time": "08:00",
            "last_completed": dt_util.now().isoformat(),
            "snooze_until": None,
        },
    )
    entry.add_to_hass(hass)

    result = await async_migrate_entry(hass, entry)

    assert result is True
    assert entry.version == 3
    assert entry.options["next_due"] is None
