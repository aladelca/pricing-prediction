# AWS App Runner + S3 Inference-Only Production Deployment Plan

> **For Codex:** REQUIRED SUB-SKILL: Use core-executing-plans to implement this plan task-by-task.

**Goal:** Deploy only the inference surface of the Flask app to AWS App Runner, keep the trained model bundle in Amazon S3, and load the active bundle from S3 at runtime without baking artifacts into the container image.

**Architecture:** Package the current Flask app as a container image, publish it to Amazon ECR, and run it on AWS App Runner behind the built-in HTTPS endpoint. Train the `current_price` model locally first, validate the generated artifact bundle locally, and then upload that versioned bundle manually to S3. In production, the service runs in an explicit inference-only mode that exposes health, HTML prediction UI, and prediction API routes only, downloads the active bundle from S3 to ephemeral local disk at startup or on first use, and stays stateless.

**Reasoning:** The repo already assumes a local model directory via `CURRENT_PRICE_MODEL_DIR`, so the lowest-risk change is to keep training local, validate the bundle there, and add a model source abstraction that resolves to a local cache directory after syncing from S3. Reading directly from S3 on every prediction would add network latency, repeated deserialization, and more failure modes; caching the validated bundle locally preserves the current inference path with minimal code churn. Because production only serves inference, the cleanest design is to keep scraping and training out of the deployed web service altogether, disable scrape routes in production, and treat S3 as the manual promotion point for approved models.

**Tech Stack:** Flask, CatBoost, boto3, Gunicorn, Docker, Amazon ECR, AWS App Runner, Amazon S3, IAM, CloudWatch Logs

---

## Current Repo Review

- The web entrypoint is [`src/pricing_prediction/app.py`](../src/pricing_prediction/app.py) and it always starts a thread pool for scrape jobs.
- Model inference currently loads a local bundle from `CURRENT_PRICE_MODEL_DIR` in [`src/pricing_prediction/services/current_price_predictions.py`](../src/pricing_prediction/services/current_price_predictions.py).
- Artifact read/write is filesystem-only in [`src/pricing_prediction/ml/current_price/artifacts.py`](../src/pricing_prediction/ml/current_price/artifacts.py).
- Production assets are missing today: no `Dockerfile`, no `gunicorn`, no App Runner configuration, and no AWS IaC.
- `POST /api/v1/scrape-runs` launches background work in the web process. That pattern is irrelevant for the production target now, because scraping should happen only once outside App Runner.

## Recommended Production Scope

- Deploy the Flask web app and prediction API to App Runner.
- Serve model inference from a locally cached bundle downloaded from S3.
- Do not require PostgreSQL at runtime for the production service.
- Do not run scraping or model training inside App Runner.
- Treat scraping, local training, and manual upload to S3 as a one-time or offline operational workflow.

## Target Topology

1. CI builds a Docker image and pushes it to Amazon ECR.
2. AWS App Runner pulls the image from ECR and exposes HTTPS.
3. App Runner injects runtime env vars such as `APP_RUNTIME_MODE=inference`, `MODEL_SOURCE=s3`, `CURRENT_PRICE_MODEL_S3_BUCKET`, and `CURRENT_PRICE_MODEL_S3_PREFIX`.
4. App Runner uses an instance role with `s3:GetObject` and `s3:ListBucket` access on the model bucket prefix.
5. At startup or first prediction request, the app downloads the active model bundle from S3 to `/tmp/pricing-prediction/models/current_price/<version>/`.
6. The existing `load_current_price_artifacts()` path loads the cached local bundle.
7. App health is checked on `/health`; readiness verifies the model bundle is available locally.
8. Scraping and training happen offline one time on a local machine, then the resulting bundle is uploaded manually to S3.
9. The production service never depends on the scraping API or a durable worker inside App Runner.

## Assumptions

- "Webrunner" refers to **AWS App Runner**.
- The first production cut serves prediction traffic and the HTML form, not training workloads.
- The production runtime does not need scrape history or training data access.
- The active model version is selected by an S3 manifest or explicit env var, not by listing arbitrary objects at request time.
- The operator will upload the approved local artifact bundle to S3 manually.
- TLS termination can use the default App Runner domain first; custom domain is optional for phase 1.

## Non-Goals

- Rewriting the app to FastAPI or serverless functions.
- Training CatBoost models inside the web container.
- Building a durable scraping orchestration layer for production.
- Adding image-binary storage to S3 for scraped products in this phase.
- Automating the local-to-S3 model promotion flow in the first cut.

## Success Criteria

- The container image can boot on App Runner using `PORT`.
- The service can run in production without a live Postgres dependency.
- `/health` returns `200` and `/ready` returns `200` only when the active model bundle is cached and valid.
- `POST /api/v1/predictions/current-price` returns predictions using a bundle downloaded from S3, not baked into the image.
- The approved model can be trained and validated locally before any upload to S3 occurs.
- The active model can be rolled forward by changing a manifest or version env var without rebuilding the application code.
- The service uses IAM roles for S3 access instead of static AWS credentials.
- The deployment story explicitly separates inference serving from the one-time scrape/train/publish workflow.

## Stop Conditions

- Stop if the target AWS region, account, and model bucket name are unknown.
- Stop if scrape jobs must remain part of the production runtime, because that conflicts with the requested inference-only scope.
- Stop if the model artifact promotion rule is undefined, because the service should not guess which S3 prefix is "active".
- Stop if the manual local training and upload workflow is not acceptable, because this plan does not automate model publishing yet.

### Task 1: Add an explicit inference-only runtime mode

**Files:**
- Modify: `src/pricing_prediction/config.py`
- Modify: `src/pricing_prediction/app.py`
- Modify: `src/pricing_prediction/api/__init__.py`
- Test: `tests/api/test_scrape_run_api.py`
- Test: `tests/web/test_pages.py`

**Step 1: Write the failing test**

- Add tests that expect:
  - scrape routes are not registered when `APP_RUNTIME_MODE=inference`
  - the prediction UI still renders
  - the app does not start scrape executor infrastructure in inference-only mode

**Step 2: Run test to verify it fails**

- `uv run pytest tests/api/test_scrape_run_api.py tests/web/test_pages.py`

**Step 3: Write minimal implementation**

- Introduce `APP_RUNTIME_MODE` or `INFERENCE_ONLY`.
- In inference-only mode:
  - register only health, web, and prediction routes
  - skip scrape executor setup
  - keep the service stateless

**Step 4: Run test to verify it passes**

- `uv run pytest tests/api/test_scrape_run_api.py tests/web/test_pages.py`

**Step 5: Commit (only after approval)**

## Task 2: Externalize model source configuration

**Files:**
- Modify: `src/pricing_prediction/config.py`
- Modify: `.env.example`
- Test: `tests/services/test_current_price_predictions.py`
- Test: `tests/api/test_predictions_api.py`

**Step 1: Write the failing test**

- Add tests that expect configuration support for:
  - `MODEL_SOURCE=local|s3`
  - `CURRENT_PRICE_MODEL_CACHE_DIR`
  - `CURRENT_PRICE_MODEL_S3_BUCKET`
  - `CURRENT_PRICE_MODEL_S3_PREFIX`
  - `CURRENT_PRICE_MODEL_S3_VERSION` or `CURRENT_PRICE_MODEL_S3_MANIFEST_KEY`

**Step 2: Run test to verify it fails**

- `uv run pytest tests/services/test_current_price_predictions.py tests/api/test_predictions_api.py`

**Step 3: Write minimal implementation**

- Keep `CURRENT_PRICE_MODEL_DIR` as the final local resolved directory used by inference.
- Add S3-related configuration fields and sane defaults for local development.
- Default cache location to `/tmp/pricing-prediction/models/current_price`.

**Step 4: Run test to verify it passes**

- `uv run pytest tests/services/test_current_price_predictions.py tests/api/test_predictions_api.py`

**Step 5: Commit (only after approval)**

## Task 3: Add an S3-backed model bundle resolver with local cache

**Files:**
- Create: `src/pricing_prediction/ml/current_price/model_store.py`
- Modify: `src/pricing_prediction/services/current_price_predictions.py`
- Modify: `src/pricing_prediction/ml/current_price/artifacts.py`
- Test: `tests/ml/test_current_price_model_store.py`
- Test: `tests/services/test_current_price_predictions.py`

**Step 1: Write the failing test**

- Add tests for:
  - downloading the required bundle files from S3 to a temp cache dir
  - validating required files before activation
  - reusing the cached local version on subsequent requests
  - surfacing a `503` if the configured S3 bundle is incomplete

**Step 2: Run test to verify it fails**

- `uv run pytest tests/ml/test_current_price_model_store.py tests/services/test_current_price_predictions.py`

**Step 3: Write minimal implementation**

- Introduce a model store abstraction that:
  - resolves the active model version from env or manifest
  - downloads artifacts atomically into a versioned cache directory
  - never serves a half-downloaded bundle
  - returns a local directory path compatible with the current loader
- Prefer `boto3.client("s3").download_file(...)` with IAM credentials from the runtime.
- Assume the S3 bundle was produced and uploaded manually from a local training run.

**Step 4: Run test to verify it passes**

- `uv run pytest tests/ml/test_current_price_model_store.py tests/services/test_current_price_predictions.py`

**Step 5: Commit (only after approval)**

## Task 4: Add readiness and operational model sync hooks

**Files:**
- Modify: `src/pricing_prediction/api/health.py`
- Modify: `src/pricing_prediction/cli.py`
- Modify: `src/pricing_prediction/app.py`
- Test: `tests/api/test_health_api.py`
- Test: `tests/services/test_current_price_predictions.py`

**Step 1: Write the failing test**

- Add tests for:
  - `/health` liveness response
  - `/ready` returning non-200 when the model is unavailable
  - a CLI command such as `sync-current-price-model` warming the local cache

**Step 2: Run test to verify it fails**

- `uv run pytest tests/api/test_health_api.py tests/services/test_current_price_predictions.py`

**Step 3: Write minimal implementation**

- Keep `/health` cheap and stable for App Runner health checks.
- Add `/ready` to verify the model bundle is already available and loadable.
- Add a CLI hook so the container entrypoint can warm the model cache before serving traffic.

**Step 4: Run test to verify it passes**

- `uv run pytest tests/api/test_health_api.py tests/services/test_current_price_predictions.py`

**Step 5: Commit (only after approval)**

## Task 5: Containerize the service for App Runner

**Files:**
- Modify: `pyproject.toml`
- Create: `Dockerfile`
- Create: `.dockerignore`
- Create: `scripts/start-web.sh`

**Step 1: Write the failing test**

- Add a smoke verification that the production command binds on `${PORT}` and can reach `/health`.
- If no automated container smoke test is added, document that omission and use a deterministic local docker run command as the evidence gate.

**Step 2: Run test to verify it fails**

- `docker build -t pricing-prediction:prod .`
- `docker run --rm -e PORT=8000 -p 8000:8000 pricing-prediction:prod`

**Step 3: Write minimal implementation**

- Add `gunicorn` and `boto3` to runtime dependencies.
- Use a startup script that optionally warms the model cache from S3 and then starts Gunicorn on `0.0.0.0:${PORT}`.
- Do not copy model artifacts into the image.

**Step 4: Run test to verify it passes**

- `docker build -t pricing-prediction:prod .`
- `docker run --rm -e PORT=8000 -e MODEL_SOURCE=local -e CURRENT_PRICE_MODEL_DIR=instance/models/current_price/dev -p 8000:8000 pricing-prediction:prod`
- `curl http://127.0.0.1:8000/health`

**Step 5: Commit (only after approval)**

## Task 6: Add AWS deployment assets for App Runner, S3, and IAM

**Files:**
- Create: `infra/aws/apprunner/main.tf`
- Create: `infra/aws/apprunner/variables.tf`
- Create: `infra/aws/apprunner/outputs.tf`
- Create: `infra/aws/apprunner/iam.tf`
- Create: `infra/aws/apprunner/s3.tf`
- Create: `infra/aws/apprunner/README.md`

**Step 1: Write the failing test**

- Define validation evidence for:
  - App Runner service creation from ECR
  - instance role granting only required S3 permissions on the model prefix

**Step 2: Run test to verify it fails**

- `terraform -chdir=infra/aws/apprunner init`
- `terraform -chdir=infra/aws/apprunner validate`

**Step 3: Write minimal implementation**

- Create an S3 bucket or bucket policy model for artifact storage with versioning enabled.
- Create an App Runner service referencing the ECR image and health check path `/health`.
- Add an instance role for S3 access.
- Do not require database wiring in the first production release.

**Step 4: Run test to verify it passes**

- `terraform -chdir=infra/aws/apprunner fmt -check`
- `terraform -chdir=infra/aws/apprunner validate`

**Step 5: Commit (only after approval)**

## Task 7: Document the one-time offline scrape, train, and publish workflow

**Files:**
- Modify: `README.md`
- Create: `docs/runbooks/aws-apprunner-production.md`
- Create: `docs/runbooks/model-publish-to-s3.md`

**Step 1: Write the failing test**

- Add documented acceptance gates for the offline workflow:
  - scrape once
  - train locally once
  - validate the local bundle
  - upload the bundle to S3 manually
  - point production to the selected version

**Step 2: Run test to verify it fails**

- Documentation review against the defined acceptance gates.

**Step 3: Write minimal implementation**

- Document the model publishing flow:
  - train bundle locally
  - validate the bundle locally
  - upload versioned files to S3 manually
  - update production manifest or env var
  - redeploy or restart App Runner if warm sync happens only at boot
- Document the one-time data bootstrap flow:
  - run scrape locally or in a one-off job
  - train locally or in a one-off job
  - verify the artifact bundle
  - upload it to S3 manually
  - deploy the inference service

**Step 4: Run test to verify it passes**

- Documentation review against the acceptance gates.

**Step 5: Commit (only after approval)**

## Verification Matrix

- Unit and service tests:
  - `uv run pytest tests/web/test_pages.py tests/api/test_scrape_run_api.py tests/services/test_current_price_predictions.py tests/api/test_predictions_api.py tests/ml/test_current_price_model_store.py tests/api/test_health_api.py`
- Static checks:
  - `uv run ruff check src tests`
  - `uv run mypy src`
- Container checks:
  - `docker build -t pricing-prediction:prod .`
  - `docker run --rm -e PORT=8000 -e APP_RUNTIME_MODE=inference -e MODEL_SOURCE=s3 ... -p 8000:8000 pricing-prediction:prod`
- Infra checks:
  - `terraform -chdir=infra/aws/apprunner fmt -check`
  - `terraform -chdir=infra/aws/apprunner validate`
- Runtime smoke:
  - `curl http://127.0.0.1:8000/health`
  - `curl http://127.0.0.1:8000/ready`
  - `curl -X POST http://127.0.0.1:8000/api/v1/predictions/current-price ...`

## Deployment Decisions To Confirm Before Execution

1. Whether the HTML `/predict` page ships in production or only the JSON inference API.
2. Whether the active model version is selected by:
   - an env var such as `CURRENT_PRICE_MODEL_S3_VERSION`, or
   - a manifest object such as `s3://<bucket>/current_price/production.json`
3. Whether the first production release needs a custom domain and WAF.

## Definition of Done

- The repo contains container, runtime, infra, and runbook assets for an App Runner inference deployment.
- The model bundle is stored in S3 and resolved into a validated local cache before inference.
- The service can boot in AWS without local model files checked into the repo or image.
- The production runtime does not expose or depend on scrape execution.
- A human can follow the runbook to scrape once, train locally, upload the approved bundle manually to S3, and switch production to it safely.
