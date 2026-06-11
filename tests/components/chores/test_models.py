"""Tests for ChoreConfig model."""

from __future__ import annotations

import pytest

from custom_components.chores.const import DOMAIN, INTERVAL_UNITS
from custom_components.chores.models import ChoreConfig


def test_from_dict_valid() -> None:
    config = ChoreConfig.from_dict(
        {"name": "Bins", "interval_value": 7, "interval_unit": "days"}
    )
    assert config.name == "Bins"
    assert config.interval_value == 7
    assert config.interval_unit == "days"


def test_from_dict_weeks() -> None:
    config = ChoreConfig.from_dict(
        {"name": "Vacuum", "interval_value": 2, "interval_unit": "weeks"}
    )
    assert config.interval_unit == "weeks"


def test_from_dict_missing_key_raises() -> None:
    with pytest.raises(ValueError, match="missing required keys"):
        ChoreConfig.from_dict({"name": "Bins", "interval_value": 7})


def test_from_dict_zero_interval_raises() -> None:
    with pytest.raises(ValueError, match="Invalid interval_value"):
        ChoreConfig.from_dict(
            {"name": "Bins", "interval_value": 0, "interval_unit": "days"}
        )


def test_from_dict_negative_interval_raises() -> None:
    with pytest.raises(ValueError, match="Invalid interval_value"):
        ChoreConfig.from_dict(
            {"name": "Bins", "interval_value": -1, "interval_unit": "days"}
        )


def test_from_dict_bool_interval_raises() -> None:
    with pytest.raises(ValueError, match="Invalid interval_value"):
        ChoreConfig.from_dict(
            {"name": "Bins", "interval_value": True, "interval_unit": "days"}
        )


def test_from_dict_invalid_unit_raises() -> None:
    with pytest.raises(ValueError, match="Invalid interval_unit"):
        ChoreConfig.from_dict(
            {"name": "Bins", "interval_value": 1, "interval_unit": "months"}
        )


def test_from_dict_ignores_extra_keys() -> None:
    config = ChoreConfig.from_dict(
        {
            "name": "Bins",
            "interval_value": 7,
            "interval_unit": "days",
            "last_completed": "2026-06-01",
            "snooze_until": None,
        }
    )
    assert config.name == "Bins"


def test_const_values() -> None:
    assert DOMAIN == "chores"
    assert set(INTERVAL_UNITS) == {"days", "weeks"}
