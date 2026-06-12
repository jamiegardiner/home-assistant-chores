"""Tests for ChoreConfig model."""

from __future__ import annotations

import pytest

from custom_components.chores.const import DOMAIN
from custom_components.chores.models import ChoreConfig


def test_from_dict_valid() -> None:
    config = ChoreConfig.from_dict({"name": "Bins", "interval_days": 7})
    assert config.name == "Bins"
    assert config.interval_days == 7
    assert config.default_snooze_value == 1
    assert config.default_snooze_unit == "days"


def test_from_dict_custom_snooze_value() -> None:
    config = ChoreConfig.from_dict(
        {"name": "Bins", "interval_days": 7, "default_snooze_value": 3}
    )
    assert config.default_snooze_value == 3


def test_from_dict_custom_snooze_unit() -> None:
    config = ChoreConfig.from_dict(
        {"name": "Bins", "interval_days": 7, "default_snooze_unit": "hours"}
    )
    assert config.default_snooze_unit == "hours"


def test_from_dict_custom_snooze_value_and_unit() -> None:
    config = ChoreConfig.from_dict(
        {
            "name": "Bins",
            "interval_days": 7,
            "default_snooze_value": 2,
            "default_snooze_unit": "hours",
        }
    )
    assert config.default_snooze_value == 2
    assert config.default_snooze_unit == "hours"


def test_from_dict_default_snooze_value_absent_defaults_to_one() -> None:
    config = ChoreConfig.from_dict({"name": "Bins", "interval_days": 14})
    assert config.default_snooze_value == 1


def test_from_dict_default_snooze_unit_absent_defaults_to_days() -> None:
    config = ChoreConfig.from_dict({"name": "Bins", "interval_days": 14})
    assert config.default_snooze_unit == "days"


def test_from_dict_all_valid_units() -> None:
    for unit in ("minutes", "hours", "days", "weeks"):
        config = ChoreConfig.from_dict(
            {"name": "Bins", "interval_days": 7, "default_snooze_unit": unit}
        )
        assert config.default_snooze_unit == unit


def test_from_dict_missing_interval_days_raises() -> None:
    with pytest.raises(ValueError, match="missing required keys"):
        ChoreConfig.from_dict({"name": "Bins"})


def test_from_dict_missing_name_raises() -> None:
    with pytest.raises(ValueError, match="missing required keys"):
        ChoreConfig.from_dict({"interval_days": 7})


def test_from_dict_zero_interval_raises() -> None:
    with pytest.raises(ValueError, match="Invalid interval_days"):
        ChoreConfig.from_dict({"name": "Bins", "interval_days": 0})


def test_from_dict_negative_interval_raises() -> None:
    with pytest.raises(ValueError, match="Invalid interval_days"):
        ChoreConfig.from_dict({"name": "Bins", "interval_days": -1})


def test_from_dict_bool_interval_raises() -> None:
    with pytest.raises(ValueError, match="Invalid interval_days"):
        ChoreConfig.from_dict({"name": "Bins", "interval_days": True})


def test_from_dict_zero_snooze_value_raises() -> None:
    with pytest.raises(ValueError, match="Invalid default_snooze_value"):
        ChoreConfig.from_dict(
            {"name": "Bins", "interval_days": 7, "default_snooze_value": 0}
        )


def test_from_dict_bool_snooze_value_raises() -> None:
    with pytest.raises(ValueError, match="Invalid default_snooze_value"):
        ChoreConfig.from_dict(
            {"name": "Bins", "interval_days": 7, "default_snooze_value": True}
        )


def test_from_dict_invalid_snooze_unit_raises() -> None:
    with pytest.raises(ValueError, match="Invalid default_snooze_unit"):
        ChoreConfig.from_dict(
            {"name": "Bins", "interval_days": 7, "default_snooze_unit": "fortnights"}
        )


def test_from_dict_ignores_extra_keys() -> None:
    config = ChoreConfig.from_dict(
        {
            "name": "Bins",
            "interval_days": 7,
            "last_completed": "2026-06-01",
            "snooze_until": None,
        }
    )
    assert config.name == "Bins"


def test_const_domain() -> None:
    assert DOMAIN == "chores"
