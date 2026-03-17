#!/bin/sh
set -eu

export APP_RUNTIME_MODE="${APP_RUNTIME_MODE:-inference}"
export PORT="${PORT:-8000}"

if [ "${MODEL_SOURCE:-local}" = "s3" ]; then
  pricing-prediction sync-current-price-model
fi

exec gunicorn \
  --bind "0.0.0.0:${PORT}" \
  --workers "${WEB_CONCURRENCY:-2}" \
  --threads "${GUNICORN_THREADS:-4}" \
  --timeout "${GUNICORN_TIMEOUT:-120}" \
  "pricing_prediction.app:create_app()"
