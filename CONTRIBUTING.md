# Contributing

## Versioning & release strategy

### SemVer driven by conventional commits

This project follows [Semantic Versioning](https://semver.org). The version bump for each release is derived
automatically from the conventional-commit prefixes of PRs merged to `main`:

| Commit prefix                                  | Bump                                           |
| ---------------------------------------------- | ---------------------------------------------- |
| `fix:`                                         | patch (e.g. `0.1.0` → `0.1.1`)                 |
| `feat:`                                        | minor (e.g. `0.1.0` → `0.2.0`)                 |
| `feat(scope)!:` or `BREAKING CHANGE:` footer   | major at `>=1.0.0`; minor at `0.x` (see below) |
| `chore:`, `docs:`, `refactor:`, `test:`, `ci:` | no release on their own                        |

### Pre-1.0 rule

While the project is at `0.x`, **breaking changes bump the minor version** (not major). The jump to `1.0.0` is a
deliberate one-time decision made by the maintainer, not triggered automatically by a breaking change.

### Release mechanism

Releases are managed by [release-please](https://github.com/googleapis/release-please):

1. As PRs are merged to `main`, release-please accumulates their conventional-commit subjects and maintains a single
   open "release PR" with a proposed version bump and `CHANGELOG.md` entry.
1. When the maintainer is ready to cut a release, they merge that release PR.
1. Merging the release PR automatically:
   - bumps the `version` field in `manifest.json`
   - creates a `vX.Y.Z` git tag
   - publishes a GitHub Release

HACS installs and updates from GitHub Releases, so no release tag means no HACS update.

> **Note:** The release-please workflow, PR-title-lint check, and repo squash-only setting are not yet configured.
> Implementation is deferred to [#66](../../issues/66).

### Manifest ↔ tag sync

`manifest.json` `version` and the `vX.Y.Z` git tag are kept in lockstep by release-please. **Do not edit the version
field in `manifest.json` manually** — doing so will desync the manifest from the tag and break HACS update detection.

### Trunk-based development

`main` is the single release line. There are no long-lived release branches. All PRs target `main` directly.

### On-demand release cadence

Merging a feature or fix PR to `main` does **not** publish a release. Release-please simply updates its open release PR
to include the new change. Work can be stacked and accumulated freely. A release is cut only when the maintainer merges
the release PR.

### Squash-only merge model

The repository is configured for **squash-merge only** (merge commits and rebase-merge are disabled).

Under squash-merge, the entire PR is collapsed into **one commit on `main`** whose subject is the **PR title**.
Individual branch commits do not appear in `main`'s history and are not seen by release-please.

Therefore:

- **The PR title is the single release-driving conventional commit.** It must reflect the PR's most significant change.
  - A PR that adds a feature plus some cleanup → title starts with `feat:` (not `chore:`)
  - A `chore:`-titled PR produces no release even if its branch contained `feat()` commits
- A `BREAKING CHANGE:` footer in the squash-merge body is still honoured for a major bump.
- PR-title-lint (enforced by CI — see [#66](../../issues/66)) is the authoritative gate; individual commit messages on
  the branch are not linted.

### PR title format

PR titles must follow [Conventional Commits](https://www.conventionalcommits.org/). The scope is `issue-<number>`:

```
feat(issue-42): add snooze button entity
fix(issue-13): correct overdue timer after DST change
docs(issue-65): document versioning and release strategy
chore(issue-71): upgrade pytest-homeassistant-custom-component
```

Use the prefix that reflects the PR's **most significant** change:

- `feat` — new user-visible capability
- `fix` — corrects incorrect behaviour
- `docs` — documentation only
- `chore` — tooling, deps, CI, refactoring with no user-facing change
- `refactor` — restructuring without behaviour change
- `test` — test additions or changes only
- `ci` — CI/CD pipeline changes only

Append `!` after the scope for a breaking change: `feat(issue-X)!: remove weeks option`.

### Contributor flow

1. Open or pick up a GitHub Issue.
1. Create a branch from `main` named `<type>/<number>-<slug>` (e.g. `feat/42-snooze-button`).
1. Implement, commit with conventional-commit messages, open a PR targeting `main`.
1. **Set the PR title to a conventional-commit message** — this is the version-bump signal under squash-merge.
1. The maintainer reviews and merges (squash). Release-please updates its release PR accordingly.
1. The maintainer cuts the release when ready by merging the release PR.

### Cutting the first 1.0.0

When initial development is complete and the project is considered stable, the maintainer adds a `Release-As: 1.0.0`
footer to a commit or PR body. Release-please will propose `1.0.0` as the next version regardless of the bump type of
that commit.
