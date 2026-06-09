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

## Step 2 — Enter plan mode immediately

Enter plan mode and present a structured implementation plan covering:
- A brief summary of what the issue requires
- Files that will be changed or created, and why
- Any design decisions or trade-offs worth flagging
- How each acceptance criteria scenario will be satisfied
- Test plan: what new or updated tests will cover the change

Discuss the plan with the user. Answer questions and revise the plan until the user explicitly approves it. Do not write any code before approval.

## Step 3 — Implement

Exit plan mode and begin implementation:

1. Create a branch named `<prefix>/<number>-<slug>` where prefix comes from the category table above and slug is a short kebab-case version of the issue title (e.g. `feat/7-button-entity-complete-chore`). Push it immediately with `git push -u origin <branch>`.
2. Implement the changes according to the approved plan.
3. Run `make test` and `make lint` after changes. Fix any failures before proceeding.
4. Commit using the prefix that matches the category:
   - `bug` → `fix(issue-<number>): <short description>`
   - `enhancement` → `feat(issue-<number>): <short description>`
   - `documentation` → `docs(issue-<number>): <short description>`
   - `chore` → `chore(issue-<number>): <short description>`
   - `security` → `fix(issue-<number>): <short description>`

## Step 4 — Open a PR

Run `gh pr create` with:
- Title: the issue title
- Body: `Closes #<number>`, a short summary of what changed, and a test plan checklist

Print the PR URL.