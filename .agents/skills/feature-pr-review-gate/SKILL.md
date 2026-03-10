---
name: feature-pr-review-gate
description: Execute implementation work through a branch-first GitHub pull request workflow with a mandatory self-review gate. Use when Codex is implementing a feature, bug fix, refactor, or non-trivial change and must create a fresh branch, open a detailed pull request, publish an exhaustive severity-ranked code review with remediation options, and post a final GO or NO-GO verdict comment on the PR.
---

# Feature PR Review Gate

Use this skill when the task must end in a reviewable GitHub pull request, not
just local file changes.

This workflow is mandatory:

1. Create a fresh branch before editing code.
2. Implement and validate the change.
3. Open a detailed PR with scope and tests.
4. Perform a self-review against the PR diff.
5. Publish a GO or NO-GO verdict comment.

## Preconditions

- Require `git` and `gh`.
- Require an authenticated GitHub CLI session before PR creation or comments.
- Refuse to keep implementation work on `main` or any unrelated existing branch.
- If the worktree already contains unrelated changes, stop and decide whether to
  isolate the work or proceed explicitly with that context.

## Start the branch before implementation

Use `scripts/git_pr_workflow.py branch` to generate a deterministic branch name.

Example:

```bash
python3 .agents/skills/feature-pr-review-gate/scripts/git_pr_workflow.py branch \
  --title "Add Falabella listing scraper" \
  --ticket pricing-prediction-123 \
  --create
```

Branch rules:

- Default prefix to `feature/`.
- Include the issue id when available.
- Use a short hyphenated slug derived from the task title.
- Create the branch from `main` unless the repo uses another explicit base.

## Implement and validate

Before opening the PR:

- Run the relevant tests, linters, builds, or scripts.
- Capture the exact commands that were executed.
- Capture the result, including failures that remain relevant to reviewers.
- Summarize risk areas and any intentionally deferred work.

Never write a PR body that says tests were run if they were not actually run.

## Create the pull request

Use `scripts/git_pr_workflow.py pr-body` to generate a PR body file, then create
the PR with `gh pr create`.

Example:

```bash
python3 .agents/skills/feature-pr-review-gate/scripts/git_pr_workflow.py pr-body \
  --title "Add Falabella listing scraper" \
  --summary "Add a Selenium-first scraper scaffold and Falabella extraction helpers." \
  --scope "Add scraper entry point and reusable parsing helpers." \
  --scope "Add tests for price normalization and URL handling." \
  --tests "python3 -m pytest tests/test_falabella_parse.py" \
  --tests "python3 -m ruff check scraper" \
  --risk "Selectors may drift during campaign landing page changes." \
  --issue pricing-prediction-123 \
  --output /tmp/pr-body.md

gh pr create \
  --base main \
  --head "$(git branch --show-current)" \
  --title "feat: add Falabella listing scraper" \
  --body-file /tmp/pr-body.md
```

The PR body must contain:

- Summary
- Scope of change
- Validation performed
- Risks and follow-ups
- Traceability to the issue or task id

## Perform the self-review

Read `references/review-rubric.md` before publishing review comments.

Review the actual diff, not just the final files:

```bash
gh pr diff <pr-number>
gh pr view <pr-number> --json files,title,body,url
```

Look for:

- behavior regressions
- broken edge cases
- missing tests
- security or data handling mistakes
- migration or rollout gaps
- misleading naming or abstractions
- weak error handling

Write findings ordered by severity:

- `critical`
- `high`
- `medium`
- `low`

For each finding include:

- severity
- affected file references
- concrete risk
- why it matters
- at least one resolution option

If there are no findings, say that explicitly.

## Publish review and verdict

Create the review body and verdict comment with the helper script.

```bash
python3 .agents/skills/feature-pr-review-gate/scripts/git_pr_workflow.py review-body \
  --summary "Self-review of the scraper PR." \
  --verdict no-go \
  --findings-file findings.md \
  --output /tmp/review-body.md

python3 .agents/skills/feature-pr-review-gate/scripts/git_pr_workflow.py verdict \
  --status no-go \
  --summary "Blocking issues remain in selector stability and missing parser coverage." \
  --blocking "2 blocking findings: 1 high, 1 critical." \
  --next-step "Fix the blocking issues, rerun validation, and refresh this review." \
  --output /tmp/verdict.md
```

Publish like this:

```bash
gh pr review <pr-number> --request-changes --body-file /tmp/review-body.md
gh pr comment <pr-number> --body-file /tmp/verdict.md
```

If the verdict is `go`, use:

```bash
gh pr review <pr-number> --comment --body-file /tmp/review-body.md
gh pr comment <pr-number> --body-file /tmp/verdict.md
```

## GO / NO-GO rule

- `no-go` if any unresolved `critical` or `high` finding exists.
- `go` only when no blocking findings remain.
- `go with caveats` still counts as `go`, but the caveats must be explicit in
  both the review body and the verdict comment.

## Deliverables

Do not consider the task complete until all of these exist:

1. Fresh implementation branch
2. Detailed GitHub PR
3. Review body published on the PR
4. GO or NO-GO verdict comment published on the PR
5. Validation commands recorded in the PR body
