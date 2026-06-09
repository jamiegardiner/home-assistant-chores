Create a new GitHub issue from the task description in $ARGUMENTS.

## Step 1 — Gather requirements

Ask the user clarifying questions before writing anything. Cover:
- Who is the user and what are they trying to achieve? (needed to write the user story)
- What triggers the behaviour or change?
- What is the expected outcome / success state?
- Are there any edge cases or failure paths that matter?
- Any constraints (e.g. must work without a restart, must be configurable via UI)?
- What category does this fall into? Choose one:
  - `bug` — something is broken or behaving incorrectly
  - `enhancement` — new feature or improvement to existing behaviour
  - `documentation` — docs, CLAUDE.md, comments, or README changes
  - `chore` — tooling, dependencies, CI, refactoring with no user-facing change
  - `security` — vulnerability or security hardening

Keep questions concise — ask them all in one message, not one at a time. Wait for the user's answers before proceeding.

## Step 2 — Draft the issue

Write the issue body using this structure:

**Category:** `<bug | enhancement | documentation | chore | security>`

**User Story** *(enhancement and bug only)*
> As a [type of user], I want [goal], so that [reason/value].

**Acceptance Criteria**

The format depends on the category:

- **enhancement / bug** — BDD-style scenarios using Given/When/Then. Each scenario is a single testable behaviour. Do not bundle multiple outcomes into one Then:
  ```
  Scenario: <short name>
    Given <precondition>
    When <action>
    Then <outcome>
  ```

- **documentation / chore / security** — Simple bullet list of what must be true when the issue is done. No Given/When/Then needed:
  ```
  - README contains an introduction section explaining what the integration does
  - Installation instructions cover adding the repo as a custom HACS repository
  ```

**Notes** (omit if empty)
Implementation hints, constraints, open questions, or links to related issues.

## Step 3 — Check scope

Before creating the issue, assess whether it should be split:
- **enhancement / bug**: more than 5 BDD scenarios, spans clearly separate concerns, or would naturally result in more than one PR
- **documentation / chore / security**: covers clearly distinct deliverables that could ship independently (e.g. README + CLAUDE.md update are separable; a single README with multiple sections is not)

If any of these apply, propose a split: show the user the suggested sub-issues and ask whether to create them separately or proceed as one. Wait for their decision.

## Step 4 — Create the issue

Once the user is happy with the content and scope, write the issue body to a temp file and use `--body-file` to avoid shell escaping mangling backticks and code blocks:

```
cat > /tmp/issue-body.md << 'EOF'
<body>
EOF
gh issue create --title "<title>" --label "<category>" --body-file /tmp/issue-body.md
```

Print the issue URL and number. Do not implement any code.