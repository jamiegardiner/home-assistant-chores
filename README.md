# 🏠 Chore Tracker

_Your household chores don't follow a calendar. Now your reminders don't have to either._

A [HACS](https://hacs.xyz)-compatible custom integration for [Home Assistant](https://www.home-assistant.io) that tracks recurring household chores and surfaces their status as HA devices.

Each chore appears as a device in Settings → Devices & Services with its own status, history, controls, and settings. It transitions automatically between `done` and `overdue` at the configured interval.

Scheduling is **rolling**: the next due date is calculated by adding the configured interval to the last completion time, so each completion rolls the schedule forward from that moment. Completing a chore late shifts its next due date forward — it does not catch up to a fixed calendar date. For fixed-day reminders (e.g. "every Tuesday"), use Home Assistant's calendar or schedule helpers instead of this integration.

______________________________________________________________________

## 🔧 Installation

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

## 📦 Entities

Each chore appears in **Settings → Devices & Services** as a single device.

### 🚦 Status

Each chore has three states:

| State     | Meaning                                                                            |
| --------- | ---------------------------------------------------------------------------------- |
| `done`    | ✅ The chore has been completed and is not yet due again                           |
| `overdue` | ⏰ The chore's due date has passed without being marked complete                   |
| `snoozed` | 😴 The chore is snoozed; overdue reminders are suppressed until the snooze expires |

### 📡 Sensors

| Entity         | Description                                                           |
| -------------- | --------------------------------------------------------------------- |
| Last completed | When the chore was last marked complete; unavailable before first use |
| Next due       | When the chore will next become overdue; unavailable before first use |
| Snooze expiry  | When an active snooze expires; unavailable when not snoozed           |

### 🔘 Buttons

| Button   | Action                                                  |
| -------- | ------------------------------------------------------- |
| Complete | Marks the chore as done and schedules the next due date |
| Snooze   | Defers the chore by the configured snooze duration      |
| Unsnooze | Cancels an active snooze immediately                    |

### ⚙️ Configuration

Found in the device's **Configuration** section:

| Entity               | Description                                                                    |
| -------------------- | ------------------------------------------------------------------------------ |
| Interval             | Days between completions before the chore becomes overdue                      |
| Default snooze value | How many units to snooze when the Snooze button is pressed                     |
| Default snooze unit  | Time unit for the default snooze (minutes / hours / days / weeks)              |
| Notification time    | Time of day when the chore transitions from done to overdue. Defaults to 08:00 |

______________________________________________________________________

## 📋 Managing chores

All configuration is done through the Home Assistant UI — there is no YAML.

**To add a chore:**

1. Go to **Settings → Devices & Services**
2. Click **Add Integration** and search for **Chore Tracker**
3. Enter a name and a recurrence interval (days)

The new chore starts overdue immediately. Press **Complete** to record the first completion and start the regular cycle.

**To edit a chore:**

1. Go to **Settings → Devices & Services**
2. Find **Chore Tracker**, open the integration, and click the chore device
3. Use the **Configuration** entities on the device page to update the interval, snooze defaults, and notification time
4. To rename the chore, use Home Assistant's built-in device rename (three-dot menu → **Rename** on the device page)

**To remove a chore:**

1. Go to **Settings → Devices & Services**
2. Find **Chore Tracker**, open the integration, click the three-dot menu (⋮) next to the chore entry, and choose **Delete**

Deleting a chore only removes that chore — all others are unaffected.

______________________________________________________________________

## ⚡ Services

These services can be used in automations and scripts.

### `chores.complete`

Marks a chore as done and schedules the next due date.

| Field          | Required | Description                                                       |
| -------------- | -------- | ----------------------------------------------------------------- |
| `completed_at` | No       | Date and time of completion, if not now. Cannot be in the future. |

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

Snooze a chore for a given duration. Provide a `value` (positive integer) and a `unit` (`minutes`, `hours`, `days`, or `weeks`).

```yaml
action: chores.snooze
target:
  entity_id: sensor.chore_vacuum_living_room
data:
  value: 3
  unit: days
```

______________________________________________________________________

### `chores.unsnooze`

Cancel an active snooze and return the chore to its normal state immediately.

```yaml
action: chores.unsnooze
target:
  entity_id: sensor.chore_vacuum_living_room
```

______________________________________________________________________

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the versioning model, release strategy, PR title conventions, and contributor flow.

______________________________________________________________________

_🤖 Written by AI, coordinated by a human._
