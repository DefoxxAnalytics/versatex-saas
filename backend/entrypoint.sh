#!/bin/sh
# Container entrypoint. Runs collectstatic at start with the real runtime
# environment (SECRET_KEY, DEBUG, etc. injected via env_file/env vars), then
# execs the gunicorn CMD. Build-time collectstatic was unreliable: the
# Dockerfile RUN step had no SECRET_KEY, so collectstatic either silently
# no-op'd or panicked, both swallowed by `|| true`. Migrations are still
# operator-driven via `docker-compose exec backend python manage.py migrate`
# per docs/setup, so they are intentionally NOT run here.
set -e

python manage.py collectstatic --noinput

exec "$@"
