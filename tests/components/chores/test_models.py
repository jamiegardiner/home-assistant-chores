"""Tests for the ChoreConfig model."""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from custom_components.chores.const import CONF_CHORES, DOMAIN, INTERVAL_UNITS
from custom_components.chores.models import ChoreConfig


def test_choreconfig_round_trip() -> None:
    c = ChoreConfig(
        name="Bins",
        interval_value=2,
        interval_unit="weeks",
        last_completed=date(2026, 6, 1),
    )
    assert ChoreConfig.from_dict(c.to_dict()) == c


def test_to_dict_serializes_date_as_iso() -> None:
    c = ChoreConfig(
        name="Bins",
        interval_value=2,
        interval_unit="weeks",
        last_completed=date(2026, 6, 1),
    )
    assert c.to_dict()["last_completed"] == "2026-06-01"


def _base_dict() -> dict[str, Any]:
    return {
        "name": "Bins",
        "interval_value": 2,
        "interval_unit": "weeks",
        "last_completed": "2026-06-01",
    }


def test_from_dict_rejects_zero_interval_value() -> None:
    data = {**_base_dict(), "interval_value": 0}
    with pytest.raises(ValueError, match="interval_value"):
        ChoreConfig.from_dict(data)


def test_from_dict_rejects_negative_interval_value() -> None:
    data = {**_base_dict(), "interval_value": -1}
    with pytest.raises(ValueError, match="interval_value"):
        ChoreConfig.from_dict(data)


def test_from_dict_rejects_non_integer_interval_value() -> None:
    data = {**_base_dict(), "interval_value": "two"}
    with pytest.raises(ValueError, match="interval_value"):
        ChoreConfig.from_dict(data)


def test_const_values() -> None:
    assert DOMAIN == "chores"
    assert CONF_CHORES == "chores"
    assert set(INTERVAL_UNITS) == {"days", "weeks"}
