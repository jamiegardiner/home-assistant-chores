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

Snooze a chore for a given duration. Provide a `value` (integer, 1–365) and a `unit` (`minutes`, `hours`, `days`, or `weeks`).

| Field   | Required | Description                                          |
| ------- | -------- | ---------------------------------------------------- |
| `value` | Yes      | Integer between 1 and 365 — how many units to snooze |
| `unit`  | Yes      | One of `minutes`, `hours`, `days`, or `weeks`        |

```yaml
action: chores.snooze
target:
  entity_id: sensor.vacuum_living_room
data:
  value: 3
  unit: days
```

______________________________________________________________________

## `chores.unsnooze`

Cancel an active snooze and return the chore to its normal state immediately.

```yaml
action: chores.unsnooze
target:
  entity_id: sensor.vacuum_living_room
```
