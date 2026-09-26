#!/bin/bash
# Render start command (render.yaml startCommand: bash start.sh).
#
# Apply pending database migrations before starting the web server. The
# render.yaml preDeployCommand does not run for this service (production was
# missing the property_views table from migration 0008), and Render ignores
# Procfile "release:" lines - so migrations are applied here, on every start.
# `migrate` only applies migrations that are not recorded yet; when nothing is
# pending it changes nothing. If a migration fails the service does not start
# (set -e), so Render keeps the previous deploy running instead of serving
# code against an outdated schema.
set -e

python manage.py migrate --noinput

# Master data (property types, amenities): idempotent - only creates missing
# records, never deletes or renames existing ones. Not critical for serving
# requests, so a failure is logged and the web server still starts.
python manage.py seed_master_data || echo "WARNING: seed_master_data failed - master data not refreshed" >&2

exec gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --access-logfile - --error-logfile -
