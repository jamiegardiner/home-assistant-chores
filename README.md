# Chore Tracker

A [HACS](https://hacs.xyz)-compatible custom integration for [Home Assistant](https://www.home-assistant.io) that tracks recurring household chores and surfaces their status as HA devices.

Each chore becomes a device with 8 entities — a primary status sensor, 4 diagnostic sensors, and 3 action buttons — transitioning automatically between `done` and `overdue` at the configured interval with no polling.

---

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

---

## Entities

Each chore appears in **Settings → Devices & Services** as a device with 8 entities.

### Status sensor

The primary entity (`sensor.chore_<name>`) reports the chore's current state:

| State | Meaning |
|-------|---------|
| `done` | The chore has been completed and is not yet due again |
| `overdue` | The chore's due date has passed without being marked complete |
| `snoozed` | The chore is snoozed; overdue transitions are suppressed until the snooze date |

### Diagnostic sensors

| Entity | Type | Description |
|--------|------|-------------|
| Last completed | Date | The date the chore was last marked complete |
| Next due | Date | The date the chore will next transition to `overdue` |
| Snooze until | Date | The date an active snooze expires; unavailable when not snoozed |
| Default snooze days | Integer | How many days the Snooze button defers the chore |

### Buttons

| Button | Action |
|--------|--------|
| Complete | Marks the chore as done today and schedules the next due date |
| Snooze | Defers the chore by the configured default snooze days |
| Unsnooze | Cancels an active snooze immediately |

---

## Managing chores

All configuration is done through the Home Assistant UI — there is no YAML.

**To add a chore:**

1. Go to **Settings → Devices & Services**
2. Click **Add Integration** and search for **Chore Tracker**
3. Enter a name, recurrence interval (days), default snooze duration, and last-completed date

**To edit a chore:**

1. Go to **Settings → Devices & Services**
2. Find **Chore Tracker**, open the integration, and click the chore device
3. Click **Configure** to update the name, interval, snooze duration, or last-completed date

**To remove a chore:**

1. Go to **Settings → Devices & Services**
2. Find **Chore Tracker**, open the integration, click the three-dot menu (⋮) next to the chore entry, and choose **Delete**

Removing a config entry removes just that chore — all other chores are unaffected.

---

## Services

Services target the primary status sensor (`sensor.chore_<name>`) or the chore's device.

### `chores.complete`

Mark a chore as done. Resets `last_completed` to today and schedules the next `overdue` transition.

```yaml
action: chores.complete
target:
  entity_id: sensor.chore_vacuum_living_room
```

---

### `chores.snooze`

Snooze a chore until a given date, suppressing `overdue` transitions in the meantime.
Provide **exactly one** of `snooze_days`, `snooze_weeks`, or `snooze_until`.

**Snooze for a number of days:**

```yaml
action: chores.snooze
target:
  entity_id: sensor.chore_vacuum_living_room
data:
  snooze_days: 3
```

**Snooze for a number of weeks:**

```yaml
action: chores.snooze
target:
  entity_id: sensor.chore_vacuum_living_room
data:
  snooze_weeks: 2
```

**Snooze until a specific date:**

```yaml
action: chores.snooze
target:
  entity_id: sensor.chore_vacuum_living_room
data:
  snooze_until: "2026-07-01"
```

---

### `chores.unsnooze`

Cancel an active snooze and return the chore to its normal `done` or `overdue` state immediately.

```yaml
action: chores.unsnooze
target:
  entity_id: sensor.chore_vacuum_living_room
```
