"""Tests for the Chores integration entry lifecycle."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.chores import async_remove_entry
from custom_components.chores.const import CONF_CHORES, DOMAIN


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    pass


async def test_async_remove_entry_deletes_store(hass) -> None:
    """Storage file is removed when the config entry is deleted."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        entry_id="test_entry_abc",
        options={CONF_CHORES: []},
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.chores.__init__.Store.async_remove",
        new_callable=AsyncMock,
    ) as mock_remove:
        await async_remove_entry(hass, entry)

    mock_remove.assert_awaited_once()
