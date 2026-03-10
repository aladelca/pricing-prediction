# Review rubric

Use this rubric when reviewing your own PR.

## Severity levels

### critical

Use `critical` when the change can cause:

- data loss
- security exposure
- broken deploy or startup
- corrupt writes
- fundamentally incorrect business results

Default verdict impact: `no-go`

### high

Use `high` when the change can cause:

- user-facing regression in a main path
- silent failure in an important workflow
- missing migration, rollback, or rollout step
- test gaps around risky logic
- integration breakage that is likely in normal usage

Default verdict impact: `no-go`

### medium

Use `medium` when the change has:

- maintainability debt that can hide future bugs
- incomplete edge-case handling with limited blast radius
- missing validation around a non-core path
- review friction due to unclear naming or structure

Default verdict impact: usually `go` with caveats

### low

Use `low` when the change has:

- polish issues
- documentation gaps
- minor readability concerns
- non-blocking cleanup opportunities

Default verdict impact: `go`

## Finding format

Use this structure for each finding:

```text
[severity] path/to/file:line
Risk: what breaks or becomes unsafe.
Why: why the current implementation is insufficient.
Options:
- concrete option 1
- concrete option 2
```

## Review checklist

- Confirm the PR body matches the actual implementation.
- Confirm the tests listed in the PR were actually run.
- Check for missing negative-path coverage.
- Check for migrations, feature flags, environment changes, or schema changes.
- Check for rollback difficulty.
- Check for logging, observability, and failure handling in risky code.
- Check whether the change creates hidden coupling or fragile abstractions.

## Verdict rules

- `no-go` when any unresolved `critical` or `high` finding exists.
- `go` when there are no blocking findings.
- `go` can still include medium or low caveats, but the caveats must be named.
