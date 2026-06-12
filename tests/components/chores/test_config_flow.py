"""Tests for the Chores config flow and options flow."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
import voluptuous as vol
from homeassistant.data_entry_flow import FlowResultType, InvalidData
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.chores.const import DOMAIN


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations in all tests."""


# ---------------------------------------------------------------------------
# Config flow (create)
# ---------------------------------------------------------------------------


async def test_user_flow_shows_form(hass):
    """The user flow shows the chore creation form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"


async def test_user_flow_creates_entry_with_options(hass):
    """Submitting valid data creates a config entry with a tz-aware last_completed."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] == FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "name": "Bins",
            "interval_days": 14,
            "default_snooze_value": 3,
            "default_snooze_unit": "hours",
            "last_completed": "2026-06-01 00:00:00",
        },
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Bins"
    assert result["data"] == {}
    opts = result["options"]
    assert opts["name"] == "Bins"
    assert opts["interval_days"] == 14
    assert opts["default_snooze_value"] == 3
    assert opts["default_snooze_unit"] == "hours"
    stored_dt = datetime.fromisoformat(opts["last_completed"])
    assert stored_dt.tzinfo is not None
    assert stored_dt.date().isoformat() == "2026-06-01"
    assert opts["snooze_until"] is None
    assert "default_snooze_days" not in opts


async def test_user_flow_default_snooze_defaults(hass):
    """interval_days=7 with no explicit snooze fields saves value=1, unit=days."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "name": "Bins",
            "interval_days": 7,
            "default_snooze_value": 1,
            "default_snooze_unit": "days",
            "last_completed": "2026-06-01 00:00:00",
        },
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["options"]["default_snooze_value"] == 1
    assert result["options"]["default_snooze_unit"] == "days"


async def test_user_flow_all_valid_units(hass):
    """All supported snooze units are accepted."""
    for unit in ("minutes", "hours", "days", "weeks"):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "name": "Bins",
                "interval_days": 7,
                "default_snooze_value": 1,
                "default_snooze_unit": unit,
                "last_completed": "2026-06-01 00:00:00",
            },
        )
        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["options"]["default_snooze_unit"] == unit


async def test_user_flow_multiple_entries_allowed(hass):
    """A second chore entry can be created (no single-instance restriction)."""
    for name in ("Bins", "Dishes"):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "name": name,
                "interval_days": 7,
                "default_snooze_value": 1,
                "default_snooze_unit": "days",
                "last_completed": "2026-06-01 00:00:00",
            },
        )
        assert result["type"] == FlowResultType.CREATE_ENTRY


async def test_user_flow_date_field_defaults_to_now(hass):
    """The initial form render has the current datetime as suggested_value for last_completed."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] == FlowResultType.FORM

    schema = result["data_schema"]
    last_completed_key = next(
        k
        for k in schema.schema
        if isinstance(k, vol.Required) and k.schema == "last_completed"
    )
    suggested = last_completed_key.description["suggested_value"]
    assert suggested.startswith(str(dt_util.now().date()))


async def test_user_flow_rejects_empty_name(hass):
    """Submitting an empty name re-shows the form with name_required error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "name": "   ",
            "interval_days": 1,
            "default_snooze_value": 1,
            "default_snooze_unit": "days",
            "last_completed": "2026-06-01 00:00:00",
        },
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert "name" in result["errors"]


async def test_user_flow_rejects_non_positive_interval(hass):
    """NumberSelector(min=1) rejects interval_days=0 at schema validation."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    with pytest.raises(InvalidData):
        await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "name": "Valid Name",
                "interval_days": 0,
                "default_snooze_value": 1,
                "default_snooze_unit": "days",
                "last_completed": "2026-06-01 00:00:00",
            },
        )


async def test_user_flow_rejects_invalid_datetime(hass):
    """DateTimeSelector rejects a malformed datetime at schema validation."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    with pytest.raises(InvalidData):
        await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "name": "Valid Name",
                "interval_days": 1,
                "default_snooze_value": 1,
                "default_snooze_unit": "days",
                "last_completed": "not-a-datetime",
            },
        )


async def test_user_flow_rejects_future_datetime(hass):
    """Submitting a future last_completed re-shows the form with future_completed_at error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    future = dt_util.now() + timedelta(days=1)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "name": "Bins",
            "interval_days": 7,
            "default_snooze_value": 1,
            "default_snooze_unit": "days",
            "last_completed": future.isoformat(sep=" ", timespec="seconds"),
        },
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert "last_completed" in result["errors"]


# ---------------------------------------------------------------------------
# Options flow (edit)
# ---------------------------------------------------------------------------

_BASE_OPTS = {
    "name": "Bins",
    "interval_days": 7,
    "default_snooze_value": 1,
    "default_snooze_unit": "days",
    "last_completed": "2026-06-01T00:00:00+00:00",
    "snooze_until": None,
}


async def test_options_flow_shows_form(hass):
    """Options flow init step shows an edit form (not a menu)."""
    entry = MockConfigEntry(domain=DOMAIN, options=dict(_BASE_OPTS))
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"


async def test_options_flow_prefills_current_values(hass):
    """Edit form is prefilled with existing option values."""
    entry = MockConfigEntry(domain=DOMAIN, options=dict(_BASE_OPTS))
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == FlowResultType.FORM

    schema = result["data_schema"]
    name_key = next(
        k for k in schema.schema if isinstance(k, vol.Required) and k.schema == "name"
    )
    assert name_key.description["suggested_value"] == "Bins"

    lc_key = next(
        k
        for k in schema.schema
        if isinstance(k, vol.Required) and k.schema == "last_completed"
    )
    # Suggested value is a naive local-time string (what DateTimeSelector expects)
    stored_dt = datetime.fromisoformat("2026-06-01T00:00:00+00:00")
    expected_suggestion = dt_util.as_local(stored_dt).strftime("%Y-%m-%d %H:%M:%S")
    assert lc_key.description["suggested_value"] == expected_suggestion

    interval_key = next(
        k
        for k in schema.schema
        if isinstance(k, vol.Required) and k.schema == "interval_days"
    )
    assert interval_key.description["suggested_value"] == 7


async def test_options_flow_saves_edits(hass):
    """Submitting valid edit data updates the entry options with a tz-aware last_completed."""
    entry = MockConfigEntry(domain=DOMAIN, options=dict(_BASE_OPTS))
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "name": "Wheelie Bins",
            "interval_days": 14,
            "default_snooze_value": 2,
            "default_snooze_unit": "hours",
            "last_completed": "2026-06-08 14:30:00",
        },
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert entry.options["name"] == "Wheelie Bins"
    assert entry.options["interval_days"] == 14
    assert entry.options["default_snooze_value"] == 2
    assert entry.options["default_snooze_unit"] == "hours"
    stored_dt = datetime.fromisoformat(entry.options["last_completed"])
    assert stored_dt.tzinfo is not None
    assert stored_dt.date().isoformat() == "2026-06-08"
    assert "default_snooze_days" not in entry.options


async def test_options_flow_preserves_snooze_until(hass):
    """Editing name/interval does not clear snooze_until."""
    snooze_dt = (dt_util.now() + timedelta(days=3)).isoformat()
    opts = {**_BASE_OPTS, "snooze_until": snooze_dt}
    entry = MockConfigEntry(domain=DOMAIN, options=opts)
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "name": "Wheelie Bins",
            "interval_days": 7,
            "default_snooze_value": 1,
            "default_snooze_unit": "days",
            "last_completed": "2026-06-01 00:00:00",
        },
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert entry.options["snooze_until"] == snooze_dt


async def test_options_flow_rejects_empty_name(hass):
    """Submitting an empty name re-shows the form with name_required error."""
    entry = MockConfigEntry(domain=DOMAIN, options=dict(_BASE_OPTS))
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "name": "   ",
            "interval_days": 1,
            "default_snooze_value": 1,
            "default_snooze_unit": "days",
            "last_completed": "2026-06-01 00:00:00",
        },
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"
    assert "name" in result["errors"]


async def test_options_flow_rejects_non_positive_interval(hass):
    """NumberSelector(min=1) rejects interval_days=0 at schema validation in options flow."""
    entry = MockConfigEntry(domain=DOMAIN, options=dict(_BASE_OPTS))
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    with pytest.raises(InvalidData):
        await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                "name": "Bins",
                "interval_days": 0,
                "default_snooze_value": 1,
                "default_snooze_unit": "days",
                "last_completed": "2026-06-01 00:00:00",
            },
        )


async def test_options_flow_rejects_future_datetime(hass):
    """Submitting a future last_completed in the options flow re-shows the form with an error."""
    entry = MockConfigEntry(domain=DOMAIN, options=dict(_BASE_OPTS))
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)

    future = dt_util.now() + timedelta(days=1)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "name": "Bins",
            "interval_days": 7,
            "default_snooze_value": 1,
            "default_snooze_unit": "days",
            "last_completed": future.isoformat(sep=" ", timespec="seconds"),
        },
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"
    assert "last_completed" in result["errors"]
