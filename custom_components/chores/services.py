"""Service schema constants and helpers for the Chores integration."""

from datetime import datetime
from typing import Any

import voluptuous as vol
from homeassistant.helpers import config_validation as cv

from .coordinator import _snooze_target

# Schemas are plain dicts so HA can wrap them with make_entity_service_schema,
# which adds the entity/area/device/label target fields automatically.
COMPLETE_SCHEMA: dict[Any, Any] = {
    vol.Optional("completed_at"): cv.datetime,
}
UNSNOOZE_SCHEMA: dict[Any, Any] = {}

# Type coercion only — range and unit validation is done in _handle_snooze via
# ServiceValidationError so HA surfaces translated messages rather than raw
# voluptuous error strings.
SNOOZE_SCHEMA: dict[Any, Any] = {
    vol.Required("value"): vol.Coerce(int),
    vol.Required("unit"): str,
}


def _parse_snooze_datetime(call_data: dict[str, Any]) -> datetime:
    """Compute the snooze target datetime from service call data."""
    return _snooze_target(call_data["value"], call_data["unit"])
