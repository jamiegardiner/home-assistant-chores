DOMAIN = "chores"

# Sentinel feature flag: marks ChoreSensor as a valid service target.
# Diagnostic sensors deliberately omit this so they are excluded from the
# entity picker and from service fan-out when a device/area is targeted.
CHORE_SERVICE_FEATURE = 1

STATUS_DONE = "done"
STATUS_OVERDUE = "overdue"
STATUS_SNOOZED = "snoozed"
STATUS_OPTIONS = [STATUS_DONE, STATUS_OVERDUE, STATUS_SNOOZED]
