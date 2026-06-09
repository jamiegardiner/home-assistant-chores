"""Service handlers for the Chores integration."""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
import homeassistant.helpers.config_validation as cv
from homeassistant.util import dt as dt_util

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

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


def _resolve_entity(call: ServiceCall, domain_data: dict[str, Any]) -> tuple[str, Any]:
    """Resolve the targeted entity to (chore_id, coordinator).

    Raises HomeAssistantError if resolution fails.
    """
    raw_entity_id = call.data.get("entity_id")
    if isinstance(raw_entity_id, str):
        target_entities: list[str] = [raw_entity_id]
    elif isinstance(raw_entity_id, list):
        target_entities = raw_entity_id
    else:
        target_entities = []

    if not target_entities:
        raise HomeAssistantError(
            f"chores.{call.service} requires a target entity"
        )

    entity_id = target_entities[0]
    for coord in domain_data.values():
        resolved = coord.chore_id_for_entity(entity_id)
        if resolved is not None:
            return resolved, coord

    raise HomeAssistantError(
        f"Could not resolve chore for entity: {entity_id!r}"
    )


async def async_register_services(hass: HomeAssistant) -> None:
    """Register integration services (idempotent)."""
    if hass.services.has_service(DOMAIN, SERVICE_COMPLETE):
        return

    async def _handle_complete(call: ServiceCall) -> None:
        """Handle chores.complete service call."""
        domain_data: dict[str, Any] = hass.data.get(DOMAIN, {})
        chore_id, coordinator = _resolve_entity(call, domain_data)
        await coordinator.async_complete(chore_id)

    async def _handle_snooze(call: ServiceCall) -> None:
        """Handle chores.snooze service call."""
        domain_data: dict[str, Any] = hass.data.get(DOMAIN, {})
        chore_id, coordinator = _resolve_entity(call, domain_data)

        snooze_days: int | None = call.data.get("snooze_days")
        snooze_weeks: int | None = call.data.get("snooze_weeks")
        snooze_until_str: str | None = call.data.get("snooze_until")

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

        await coordinator.async_snooze(chore_id, snooze_until)

    async def _handle_unsnooze(call: ServiceCall) -> None:
        """Handle chores.unsnooze service call."""
        domain_data: dict[str, Any] = hass.data.get(DOMAIN, {})
        chore_id, coordinator = _resolve_entity(call, domain_data)
        await coordinator.async_unsnooze(chore_id)

    hass.services.async_register(
        DOMAIN,
        SERVICE_COMPLETE,
        _handle_complete,
        schema=COMPLETE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SNOOZE,
        _handle_snooze,
        schema=SNOOZE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_UNSNOOZE,
        _handle_unsnooze,
        schema=UNSNOOZE_SCHEMA,
    )
    _LOGGER.debug("Registered services for domain %s", DOMAIN)


def async_unregister_services(hass: HomeAssistant) -> None:
    """Unregister integration services (called when last entry unloads)."""
    for service in (SERVICE_COMPLETE, SERVICE_SNOOZE, SERVICE_UNSNOOZE):
        if hass.services.has_service(DOMAIN, service):
            hass.services.async_remove(DOMAIN, service)
    _LOGGER.debug("Unregistered services for domain %s", DOMAIN)
