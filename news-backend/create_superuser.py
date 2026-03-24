import os
import django

# Django environment setup karna zaroori hai script run karne se pehle
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'newshub_core.settings')
django.setup()

from django.contrib.auth import get_user_model

def create_auto_superuser():
    User = get_user_model()
    
    # Environment variables se credentials lenge, taaki code me password expose na ho
    email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'muhammadhelal228@gmail.com')
    password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'helal@123')
    name = os.environ.get('DJANGO_SUPERUSER_NAME', 'Super Admin')

    # Check karte hain ki is email se user pehle se hai ya nahi
    if not User.objects.filter(email=email).exists():
        print(f"🔄 Creating superuser with email: {email}")
        # Aapke custom model ke hisab se 'name' pass karna zaroori hai
        User.objects.create_superuser(email=email, password=password, name=name)
        print("✅ Superuser created successfully!")
    else:
        print("⚡ Superuser already exists. Skipping creation.")

if __name__ == '__main__':
    create_auto_superuser()