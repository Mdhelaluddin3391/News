import os
import django

# Django environment setup karna zaroori hai script run karne se pehle
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'newshub_core.settings')
django.setup()

from django.contrib.auth import get_user_model

def create_auto_superuser():
    User = get_user_model()

    email = os.getenv('DJANGO_SUPERUSER_EMAIL', '').strip()
    password = os.getenv('DJANGO_SUPERUSER_PASSWORD', '').strip()
    name = os.getenv('DJANGO_SUPERUSER_NAME', 'Admin User').strip() or 'Admin User'

    if not email or not password:
        print("Skipping superuser creation. Set DJANGO_SUPERUSER_EMAIL and DJANGO_SUPERUSER_PASSWORD to enable it.")
        return

    if not User.objects.filter(email=email).exists():
        print(f"Creating superuser with email: {email}")
        User.objects.create_superuser(email=email, password=password, name=name)
        print("Superuser created successfully.")
    else:
        print("Superuser already exists. Skipping creation.")

if __name__ == '__main__':
    create_auto_superuser()
