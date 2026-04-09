#!/bin/bash

# Agar koi command fail hoti hai toh script wahi ruk jayegi
set -e

# Sirf tabhi migrate karo jab RUN_MIGRATIONS true ho
if [ "$RUN_MIGRATIONS" = "true" ]; then
    echo "Applying database migrations..."
    python manage.py migrate --noinput

    # echo "Checking/Creating Superuser..."
    # python create_superuser.py
fi

# Skip collectstatic during development
if [ "$SKIP_COLLECTSTATIC" != "true" ]; then
    echo "Collecting static files..."
    python manage.py collectstatic --noinput
fi

if [ "$RUN_DEPLOY_CHECKS" = "true" ]; then
    echo "Running Django deployment checks..."
    python manage.py check --deploy --fail-level WARNING
fi

echo "Starting server..."
# "$@" ka matlab hai ki jo command Dockerfile ya docker-compose mein di gayi hai, wo execute hogi
exec "$@"
