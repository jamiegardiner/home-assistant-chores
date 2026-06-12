from enum import IntFlag

DOMAIN = "chores"

STATUS_DONE = "done"
STATUS_OVERDUE = "overdue"
STATUS_SNOOZED = "snoozed"
STATUS_OPTIONS = [STATUS_DONE, STATUS_OVERDUE, STATUS_SNOOZED]

SNOOZE_UNITS: tuple[str, ...] = ("minutes", "hours", "days", "weeks")


class ChoreSensorEntityFeature(IntFlag):
    """Features supported by ChoreSensor entities."""

    TARGETABLE = 1
