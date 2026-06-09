# Chores — Home Assistant Custom Integration

A HACS-compatible custom integration that tracks recurring household chores and surfaces their status as sensor entities inside Home Assistant. Each chore becomes a sensor entity whose state is `done` or `overdue`, automatically transitioning at the configured interval with no polling.

---

## Project structure

```
custom_components/chores/
  __init__.py          # entry setup/teardown, forwards to platforms and services
  const.py             # DOMAIN, CONF_CHORES, INTERVAL_UNITS
  models.py            # ChoreConfig dataclass (name, interval, last_completed)
  coordinator.py       # ChoresCoordinator — runtime state, timers, persistence
  sensor.py            # ChoreSensor entity (one per chore)
  config_flow.py       # UI config flow (single-instance) + options flow (add/remove)
  services.py          # chores.complete service handler
  services.yaml        # service schema for the HA UI
  strings.json         # translation source (used by tooling/validation)
  translations/
    en.json            # runtime translations loaded by HA (mirrors strings.json)
  manifest.json        # HACS/HA integration metadata

tests/
  components/chores/
    conftest.py        # shared fixtures (chore dict builder)
    test_config_flow.py
    test_coordinator.py
    test_models.py
  test_sensor.py

ha-config/             # local HA config directory, mounted into Docker at /config
docker-compose.yml     # runs ghcr.io/home-assistant/home-assistant:stable on :8123
pyproject.toml         # project metadata + mypy config
requirements_test.txt  # pinned dev/test dependencies
Makefile               # all common dev tasks (see below)
```

---

## Architecture

### Data flow

```
config entry data (CONF_CHORES list)
        │
        ▼
ChoresCoordinator.async_initialize()
  ├── loads last_completed overrides from HA Store (survives restarts)
  ├── builds ChoreRuntime per chore (status, next_due)
  └── schedules a point-in-time timer per chore at next_due
        │
        ▼ timer fires / async_complete called
ChoresCoordinator.async_set_updated_data(snapshot)
        │
        ▼
ChoreSensor.native_value / extra_state_attributes (pushed by CoordinatorEntity)
```

### Key types

| Type | File | Purpose |
|---|---|---|
| `ChoreConfig` | `models.py` | Immutable config parsed from the config entry |
| `ChoreRuntime` | `coordinator.py` | Mutable runtime state: status, next_due, timer cancel fn |
| `ChoresCoordinator` | `coordinator.py` | Owns all chores, pushes updates to sensors |
| `ChoreSensor` | `sensor.py` | `CoordinatorEntity` — reads from coordinator snapshot |

### Status transitions

- **`done` → `overdue`**: HA point-in-time timer fires at `next_due` (start of local day of `last_completed + interval`)
- **`overdue` → `done`**: `chores.complete` service call resets `last_completed` to today, recomputes `next_due`, schedules new timer

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
make format         # ruff format — auto-fixes formatting
make typecheck      # mypy
make check          # lint + typecheck + test in one go

# Docker (local HA instance at http://localhost:8123)
make up             # start Home Assistant
make down           # stop HA (data preserved)
make destroy        # stop HA and wipe volumes
make logs           # tail HA container logs
```

Activate the venv for interactive use: `source .venv/bin/activate`

---

## Adding a new feature

### 1. New sensor attribute
Add the key to `coordinator.py:_snapshot()` and read it in `sensor.py:extra_state_attributes`.

### 2. New service
1. Add the handler in `services.py` and register it in `async_register_services`.
2. Add the schema and UI description to `services.yaml`.
3. Unregister it in `async_unregister_services`.

### 3. New platform (e.g. `button`, `select`)
1. Add `Platform.BUTTON` (etc.) to `PLATFORMS` in `__init__.py`.
2. Create `custom_components/chores/<platform>.py` implementing `async_setup_entry` and the entity class.
3. The entity should be a `CoordinatorEntity` and read state via `coordinator.chore_state(chore_id)`.

### 4. New config option
1. Add the constant to `const.py`.
2. Add the field to `ChoreConfig` in `models.py` (update `to_dict` / `from_dict`).
3. Add the form field to `config_flow.py:async_step_add`.
4. Add the label to both `strings.json` and `translations/en.json` under `options.step.add.data`.

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
- Coordinator tests patch `Store.async_load` and `Store.async_save` to avoid touching the filesystem.

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

- Single-instance integration — only one Chores config entry is allowed.
- No YAML configuration — all setup is through the UI options flow.
- Python `>=3.14.2` (matches Home Assistant's own requirement).
- `integration_type: hub` in `manifest.json` — must not be changed to `helper` or the integration appears in the wrong section of the HA UI.
