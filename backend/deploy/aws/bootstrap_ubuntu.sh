#!/usr/bin/env bash

set -euo pipefail

APP_DIR="${APP_DIR:-/home/ubuntu/Myproject/news-backend}"
VENV_DIR="${VENV_DIR:-/home/ubuntu/venvs/newshub}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

sudo apt-get update
sudo apt-get install -y \
  git \
  nginx \
  redis-server \
  python3-venv \
  python3-dev \
  build-essential \
  libpq-dev

mkdir -p "$(dirname "$VENV_DIR")"
"$PYTHON_BIN" -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

pip install --upgrade pip
pip install -r "$APP_DIR/requirements.txt"

cd "$APP_DIR"
python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py check --deploy --fail-level WARNING

sudo cp "$APP_DIR/deploy/systemd/newshub-daphne.service" /etc/systemd/system/
sudo cp "$APP_DIR/deploy/systemd/newshub-celery.service" /etc/systemd/system/
sudo cp "$APP_DIR/deploy/systemd/newshub-celery-beat.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable newshub-daphne
sudo systemctl enable newshub-celery
sudo systemctl enable newshub-celery-beat
sudo systemctl restart newshub-daphne
sudo systemctl restart newshub-celery
sudo systemctl restart newshub-celery-beat

echo "Bootstrap complete."
