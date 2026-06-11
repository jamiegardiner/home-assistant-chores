"""Config flow and options flow for the Chores integration."""

from __future__ import annotations

from datetime import date
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    DateSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
)
from homeassistant.util import dt as dt_util

from .const import DOMAIN, INTERVAL_UNITS


def _chore_schema() -> vol.Schema:
    """Return the shared schema for the chore create/edit form."""
    return vol.Schema(
        {
            vol.Required("name"): str,
            vol.Required("interval_value"): NumberSelector(
                NumberSelectorConfig(min=1, step=1, mode=NumberSelectorMode.BOX)
            ),
            vol.Required("interval_unit"): SelectSelector(
                SelectSelectorConfig(
                    options=[
                        SelectOptionDict(value=unit, label=unit.capitalize())
                        for unit in INTERVAL_UNITS
                    ]
                )
            ),
            vol.Required("last_completed"): DateSelector(),
        }
    )


def _validate_chore_input(
    user_input: dict[str, Any], errors: dict[str, str]
) -> tuple[str, int, str, date]:
    """Validate and coerce chore form input. Populates errors in-place.

    Returns (name, interval_value, interval_unit, last_completed).
    """
    name = str(user_input.get("name", "")).strip()
    if not name:
        errors["name"] = "name_required"

    interval_value = int(user_input.get("interval_value", 1))
    if interval_value < 1:
        errors["interval_value"] = "invalid_interval"

    interval_unit = user_input.get("interval_unit", INTERVAL_UNITS[0])
    last_completed: date = date.fromisoformat(str(user_input["last_completed"]))

    return name, interval_value, interval_unit, last_completed


class ChoresConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the initial config flow: collect details for one chore."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the chore creation form and create the entry on submit."""
        errors: dict[str, str] = {}

        if user_input is not None:
            name, interval_value, interval_unit, last_completed = _validate_chore_input(
                user_input, errors
            )
            if not errors:
                return self.async_create_entry(
                    title=name,
                    data={},
                    options={
                        "name": name,
                        "interval_value": interval_value,
                        "interval_unit": interval_unit,
                        "last_completed": last_completed.isoformat(),
                        "snooze_until": None,
                    },
                )

        today = str(dt_util.now().date())
        suggested = {
            "last_completed": (
                str(user_input.get("last_completed", today)) if user_input else today
            ),
        }
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(_chore_schema(), suggested),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> ChoresOptionsFlow:
        """Return the options flow handler."""
        return ChoresOptionsFlow()


class ChoresOptionsFlow(config_entries.OptionsFlow):
    """Handle the options flow: edit an existing chore in-place."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the chore edit form pre-filled from current options."""
        errors: dict[str, str] = {}
        opts = self.config_entry.options

        if user_input is not None:
            name, interval_value, interval_unit, last_completed = _validate_chore_input(
                user_input, errors
            )
            if not errors:
                return self.async_create_entry(
                    data={
                        "name": name,
                        "interval_value": interval_value,
                        "interval_unit": interval_unit,
                        "last_completed": last_completed.isoformat(),
                        # Preserve existing snooze — managed exclusively via services
                        "snooze_until": opts.get("snooze_until"),
                    }
                )

        suggested = {
            "name": opts.get("name", ""),
            "interval_value": opts.get("interval_value", 1),
            "interval_unit": opts.get("interval_unit", INTERVAL_UNITS[0]),
            "last_completed": opts.get("last_completed", str(dt_util.now().date())),
        }
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(_chore_schema(), suggested),
            errors=errors,
        )
