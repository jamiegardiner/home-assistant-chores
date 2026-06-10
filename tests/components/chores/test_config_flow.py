"""Tests for the Chores config flow and options flow."""

from __future__ import annotations

import pytest
import voluptuous as vol
from homeassistant.data_entry_flow import FlowResultType, InvalidData
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.chores.const import CONF_CHORES, DOMAIN


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):  # noqa: PT004
    """Enable custom integrations in all tests."""


async def test_user_flow_creates_single_entry(hass):
    """A first-time config flow creates the Chores entry with an empty chore list."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Chores"
    assert result["data"] == {CONF_CHORES: []}


async def test_user_flow_aborts_on_second_instance(hass):
    """A second config flow attempt aborts with single_instance_allowed."""
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_CHORES: []})
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


async def test_options_flow_shows_menu(hass):
    """Options flow init step shows the add/remove menu."""
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_CHORES: []})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == FlowResultType.MENU
    assert "add" in result["menu_options"]
    assert "remove" in result["menu_options"]


async def test_options_add_chore(hass):
    """Submitting valid add data stores a chore in the config entry."""
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_CHORES: []})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == FlowResultType.MENU

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "add"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "add"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "name": "Bins",
            "interval_value": 2,
            "interval_unit": "weeks",
            "last_completed": "2026-06-01",
        },
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY

    chores = entry.data[CONF_CHORES]
    assert len(chores) == 1
    assert chores[0]["name"] == "Bins"
    assert chores[0]["interval_value"] == 2
    assert chores[0]["interval_unit"] == "weeks"
    assert chores[0]["last_completed"] == "2026-06-01"


async def test_options_add_date_field_has_suggested_value(hass):
    """Initial add form render binds today's date as suggested_value for last_completed."""
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_CHORES: []})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "add"}
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


async def test_options_add_rejects_empty_name(hass):
    """Submitting an empty name re-shows the form with an error."""
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_CHORES: []})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "add"}
    )
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
    assert result["step_id"] == "add"
    assert "name" in result["errors"]


async def test_options_add_rejects_non_positive_interval(hass):
    """NumberSelector(min=1) rejects interval_value=0 at schema validation."""
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_CHORES: []})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "add"}
    )
    with pytest.raises(InvalidData):
        await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                "name": "Valid Name",
                "interval_value": 0,
                "interval_unit": "days",
                "last_completed": "2026-06-01",
            },
        )


async def test_options_remove_chore(hass):
    """Selecting a chore to remove removes it from the stored list."""
    existing_chore = {
        "name": "Mow lawn",
        "interval_value": 1,
        "interval_unit": "weeks",
        "last_completed": "2026-06-01",
    }
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_CHORES: [existing_chore]})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == FlowResultType.MENU

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "remove"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "remove"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"chore": "0"}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert entry.data[CONF_CHORES] == []


async def test_options_add_rejects_invalid_date(hass):
    """DateSelector rejects a malformed date at schema validation."""
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_CHORES: []})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "add"}
    )
    with pytest.raises(InvalidData):
        await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                "name": "Valid Name",
                "interval_value": 1,
                "interval_unit": "days",
                "last_completed": "not-a-date",
            },
        )


async def test_options_add_rejects_duplicate_name(hass):
    """Adding a chore with an exact duplicate name re-shows the form with an error."""
    existing_chore = {
        "name": "Bins",
        "interval_value": 1,
        "interval_unit": "weeks",
        "last_completed": "2026-06-01",
    }
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_CHORES: [existing_chore]})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "add"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "name": "Bins",
            "interval_value": 1,
            "interval_unit": "days",
            "last_completed": "2026-06-01",
        },
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "add"
    assert result["errors"].get("name") == "duplicate_name"


async def test_options_add_rejects_duplicate_name_case_insensitive(hass):
    """Duplicate name check is case-insensitive."""
    existing_chore = {
        "name": "Bins",
        "interval_value": 1,
        "interval_unit": "weeks",
        "last_completed": "2026-06-01",
    }
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_CHORES: [existing_chore]})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "add"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "name": "BINS",
            "interval_value": 1,
            "interval_unit": "days",
            "last_completed": "2026-06-01",
        },
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "add"
    assert result["errors"].get("name") == "duplicate_name"


async def test_options_remove_aborts_when_no_chores(hass):
    """The remove step aborts immediately when no chores exist."""
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_CHORES: []})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "remove"}
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "no_chores"
