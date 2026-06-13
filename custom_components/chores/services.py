"""Service schema constants and helpers for the Chores integration."""

from datetime import datetime, timedelta
from typing import Any

import voluptuous as vol
from homeassistant.helpers import config_validation as cv
from homeassistant.util import dt as dt_util

from .const import SNOOZE_UNITS

SERVICE_COMPLETE = "complete"
SERVICE_SNOOZE = "snooze"
SERVICE_UNSNOOZE = "unsnooze"

# Schemas are plain dicts so HA can wrap them with make_entity_service_schema,
# which adds the entity/area/device/label target fields automatically.
COMPLETE_SCHEMA: dict[Any, Any] = {
    vol.Optional("completed_at"): cv.datetime,
}
UNSNOOZE_SCHEMA: dict[Any, Any] = {}

SNOOZE_SCHEMA: dict[Any, Any] = {
    vol.Required("value"): vol.All(vol.Coerce(int), vol.Range(min=1)),
    vol.Required("unit"): vol.In(SNOOZE_UNITS),
}


def _parse_snooze_datetime(call_data: dict[str, Any]) -> datetime:
    """Compute the snooze target datetime from service call data."""
    value: int = call_data["value"]
    unit: str = call_data["unit"]

    delta_kwargs: dict[str, int] = {unit: value}
    return dt_util.now() + timedelta(**delta_kwargs)
