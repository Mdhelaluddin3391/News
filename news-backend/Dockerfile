FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Requirements copy aur install karein
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# Pura backend ka code copy karein
COPY . /app/

# NAYA: Entrypoint script ko executable banayein
RUN chmod +x /app/entrypoint.sh

# Build argument to skip collectstatic during development
ARG SKIP_COLLECTSTATIC=false
ARG SECRET_KEY="dummy-key-for-build-only"
ENV SECRET_KEY=${SECRET_KEY}
ENV SKIP_COLLECTSTATIC=${SKIP_COLLECTSTATIC}

# Static files collect karein (skip during development)
RUN if [ "$SKIP_COLLECTSTATIC" = "false" ]; then python manage.py collectstatic --noinput; fi

# NAYA: Entrypoint set karein
ENTRYPOINT ["/app/entrypoint.sh"]

# Gunicorn ke through server run karein (Default command)
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "newshub_core.asgi:application"]