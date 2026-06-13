# Chore Tracker — Home Assistant Custom Integration

A HACS-compatible custom integration that tracks recurring household chores and surfaces their status as HA devices. Each chore becomes a device that transitions automatically between `done` and `overdue` at the configured interval.

______________________________________________________________________

## Project structure

```
custom_components/chores/
  __init__.py          # entry setup/teardown, forwards to platforms and services
  const.py             # DOMAIN, STATUS_* constants
  models.py            # ChoreConfig dataclass (name, interval_days, default_snooze_value, default_snooze_unit, notification_time)
  coordinator.py       # ChoresCoordinator — runtime state, timers, persistence
  button.py            # Complete, Snooze, Unsnooze button entities
  number.py            # Interval and Default Snooze Value CONFIG number entities
  select.py            # Default Snooze Unit CONFIG select entity
  time.py              # Notification Time CONFIG time entity
  sensor.py            # ChoreSensor + 3 diagnostic sensor entities (one set per config entry)
  config_flow.py       # UI config flow (create chore — name + interval only; no options flow)
  services.py          # chores.complete/snooze/unsnooze service handlers
  services.yaml        # service structure for the HA UI (target, fields, selectors)
  strings.json         # translation source (used by tooling/validation)
  translations/
    en.json            # runtime translations loaded by HA (mirrors strings.json)
  manifest.json        # HACS/HA integration metadata

tests/components/chores/   # mirrors source layout; one test file per module
```

______________________________________________________________________

## Architecture

### Data model

Each chore is a separate config entry (`integration_type: device`). All state lives in `entry.options`:

```json
{
  "name": "Bins",
  "interval_days": 14,
  "default_snooze_value": 1,
  "default_snooze_unit": "days",
  "notification_time": "08:00",
  "last_completed": "2026-06-01T14:30:00+10:00",
  "snooze_until": null
}
```

`last_completed` is `null` on creation; the chore starts overdue. It is set to a tz-aware ISO 8601 datetime string only when `chores.complete` is called.

### Data flow

```
entry.options (one chore per entry)
        │
        ▼
ChoresCoordinator.async_initialize()
  ├── reads last_completed / snooze_until / interval_days / default_snooze_value / default_snooze_unit / notification_time from entry.options
  ├── builds ChoreRuntime (status, next_due — both None when last_completed is None)
  └── schedules a point-in-time timer at next_due (skipped when next_due is None)
        │
        ▼ timer fires / service called / options edited
ChoresCoordinator.async_set_updated_data(snapshot)
        │
        ▼
ChoreSensor.native_value + diagnostic sensors + number/select/time entities (pushed by CoordinatorEntity)
```

Options updates (from config flow edits) are handled in-place via `async_update_config` — no `async_reload`, no entity teardown.

### Key types

| Type                            | File             | Purpose                                                                                             |
| ------------------------------- | ---------------- | --------------------------------------------------------------------------------------------------- |
| `ChoreConfig`                   | `models.py`      | Immutable config: name, interval_days, default_snooze_value, default_snooze_unit, notification_time |
| `ChoreRuntime`                  | `coordinator.py` | Mutable runtime state: last_completed (datetime \| None), status, next_due, timer fns               |
| `ChoresCoordinator`             | `coordinator.py` | Owns one chore, pushes updates to all entities                                                      |
| `ChoreSensor`                   | `sensor.py`      | Primary `CoordinatorEntity` — reads status from coordinator snapshot                                |
| `_ChoreDateSensor`              | `sensor.py`      | Base class for diagnostic date sensors                                                              |
| `ChoreIntervalNumber`           | `number.py`      | CONFIG number entity for interval_days (writable)                                                   |
| `ChoreDefaultSnoozeValueNumber` | `number.py`      | CONFIG number entity for default_snooze_value (writable)                                            |
| `ChoreDefaultSnoozeUnitSelect`  | `select.py`      | CONFIG select entity for default_snooze_unit (writable)                                             |
| `ChoreNotificationTimeEntity`   | `time.py`        | CONFIG time entity for notification_time (writable)                                                 |
| `Chore*Button`                  | `button.py`      | Complete / Snooze / Unsnooze button entities                                                        |

### Status transitions

- **New chore**: `last_completed` is `None`; status starts as `overdue`; `next_due` is `None` (no timer scheduled)
- **`done` → `overdue`**: HA point-in-time timer fires at `next_due` (`notification_time` on the local day of `last_completed + interval`)
- **`overdue` → `done`**: `chores.complete` service call sets `last_completed` to now (or the supplied `completed_at` datetime), persists to `entry.options`, recomputes `next_due`, schedules new timer
- **`snoozed`**: any state (including never-completed) can be snoozed; `chores.snooze` sets `snooze_until` in `entry.options` as a timezone-aware ISO datetime; a snooze-expiry timer fires at exactly `snooze_until`; expiry returns to `overdue` when `last_completed` is `None`

______________________________________________________________________

## Make commands

```bash
# Setup
make venv           # create .venv and install all deps (run once)
make install        # sync updated deps into existing .venv
make venv-destroy   # delete .venv entirely

# Code quality (run before every commit)
make test           # pytest
make lint           # ruff check — flags bugs and style issues
make format         # auto-fix formatting: Python (ruff format + ruff check --fix) and all markdown (mdformat)
make typecheck      # mypy
make check          # lint + format-check + typecheck + markdown + test in one go (mirrors CI, read-only)

# Docker (local HA instance at http://localhost:8123)
make up             # start Home Assistant
make down           # stop and remove HA container
make stop           # pause HA container (preserves container state)
make start          # resume a paused HA container
make logs           # tail HA container logs
```

Activate the venv for interactive use: `source .venv/bin/activate`

______________________________________________________________________

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

Config options can be surfaced in two ways:

**Via creation form only** (name, interval_days): Add the form field to `config_flow.py:_chore_schema()` and add the label to both `strings.json` and `translations/en.json` under `config.step.user.data`. There is no options flow — all post-creation editing goes through CONFIG entities.

**Via CONFIG entity** (interval_days, default_snooze_value, default_snooze_unit, notification_time): Add the key to `coordinator.py:_snapshot()`. Create a number, select, or time entity in `number.py`, `select.py`, or `time.py` whose setter calls `coordinator._persist({"key": value})` — this triggers the update listener which calls `async_update_config` for in-place recomputation. Add entity strings under `entity.number`, `entity.select`, or `entity.time` in both `strings.json` and `translations/en.json`.

### 5. Strings / translations

Every user-visible string must exist in **both** files:

- `strings.json` — used by HA tooling and validation
- `translations/en.json` — loaded at runtime by HA

They must be kept in sync. If you add to one, add to the other.

______________________________________________________________________

## Code style

Ruff and mypy own: import order, modern typing/union syntax, f-strings over `.format()`, `is None`/`is not None`, no mutable default args, no unused imports. Do not restate these.

- **All imports must be at the top of the file.** Inline imports (`import x` or `__import__("x")` inside functions, methods, or class bodies) are not allowed anywhere in the codebase — production code or tests. If a module is needed, add it to the top-level import block.
- **`from __future__ import annotations`** at the top of every module. Not enforced by tooling — easy to omit on new files.
- **Complete type hints** on every function/method (params + return). mypy is not in strict mode so omissions are not caught automatically.
- **PEP 695 `type` aliases** for parametrised types: `type ChoresConfigEntry = ConfigEntry[ChoresCoordinator]`.
- **Validation in `from_dict` / `_parse_*` helpers**: raise `ValueError` with an f-string that includes the offending value via `!r`. For `int` fields, reject `bool` explicitly: `isinstance(x, int) and not isinstance(x, bool)`.
- **All constants in `const.py`** — never inline string or number literals.

### Home Assistant patterns

- **`entry.runtime_data`** holds the coordinator (typed via the `ConfigEntry[...]` alias). Never use `hass.data[DOMAIN]`.
- **`entry.async_on_unload(...)`** must wrap every teardown — update listeners, timer cancel callbacks. Missing this causes leaks.
- **All datetime via `dt_util`** (`now`, `start_of_local_day`, `as_local`) — never `datetime.now()`. Datetimes are always tz-aware; persist as ISO strings; call `as_local` before deriving a calendar date.

______________________________________________________________________

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
- Coordinator tests must call `entry.add_to_hass(hass)` so that `hass.config_entries.async_update_entry` works (state lives in `entry.options`).

______________________________________________________________________

## Issue → PR workflow

**Branch naming:** `<type>/<number>-<slug>` (e.g. `feat/42-snooze-button`, `fix/13-dst-timer`). **Commit style:** `feat(issue-<number>): <description>` or `fix(issue-<number>): <description>`. **PRs must contain** `Closes #<number>` so the issue auto-closes on merge.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full versioning model, release strategy, squash-merge conventions, and PR title rules.

______________________________________________________________________

## Constraints

- Each chore is a separate config entry — multiple entries are allowed.
- No YAML configuration — all setup is through the UI.
- All chore state (`last_completed`, `snooze_until`) lives in `entry.options`.
- Python `>=3.14.2` (matches Home Assistant's own requirement). This enables PEP 758 — `except TypeError, ValueError:` without parentheses is **valid syntax** at this version. Ruff enforces the parenthesis-free form; do not flag it as a bug.
- `integration_type: device` in `manifest.json` — chores appear in the Devices & Services panel, not the Helpers panel.
- Interval is stored as `interval_days` (int, days only).
- `default_snooze_value` (default: `1`) + `default_snooze_unit` (default: `"days"`) control the snooze duration. Both the Snooze button and the `chores.snooze` service share the same unit set, defined in `const.py`.
- `last_completed` is `null` on creation; set to a tz-aware ISO 8601 datetime string only when `chores.complete` is called.
- `notification_time` is stored as an `"HH:MM"` string in `entry.options`.
- The `chores.complete` service accepts an optional `completed_at` datetime (must not be in the future). Omit it to default to now.
