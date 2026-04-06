import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "newshub_core.settings")
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

# Env variables se admin details lein ya default set karein
DJANGO_SU_NAME = os.environ.get('DJANGO_SU_NAME', 'mdhelaluddin')
DJANGO_SU_EMAIL = os.environ.get('DJANGO_SU_EMAIL', 'muhammadhelal228@gmail.com')
DJANGO_SU_PASSWORD = os.environ.get('DJANGO_SU_PASSWORD', 'helal@123')

if not User.objects.filter(username=DJANGO_SU_NAME).exists():
    User.objects.create_superuser(
        username=DJANGO_SU_NAME,
        email=DJANGO_SU_EMAIL,
        password=DJANGO_SU_PASSWORD
    )
    print(f"Superuser '{DJANGO_SU_NAME}' created successfully.")
else:
    print(f"Superuser '{DJANGO_SU_NAME}' already exists.")