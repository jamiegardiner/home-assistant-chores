from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from .const import INTERVAL_UNITS


@dataclass
class ChoreConfig:
    name: str
    interval_value: int
    interval_unit: str  # one of INTERVAL_UNITS ("days" | "weeks")
    last_completed: date

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "interval_value": self.interval_value,
            "interval_unit": self.interval_unit,
            "last_completed": self.last_completed.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ChoreConfig":
        required_keys = {"name", "interval_value", "interval_unit", "last_completed"}
        missing = required_keys - data.keys()
        if missing:
            raise ValueError(f"ChoreConfig missing required keys: {missing}")
        if data["interval_unit"] not in INTERVAL_UNITS:
            raise ValueError(
                f"Invalid interval_unit {data['interval_unit']!r}; must be one of {INTERVAL_UNITS}"
            )
        try:
            last_completed = date.fromisoformat(data["last_completed"])
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Invalid last_completed date {data['last_completed']!r}: {exc}"
            ) from exc
        return cls(
            name=data["name"],
            interval_value=data["interval_value"],
            interval_unit=data["interval_unit"],
            last_completed=last_completed,
        )
