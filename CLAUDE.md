# Chore Tracker — Home Assistant Custom Integration

A HACS-compatible custom integration that tracks recurring household chores and surfaces their status as HA devices. Each chore becomes a device with 8 entities — a primary status sensor, 4 diagnostic sensors, and 3 action buttons — automatically transitioning between `done` and `overdue` at the configured interval with no polling.

---

## Project structure

```
custom_components/chores/
  __init__.py          # entry setup/teardown, forwards to platforms and services
  const.py             # DOMAIN, STATUS_* constants
  models.py            # ChoreConfig dataclass (name, interval_days, default_snooze_days)
  coordinator.py       # ChoresCoordinator — runtime state, timers, persistence
  button.py            # Complete, Snooze, Unsnooze button entities
  sensor.py            # ChoreSensor + 4 diagnostic sensor entities (one set per config entry)
  config_flow.py       # UI config flow (create chore) + options flow (edit chore)
  services.py          # chores.complete/snooze/unsnooze service handlers
  services.yaml        # service structure for the HA UI (target, fields, selectors)
  strings.json         # translation source (used by tooling/validation)
  translations/
    en.json            # runtime translations loaded by HA (mirrors strings.json)
  manifest.json        # HACS/HA integration metadata

tests/
  components/chores/
    conftest.py        # shared fixtures
    test_config_flow.py
    test_coordinator.py
    test_models.py
    test_sensor.py
    test_services.py

docker-compose.yml     # runs ghcr.io/home-assistant/home-assistant:stable on :8123; bind-mounts ./custom_components/chores into /config/custom_components/chores
pyproject.toml         # project metadata + mypy config
requirements_test.txt  # pinned dev/test dependencies
Makefile               # all common dev tasks (see below)
```

---

## Architecture

### Data model

Each chore is a separate config entry (`integration_type: device`). All state lives in `entry.options` — there is no separate Store:

```json
{
  "name": "Bins",
  "interval_days": 14,
  "default_snooze_days": 1,
  "last_completed": "2026-06-01",
  "snooze_until": null
}
```

### Data flow

```
entry.options (one chore per entry)
        │
        ▼
ChoresCoordinator.async_initialize()
  ├── reads last_completed / snooze_until / interval_days / default_snooze_days from entry.options
  ├── builds ChoreRuntime (status, next_due)
  └── schedules a point-in-time timer at next_due
        │
        ▼ timer fires / service called / options edited
ChoresCoordinator.async_set_updated_data(snapshot)
        │
        ▼
ChoreSensor.native_value + 4 diagnostic sensors (pushed by CoordinatorEntity)
```

Options updates (from config flow edits) are handled in-place via `async_update_config` — no `async_reload`, no entity teardown.

### Key types

| Type | File | Purpose |
|---|---|---|
| `ChoreConfig` | `models.py` | Immutable config: name, interval_days, default_snooze_days |
| `ChoreRuntime` | `coordinator.py` | Mutable runtime state: status, next_due, timer cancel fns |
| `ChoresCoordinator` | `coordinator.py` | Owns one chore, pushes updates to the sensor |
| `ChoreSensor` | `sensor.py` | Primary `CoordinatorEntity` — reads status from coordinator snapshot |
| `_ChoreDateSensor` | `sensor.py` | Base class for the 3 diagnostic date sensors |
| `ChoreDefaultSnoozeDaysSensor` | `sensor.py` | Diagnostic sensor for default_snooze_days |
| `Chore*Button` | `button.py` | Complete / Snooze / Unsnooze button entities |

### Status transitions

- **`done` → `overdue`**: HA point-in-time timer fires at `next_due` (start of local day of `last_completed + interval`)
- **`overdue` → `done`**: `chores.complete` service call resets `last_completed` to today, persists to `entry.options`, recomputes `next_due`, schedules new timer
- **`snoozed`**: any state can be snoozed; `chores.snooze` sets `snooze_until` in `entry.options`; a snooze-expiry timer fires at that date

---

## Make commands

```bash
# Setup
make venv           # create .venv and install all deps (run once)
make install        # sync updated deps into existing .venv
make venv-destroy   # delete .venv entirely

# Code quality (run before every commit)
make test           # pytest
make lint           # ruff check — flags bugs and style issues
make format         # auto-fix formatting (ruff format) and fixable lint issues (ruff check --fix)
make typecheck      # mypy
make check          # lint + format-check + typecheck + test in one go (mirrors CI, read-only)

# Docker (local HA instance at http://localhost:8123)
make up             # start Home Assistant
make down           # stop and remove HA container
make stop           # pause HA container (preserves container state)
make start          # resume a paused HA container
make logs           # tail HA container logs
```

Activate the venv for interactive use: `source .venv/bin/activate`

---

## Adding a new feature

### 1. New sensor attribute
Add the key to `coordinator.py:_snapshot()`. To surface it as a diagnostic entity, create a new sensor class in `sensor.py` and add it to `async_setup_entry`.

### 2. New service
Services are entity services — HA handles all target resolution (entity, area, device, label) and fan-out automatically.
1. Add the service name constant and schema dict to `services.py`.
2. Add a handler function `_handle_<name>(entity: ChoreSensor, call: ServiceCall)` in `sensor.py` and register it in `async_setup_entry` via `platform.async_register_entity_service`.
3. Add the service structure (target, fields, selectors) to `services.yaml` — but **not** `name`/`description`. Service and field display strings live under the `services` key in both `strings.json` and `translations/en.json` (kept in sync, per HA's 2023.8+ convention). No unregister step needed — entity services are torn down automatically when the platform unloads.

### 3. New platform (e.g. `button`, `select`)
1. Add `Platform.BUTTON` (etc.) to `PLATFORMS` in `__init__.py`.
2. Create `custom_components/chores/<platform>.py` implementing `async_setup_entry` and the entity class.
3. The entity should be a `CoordinatorEntity` and read state from `coordinator.data` (flat dict).

### 4. New config option
1. Add the field to `ChoreConfig` in `models.py` (update `from_dict`).
2. Add the form field to `config_flow.py:_chore_schema()` (used by both user and options flow).
3. Add the label to both `strings.json` and `translations/en.json` under both `config.step.user.data` and `options.step.init.data`.

### 5. Strings / translations
Every user-visible string must exist in **both** files:
- `strings.json` — used by HA tooling and validation
- `translations/en.json` — loaded at runtime by HA

They must be kept in sync. If you add to one, add to the other.

---

## Testing conventions

- Framework: `pytest` + `pytest-homeassistant-custom-component`
- Async mode: `auto` (configured in `pytest.ini`)
- Config flow tests must request the `enable_custom_integrations` fixture (directly or via `autouse`) so HA's loader can find the integration:
  ```python
  @pytest.fixture(autouse=True)
  def auto_enable_custom_integrations(enable_custom_integrations):
      pass
  ```
- Use `MockConfigEntry` from `pytest_homeassistant_custom_component.common` to set up config entries in tests without going through the UI flow.
- Coordinator tests must call `entry.add_to_hass(hass)` so that `hass.config_entries.async_update_entry` works; no Store patching needed (state lives in `entry.options`).

---

## Issue → PR workflow

All feature and fix work goes through GitHub Issues:

```
/new-issue <rough description>   → guided issue creation (user story + BDD ACs)
/implement <issue-number>        → plan mode → approval → code → PR
```

**Branch naming:** `issue-<number>-<short-slug>`
**Commit style:** `feat(issue-<number>): <description>` or `fix(issue-<number>): <description>`
**PRs must contain** `Closes #<number>` so the issue auto-closes on merge.

---

## Constraints

- Each chore is a separate config entry — multiple entries are allowed. **Adding a chore** = "Add Integration → Chores". **Removing a chore** = delete that config entry.
- No YAML configuration — all setup is through the UI.
- All chore state (`last_completed`, `snooze_until`) lives in `entry.options`, not in a separate Store. The update listener calls `coordinator.async_update_config` (never `async_reload`) so edits are applied in-place without entity teardown.
- Python `>=3.14.2` (matches Home Assistant's own requirement).
- `integration_type: device` in `manifest.json` — chores appear in the Devices & Services panel, not the Helpers panel.
- Interval is stored as `interval_days` (int, days only). The UI previously offered a weeks selector; it no longer does.
- `default_snooze_days` (default: 1) controls how far ahead the Snooze button defers the chore.
- The Snooze button uses `default_snooze_days`; the `chores.snooze` service still accepts an explicit date/offset.
