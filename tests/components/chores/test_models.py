"""Tests for ChoreConfig model."""

from datetime import time

import pytest

from custom_components.chores.const import DOMAIN
from custom_components.chores.models import ChoreConfig, parse_time_of_day


def test_from_dict_valid() -> None:
    config = ChoreConfig.from_dict({"name": "Bins", "interval_value": 7})
    assert config.name == "Bins"
    assert config.interval_value == 7
    assert config.default_snooze_value == 1
    assert config.default_snooze_unit == "days"


def test_from_dict_custom_snooze_value() -> None:
    config = ChoreConfig.from_dict(
        {"name": "Bins", "interval_value": 7, "default_snooze_value": 3}
    )
    assert config.default_snooze_value == 3


def test_from_dict_custom_snooze_unit() -> None:
    config = ChoreConfig.from_dict(
        {"name": "Bins", "interval_value": 7, "default_snooze_unit": "hours"}
    )
    assert config.default_snooze_unit == "hours"


def test_from_dict_custom_snooze_value_and_unit() -> None:
    config = ChoreConfig.from_dict(
        {
            "name": "Bins",
            "interval_value": 7,
            "default_snooze_value": 2,
            "default_snooze_unit": "hours",
        }
    )
    assert config.default_snooze_value == 2
    assert config.default_snooze_unit == "hours"


def test_from_dict_default_snooze_value_absent_defaults_to_one() -> None:
    config = ChoreConfig.from_dict({"name": "Bins", "interval_value": 14})
    assert config.default_snooze_value == 1


def test_from_dict_default_snooze_unit_absent_defaults_to_days() -> None:
    config = ChoreConfig.from_dict({"name": "Bins", "interval_value": 14})
    assert config.default_snooze_unit == "days"


def test_from_dict_all_valid_units() -> None:
    for unit in ("minutes", "hours", "days", "weeks"):
        config = ChoreConfig.from_dict(
            {"name": "Bins", "interval_value": 7, "default_snooze_unit": unit}
        )
        assert config.default_snooze_unit == unit


def test_from_dict_missing_interval_value_raises() -> None:
    with pytest.raises(ValueError, match="missing required keys"):
        ChoreConfig.from_dict({"name": "Bins"})


def test_from_dict_missing_name_raises() -> None:
    with pytest.raises(ValueError, match="missing required keys"):
        ChoreConfig.from_dict({"interval_value": 7})


def test_from_dict_zero_interval_raises() -> None:
    with pytest.raises(ValueError, match="Invalid interval_value"):
        ChoreConfig.from_dict({"name": "Bins", "interval_value": 0})


def test_from_dict_negative_interval_raises() -> None:
    with pytest.raises(ValueError, match="Invalid interval_value"):
        ChoreConfig.from_dict({"name": "Bins", "interval_value": -1})


def test_from_dict_bool_interval_raises() -> None:
    with pytest.raises(ValueError, match="Invalid interval_value"):
        ChoreConfig.from_dict({"name": "Bins", "interval_value": True})


def test_from_dict_name_is_stripped() -> None:
    config = ChoreConfig.from_dict({"name": "  Bins  ", "interval_value": 7})
    assert config.name == "Bins"


def test_from_dict_non_str_name_raises() -> None:
    with pytest.raises(ValueError, match="Invalid name"):
        ChoreConfig.from_dict({"name": 123, "interval_value": 7})


@pytest.mark.parametrize(
    "bad_name",
    [
        pytest.param("", id="empty"),
        pytest.param("   ", id="whitespace_only"),
    ],
)
def test_from_dict_blank_name_raises(bad_name: str) -> None:
    with pytest.raises(ValueError, match="Invalid name"):
        ChoreConfig.from_dict({"name": bad_name, "interval_value": 7})


def test_from_dict_zero_snooze_value_raises() -> None:
    with pytest.raises(ValueError, match="Invalid default_snooze_value"):
        ChoreConfig.from_dict(
            {"name": "Bins", "interval_value": 7, "default_snooze_value": 0}
        )


def test_from_dict_bool_snooze_value_raises() -> None:
    with pytest.raises(ValueError, match="Invalid default_snooze_value"):
        ChoreConfig.from_dict(
            {"name": "Bins", "interval_value": 7, "default_snooze_value": True}
        )


def test_from_dict_invalid_snooze_unit_raises() -> None:
    with pytest.raises(ValueError, match="Invalid default_snooze_unit"):
        ChoreConfig.from_dict(
            {"name": "Bins", "interval_value": 7, "default_snooze_unit": "fortnights"}
        )


def test_from_dict_ignores_extra_keys() -> None:
    config = ChoreConfig.from_dict(
        {
            "name": "Bins",
            "interval_value": 7,
            "last_completed": "2026-06-01",
            "snooze_until": None,
        }
    )
    assert config.name == "Bins"


def test_const_domain() -> None:
    assert DOMAIN == "chores"


def test_from_dict_default_notification_time() -> None:
    config = ChoreConfig.from_dict({"name": "Bins", "interval_value": 7})
    assert config.notification_time == "08:00"


def test_from_dict_notification_time_absent_uses_default() -> None:
    data = {"name": "Bins", "interval_value": 14}
    config = ChoreConfig.from_dict(data)
    assert config.notification_time == "08:00"


def test_from_dict_custom_notification_time() -> None:
    config = ChoreConfig.from_dict(
        {"name": "Bins", "interval_value": 7, "notification_time": "08:30"}
    )
    assert config.notification_time == "08:30"


@pytest.mark.parametrize(
    "bad_time",
    [
        pytest.param("25:00", id="hour_out_of_range"),
        pytest.param("12:60", id="minute_out_of_range"),
        pytest.param("abc", id="not_time_format"),
        pytest.param("8:00", id="missing_leading_zero"),
        pytest.param("", id="empty_string"),
        pytest.param(None, id="none_value"),
    ],
)
def test_from_dict_invalid_notification_time_raises(bad_time) -> None:
    with pytest.raises(ValueError, match="Invalid notification_time"):
        ChoreConfig.from_dict(
            {"name": "Bins", "interval_value": 7, "notification_time": bad_time}
        )


def test_from_dict_interval_unit_defaults_to_days() -> None:
    config = ChoreConfig.from_dict({"name": "Bins", "interval_value": 7})
    assert config.interval_unit == "days"


def test_from_dict_custom_interval_unit_weeks() -> None:
    config = ChoreConfig.from_dict(
        {"name": "Bins", "interval_value": 2, "interval_unit": "weeks"}
    )
    assert config.interval_unit == "weeks"


def test_from_dict_invalid_interval_unit_raises() -> None:
    with pytest.raises(ValueError, match="Invalid interval_unit"):
        ChoreConfig.from_dict(
            {"name": "Bins", "interval_value": 7, "interval_unit": "fortnights"}
        )


def test_parse_time_of_day() -> None:
    assert parse_time_of_day("08:30") == time(8, 30)


def test_parse_time_of_day_midnight() -> None:
    assert parse_time_of_day("00:00") == time(0, 0)
