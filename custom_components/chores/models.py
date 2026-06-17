from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .const import (
    DEFAULT_INTERVAL_UNIT,
    DEFAULT_NOTIFICATION_TIME,
    DEFAULT_SNOOZE_UNIT,
    DEFAULT_SNOOZE_VALUE,
    INTERVAL_UNIT_DAYS,
    INTERVAL_UNITS,
    SNOOZE_UNITS,
)


@dataclass(frozen=True, slots=True)
class ChoreConfig:
    name: str
    interval_value: int
    interval_unit: str = DEFAULT_INTERVAL_UNIT
    default_snooze_value: int = DEFAULT_SNOOZE_VALUE
    default_snooze_unit: str = DEFAULT_SNOOZE_UNIT
    notification_time: str = DEFAULT_NOTIFICATION_TIME

    @property
    def interval_in_days(self) -> int:
        """Return the interval expressed as a number of days."""
        return self.interval_value * INTERVAL_UNIT_DAYS[self.interval_unit]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ChoreConfig:
        required_keys = {"name", "interval_value"}
        missing = required_keys - data.keys()
        if missing:
            raise ValueError(f"ChoreConfig missing required keys: {missing}")
        name = data["name"]
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"Invalid name {name!r}; must be a non-empty string")
        interval_value = data["interval_value"]
        if (
            not isinstance(interval_value, int)
            or isinstance(interval_value, bool)
            or interval_value < 1
        ):
            raise ValueError(
                f"Invalid interval_value {interval_value!r}; must be a positive integer"
            )
        interval_unit = data.get("interval_unit", DEFAULT_INTERVAL_UNIT)
        if interval_unit not in INTERVAL_UNITS:
            raise ValueError(
                f"Invalid interval_unit {interval_unit!r}; must be one of {INTERVAL_UNITS}"
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
            name=name.strip(),
            interval_value=interval_value,
            interval_unit=interval_unit,
            default_snooze_value=default_snooze_value,
            default_snooze_unit=default_snooze_unit,
            notification_time=notification_time,
        )
