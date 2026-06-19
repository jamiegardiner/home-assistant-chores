# Chore Tracker — Service Reference

These services can be used in Home Assistant automations and scripts. You can target an individual chore, its device, an area, or a label — the service runs on every matching chore.

______________________________________________________________________

## `chores.complete`

Marks a chore as done and schedules the next due date.

| Field          | Required | Description                                                       |
| -------------- | -------- | ----------------------------------------------------------------- |
| `completed_at` | No       | Date and time of completion, if not now. Cannot be in the future. |

**Mark complete now:**

```yaml
action: chores.complete
target:
  entity_id: sensor.vacuum_living_room
```

**Record a specific past completion time:**

```yaml
action: chores.complete
target:
  entity_id: sensor.vacuum_living_room
data:
  completed_at: "2026-06-08 14:30:00"
```

______________________________________________________________________

## `chores.snooze`

Snooze a chore for a given duration. Omit both `value` and `unit` to use the device's configured default snooze duration (the same as pressing the Snooze button). Provide both to override the default.

| Field   | Required | Description                                                                         |
| ------- | -------- | ----------------------------------------------------------------------------------- |
| `value` | No       | Integer between 1 and 365 — how many units to snooze. Omit with `unit` for default. |
| `unit`  | No       | One of `minutes`, `hours`, `days`, or `weeks`. Omit with `value` for default.       |

Both fields must be supplied together — providing only one raises a validation error.

**Use the device default:**

```yaml
action: chores.snooze
target:
  entity_id: sensor.vacuum_living_room
```

**Override with a specific duration:**

```yaml
action: chores.snooze
target:
  entity_id: sensor.vacuum_living_room
data:
  value: 3
  unit: days
```

______________________________________________________________________

## `chores.snooze_exact`

Snooze a chore until a specific date and time. Use this when you know the exact expiry moment rather than a duration.

| Field          | Required | Description                                                      |
| -------------- | -------- | ---------------------------------------------------------------- |
| `snooze_until` | Yes      | The datetime at which the snooze expires. Must be in the future. |

```yaml
action: chores.snooze_exact
target:
  entity_id: sensor.vacuum_living_room
data:
  snooze_until: "2026-06-21 08:00:00"
```

______________________________________________________________________

## `chores.unsnooze`

Cancel an active snooze and return the chore to its normal state immediately.

```yaml
action: chores.unsnooze
target:
  entity_id: sensor.vacuum_living_room
```
