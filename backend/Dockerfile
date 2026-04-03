FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies required for psycopg2, Pillow, etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install requirements first to leverage Docker layer caching
COPY requirements.txt /app/
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . /app/

# Make entrypoint executable
RUN chmod +x /app/entrypoint.sh

# Build arguments for collecting static files
ARG SKIP_COLLECTSTATIC=true
ARG SECRET_KEY="dummy-key-for-build-only"
ENV SECRET_KEY=${SECRET_KEY}
ENV SKIP_COLLECTSTATIC=${SKIP_COLLECTSTATIC}

RUN if [ "$SKIP_COLLECTSTATIC" = "false" ]; \
    then python manage.py collectstatic --noinput; fi

ENTRYPOINT ["/app/entrypoint.sh"]

# Better syntax without wrapping inside "sh -c"
CMD ["daphne", "-b", "0.0.0.0", "-p", "5000", "newshub_core.asgi:application"]