---
model: opus
---

Review the pull request number provided in $ARGUMENTS.

## Step 1 — Fetch the PR

Run `gh pr view <number> --json title,body,headRefName` to get the PR details. Run `gh pr diff <number>` to get the full diff. The diff plus reading individual files (`gh api repos/{owner}/{repo}/contents/<path>?ref=<headRefName> -q .content | base64 -d`) is usually enough. Check out the branch only if you genuinely need it — e.g. to trace cross-file context the diff doesn't show. Do **not** check it out just to run `ruff`, `mypy`, `mdformat`, or the tests: CI already runs `make check` on every PR, so re-running those locally is wasted work.

## Step 2 — Review criteria

Scrutinise every changed file against all of the following categories. Flag anything that fails.

**Scope:** Only flag issues that the tooling does **not** already catch. Ruff, mypy (strict mode), and mdformat run in CI and own import order, modern typing/union syntax, f-strings, `is None`/`is not None`, mutable default args, unused imports/variables, bare `except`, comprehension rewrites, complete type annotations, and all markdown formatting. Do not restate or report on those — focus on the judgment calls below that no linter enforces.

### Python correctness & style

- [ ] No magic numbers or strings — use named constants from `const.py`
- [ ] No deeply nested blocks (more than 3 levels is a smell)
- [ ] No commented-out code or stray TODOs without a linked issue

### Pythonic patterns

- [ ] Dataclasses use `field()` for mutable defaults, not bare mutable literals
- [ ] `@property` used correctly — no side effects in getters
- [ ] Context managers (`with`) used where appropriate (file I/O, locks)
- [ ] `dict.get(key, default)` preferred over `key in dict` + access
- [ ] Early returns used to reduce nesting (guard clauses)

### Home Assistant best practices

- [ ] `@callback` decorator on every synchronous function called from an async context
- [ ] All async methods prefixed with `async_`
- [ ] No `time.sleep()` — use `await asyncio.sleep()` or HA timer helpers
- [ ] All datetime operations go through `homeassistant.util.dt` (`dt_util`), never `datetime.now()` directly
- [ ] No blocking I/O in async functions
- [ ] `hass.async_create_task()` used instead of `asyncio.create_task()`
- [ ] Entities use `_attr_*` class variables where possible instead of `@property` overrides
- [ ] `_attr_has_entity_name = True` set on entities
- [ ] Entity `unique_id` is stable, unique, and based on `entry.entry_id`
- [ ] Services use `vol.ALLOW_EXTRA` on schemas that accept entity targets
- [ ] All user-visible strings exist in both `strings.json` and `translations/en.json`
- [ ] Cleanup (timers, listeners, services) registered via `entry.async_on_unload()`
- [ ] `Platform` enum used (not raw strings like `"sensor"`)
- [ ] `CoordinatorEntity` used for coordinator-backed entities
- [ ] No direct state mutations outside the coordinator

### Code smells

- [ ] Functions do one thing (single responsibility — if a function needs sub-headings to describe it, split it)
- [ ] No duplicated logic that should be extracted to a helper
- [ ] No overly long functions (more than ~40 lines is worth questioning)
- [ ] No unnecessary class — a module-level function is simpler when there's no state

### Documentation

- [ ] If the PR adds or changes a service, `README.md` documents it (name, description, YAML example)
- [ ] If the PR adds or changes sensor states or attributes, `README.md` reflects them
- [ ] If the PR changes configuration options, setup steps, or architecture, `README.md` and/or `CLAUDE.md` are updated
- [ ] If the PR introduces new developer patterns or conventions, `CLAUDE.md` covers them

## Step 3 — Compile findings

Group findings by file. For each issue record:

- File path (relative to repo root, e.g. `custom_components/chores/config_flow.py`)
- Line number in the file (use the diff to identify the exact line)
- Which checklist item it violates
- A short explanation of why it's a problem
- A concrete suggested fix

Only report genuine issues — do not flag things that are already correct, and do not invent problems.

If there are no issues, say so explicitly.

## Step 4 — Report to user

Present the full findings to the user in the terminal, grouped by file.

## Step 5 — Post inline PR review

Post findings as a GitHub code review with inline comments on the exact lines using `gh api`. This creates proper line-level annotations visible in the GitHub diff view, with a summary at the top.

Get the repo owner/name first:

```
gh repo view --json nameWithOwner -q .nameWithOwner
```

Build a JSON review file at `/tmp/pr-review.json`. The structure is:

```json
{
  "body": "<overall summary with verdict>",
  "event": "COMMENT",
  "comments": [
    {
      "path": "<relative file path>",
      "line": <line number in the file on the RIGHT side of the diff>,
      "side": "RIGHT",
      "body": "<issue explanation and suggested fix>"
    }
  ]
}
```

- `body`: markdown summary with a final verdict (✅ No issues / ⚠️ N issues found)
- One entry in `comments` per finding
- `line` must be a line that appears in the PR diff — use the diff output to confirm the line exists on the changed side. If a line is not in the diff (e.g. it is unchanged context), place the comment on the nearest changed line and note the actual line in the comment body
- If there are no findings, omit the `comments` array and just post the summary via `gh pr comment <number> --body-file`

Post the review:

```
gh api repos/{owner}/{repo}/pulls/<number>/reviews --input /tmp/pr-review.json
```
