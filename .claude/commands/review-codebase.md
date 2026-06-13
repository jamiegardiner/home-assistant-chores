---
model: opus
---

Perform a full, holistic review of the entire codebase as an experienced senior Python engineer who specialises in Home Assistant custom integrations.

This is **not** a diff review (`/review-pr` covers that). You are reviewing the whole integration as it stands today: `custom_components/chores/` and `tests/`, plus the docs. If `$ARGUMENTS` names a specific area (e.g. `coordinator`, `tests`, `security`), focus there but still read enough surrounding code to judge it in context. With no arguments, review everything.

## Step 1 — Build context first

Before judging anything, understand the integration:

- Read `CLAUDE.md` — this is the **source of truth** for the project's documented code-style and Home Assistant conventions. Judge "idiomatic Python" and "HA patterns" against what `CLAUDE.md` documents; do not invent rules it doesn't state, and flag code that contradicts it.
- Read `README.md` and `manifest.json` to understand the user-facing behaviour and integration metadata.
- Skim every module under `custom_components/chores/` and every file under `tests/` so you can reason about cross-module relationships (e.g. whether buttons and services share logic), not just one file at a time.

Two external standards inform this review (they are evaluation lenses, deliberately kept out of `CLAUDE.md` so they don't tax every session):

- **HA Integration Quality Scale checklist** — <https://developers.home-assistant.io/docs/core/integration-quality-scale/checklist>. This is a living document, so **fetch it now** rather than relying on memory, and use its tiered rules to judge the HA-patterns dimension. Treat it as aspirational guidance for a custom (non-core) integration, not a hard gate. As you read it, track which requirements each tier (Bronze → Silver → Gold → Platinum) passes or fails so you can produce an estimated grade in the report (see Step 4).
- **The Zen of Python (PEP 20)** — <https://peps.python.org/pep-0020/>. Use its principles (explicit over implicit, simple over complex, readability counts, flat over nested, errors never pass silently) as the lens for the idiomatic/Pythonic dimension.

## Step 2 — Review dimensions

Work through every dimension below. For each, scrutinise the relevant code and flag genuine problems. These are reworded for clarity — apply the intent, not just the words.

### Security (the integration only, not Home Assistant core)

- Untrusted input — config-flow fields, service-call payloads, persisted `entry.options` — is validated and parsed safely before use.
- No injection or unsafe evaluation paths (`eval`, `exec`, shell-outs, dynamic imports, string-built queries).
- No secrets, tokens, or sensitive data logged, persisted in plain options, or exposed in entity attributes/state.
- Assume HA itself is trusted; only flag issues introduced by *this integration's* code.

### Memory & resource management

- Every timer, listener, and subscription is cancelled/unsubscribed — registered via `entry.async_on_unload(...)` or explicitly cancelled — so nothing leaks across reloads or entry removal.
- Timer cancel handles are nulled after use; no dangling references that keep objects alive.
- No unbounded growth in coordinator state, caches, or persisted options over time.
- Persistence writes are necessary and not redundantly triggering reload/rebuild cycles.

### Documentation accuracy

- `README.md` and `CLAUDE.md` match the actual code: entity counts, service names/parameters, configuration options, and architecture descriptions are current.
- No conflicting, out-of-date, or false statements between the docs and the implementation (e.g. a documented option that no longer exists, or behaviour described that the code doesn't do).
- `strings.json` and `translations/en.json` are in sync and cover every user-visible string.

### Tests

- **Unit coverage**: each module's meaningful behaviour and edge cases are covered (status transitions, null `last_completed`, snooze expiry, DST/timezone handling, validation failures). Identify untested branches and any logic with no test at all.
- **End-to-end / integration coverage**: the full flow is exercised through the coordinator and entities, not just isolated functions — config entry setup, service calls landing on entity state, option edits applied in place.
- **Compaction**: tests asserting the same behaviour across varied inputs that could collapse into `@pytest.mark.parametrize`; repeated setup that belongs in a fixture. Suggest concrete consolidations — but don't over-merge unrelated cases.
- Tests follow the documented conventions (`enable_custom_integrations`, `MockConfigEntry`, `entry.add_to_hass(hass)`), and no inline imports.
- If a coverage tool is available, run it; otherwise reason about coverage by reading the tests against the code.

### General code quality

- Functions are single-purpose, reasonably sized, and clearly named; control flow favours guard clauses over deep nesting.
- No dead code, commented-out blocks, or unlinked TODOs.
- Error handling is specific and intentional, not swallowed.

### Duplication (cross-module)

- The same logic isn't implemented in two places. Specifically check that the **buttons** (`button.py`) and the **services** (`services.py` / `sensor.py` handlers) share the same underlying coordinator operations rather than re-implementing complete/snooze/unsnooze independently.
- Some small, local repetition is acceptable — do **not** push for premature abstraction or over-engineered indirection. Only flag duplication where a single shared helper would genuinely reduce risk of divergence.

### Home Assistant patterns

- The code uses HA the expected way; flag anything out of the ordinary or that violates documented HA conventions in `CLAUDE.md` or the fetched Integration Quality Scale checklist.
- **Entity setup is categorised correctly**: the primary status sensor is a normal sensor; diagnostic sensors carry `EntityCategory.DIAGNOSTIC`; the writable interval/snooze/notification entities are CONFIG (`EntityCategory.CONFIG`); buttons are actions. Verify each entity's category, device class, and `translation_key` are appropriate for its role.
- Coordinator/push model, `CoordinatorEntity` state reads, `entry.runtime_data`, `Platform` enum, in-place `async_update_config` (never `async_reload`), and datetime via `dt_util` are all honoured.

### Idiomatic / Pythonic style

- Code reads as natural, modern Python consistent with the idioms documented in `CLAUDE.md` and the spirit of PEP 20 (explicit, simple, readable, flat over nested).
- Don't restate rules already enforced by `ruff`/`mypy` — assume those pass. Focus on idioms tooling can't catch.

### Best practices / design (SOLID)

- **Single responsibility**: each class/module owns one concern (coordinator owns state, entities present it, services/buttons trigger operations).
- **Open/closed & extension**: adding a new entity or service follows the documented extension points without modifying unrelated code.
- **Dependency direction**: entities depend on the coordinator, not the reverse; no circular or leaky dependencies.
- Flag genuine design smells, but weigh them against the size of the project — this is a focused integration, not an enterprise system. Pragmatism over dogma.

## Step 3 — Compile findings

Group findings by dimension (or by file where that reads more clearly). For each finding record:

- A **severity**: `Critical` (security/data-loss/leak), `High` (incorrect behaviour or clear violation), `Medium` (quality/maintainability), `Low` (nit / nice-to-have).
- The file path and line number (`custom_components/chores/coordinator.py:142`).
- What the problem is and **why** it matters.
- A concrete, specific suggested fix.

Only report genuine issues. Do not flag correct code, do not invent problems, and do not restate things `ruff`/`mypy` already enforce. If a dimension is clean, say so in one line rather than padding.

## Step 4 — Report to the user

Present the findings in the terminal, ordered by severity (Critical first). Open with a short overall assessment (one paragraph) and a count per severity.

Include an **estimated HA Quality Scale grade** — the highest tier (Bronze → Silver → Gold → Platinum) whose requirements the integration plausibly meets, based on the checklist you fetched in Step 1. State this is an **unofficial self-assessment, not an official Home Assistant grade**. Back it with: which tier it clears, the specific unmet requirements blocking the next tier up, and (where useful) which of those gaps overlap findings already raised above. Don't overstate — if a tier is borderline, say so and explain what tips it.

End with a prioritised shortlist of what to tackle first.

## Step 5 — Offer to triage into issues

This repo is issue-driven (`/new-issue` → `/implement`). After reporting, ask the user whether they want to turn findings into GitHub issues. If yes, group related findings into coherent, independently-shippable issues (don't file one issue per nit), and create them following the `/new-issue` conventions — correct category label, BDD ACs for `bug`/`enhancement`, bullet ACs for `chore`/`security`/`documentation`. Do not write any code in this command.
