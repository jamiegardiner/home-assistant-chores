"""Service schema constants and helpers for the Chores integration."""

from datetime import datetime, timedelta
from typing import Any

import voluptuous as vol
from homeassistant.helpers import config_validation as cv
from homeassistant.util import dt as dt_util

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
    vol.Optional("value"): vol.Coerce(int),
    vol.Optional("unit"): str,
}
SNOOZE_EXACT_SCHEMA: dict[Any, Any] = {
    vol.Required("snooze_until"): cv.datetime,
}


def _parse_snooze_datetime(call_data: dict[str, Any]) -> datetime:
    """Compute the snooze target datetime from service call data."""
    return dt_util.now() + timedelta(**{call_data["unit"]: call_data["value"]})
