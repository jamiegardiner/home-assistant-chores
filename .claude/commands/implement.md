---
model: opusplan
---

Implement the GitHub issue number provided in $ARGUMENTS.

## Step 1 — Read the issue

Fetch the issue with `gh issue view <number>` to read the title, category label, user story, and acceptance criteria.

Derive the branch prefix from the category label:

| Label           | Branch prefix |
|-----------------|---------------|
| `bug`           | `bug/`        |
| `enhancement`   | `feat/`       |
| `documentation` | `docs/`       |
| `chore`         | `chore/`      |
| `security`      | `security/`   |

If no label is set, default to `feat/`.

## Step 2 — Ask clarifying questions

Before planning anything, use `AskUserQuestion` to gather context you can't derive from the issue alone. Ask all questions in a single questionnaire — do not ask follow-ups one at a time.

Design your questions based on what the issue leaves ambiguous. Common questions to consider (pick the ones that apply, drop the rest):

- **Scope** — Are there any parts of this issue that are out of scope for now, or anything that should be tackled beyond what's written?
- **Design preference** — Is there a preferred approach when multiple reasonable solutions exist? (e.g. new entity vs. service, attribute vs. state)
- **UI strings** — Should any new user-visible text follow an existing pattern or wording from the codebase?
- **Edge cases** — Are there edge cases the ACs don't cover that need handling (e.g. empty state, concurrent calls)?
- **Testing** — Are there specific scenarios that must be covered by tests beyond the ACs?

If the issue is completely unambiguous and none of these questions apply, skip this step and move straight to Step 3.

## Step 3 — Enter plan mode

Enter plan mode and present a structured implementation plan covering:
- A brief summary of what the issue requires
- Files that will be changed or created, and why
- Any design decisions or trade-offs worth flagging
- How each acceptance criteria scenario will be satisfied
- Test plan: what new or updated tests will cover the change

Discuss the plan with the user. Answer questions and revise the plan until the user explicitly approves it. Do not write any code before approval.

## Step 4 — Implement

Exit plan mode and begin implementation:

1. Ensure main is up to date before branching: `git checkout main && git pull origin main`. Then create a branch named `<prefix>/<number>-<slug>` where prefix comes from the category table above and slug is a short kebab-case version of the issue title (e.g. `feat/7-button-entity-complete-chore`). Push it immediately with `git push -u origin <branch>`.
2. Implement the changes according to the approved plan.
3. Run `make format && make check` after changes. This covers Python formatting/linting (ruff), type checking (mypy), tests (pytest), and markdown formatting across the whole repo (mdformat) — fix any failures before proceeding.
4. Commit the code changes following [Conventional Commits](https://www.conventionalcommits.org/) style: `type(scope): description`. The scope is always `issue-<number>`. Map the category label to the commit type:
   - `bug` → `fix(issue-<number>): <short description>`
   - `enhancement` → `feat(issue-<number>): <short description>`
   - `documentation` → `docs(issue-<number>): <short description>`
   - `chore` → `chore(issue-<number>): <short description>`
   - `security` → `fix(issue-<number>): <short description>`
5. After the code commit, review whether `README.md` or `CLAUDE.md` need updating to reflect the change (e.g. new services, changed behaviour, new configuration options, updated architecture). If so, update them and commit separately with the message `docs(issue-<number>): update documentation`.

## Step 5 — Open a PR

### PR title format

The PR title **must** be a conventional-commit message. Under the repo's squash-merge-only model, the PR title becomes the single commit on `main` that release-please uses to determine the version bump — individual branch commits never reach `main`.

Format: `type(issue-<number>): <short description>`

Use the type that reflects the PR's **most significant** change:

| Type | When to use |
|------|-------------|
| `feat` | new user-visible capability |
| `fix` | corrects incorrect behaviour |
| `docs` | documentation only |
| `chore` | tooling, deps, CI, refactoring with no user-facing change |

A `chore:`-titled PR produces no release even if its branch contained `feat()` commits. A `BREAKING CHANGE:` footer in the PR body is honoured for a major bump.

Examples:
- `feat(issue-42): add snooze button entity`
- `fix(issue-13): correct overdue timer after DST change`
- `docs(issue-65): document versioning and release strategy`

### Creating the PR

Write the PR body to a temp file and use `--body-file` to avoid shell escaping mangling backticks and code blocks:

```
cat > /tmp/pr-body.md << 'EOF'
Closes #<number>

## Summary
<what changed>

## Test plan
- [ ] ...
EOF
gh pr create --title "type(issue-<number>): <description>" --body-file /tmp/pr-body.md
```

Print the PR URL.