# ----- BUILD STAGE -----
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# System dependencies for building wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Build wheels and install Gunicorn/Uvicorn explicitly
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt \
    && pip install --no-cache-dir gunicorn uvicorn

# ----- FINAL STAGE -----
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Only runtime dependencies needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy wheels from builder and install
COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache /wheels/* gunicorn uvicorn

# Create non-root user
RUN useradd -m appuser

# Copy project correctly in one line
COPY --chown=appuser:appuser . /app/

RUN mkdir -p /app/staticfiles /app/media && \
    chown -R appuser:appuser /app/staticfiles /app/media

RUN chmod +x /app/entrypoint.sh

USER appuser

# Optional collectstatic during build
ARG SKIP_COLLECTSTATIC=true
ENV SKIP_COLLECTSTATIC=${SKIP_COLLECTSTATIC}
RUN if [ "$SKIP_COLLECTSTATIC" = "false" ]; then python manage.py collectstatic --noinput; fi

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "newshub_core.asgi:application", "-k", "uvicorn.workers.UvicornWorker", "--workers", "4", "--bind", "0.0.0.0:5000"]