FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Ab requirements.txt same folder mein hai, isliye directly copy kar sakte hain
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# Pura backend ka code current directory se /app/ mein copy karein
COPY . /app/

# Static files collect karein (Django admin aur Nginx ke liye zaroori hai)
RUN python manage.py collectstatic --noinput

# Gunicorn ke through server run karein
CMD ["gunicorn", "newshub_core.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]