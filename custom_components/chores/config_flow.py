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

from .const import CONF_CHORES, DOMAIN, INTERVAL_UNITS
from .models import ChoreConfig


class ChoresConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the initial config flow for Chores."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a user-initiated config flow (single-instance enforcement)."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        return self.async_create_entry(
            title="Chores",
            data={CONF_CHORES: []},
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> ChoresOptionsFlow:
        """Return the options flow handler."""
        return ChoresOptionsFlow()


class ChoresOptionsFlow(config_entries.OptionsFlow):
    """Handle the options flow to add and remove chores."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the action menu (add or remove)."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["add", "remove"],
        )

    async def async_step_add(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle adding a new chore."""
        errors: dict[str, str] = {}

        schema = vol.Schema(
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

        if user_input is not None:
            # Validate name manually (voluptuous str alone allows empty)
            name = str(user_input.get("name", "")).strip()
            if not name:
                errors["name"] = "name_required"

            # NumberSelector returns float; coerce to int
            interval_value = int(user_input.get("interval_value", 1))
            if interval_value < 1:
                errors["interval_value"] = "invalid_interval"

            # DateSelector validates format and returns the date string; parse to date
            last_completed: date = date.fromisoformat(str(user_input["last_completed"]))

            if not errors:
                chore = ChoreConfig(
                    name=name,
                    interval_value=interval_value,
                    interval_unit=user_input["interval_unit"],
                    last_completed=last_completed,
                )
                current = list(self.config_entry.data.get(CONF_CHORES, []))
                current.append(chore.to_dict())
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data={**self.config_entry.data, CONF_CHORES: current},
                )
                return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="add",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_remove(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle removing an existing chore."""
        chores: list[dict] = list(self.config_entry.data.get(CONF_CHORES, []))

        if user_input is not None:
            idx = int(user_input["chore"])
            new_chores = [c for i, c in enumerate(chores) if i != idx]
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data={**self.config_entry.data, CONF_CHORES: new_chores},
            )
            return self.async_create_entry(title="", data={})

        if not chores:
            return self.async_abort(reason="no_chores")

        options = {str(i): c["name"] for i, c in enumerate(chores)}
        schema = vol.Schema({vol.Required("chore"): vol.In(options)})
        return self.async_show_form(step_id="remove", data_schema=schema)
