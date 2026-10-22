#!/usr/bin/env bash
set -e

# Run Django database migrations
echo "[profile-entrypoint] Applying Django database migrations..."
if python manage.py migrate --noinput; then
    echo "[profile-entrypoint] Database migrations applied successfully."
else
    echo "[profile-entrypoint] WARNING: Django migrate failed or database connection is pending. Continuing startup..."
fi

exec "$@"
