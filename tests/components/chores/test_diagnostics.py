"""Unit tests for custom_components/chores/diagnostics.py."""

from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock

import pytest

from custom_components.chores.diagnostics import async_get_config_entry_diagnostics
from tests.components.chores.helpers import make_entry, setup_coord

_LC = datetime(2026, 6, 1, 14, 30, tzinfo=UTC)
_SNOOZE = datetime(2026, 6, 3, 8, 0, tzinfo=UTC)
_NEXT_DUE = datetime(2026, 6, 8, 8, 0, tzinfo=UTC)

_FAKE_STATE = {
    "name": "Dishes",
    "status": "overdue",
    "last_completed": _LC,
    "next_due": _NEXT_DUE,
    "snooze_until": None,
    "interval_days": 7,
    "default_snooze_value": 1,
    "default_snooze_unit": "days",
    "notification_time": "08:00",
}


class FakeCoordinator:
    def __init__(self, state: dict) -> None:
        self.data = dict(state)


def _make_fake_entry(coordinator: FakeCoordinator) -> MagicMock:
    entry = MagicMock()
    entry.runtime_data = coordinator
    return entry


# ---------------------------------------------------------------------------
# Anchor test — real coordinator via make_entry/setup_coord so snapshot drift
# in coordinator._snapshot() is caught immediately.
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: Any) -> None:
    pass


async def test_real_coordinator_snapshot_shape(hass: Any) -> None:
    """Diagnostics output matches the live coordinator snapshot keys."""
    entry = make_entry(days_ago=0, interval_days=7, notification_time="08:00")
    entry.add_to_hass(hass)
    coord = await setup_coord(hass, entry)
    entry.runtime_data = coord

    result = await async_get_config_entry_diagnostics(hass, entry)
    data = result["coordinator_data"]

    expected_keys = {
        "name",
        "status",
        "last_completed",
        "next_due",
        "snooze_until",
        "interval_days",
        "default_snooze_value",
        "default_snooze_unit",
        "notification_time",
    }
    assert set(data.keys()) == expected_keys
    assert data["status"] == "done"
    assert data["interval_days"] == 7
    assert data["notification_time"] == "08:00"


# ---------------------------------------------------------------------------
# Edge-case tests — fake coordinator is fine here; snapshot shape is already
# pinned by the real-coordinator anchor above.
# ---------------------------------------------------------------------------


async def test_never_completed_chore() -> None:
    state = {
        **_FAKE_STATE,
        "last_completed": None,
        "next_due": None,
        "status": "overdue",
    }
    coord = FakeCoordinator(state)
    entry = _make_fake_entry(coord)
    result = await async_get_config_entry_diagnostics(MagicMock(), entry)
    data = result["coordinator_data"]
    assert data["last_completed"] is None
    assert data["next_due"] is None
    assert data["status"] == "overdue"


async def test_active_snooze_included() -> None:
    state = {**_FAKE_STATE, "status": "snoozed", "snooze_until": _SNOOZE}
    coord = FakeCoordinator(state)
    entry = _make_fake_entry(coord)
    result = await async_get_config_entry_diagnostics(MagicMock(), entry)
    assert result["coordinator_data"]["snooze_until"] == _SNOOZE
    assert result["coordinator_data"]["status"] == "snoozed"


async def test_snapshot_is_copy() -> None:
    coord = FakeCoordinator(_FAKE_STATE)
    entry = _make_fake_entry(coord)
    result = await async_get_config_entry_diagnostics(MagicMock(), entry)
    result["coordinator_data"]["name"] = "mutated"
    assert coord.data["name"] == "Dishes"
