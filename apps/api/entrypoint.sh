#!/bin/sh
# Runs Alembic migrations, then starts the app (the container CMD). Retries so a
# just-booted / not-yet-reachable Postgres doesn't crash the first `up`.
set -e

echo "[entrypoint] applying database migrations (alembic upgrade head)..."
n=0
until alembic upgrade head; do
  n=$((n + 1))
  if [ "$n" -ge 10 ]; then
    echo "[entrypoint] migrations failed after $n attempts — giving up" >&2
    exit 1
  fi
  echo "[entrypoint] attempt $n failed (DB not ready?); retrying in 3s..."
  sleep 3
done

echo "[entrypoint] migrations complete — starting server"
exec "$@"
