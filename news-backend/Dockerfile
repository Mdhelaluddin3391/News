# news-backend/Dockerfile
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Requirements file root directory se aayegi (Docker context ke through)
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# Backend ka code copy karein
COPY news-backend/ /app/

# Static files collect karein (Django admin aur Nginx ke liye zaroori hai)
RUN python manage.py collectstatic --noinput

# Gunicorn ke through server run karein
CMD ["gunicorn", "newshub_core.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]