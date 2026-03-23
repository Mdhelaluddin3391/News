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

# Build time error se bachne ke liye dummy SECRET_KEY set karein
ARG SECRET_KEY="dummy-key-for-build-only"
ENV SECRET_KEY=${SECRET_KEY}

# Static files collect karein
RUN python manage.py collectstatic --noinput

# NAYA: Entrypoint set karein
ENTRYPOINT ["/app/entrypoint.sh"]

# Gunicorn ke through server run karein (Default command)
CMD ["gunicorn", "newshub_core.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]