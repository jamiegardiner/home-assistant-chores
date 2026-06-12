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
)
from homeassistant.util import dt as dt_util

from .const import DOMAIN


def _chore_schema() -> vol.Schema:
    """Return the shared schema for the chore create/edit form."""
    return vol.Schema(
        {
            vol.Required("name"): str,
            vol.Required("interval_days"): NumberSelector(
                NumberSelectorConfig(min=1, step=1, mode=NumberSelectorMode.BOX)
            ),
            vol.Required("default_snooze_days"): NumberSelector(
                NumberSelectorConfig(min=1, step=1, mode=NumberSelectorMode.BOX)
            ),
            vol.Required("last_completed"): DateSelector(),
        }
    )


def _validate_chore_input(
    user_input: dict[str, Any], errors: dict[str, str]
) -> tuple[str, int, int, date]:
    """Validate and coerce chore form input. Populates errors in-place.

    Returns (name, interval_days, default_snooze_days, last_completed).
    """
    name = str(user_input.get("name", "")).strip()
    if not name:
        errors["name"] = "name_required"

    interval_days = int(user_input.get("interval_days", 1))
    if interval_days < 1:
        errors["interval_days"] = "invalid_interval"

    default_snooze_days = int(user_input.get("default_snooze_days", 1))
    if default_snooze_days < 1:
        errors["default_snooze_days"] = "invalid_interval"

    last_completed: date = date.fromisoformat(str(user_input["last_completed"]))

    return name, interval_days, default_snooze_days, last_completed


class ChoresConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the initial config flow: collect details for one chore."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the chore creation form and create the entry on submit."""
        errors: dict[str, str] = {}

        if user_input is not None:
            name, interval_days, default_snooze_days, last_completed = (
                _validate_chore_input(user_input, errors)
            )
            if not errors:
                return self.async_create_entry(
                    title=name,
                    data={},
                    options={
                        "name": name,
                        "interval_days": interval_days,
                        "default_snooze_days": default_snooze_days,
                        "last_completed": last_completed.isoformat(),
                        "snooze_until": None,
                    },
                )

        today = str(dt_util.now().date())
        suggested = (
            user_input
            if user_input is not None
            else {
                "last_completed": today,
                "default_snooze_days": 1,
            }
        )
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
            name, interval_days, default_snooze_days, last_completed = (
                _validate_chore_input(user_input, errors)
            )
            if not errors:
                return self.async_create_entry(
                    data={
                        "name": name,
                        "interval_days": interval_days,
                        "default_snooze_days": default_snooze_days,
                        "last_completed": last_completed.isoformat(),
                        # Preserve existing snooze — managed exclusively via services
                        "snooze_until": opts.get("snooze_until"),
                    }
                )

        suggested = {
            "name": opts.get("name", ""),
            "interval_days": opts.get("interval_days", 7),
            "default_snooze_days": opts.get("default_snooze_days", 1),
            "last_completed": opts.get("last_completed", str(dt_util.now().date())),
        }
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(_chore_schema(), suggested),
            errors=errors,
        )
