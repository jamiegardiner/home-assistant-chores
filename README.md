# Chore Tracker

A [HACS](https://hacs.xyz)-compatible custom integration for [Home Assistant](https://www.home-assistant.io) that tracks recurring household chores and surfaces their status as HA devices.

Each chore becomes a device in Settings → Devices & Services, grouping its status sensor, diagnostic sensors, action buttons, and configuration controls. It transitions automatically between `done` and `overdue` at the configured interval with no polling.

______________________________________________________________________

## Installation

### Option A — one click (recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=jamiegardiner&repository=home-assistant-chores&category=integration)

### Option B — manual HACS setup

1. In Home Assistant go to **Settings → HACS**
2. Click the three-dot menu (⋮) in the top-right corner and choose **Custom repositories**
3. Paste `https://github.com/jamiegardiner/home-assistant-chores` and set the category to **Integration**, then click **Add**
4. Search for **Chore Tracker** in the HACS store and click **Download**
5. Restart Home Assistant
6. Go to **Settings → Devices & Services → Add Integration**, search for **Chore Tracker**, and follow the setup wizard

______________________________________________________________________

## Entities

Each chore appears in **Settings → Devices & Services** as a single device grouping the entities below.

### Status sensor

The primary entity (`sensor.chore_<name>`) reports the chore's current state:

| State     | Meaning                                                                           |
| --------- | --------------------------------------------------------------------------------- |
| `done`    | The chore has been completed and is not yet due again                             |
| `overdue` | The chore's due date has passed without being marked complete                     |
| `snoozed` | The chore is snoozed; overdue transitions are suppressed until the snooze expires |

### Diagnostic sensors

| Entity         | Type     | Description                                                         |
| -------------- | -------- | ------------------------------------------------------------------- |
| Last completed | Datetime | The date and time the chore was last marked complete                |
| Next due       | Datetime | The datetime the chore will next transition to `overdue`            |
| Snooze Expiry  | Datetime | The datetime an active snooze expires; unavailable when not snoozed |

### Buttons

| Button   | Action                                                         |
| -------- | -------------------------------------------------------------- |
| Complete | Marks the chore as done today and schedules the next due date  |
| Snooze   | Defers the chore by the configured default snooze value + unit |
| Unsnooze | Cancels an active snooze immediately                           |

### Configuration entities

These writable entities (in the device's **Configuration** section) edit the chore's settings in place — no reload, no entity teardown.

| Entity               | Type   | Description                                                     |
| -------------------- | ------ | --------------------------------------------------------------- |
| Interval             | Number | Days between completions before the chore becomes `overdue`     |
| Default snooze value | Number | The count used when the Snooze button is pressed                |
| Default snooze unit  | Select | The time unit for the default snooze (minutes/hours/days/weeks) |

______________________________________________________________________

## Managing chores

All configuration is done through the Home Assistant UI — there is no YAML.

**To add a chore:**

1. Go to **Settings → Devices & Services**
2. Click **Add Integration** and search for **Chore Tracker**
3. Enter a name, recurrence interval (days), and last-completed date and time

The default snooze duration is set afterwards via the chore device's **Configuration** entities (see [Configuration entities](#configuration-entities)).

**To edit a chore:**

1. Go to **Settings → Devices & Services**
2. Find **Chore Tracker**, open the integration, and click the chore device
3. Click **Configure** to update the name, interval, or last-completed date and time. The interval and snooze defaults can also be changed directly via the device's **Configuration** entities.

**To remove a chore:**

1. Go to **Settings → Devices & Services**
2. Find **Chore Tracker**, open the integration, click the three-dot menu (⋮) next to the chore entry, and choose **Delete**

Removing a config entry removes just that chore — all other chores are unaffected.

______________________________________________________________________

## Services

Services target the primary status sensor (`sensor.chore_<name>`) or the chore's device.

### `chores.complete`

Mark a chore as done. Records `last_completed` as the current datetime (or a supplied past datetime) and schedules the next `overdue` transition.

| Field          | Required | Description                                                                 |
| -------------- | -------- | --------------------------------------------------------------------------- |
| `completed_at` | No       | ISO 8601 datetime of completion. Must not be in the future. Defaults to now |

```yaml
action: chores.complete
target:
  entity_id: sensor.chore_vacuum_living_room
```

**Record a specific past completion time:**

```yaml
action: chores.complete
target:
  entity_id: sensor.chore_vacuum_living_room
data:
  completed_at: "2026-06-08 14:30:00"
```

______________________________________________________________________

### `chores.snooze`

Snooze a chore for a given duration, suppressing `overdue` transitions in the meantime. Provide a `value` (positive integer) and a `unit` (`minutes`, `hours`, `days`, or `weeks`).

**Snooze for 30 minutes:**

```yaml
action: chores.snooze
target:
  entity_id: sensor.chore_vacuum_living_room
data:
  value: 30
  unit: minutes
```

**Snooze for 3 days:**

```yaml
action: chores.snooze
target:
  entity_id: sensor.chore_vacuum_living_room
data:
  value: 3
  unit: days
```

**Snooze for 2 weeks:**

```yaml
action: chores.snooze
target:
  entity_id: sensor.chore_vacuum_living_room
data:
  value: 2
  unit: weeks
```

______________________________________________________________________

### `chores.unsnooze`

Cancel an active snooze and return the chore to its normal `done` or `overdue` state immediately.

```yaml
action: chores.unsnooze
target:
  entity_id: sensor.chore_vacuum_living_room
```

______________________________________________________________________

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the versioning model, release strategy, PR title conventions, and contributor flow.
