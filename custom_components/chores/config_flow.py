"""Config flow for the Chores integration."""

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
)

from .const import (
    DEFAULT_NOTIFICATION_TIME,
    DEFAULT_SNOOZE_UNIT,
    DEFAULT_SNOOZE_VALUE,
    DOMAIN,
    MAX_NUMBER_VALUE,
)
from .models import ChoreConfig


def _chore_schema() -> vol.Schema:
    """Return the schema for the chore creation form."""
    return vol.Schema(
        {
            vol.Required("name"): str,
            vol.Required("interval_days"): NumberSelector(
                NumberSelectorConfig(
                    min=1, max=MAX_NUMBER_VALUE, step=1, mode=NumberSelectorMode.BOX
                )
            ),
        }
    )


class ChoresConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the initial config flow: collect name and interval for one chore."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the chore creation form and create the entry on submit."""
        errors: dict[str, str] = {}

        if user_input is not None:
            if not str(user_input.get("name", "")).strip():
                errors["name"] = "name_required"
            else:
                config = ChoreConfig.from_dict(
                    {
                        **user_input,
                        "interval_days": int(user_input.get("interval_days", 1)),
                    }
                )
                return self.async_create_entry(
                    title=config.name,
                    data={},
                    options={
                        "name": config.name,
                        "interval_days": config.interval_days,
                        "default_snooze_value": DEFAULT_SNOOZE_VALUE,
                        "default_snooze_unit": DEFAULT_SNOOZE_UNIT,
                        "notification_time": DEFAULT_NOTIFICATION_TIME,
                        "last_completed": None,
                        "snooze_until": None,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                _chore_schema(), user_input or {}
            ),
            errors=errors,
        )
