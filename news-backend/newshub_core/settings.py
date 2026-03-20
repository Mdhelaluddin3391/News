from pathlib import Path
import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# Security and Core Settings
SECRET_KEY = os.getenv('SECRET_KEY')
DEBUG = os.getenv('DEBUG', 'False') == 'True'
ALLOWED_HOSTS = ['*'] # Production me yahan apna domain name add karein

INSTALLED_APPS = [
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third-party apps
    'rest_framework',
    'corsheaders',
    'django_filters',
    'rest_framework_simplejwt',
    'tinymce',
    'django.contrib.sites',   
    'django.contrib.sitemaps',
    
    # Custom apps
    'users',
    'news',
    'interactions',
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'newshub_core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'newshub_core.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB', 'newshub_db'),
        'USER': os.getenv('POSTGRES_USER', 'newshub_user'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'newshub_password'),
        'HOST': os.getenv('POSTGRES_HOST', 'db'), # Ye Docker compose service ka naam hoga
        'PORT': os.getenv('POSTGRES_PORT', '5432'),
    }
}

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 6,
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static & Media Files
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
MEDIA_URL = '/media/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# CORS & Custom Auth
CORS_ALLOW_ALL_ORIGINS = True
CSRF_TRUSTED_ORIGINS = [
    "http://127.0.0.1:5501/news-website",
    "http://127.0.0.1:5501",  # Aapke frontend ka port
    "http://127.0.0.1:8000",  # <--- YEH NAYA ADD KIYA HAI (Admin Login ke liye)
    "http://localhost:8000",
]
AUTH_USER_MODEL = 'users.User'

# Email Settings
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL')

# URLs and IDs
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://127.0.0.1:5501/news-website')
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
SITE_ID = 1

# JWT Settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=7),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# TinyMCE Setup
TINYMCE_DEFAULT_CONFIG = {
    'height': 500,
    'width': 'auto',
    'menubar': 'file edit view insert format tools table help',
    'plugins': 'advlist autolink lists link image charmap print preview anchor searchreplace visualblocks code fullscreen insertdatetime media table paste code help wordcount',
    'toolbar': 'undo redo | formatselect | bold italic backcolor | alignleft aligncenter alignright alignjustify | bullist numlist outdent indent | removeformat | help',
    'custom_undo_redo_levels': 10,
}

REDIS_HOST = os.getenv('REDIS_HOST', '127.0.0.1')

# Redis Caching Setup
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{REDIS_HOST}:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "IGNORE_EXCEPTIONS": True,
        }
    }
}

# Web Push Settings
WEBPUSH_SETTINGS = {
    "VAPID_PUBLIC_KEY": os.getenv('VAPID_PUBLIC_KEY'), 
    "VAPID_PRIVATE_KEY": os.getenv('VAPID_PRIVATE_KEY'), 
    "VAPID_ADMIN_EMAIL": os.getenv('VAPID_ADMIN_EMAIL') 
}

# Social Media Auto-Post Settings
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')
FACEBOOK_PAGE_ID = os.getenv('FACEBOOK_PAGE_ID')
FACEBOOK_ACCESS_TOKEN = os.getenv('FACEBOOK_ACCESS_TOKEN')
TWITTER_API_KEY = os.getenv('TWITTER_API_KEY')
TWITTER_API_SECRET = os.getenv('TWITTER_API_SECRET')
TWITTER_ACCESS_TOKEN = os.getenv('TWITTER_ACCESS_TOKEN')
TWITTER_ACCESS_TOKEN_SECRET = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')

CELERY_BROKER_URL = f'redis://{REDIS_HOST}:6379/2'
CELERY_RESULT_BACKEND = f'redis://{REDIS_HOST}:6379/2'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# Jazzmin Admin Settings
JAZZMIN_SETTINGS = {
    "site_title": "NewsHub Admin",
    "site_header": "NewsHub",
    "site_brand": "NewsHub Dashboard",
    "welcome_sign": "Welcome to NewsHub Admin Panel",
    "copyright": "NewsHub by Dharmanagar Live",
    "search_model": ["news.Article", "users.User"],
    "custom_css": "css/admin_custom.css",
    "topmenu_links": [
        {"name": "Home",  "url": "admin:index", "permissions": ["auth.view_user"]},
        {"name": "View Frontend Site", "url": os.getenv('FRONTEND_URL', 'http://127.0.0.1:5500') + "/index.html", "new_window": True},
    ],
    "icons": {
        "auth": "fas fa-users-cog",
        "users.User": "fas fa-user",
        "auth.Group": "fas fa-users",
        "news.Article": "fas fa-newspaper",
        "news.Category": "fas fa-list-alt",
        "news.Author": "fas fa-user-edit",
        "news.Tag": "fas fa-tags",
        "news.LiveUpdate": "fas fa-broadcast-tower",
        "interactions.Comment": "fas fa-comments",
        "interactions.Poll": "fas fa-poll",
        "interactions.Bookmark": "fas fa-bookmark",
        "interactions.NewsletterSubscriber": "fas fa-envelope-open-text",
        "interactions.PushSubscription": "fas fa-bell",
        "core.Advertisement": "fas fa-ad",
        "core.ContactMessage": "fas fa-envelope",
    },
    "show_sidebar": True,
    "navigation_expanded": True,
    "related_modal_active": True,
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": "navbar-navy",
    "navbar": "navbar-navy navbar-dark",
    "accent": "accent-danger",
    "sidebar": "sidebar-light-navy",
    "no_navbar_border": False,
    "navbar_fixed": True,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": True,
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": True,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": True,
    "theme": "default",
    "dark_mode_theme": "darkly",
    "button_classes": {
        "primary": "btn-primary",
        "secondary": "btn-danger",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success"
    }
}