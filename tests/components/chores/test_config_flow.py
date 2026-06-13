"""Tests for the Chores config flow."""

import pytest
from homeassistant.data_entry_flow import FlowResultType, InvalidData

from custom_components.chores.const import DOMAIN


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations in all tests."""


async def test_user_flow_shows_form(hass):
    """The user flow shows the chore creation form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"


async def test_user_flow_creates_entry_with_options(hass):
    """Submitting valid data creates a config entry with last_completed=None."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] == FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"name": "Bins", "interval_days": 14},
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Bins"
    assert result["data"] == {}
    opts = result["options"]
    assert opts["name"] == "Bins"
    assert opts["interval_days"] == 14
    assert opts["default_snooze_value"] == 1
    assert opts["default_snooze_unit"] == "days"
    assert opts["last_completed"] is None
    assert opts["snooze_until"] is None


async def test_user_flow_last_completed_is_none(hass):
    """A brand-new chore has last_completed=None (starts overdue)."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"name": "Vacuuming", "interval_days": 7},
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["options"]["last_completed"] is None


async def test_user_flow_snooze_defaults_hardcoded(hass):
    """New chores always default to default_snooze_value=1 and default_snooze_unit=days."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"name": "Bins", "interval_days": 7},
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["options"]["default_snooze_value"] == 1
    assert result["options"]["default_snooze_unit"] == "days"


async def test_user_flow_multiple_entries_allowed(hass):
    """A second chore entry can be created (no single-instance restriction)."""
    for name in ("Bins", "Dishes"):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"name": name, "interval_days": 7},
        )
        assert result["type"] == FlowResultType.CREATE_ENTRY


async def test_user_flow_rejects_empty_name(hass):
    """Submitting an empty name re-shows the form with name_required error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"name": "   ", "interval_days": 1},
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
            {"name": "Valid Name", "interval_days": 0},
        )
