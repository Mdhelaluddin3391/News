FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --root-user-action=ignore -r requirements.txt

# Create non-root user
RUN useradd -m appuser

# Copy project with correct ownership 🔥
COPY --chown=appuser:appuser . /app/

# Ensure entrypoint is executable
RUN chmod +x /app/entrypoint.sh

# Switch to non-root user
USER appuser

# Static files control
ARG SKIP_COLLECTSTATIC=true
ENV SKIP_COLLECTSTATIC=${SKIP_COLLECTSTATIC}

# Optional collectstatic during build
RUN if [ "$SKIP_COLLECTSTATIC" = "false" ]; then \
    python manage.py collectstatic --noinput; \
    fi

ENTRYPOINT ["/app/entrypoint.sh"]

CMD ["daphne", "-b", "0.0.0.0", "-p", "5000", "newshub_core.asgi:application"]