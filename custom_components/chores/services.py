"""Service handlers for the Chores integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SERVICE_COMPLETE = "complete"

COMPLETE_SCHEMA = vol.Schema({}, extra=vol.ALLOW_EXTRA)


async def async_register_services(hass: HomeAssistant) -> None:
    """Register integration services (idempotent)."""
    if hass.services.has_service(DOMAIN, SERVICE_COMPLETE):
        return

    async def _handle_complete(call: ServiceCall) -> None:
        """Handle chores.complete service call."""
        chore_id: str | None = None
        coordinator = None

        domain_data: dict[str, Any] = hass.data.get(DOMAIN, {})

        raw_entity_id = call.data.get("entity_id")
        if isinstance(raw_entity_id, str):
            target_entities: list[str] = [raw_entity_id]
        elif isinstance(raw_entity_id, list):
            target_entities = raw_entity_id
        else:
            target_entities = []

        if not target_entities:
            raise HomeAssistantError("chores.complete requires a target entity")

        entity_id = target_entities[0]
        for coord in domain_data.values():
            resolved = coord.chore_id_for_entity(entity_id)
            if resolved is not None:
                chore_id = resolved
                coordinator = coord
                break

        if coordinator is None or chore_id is None:
            raise HomeAssistantError(
                f"Could not resolve chore for entity: {entity_id!r}"
            )

        await coordinator.async_complete(chore_id)

    hass.services.async_register(
        DOMAIN,
        SERVICE_COMPLETE,
        _handle_complete,
        schema=COMPLETE_SCHEMA,
    )
    _LOGGER.debug("Registered service %s.%s", DOMAIN, SERVICE_COMPLETE)


def async_unregister_services(hass: HomeAssistant) -> None:
    """Unregister integration services (called when last entry unloads)."""
    if hass.services.has_service(DOMAIN, SERVICE_COMPLETE):
        hass.services.async_remove(DOMAIN, SERVICE_COMPLETE)
        _LOGGER.debug("Unregistered service %s.%s", DOMAIN, SERVICE_COMPLETE)
