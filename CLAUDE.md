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
  number.py            # Interval and Snooze interval CONFIG number entities
  select.py            # Snooze unit CONFIG select entity
  time.py              # Overdue time CONFIG time entity
  sensor.py            # ChoreSensor + 2 primary date sensors + 1 diagnostic sensor (one set per config entry)
  diagnostics.py       # async_get_config_entry_diagnostics — full coordinator snapshot for HA diagnostics download
  config_flow.py       # UI config flow (create chore — name + interval only; no options flow)
  services.py          # chores.complete/snooze/unsnooze service handlers
  services.yaml        # service structure for the HA UI (target, fields, selectors)
  strings.json         # translation source (used by tooling/validation)
  translations/
    en.json            # runtime translations loaded by HA (mirrors strings.json)
  manifest.json        # HACS/HA integration metadata

tests/components/chores/   # one test file per source module; coordinator tests are split across four focused files
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

| Type                            | File             | Purpose                                                                                                                     |
| ------------------------------- | ---------------- | --------------------------------------------------------------------------------------------------------------------------- |
| `ChoreConfig`                   | `models.py`      | Immutable config: name, interval_days, default_snooze_value, default_snooze_unit, notification_time                         |
| `ChoreRuntime`                  | `coordinator.py` | Mutable runtime state: last_completed (datetime \| None), status, next_due, timer fns                                       |
| `ChoresCoordinator`             | `coordinator.py` | Owns one chore, pushes updates to all entities                                                                              |
| `ChoreSensor`                   | `sensor.py`      | Primary `CoordinatorEntity` — reads status from coordinator snapshot                                                        |
| `_ChoreDateSensor`              | `sensor.py`      | Base class for date sensors; `last_completed` and `next_due` are primary; `snooze_until` is diagnostic, disabled by default |
| `ChoreIntervalNumber`           | `number.py`      | CONFIG number entity for interval_days (writable)                                                                           |
| `ChoreDefaultSnoozeValueNumber` | `number.py`      | CONFIG number entity for default_snooze_value (writable)                                                                    |
| `ChoreDefaultSnoozeUnitSelect`  | `select.py`      | CONFIG select entity for default_snooze_unit (writable)                                                                     |
| `ChoreNotificationTimeEntity`   | `time.py`        | CONFIG time entity for notification_time (writable)                                                                         |
| `Chore*Button`                  | `button.py`      | Complete / Snooze / Unsnooze button entities                                                                                |

### Status transitions

- **New chore**: `last_completed` is `None`; status starts as `overdue`; `next_due` is `None` (no timer scheduled)
- **`done` → `overdue`**: HA point-in-time timer fires at `next_due` (`notification_time` on the local day of `last_completed + interval`)
- **`overdue` → `done`**: `chores.complete` service call sets `last_completed` to now (or the supplied `completed_at` datetime), persists to `entry.options`, recomputes `next_due`, schedules new timer
- **`snoozed`**: any state (including never-completed) can be snoozed; `chores.snooze` sets `snooze_until` in `entry.options` as a timezone-aware ISO datetime; a snooze-expiry timer fires at exactly `snooze_until`; expiry returns to `overdue` when `last_completed` is `None`
- **Corrupt state recovery**: `async_initialize` handles two failure modes — recoverable fields (`last_completed`, `snooze_until`) are sanitised to `None` and a WARNING repair issue is raised via `ir.async_create_issue`; unrecoverable fields (`name`, `interval_days`) raise `ConfigEntryError` and an ERROR repair issue. Repair issue IDs are `{REPAIR_ISSUE_CORRUPT_FIELD}_{entry_id}` and `{REPAIR_ISSUE_CORRUPT_CONFIG}_{entry_id}` (constants in `const.py`).

______________________________________________________________________

## Make commands

```bash
# Setup
make venv           # create .venv and install all deps (run once)
make install        # sync updated deps into existing .venv
make install-hooks  # install pre-commit hook into .git/hooks (run once after make venv)
make venv-destroy   # delete .venv entirely
make clean          # remove all caches (__pycache__, .pytest_cache, .mypy_cache, .ruff_cache)

# Code quality (run before every commit)
make test           # pytest (no coverage overhead — fast day-to-day runs)
make test-coverage  # pytest with term-missing coverage report; fails below 95%
make lint           # ruff check — flags bugs and style issues
make format         # auto-fix formatting: Python (ruff format + ruff check --fix) and all markdown (mdformat)
make typecheck      # mypy
make translations   # assert strings.json and translations/en.json have identical key paths
make check          # lint + format-check + typecheck + markdown + translations + test (with 95% coverage gate) in one go (mirrors CI, read-only)

# Docker (local HA instance at http://localhost:8123)
make up             # start Home Assistant
make down           # stop and remove HA container
make stop           # pause HA container (preserves container state)
make start          # resume a paused HA container
make logs           # tail HA container logs
```

Activate the venv for interactive use: `source .venv/bin/activate`

To exclude a file from markdown formatting, add a glob to the `exclude` list in `.mdformat.toml`. mdformat only honours `exclude` when invoked with a directory or glob (e.g. `mdformat .`), **not** when passed an explicit file list — the Makefile uses `mdformat .` for exactly this reason. `CHANGELOG.md` is excluded because it is release-managed by release-please and must not be reformatted.

______________________________________________________________________

## Adding a new feature

### 1. New sensor attribute

Add the key to `coordinator.py:_snapshot()`. To surface it as a diagnostic entity, create a new sensor class in `sensor.py` and add it to `async_setup_entry`. Add an icon for the new translation key under `entity.sensor` in `icons.json`.

### 2. New service

Services are entity services — HA handles all target resolution (entity, area, device, label) and fan-out automatically.

1. Add the service name constant and schema dict to `services.py`.
2. Add a handler function `_handle_<name>(entity: ChoreSensor, call: ServiceCall)` in `sensor.py` and register it in `async_setup_entry` via `platform.async_register_entity_service`.
3. Add the service structure (target, fields, selectors) to `services.yaml` — but **not** `name`/`description`. Service and field display strings live under the `services` key in both `strings.json` and `translations/en.json` (kept in sync, per HA's 2023.8+ convention). No unregister step needed — entity services are torn down automatically when the platform unloads.

### 3. New platform (e.g. `button`, `select`)

1. Add `Platform.BUTTON` (etc.) to `PLATFORMS` in `__init__.py`.
2. Create `custom_components/chores/<platform>.py` implementing `async_setup_entry` and the entity class.
3. The entity should be a `CoordinatorEntity` and read state from `coordinator.data` (flat dict).
4. Declare `PARALLEL_UPDATES = 0` at module level (after imports) — required by the Silver quality-scale `parallel-updates` rule.
5. Add icons for each new entity translation key under the appropriate platform key in `icons.json`.

### 4. New config option

Config options can be surfaced in two ways:

**Via creation form only** (name, interval_days): Add the form field to `config_flow.py:_chore_schema()` and add the label to both `strings.json` and `translations/en.json` under `config.step.user.data`. There is no options flow — all post-creation editing goes through CONFIG entities.

**Via CONFIG entity** (interval_days, default_snooze_value, default_snooze_unit, notification_time): Add the key to `coordinator.py:_snapshot()`. Create a number, select, or time entity in `number.py`, `select.py`, or `time.py` whose setter calls `coordinator.set_option("key", value)` — this triggers the update listener which calls `async_update_config` for in-place recomputation. Add entity strings under `entity.number`, `entity.select`, or `entity.time` in both `strings.json` and `translations/en.json`.

### 5. Strings / translations

Every user-visible string must exist in **both** files:

- `strings.json` — used by HA tooling and validation
- `translations/en.json` — loaded at runtime by HA

They must be kept in sync. If you add to one, add to the other. Enforced by `make translations` (`scripts/check_translations.py`), which is part of `make check`.

______________________________________________________________________

## Code style

Ruff and mypy own: import order, modern typing/union syntax, f-strings over `.format()`, `is None`/`is not None`, no mutable default args, no unused imports. Do not restate these.

- **Check IDE diagnostics** after every change using `mcp__ide__getDiagnostics`. ruff and mypy don't catch everything — IDE inspections surface additional smells that tooling misses. Fix all warnings before committing.
- **Never suppress tooling without confirmation.** Do not add `# noqa`, `# type: ignore`, per-file ruff exclusions, or mdformat exclusions to work around a failing check — fix the root cause instead. If suppression is genuinely necessary, ask first.
- **Complete type hints** on every function/method (params + return). mypy runs in strict mode, so omissions are caught in CI.
- **PEP 695 `type` aliases** for parametrised types: `type ChoresConfigEntry = ConfigEntry[ChoresCoordinator]`.
- **Validation in `from_dict` / `_parse_*` helpers**: raise `ValueError` with an f-string that includes the offending value via `!r`. For `int` fields, reject `bool` explicitly: `isinstance(x, int) and not isinstance(x, bool)`.
- **All constants in `const.py`** — never inline string or number literals.
- **No nested ternaries.** If you need two conditions, use a guard clause + single flat ternary, or a plain `if`/`elif`/`else` block. Flat single ternaries remain acceptable.

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

### Coordinator test layout

Coordinator tests are split across four focused modules:

| File                           | Coverage                                                  |
| ------------------------------ | --------------------------------------------------------- |
| `test_coordinator_init.py`     | Initialization, status computation, `async_update_config` |
| `test_coordinator_snooze.py`   | Snooze, unsnooze, never-completed chore behaviour         |
| `test_coordinator_complete.py` | `async_complete`, `completed_at`, notification time       |
| `test_coordinator_coverage.py` | Timer-reschedule guard branches, `_parse_aware_datetime`  |

`conftest.py` provides two fixtures auto-discovered by pytest — no import needed:

- `patch_track` (`autouse=True`) — patches `async_track_point_in_time` for every coordinator test automatically.
- `fake_track` — overrides `patch_track` to capture the scheduled callback for timer-firing tests.

`helpers.py` provides shared functions — import explicitly in each test file:

```python
from tests.components.chores.helpers import make_entry, setup_coord
```

- `make_entry(...)` — builds a `MockConfigEntry` for a single chore.
- `setup_coord(hass, entry)` — constructs and initialises a `ChoresCoordinator`.

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
- `quality_scale.yaml` lives at `custom_components/chores/quality_scale.yaml` and lists every HA Integration Quality Scale rule with `done`, `todo`, or `exempt`. Update it whenever a rule's status changes (e.g. a `todo` is implemented or an `exempt` justification changes).
- The `reconfiguration-flow` quality scale rule is intentionally not implemented. Post-creation editing is handled entirely through CONFIG entities (number, select, time), which already provide an in-place edit experience without a separate reconfiguration flow.
