FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python deps
COPY requirements.txt /app/
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --root-user-action=ignore -r requirements.txt

# Copy project
COPY . /app/
RUN useradd -m appuser
USER appuser

# Entry
RUN chmod +x /app/entrypoint.sh

ARG SKIP_COLLECTSTATIC=true
ENV SKIP_COLLECTSTATIC=${SKIP_COLLECTSTATIC}

RUN if [ "$SKIP_COLLECTSTATIC" = "false" ]; then \
    python manage.py collectstatic --noinput; \
    fi

ENTRYPOINT ["/app/entrypoint.sh"]

CMD ["daphne", "-b", "0.0.0.0", "-p", "5000", "newshub_core.asgi:application"]