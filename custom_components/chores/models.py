from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .const import (
    DEFAULT_NOTIFICATION_TIME,
    DEFAULT_SNOOZE_UNIT,
    DEFAULT_SNOOZE_VALUE,
    SNOOZE_UNITS,
)


@dataclass(frozen=True, slots=True)
class ChoreConfig:
    name: str
    interval_days: int
    default_snooze_value: int = DEFAULT_SNOOZE_VALUE
    default_snooze_unit: str = DEFAULT_SNOOZE_UNIT
    notification_time: str = DEFAULT_NOTIFICATION_TIME

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ChoreConfig:
        required_keys = {"name", "interval_days"}
        missing = required_keys - data.keys()
        if missing:
            raise ValueError(f"ChoreConfig missing required keys: {missing}")
        interval_days = data["interval_days"]
        if (
            not isinstance(interval_days, int)
            or isinstance(interval_days, bool)
            or interval_days < 1
        ):
            raise ValueError(
                f"Invalid interval_days {interval_days!r}; must be a positive integer"
            )
        default_snooze_value = data.get("default_snooze_value", DEFAULT_SNOOZE_VALUE)
        if (
            not isinstance(default_snooze_value, int)
            or isinstance(default_snooze_value, bool)
            or default_snooze_value < 1
        ):
            raise ValueError(
                f"Invalid default_snooze_value {default_snooze_value!r}; must be a positive integer"
            )
        default_snooze_unit = data.get("default_snooze_unit", DEFAULT_SNOOZE_UNIT)
        if default_snooze_unit not in SNOOZE_UNITS:
            raise ValueError(
                f"Invalid default_snooze_unit {default_snooze_unit!r}; must be one of {SNOOZE_UNITS}"
            )
        notification_time = data.get("notification_time", DEFAULT_NOTIFICATION_TIME)
        try:
            if notification_time != datetime.strptime(
                notification_time, "%H:%M"
            ).strftime("%H:%M"):
                raise ValueError(notification_time)
        except TypeError, ValueError:
            raise ValueError(
                f"Invalid notification_time {notification_time!r}; must be HH:MM (00:00-23:59)"
            ) from None
        return cls(
            name=data["name"],
            interval_days=interval_days,
            default_snooze_value=default_snooze_value,
            default_snooze_unit=default_snooze_unit,
            notification_time=notification_time,
        )
