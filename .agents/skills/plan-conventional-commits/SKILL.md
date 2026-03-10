---
name: plan-conventional-commits
description: Analyze a git worktree, group changed files by cohesive change intent, and propose an approval-ready Conventional Commits plan before any staging or commit happens. Use when Codex needs to split a dirty worktree into logical commits, infer commit type and scope, review mixed changes, or prepare conventional commit messages for explicit user approval.
---

# Plan Conventional Commits

Turn a messy git worktree into a small set of coherent Conventional Commits.
Always stop after presenting the plan unless the user explicitly approves
staging and committing.

## Start with the analyzer

Run the bundled analyzer first:

```bash
python3 .agents/skills/plan-conventional-commits/scripts/plan_commits.py --format json
```

Use `--repo /path/to/repo` when the target repository is not the current
directory. The script classifies changed files, suggests commit groups, and
marks low-confidence cases that need manual review.

## Build the plan

- Treat the script output as a starting point, not final truth.
- Group by change intent, not by extension alone.
- Keep tests and docs with the code change they validate when they are not
  meaningful on their own.
- Split repo-wide tooling, CI, or dependency changes away from product code
  unless they are required for the same feature.
- Prefer the fewest commits that still have one clear objective.
- Reject grouping that would force a vague message such as
  `chore(repo): update files`.

Use these commit types:

- `feat`: new user-facing capability or notable workflow addition
- `fix`: bug correction, compatibility repair, or logic defect
- `refactor`: internal restructuring without feature intent
- `perf`: measurable runtime or resource improvement
- `docs`: documentation-only changes
- `test`: tests-only changes
- `build`: dependency, packaging, or build pipeline updates
- `ci`: CI workflow changes
- `chore`: repository maintenance that does not fit the above
- `revert`: rollback of a previous commit

## Choose scope and subject

- Use the product area, package, service, or module as the scope.
- Avoid scopes such as `json`, `md`, `config`, or `misc`.
- Write the subject in lowercase imperative form with no trailing period.
- Keep the subject specific enough that another engineer can predict the diff.

Good patterns:

- `feat(auth): add passwordless login`
- `fix(scraper): handle empty price blocks`
- `refactor(training): split feature engineering helpers`
- `build(repo): pin selenium driver`

## Inspect ambiguity before proposing the final plan

Read targeted diffs when any of these happen:

- the analyzer returns `confidence: low`
- a group has repo-wide source files
- a file could plausibly belong to more than one commit
- a rename or delete changes the apparent scope
- merge conflicts are present

Use focused inspection:

```bash
git diff -- path/to/file
git diff -- path/one path/two
git diff --stat
```

## Approval output

Return a plan only. Do not stage or commit yet.

Use this shape:

```markdown
## Proposed Commit Plan

1. `type(scope): subject`
Why: one sentence on the shared objective.
Files:
- path/to/file
- another/file
Notes: optional risk, dependency, or ambiguity note.

2. `type(scope): subject`
Why: ...
Files:
- ...

Waiting for approval before running `git add` or `git commit`.
```

## After approval

Once the user approves:

1. stage only the files or hunks that belong to the approved commit
2. create commits in the approved order
3. report the exact commit messages that were created
