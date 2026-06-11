from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ChoreConfig:
    name: str
    interval_days: int
    default_snooze_days: int = 1

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
        default_snooze_days = data.get("default_snooze_days", 1)
        if (
            not isinstance(default_snooze_days, int)
            or isinstance(default_snooze_days, bool)
            or default_snooze_days < 1
        ):
            raise ValueError(
                f"Invalid default_snooze_days {default_snooze_days!r}; must be a positive integer"
            )
        return cls(
            name=data["name"],
            interval_days=interval_days,
            default_snooze_days=default_snooze_days,
        )
