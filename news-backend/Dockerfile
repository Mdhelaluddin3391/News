# Python ka official slim image use karenge
FROM python:3.10-slim

# Environment variables set karenge taaki Python output buffer na kare
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Container ke andar working directory set karenge
WORKDIR /app

# Requirements file copy karenge aur packages install karenge
COPY ../requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# Pura backend code copy karenge
COPY . /app/

# Port expose karenge
EXPOSE 8000

# Django server run karne ka command (Production me gunicorn use karna better hota hai, par abhi runserver use kar rahe hain)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]