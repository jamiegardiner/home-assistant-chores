"""Tests for the Chores config flow and options flow."""

from __future__ import annotations

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
    """Submitting valid data creates a config entry with options set."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] == FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "name": "Bins",
            "interval_value": 2,
            "interval_unit": "weeks",
            "last_completed": "2026-06-01",
        },
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Bins"
    assert result["data"] == {}
    opts = result["options"]
    assert opts["name"] == "Bins"
    assert opts["interval_value"] == 2
    assert opts["interval_unit"] == "weeks"
    assert opts["last_completed"] == "2026-06-01"
    assert opts["snooze_until"] is None


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
                "interval_value": 7,
                "interval_unit": "days",
                "last_completed": "2026-06-01",
            },
        )
        assert result["type"] == FlowResultType.CREATE_ENTRY


async def test_user_flow_date_field_defaults_to_today(hass):
    """The initial form render has today's date as suggested_value for last_completed."""
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
    assert last_completed_key.description["suggested_value"] == str(
        dt_util.now().date()
    )


async def test_user_flow_rejects_empty_name(hass):
    """Submitting an empty name re-shows the form with name_required error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "name": "   ",
            "interval_value": 1,
            "interval_unit": "days",
            "last_completed": "2026-06-01",
        },
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert "name" in result["errors"]


async def test_user_flow_rejects_non_positive_interval(hass):
    """NumberSelector(min=1) rejects interval_value=0 at schema validation."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    with pytest.raises(InvalidData):
        await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "name": "Valid Name",
                "interval_value": 0,
                "interval_unit": "days",
                "last_completed": "2026-06-01",
            },
        )


async def test_user_flow_rejects_invalid_date(hass):
    """DateSelector rejects a malformed date at schema validation."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    with pytest.raises(InvalidData):
        await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "name": "Valid Name",
                "interval_value": 1,
                "interval_unit": "days",
                "last_completed": "not-a-date",
            },
        )


# ---------------------------------------------------------------------------
# Options flow (edit)
# ---------------------------------------------------------------------------


async def test_options_flow_shows_form(hass):
    """Options flow init step shows an edit form (not a menu)."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        options={
            "name": "Bins",
            "interval_value": 7,
            "interval_unit": "days",
            "last_completed": "2026-06-01",
            "snooze_until": None,
        },
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"


async def test_options_flow_prefills_current_values(hass):
    """Edit form is prefilled with existing option values."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        options={
            "name": "Bins",
            "interval_value": 7,
            "interval_unit": "days",
            "last_completed": "2026-06-01",
            "snooze_until": None,
        },
    )
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
    assert lc_key.description["suggested_value"] == "2026-06-01"


async def test_options_flow_saves_edits(hass):
    """Submitting valid edit data updates the entry options."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        options={
            "name": "Bins",
            "interval_value": 7,
            "interval_unit": "days",
            "last_completed": "2026-06-01",
            "snooze_until": None,
        },
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "name": "Wheelie Bins",
            "interval_value": 2,
            "interval_unit": "weeks",
            "last_completed": "2026-06-08",
        },
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert entry.options["name"] == "Wheelie Bins"
    assert entry.options["interval_value"] == 2
    assert entry.options["interval_unit"] == "weeks"
    assert entry.options["last_completed"] == "2026-06-08"


async def test_options_flow_preserves_snooze_until(hass):
    """Editing name/interval does not clear snooze_until."""
    snooze_date = (
        dt_util.now().date() + __import__("datetime").timedelta(days=3)
    ).isoformat()
    entry = MockConfigEntry(
        domain=DOMAIN,
        options={
            "name": "Bins",
            "interval_value": 7,
            "interval_unit": "days",
            "last_completed": "2026-06-01",
            "snooze_until": snooze_date,
        },
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "name": "Wheelie Bins",
            "interval_value": 7,
            "interval_unit": "days",
            "last_completed": "2026-06-01",
        },
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert entry.options["snooze_until"] == snooze_date


async def test_options_flow_rejects_empty_name(hass):
    """Submitting an empty name re-shows the form with name_required error."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        options={
            "name": "Bins",
            "interval_value": 7,
            "interval_unit": "days",
            "last_completed": "2026-06-01",
            "snooze_until": None,
        },
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "name": "   ",
            "interval_value": 1,
            "interval_unit": "days",
            "last_completed": "2026-06-01",
        },
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"
    assert "name" in result["errors"]


async def test_options_flow_rejects_non_positive_interval(hass):
    """NumberSelector(min=1) rejects interval_value=0 at schema validation in options flow."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        options={
            "name": "Bins",
            "interval_value": 7,
            "interval_unit": "days",
            "last_completed": "2026-06-01",
            "snooze_until": None,
        },
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    with pytest.raises(InvalidData):
        await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                "name": "Bins",
                "interval_value": 0,
                "interval_unit": "days",
                "last_completed": "2026-06-01",
            },
        )
