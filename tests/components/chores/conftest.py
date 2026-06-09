"""Fixtures for Chores coordinator tests."""

from __future__ import annotations

from datetime import date, timedelta

import pytest


def _make_chore_dict(
    name: str,
    interval_value: int,
    interval_unit: str,
    days_ago: int,
) -> dict:
    """Build a chore config dict with last_completed = today - days_ago."""
    last_completed = (date.today() - timedelta(days=days_ago)).isoformat()
    return {
        "name": name,
        "interval_value": interval_value,
        "interval_unit": interval_unit,
        "last_completed": last_completed,
    }


@pytest.fixture
def chore_dicts() -> list[dict]:
    """Two chores: A is overdue (30 days ago, 7d interval), B is done (today, 7d interval)."""
    return [
        _make_chore_dict("Chore A", 7, "days", 30),  # overdue
        _make_chore_dict("Chore B", 7, "days", 0),  # done
    ]
