---
name: flask-backend
description: Implement and modify backend systems with Flask. Use when Codex is asked to build or change APIs, backend endpoints, request handlers, business logic, server-side integrations, authentication, persistence, jobs, admin services, or any backend application behavior. Default new backend work to Flask and Flask blueprints. Also applies to Spanish prompts like "backend", "api", "endpoint", "ruta", "controlador", "servicio", "modelo", "cambio en backend", or "implementacion backend". If the repository already has a different established backend framework, inspect it first and avoid mixing frameworks without calling out the conflict.
---

# Flask Backend

Use this skill for backend work in this repository. Treat Flask as the default
framework for new backend work.

## Workflow

1. Inspect the current backend shape before editing.
2. Keep HTTP handlers thin and move domain logic into services or modules.
3. Use Flask-native structure: app factory, blueprints, config, extensions, and
   centralized error handling.
4. Add or update tests with every behavior change.
5. Report env vars, migrations, and operational side effects in the final task
   handoff.

## Inspect first

- Find the app entry point, app factory, blueprint registration, config
  objects, ORM layer, migration tooling, and test setup before adding files.
- If no backend exists yet, scaffold the smallest viable Flask layout instead
  of dropping logic into ad hoc scripts.
- If the repo already uses another backend framework, do not silently add Flask
  beside it. Call out the conflict and either preserve the existing stack or
  get explicit approval to introduce Flask.

## Implementation defaults

- Use an application factory such as `create_app`.
- Group routes by domain with Flask blueprints.
- Keep request parsing, validation, service logic, and persistence separate.
- Reuse the repo's existing validation or serialization pattern when one
  already exists. If none exists, introduce one approach consistently instead
  of mixing libraries.
- Centralize error handling and return consistent JSON payloads for APIs.
- Read configuration from env vars or config classes. Never hardcode secrets.
- Prefer explicit dependency wiring over hidden globals.

## API rules

- Define request and response contracts before coding.
- Validate query params, path params, headers, and JSON bodies.
- Use correct HTTP status codes and stable error shapes.
- Keep database access out of route functions when the logic is non-trivial.
- Add health or readiness routes when the backend surface is new or operational
  visibility is missing.

## Data and persistence

- Reuse the repository's ORM and migration tooling if they already exist.
- When introducing persistence, include schema changes, migration notes, and
  rollback considerations.
- Make write paths idempotent when retries are plausible.
- Wrap external calls with timeouts and explicit failure handling.

## Testing bar

- Add route tests for the happy path, validation failures, auth failures, and
  dependency failures.
- Add unit tests for business logic when route-level tests would become too
  broad.
- If the change affects data models or serialization, cover those boundaries
  explicitly.

## Non-HTTP backend work

- For background jobs, webhooks, admin tasks, or CLI-triggered backend flows,
  keep core logic in reusable modules that can be called from Flask routes, CLI
  commands, or workers.
- Avoid one-off scripts that bypass the backend structure unless the task is
  explicitly disposable.

## References

- Read `references/completeness-checklist.md` when the task touches auth,
  database changes, file uploads, background jobs, observability, deployment,
  or other production concerns.
