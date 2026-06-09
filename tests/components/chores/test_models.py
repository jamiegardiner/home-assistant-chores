from datetime import date

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


def test_const_values() -> None:
    assert DOMAIN == "chores"
    assert CONF_CHORES == "chores"
    assert set(INTERVAL_UNITS) == {"days", "weeks"}
