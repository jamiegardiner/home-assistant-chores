"""Service schema constants and helpers for the Chores integration."""

from __future__ import annotations

from datetime import datetime, timedelta

import voluptuous as vol
from homeassistant.util import dt as dt_util

SERVICE_COMPLETE = "complete"
SERVICE_SNOOZE = "snooze"
SERVICE_UNSNOOZE = "unsnooze"

SNOOZE_UNITS: tuple[str, ...] = ("minutes", "hours", "days", "weeks")

# Schemas are plain dicts so HA can wrap them with make_entity_service_schema,
# which adds the entity/area/device/label target fields automatically.
COMPLETE_SCHEMA: dict = {}
UNSNOOZE_SCHEMA: dict = {}

SNOOZE_SCHEMA: dict = {
    vol.Required("value"): vol.All(vol.Coerce(int), vol.Range(min=1)),
    vol.Required("unit"): vol.In(SNOOZE_UNITS),
}


def _parse_snooze_datetime(call_data: dict) -> datetime:
    """Compute the snooze target datetime from service call data."""
    value: int = call_data["value"]
    unit: str = call_data["unit"]

    delta_kwargs: dict[str, int] = {unit: value}
    return dt_util.now() + timedelta(**delta_kwargs)
