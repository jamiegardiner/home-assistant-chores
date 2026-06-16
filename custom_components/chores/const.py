from enum import IntFlag

DOMAIN = "chores"

STATUS_DONE = "done"
STATUS_OVERDUE = "overdue"
STATUS_SNOOZED = "snoozed"
STATUS_OPTIONS = [STATUS_DONE, STATUS_OVERDUE, STATUS_SNOOZED]

SNOOZE_UNITS: tuple[str, ...] = ("minutes", "hours", "days", "weeks")

DEFAULT_SNOOZE_VALUE: int = 1
DEFAULT_SNOOZE_UNIT: str = "days"
DEFAULT_NOTIFICATION_TIME: str = "08:00"

MAX_NUMBER_VALUE: int = 365

SERVICE_COMPLETE = "complete"
SERVICE_SNOOZE = "snooze"
SERVICE_UNSNOOZE = "unsnooze"


REPAIR_ISSUE_CORRUPT_FIELD = "corrupt_recoverable_field"
REPAIR_ISSUE_CORRUPT_CONFIG = "corrupt_unrecoverable_config"


class ChoreSensorEntityFeature(IntFlag):
    """Features supported by ChoreSensor entities."""

    TARGETABLE = 1
