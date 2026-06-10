# Chores

A [HACS](https://hacs.xyz)-compatible custom integration for [Home Assistant](https://www.home-assistant.io) that tracks recurring household chores and surfaces their status as sensor entities.

Each chore becomes a sensor whose state is `done` or `overdue`, automatically transitioning at the configured interval — no polling required.

## Features

- Add chores with a name and recurrence interval (days, weeks, or months)
- Each chore appears as a sensor entity in Home Assistant
- Mark chores complete via a service call or UI button
- Status transitions happen automatically at the configured interval
- Snooze support via the `chores.unsnooze` service
- State survives Home Assistant restarts

## Installation

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=jamiegardiner&repository=home-assistant-chores&category=integration)

1. Add this repository to HACS as a custom repository (category: Integration)
2. Install the **Chores** integration via HACS
3. Restart Home Assistant
4. Go to **Settings → Devices & Services → Add Integration** and search for **Chores**

## Usage

After adding the integration, use the **Options** menu to add or remove chores. Each chore needs:

- **Name** — displayed in the UI and used as the entity ID
- **Interval** — how often the chore recurs (number + unit)

### Services

| Service | Description |
|---------|-------------|
| `chores.complete` | Mark a chore as done (resets the timer) |
| `chores.unsnooze` | Cancel a snooze and return the chore to its normal schedule |

## Development

```bash
make venv    # create venv and install dependencies
make check   # lint, format-check, typecheck, tests (mirrors CI)
make format  # auto-fix formatting and lint issues
make up      # start a local Home Assistant instance on :8123
```

See the [Makefile](Makefile) for all available targets.
