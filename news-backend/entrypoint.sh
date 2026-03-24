#!/bin/bash

# Agar koi command fail hoti hai toh script wahi ruk jayegi
set -e

echo "Applying database migrations..."
python manage.py migrate --noinput

echo "Checking/Creating Superuser..."
python create_superuser.py

# (Optional) Agar aap chahte hain ki static files bhi har baar collect hon
echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting server..."
# "$@" ka matlab hai ki jo command Dockerfile ya docker-compose mein di gayi hai, wo execute hogi
exec "$@"