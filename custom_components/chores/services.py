"""Service schema constants and helpers for the Chores integration."""

from __future__ import annotations

from datetime import date, timedelta

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util

SERVICE_COMPLETE = "complete"
SERVICE_SNOOZE = "snooze"
SERVICE_UNSNOOZE = "unsnooze"

COMPLETE_SCHEMA = vol.Schema({}, extra=vol.ALLOW_EXTRA)
UNSNOOZE_SCHEMA = vol.Schema({}, extra=vol.ALLOW_EXTRA)

SNOOZE_SCHEMA = vol.Schema(
    {
        vol.Optional("snooze_days"): vol.All(vol.Coerce(int), vol.Range(min=1)),
        vol.Optional("snooze_weeks"): vol.All(vol.Coerce(int), vol.Range(min=1)),
        vol.Optional("snooze_until"): cv.string,
    },
    extra=vol.ALLOW_EXTRA,
)


def _parse_snooze_until(call_data: dict) -> date:
    """Parse and validate snooze target date from service call data.

    Exactly one of snooze_days, snooze_weeks, or snooze_until must be provided.
    The resolved date must be in the future.

    Raises HomeAssistantError on invalid input.
    """
    snooze_days: int | None = call_data.get("snooze_days")
    snooze_weeks: int | None = call_data.get("snooze_weeks")
    snooze_until_str: str | None = call_data.get("snooze_until")

    provided = sum(x is not None for x in [snooze_days, snooze_weeks, snooze_until_str])
    if provided != 1:
        raise HomeAssistantError(
            "Exactly one of snooze_days, snooze_weeks, or snooze_until must be provided"
        )

    today = dt_util.now().date()
    if snooze_days is not None:
        snooze_until: date = today + timedelta(days=snooze_days)
    elif snooze_weeks is not None:
        snooze_until = today + timedelta(weeks=snooze_weeks)
    else:
        try:
            snooze_until = date.fromisoformat(str(snooze_until_str))
        except ValueError as exc:
            raise HomeAssistantError(
                f"Invalid snooze_until date: {snooze_until_str!r}"
            ) from exc

    if snooze_until <= dt_util.now().date():
        raise HomeAssistantError(
            f"snooze_until must be a future date, got {snooze_until}"
        )

    return snooze_until
