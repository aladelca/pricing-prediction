# Flask Backend Completeness Checklist

Read this file when the backend task goes beyond a small route tweak and you
need a fuller production checklist.

## Architecture

- Confirm the Flask app entry point, app factory, blueprint registration, and
  extension initialization order.
- Keep config split by environment when the project already distinguishes
  local, test, and production settings.
- Decide whether the change belongs in a route, service, repository, worker, or
  CLI command before coding.

## API design

- Define the request and response schema before implementation.
- Decide whether the endpoint needs pagination, filtering, sorting, or version
  handling.
- Keep response envelopes and error payloads consistent across endpoints.
- Confirm idempotency for retries on `POST`, `PUT`, webhook handlers, and job
  triggers.

## Auth and security

- Check authentication and authorization requirements separately.
- Reuse the repo's existing token, session, or API key pattern instead of
  inventing a new one.
- Review CORS, CSRF, rate limiting, and secret management when exposing a new
  surface.
- Validate file types, file sizes, and untrusted payloads at the boundary.

## Data and migrations

- Identify whether the change needs a schema migration, seed data, or backfill.
- Keep transaction boundaries explicit around multi-step writes.
- Add indexes or constraints when new read or write paths depend on them.
- Document rollback expectations if the migration is not trivially reversible.

## External integrations

- Add timeouts, retries, and structured error handling for outbound HTTP calls.
- Keep integration adapters separate from Flask route code.
- Record which failures are user-facing versus retriable versus internal.

## Background jobs and async work

- Put retryable job logic behind reusable functions, not inline route code.
- Track idempotency, retry policy, and failure visibility for queued work.
- If a worker stack is added, document how Flask config is loaded there too.

## Observability

- Add structured logging around new backend flows.
- Include correlation or request IDs when the repo already supports them.
- Add metrics, tracing, or health checks for new critical paths when the stack
  supports them.
- Make failure modes visible through logs or explicit error reporting.

## Testing

- Cover happy path, invalid input, auth rejection, dependency failure, and
  unexpected internal errors.
- Prefer focused unit tests for business logic and route tests for HTTP
  behavior.
- Add contract coverage for serializers, model mapping, or webhook payloads
  when those boundaries are easy to regress.

## Operations

- Update env var docs or `.env.example` when configuration changes.
- Confirm local run commands, test commands, and production serve commands still
  work.
- If the change needs Gunicorn, Docker, migrations, or worker startup updates,
  include them in the task scope instead of leaving them implicit.
