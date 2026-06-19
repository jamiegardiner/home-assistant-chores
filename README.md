![Chore Tracker](assets/banner.png)

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration) [![Version](https://img.shields.io/github/v/release/jamiegardiner/home-assistant-chores)](https://github.com/jamiegardiner/home-assistant-chores/releases) [![CI](https://github.com/jamiegardiner/home-assistant-chores/actions/workflows/ci.yaml/badge.svg)](https://github.com/jamiegardiner/home-assistant-chores/actions/workflows/ci.yaml)

*Because "when did we last clean the gutters?" shouldn't need to be a mystery.*

Chore Tracker helps you keep on top of recurring household jobs inside Home Assistant. Whether it's cleaning the gutters, descaling the kettle, replacing smoke alarm batteries, or changing air filters, you'll always know what's due and what can wait.

Everything runs locally inside Home Assistant — no accounts, no cloud services, and no data leaving your home.

Each chore appears as its own device in **Settings → Devices & Services**, complete with status, history, controls, and configuration. Once you've set up a chore, Home Assistant keeps track of when it's due again — all you need to do is mark it as complete.

Chores use a **rolling schedule**. When you complete a task, its next due date is calculated from that completion time. If a monthly chore is finished a week late, the next reminder moves forward by a week too.

Looking for fixed schedules like "every Tuesday" or "the first day of every month"? Home Assistant's calendar and schedule helpers are a better fit.

______________________________________________________________________

## ✨ What it can do

- 📱 **Every chore gets its own Home Assistant device** with history, controls, and configuration
- 🔄 **Set it and forget it** — chores automatically become overdue when they're due again
- 📅 **Rolling schedules** that adapt to when chores are actually completed
- 😴 **Snooze and unsnooze** chores with configurable defaults (minutes, hours, days, or weeks)
- 🕗 **Choose when chores become overdue** with a configurable overdue time of day
- 📡 **Date sensors** for last completed and next due dates (dashboard-ready); diagnostic snooze expiry sensor (hidden by default)
- 🖱️ **Full UI configuration** — create and manage chores without touching YAML
- ⚡ **Automation-friendly services** for completing, snoozing, and unsnoozing chores

______________________________________________________________________

## 🚀 Getting Started

Install via HACS in one click (see [Installation](#-installation) below), then restart Home Assistant.

Adding your first chore takes less than a minute:

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **Chore Tracker**
3. Enter a name (for example, "Vacuum living room")
4. Enter an interval and choose the unit (days or weeks, for example `2 weeks`)
5. Click **Submit**

That's it.

New chores start in an overdue state so you can record the first completion and begin the regular cycle. Press **Complete** once, and Chore Tracker will start tracking it from there.

______________________________________________________________________

## 🎯 Designed to do one thing well

Chore Tracker intentionally stays focused on tracking recurring chores.

Rather than trying to become a full household management platform, it concentrates on answering a simple question:

> Has this job been done, and when is it due again?

A few things are deliberately out of scope:

- **Fixed calendar scheduling** — chores are based on rolling intervals from the last completion date. If you need "every Tuesday" reminders, Home Assistant's built-in calendar and schedule helpers are a better choice.
- **Gamification, points, and assignments** — no scores, leaderboards, or assigning chores to individual people.
- **Built-in notifications** — Chore Tracker tracks status and exposes entities. How you're notified is entirely up to you.
- **Custom dashboard cards** — chore data is available through standard Home Assistant entities, so it works with the cards and dashboards you already use.
- **Cloud services and external accounts** — everything stays local to Home Assistant.
- **YAML configuration** — setup and management happen entirely through the UI.

______________________________________________________________________

## 🔧 Installation

### Option A — One-click install (recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=jamiegardiner&repository=home-assistant-chores&category=integration)

### Option B — Manual HACS setup

1. Open **Settings → HACS**
2. Click the three-dot menu (⋮) in the top-right corner and select **Custom repositories**
3. Add `https://github.com/jamiegardiner/home-assistant-chores`
4. Select **Integration** as the category
5. Click **Add**
6. Search for **Chore Tracker** in HACS and click **Download**
7. Restart Home Assistant
8. Go to **Settings → Devices & Services → Add Integration**
9. Search for **Chore Tracker** and complete the setup wizard

______________________________________________________________________

## 📦 Entities

Each chore appears in Home Assistant as a dedicated device.

### 🚦 Status

Each chore has one of three states:

| State     | Meaning                                                  |
| --------- | -------------------------------------------------------- |
| `done`    | ✅ The chore has been completed and is not yet due again |
| `overdue` | ⏰ The chore is due and waiting to be completed          |
| `snoozed` | 😴 The chore has been temporarily deferred               |

The status sensor also exposes `next_due` and `last_completed` as extra state attributes, useful for templates.

### 📡 Sensors

| Entity         | Description                             | Notes                           |
| -------------- | --------------------------------------- | ------------------------------- |
| Last completed | When the chore was last marked complete | Primary — appears on dashboards |
| Next due       | When the chore will next become overdue | Primary — appears on dashboards |
| Snooze expiry  | When the current snooze period ends     | Diagnostic — hidden by default  |

### 🔘 Buttons

| Button   | Action                                                      |
| -------- | ----------------------------------------------------------- |
| Complete | Marks the chore as complete and schedules the next due date |
| Snooze   | Defers the chore using the configured snooze duration       |
| Unsnooze | Ends an active snooze immediately                           |

### ⚙️ Configuration

Available from the device's **Configuration** section:

| Entity              | Description                                                 |
| ------------------- | ----------------------------------------------------------- |
| Interval            | How many days or weeks before the chore becomes overdue     |
| Interval unit       | Days or weeks                                               |
| Snooze interval     | Amount of time to snooze when the Snooze button is pressed  |
| Snooze unit         | Minutes, hours, days, or weeks                              |
| Overdue time of day | Time of day when the chore becomes overdue (default: 08:00) |

______________________________________________________________________

## 📋 Managing chores

Everything is configured through the Home Assistant UI.

### Adding a chore

1. Go to **Settings → Devices & Services**
2. Click **Add Integration**
3. Search for **Chore Tracker**
4. Enter a name and recurrence interval

The chore will appear immediately and can be completed to start its regular schedule.

### Editing a chore

1. Go to **Settings → Devices & Services**
2. Open **Chore Tracker**
3. Select the chore device
4. Use the **Configuration** entities to update intervals, snooze defaults, and overdue times of day

To rename a chore, use Home Assistant's built-in device rename option from the device page.

### Removing a chore

1. Go to **Settings → Devices & Services**
2. Open **Chore Tracker**
3. Click the three-dot menu (⋮) beside the chore
4. Select **Delete**

Removing a chore only affects that chore. All other chores remain unchanged.

______________________________________________________________________

## ⚡ Services

Want chores to be part of your automations?

Chore Tracker provides four services:

- `chores.complete`
- `chores.snooze`
- `chores.snooze_exact`
- `chores.unsnooze`

Use them from automations, scripts, dashboards, voice assistants, or anything else that can call Home Assistant services.

See [docs/services.md](docs/services.md) for full service documentation and [docs/automations.md](docs/automations.md) for worked automation examples.

______________________________________________________________________

## 🔍 Troubleshooting

Running into an unexpected state or a repair issue? See [docs/troubleshooting.md](docs/troubleshooting.md) for guidance on common scenarios including corrupt field recovery, failed entry loads, and why new chores start overdue.

______________________________________________________________________

## 🤝 Contributing

Contributions, bug reports, feature suggestions, and pull requests are welcome.

See [CONTRIBUTING.md](CONTRIBUTING.md) for details on versioning, releases, and contributor guidelines.

______________________________________________________________________

_🤖 Designed by a human, built with Claude._
