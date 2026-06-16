"""Unit tests for custom_components/chores/diagnostics.py."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

from custom_components.chores.diagnostics import async_get_config_entry_diagnostics

_LC = datetime(2026, 6, 1, 14, 30, tzinfo=UTC)
_SNOOZE = datetime(2026, 6, 3, 8, 0, tzinfo=UTC)
_NEXT_DUE = datetime(2026, 6, 8, 8, 0, tzinfo=UTC)

_FULL_STATE = {
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


def _make_entry(coordinator: FakeCoordinator) -> MagicMock:
    entry = MagicMock()
    entry.runtime_data = coordinator
    return entry


class TestDiagnostics:
    async def test_returns_coordinator_data_key(self):
        coord = FakeCoordinator(_FULL_STATE)
        entry = _make_entry(coord)
        result = await async_get_config_entry_diagnostics(MagicMock(), entry)
        assert "coordinator_data" in result

    async def test_all_safe_fields_present(self):
        coord = FakeCoordinator(_FULL_STATE)
        entry = _make_entry(coord)
        result = await async_get_config_entry_diagnostics(MagicMock(), entry)
        data = result["coordinator_data"]
        assert data["name"] == "Dishes"
        assert data["status"] == "overdue"
        assert data["next_due"] == _NEXT_DUE
        assert data["interval_days"] == 7
        assert data["default_snooze_value"] == 1
        assert data["default_snooze_unit"] == "days"
        assert data["notification_time"] == "08:00"

    async def test_last_completed_included(self):
        coord = FakeCoordinator(_FULL_STATE)
        entry = _make_entry(coord)
        result = await async_get_config_entry_diagnostics(MagicMock(), entry)
        assert result["coordinator_data"]["last_completed"] == _LC

    async def test_snooze_until_included_when_set(self):
        state = {**_FULL_STATE, "status": "snoozed", "snooze_until": _SNOOZE}
        coord = FakeCoordinator(state)
        entry = _make_entry(coord)
        result = await async_get_config_entry_diagnostics(MagicMock(), entry)
        assert result["coordinator_data"]["snooze_until"] == _SNOOZE

    async def test_never_completed_chore(self):
        state = {
            **_FULL_STATE,
            "last_completed": None,
            "next_due": None,
            "status": "overdue",
        }
        coord = FakeCoordinator(state)
        entry = _make_entry(coord)
        result = await async_get_config_entry_diagnostics(MagicMock(), entry)
        data = result["coordinator_data"]
        assert data["last_completed"] is None
        assert data["next_due"] is None
        assert data["status"] == "overdue"

    async def test_snapshot_is_copy(self):
        coord = FakeCoordinator(_FULL_STATE)
        entry = _make_entry(coord)
        result = await async_get_config_entry_diagnostics(MagicMock(), entry)
        result["coordinator_data"]["name"] = "mutated"
        assert coord.data["name"] == "Dishes"
