# Chores

A [HACS](https://hacs.xyz)-compatible custom integration for [Home Assistant](https://www.home-assistant.io) that tracks recurring household chores and surfaces their status as sensor entities.

Each chore becomes a sensor whose state is `done`, `overdue`, or `snoozed`, transitioning automatically at the configured interval — no polling required. Mark a chore complete from an automation, a dashboard button, or the Developer Tools, and the clock resets.

---

## Installation

### Option A — one click (recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=jamiegardiner&repository=home-assistant-chores&category=integration)

### Option B — manual HACS setup

1. In Home Assistant go to **Settings → HACS**
2. Click the three-dot menu (⋮) in the top-right corner and choose **Custom repositories**
3. Paste `https://github.com/jamiegardiner/home-assistant-chores` and set the category to **Integration**, then click **Add**
4. Search for **Chores** in the HACS store and click **Download**
5. Restart Home Assistant
6. Go to **Settings → Devices & Services → Add Integration**, search for **Chores**, and follow the setup wizard

---

## Sensor entities

Each chore you create becomes a sensor entity named `sensor.chore_<name>`.

### States

| State | Meaning |
|-------|---------|
| `done` | The chore has been completed and is not yet due again |
| `overdue` | The chore's due date has passed without being marked complete |
| `snoozed` | The chore has been snoozed; overdue transitions are suppressed until the snooze date |

### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `last_completed` | ISO date or `null` | The date the chore was last marked complete |
| `next_due` | ISO date or `null` | The date the chore will next transition to `overdue` |
| `snooze_until` | ISO date or `null` | The date an active snooze expires; `null` when not snoozed |

---

## Managing chores

All configuration is done through the Home Assistant UI — there is no YAML.

**To add a chore:**

1. Go to **Settings → Devices & Services**
2. Find the **Chores** integration and click **Configure**
3. Choose **Add chore**
4. Enter a name and a recurrence interval (number + unit: days, weeks, or months)

**To remove a chore:**

1. Go to **Settings → Devices & Services → Chores → Configure**
2. Choose **Remove chore** and select the chore to delete

---

## Services

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

