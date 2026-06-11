from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .const import INTERVAL_UNITS


@dataclass(frozen=True, slots=True)
class ChoreConfig:
    name: str
    interval_value: int
    interval_unit: str  # one of INTERVAL_UNITS ("days" | "weeks")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ChoreConfig:
        required_keys = {"name", "interval_value", "interval_unit"}
        missing = required_keys - data.keys()
        if missing:
            raise ValueError(f"ChoreConfig missing required keys: {missing}")
        interval_value = data["interval_value"]
        if (
            not isinstance(interval_value, int)
            or isinstance(interval_value, bool)
            or interval_value < 1
        ):
            raise ValueError(
                f"Invalid interval_value {interval_value!r}; must be a positive integer"
            )
        if data["interval_unit"] not in INTERVAL_UNITS:
            raise ValueError(
                f"Invalid interval_unit {data['interval_unit']!r}; must be one of {INTERVAL_UNITS}"
            )
        return cls(
            name=data["name"],
            interval_value=interval_value,
            interval_unit=data["interval_unit"],
        )
