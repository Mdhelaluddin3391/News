from pathlib import Path
import os
from datetime import timedelta
from dotenv import load_dotenv
from urllib.parse import urlparse

# Load environment variables from .env file
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# Security and Core Settings
SECRET_KEY = os.getenv('SECRET_KEY')
DEBUG = os.getenv('DEBUG', 'False') == 'True'
if not DEBUG:
    # HTTP requests ne automatically HTTPS par redirect karse
    SECURE_SSL_REDIRECT = True
    
    # Cookies ne sirf HTTPS par j send karva de
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    
    # HSTS (HTTP Strict Transport Security) enable karva (optional but recommended)
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '*').split(',') # Production me yahan apna domain name add karein

INSTALLED_APPS = [
    'daphne',
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
    'storages',
    
    # Custom apps
    'users',
    'news',
    'interactions',
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
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
ASGI_APPLICATION = 'newshub_core.asgi.application'

# CHANNEL_LAYERS = {
#     "default": {
#         "BACKEND": "channels_redis.core.RedisChannelLayer",
#         "CONFIG": {
#             "hosts": [(os.getenv('REDIS_HOST', '127.0.0.1'), 6379)],
#         },
#     },
# }

DATABASE_URL = os.getenv('DATABASE_URL')

if DATABASE_URL:
    # Agar Render par DATABASE_URL diya gaya hai, toh ye automatically URL se username, password, host nikal lega
    url = urlparse(DATABASE_URL)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': url.path[1:],  # Shuru ka '/' hatane ke liye
            'USER': url.username,
            'PASSWORD': url.password,
            'HOST': url.hostname,
            'PORT': url.port or '5432',
        }
    }
else:
    # Local development ke liye aapka purana tareeqa
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('POSTGRES_DB', 'newshub_db'),
            'USER': os.getenv('POSTGRES_USER', 'newshub_user'),
            'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'newshub_password'),
            'HOST': os.getenv('POSTGRES_HOST', 'db'), 
            'PORT': os.getenv('POSTGRES_PORT', '5432'),
        }
    }

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 6,
    
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle', # Bina login wale users ke liye
        'rest_framework.throttling.UserRateThrottle'  # Logged in users ke liye
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '200/hour',      # Aam public 1 ghante mein max 200 requests kar sakti hai
        'user': '1000/hour',     # Logged in user 1 ghante mein 1000 requests kar sakta hai
        'auth': '5/minute',      # Sensitive APIs (Login/Register) ke liye 1 minute me max 5 try
        'email_alert': '3/hour', # Forgot password jaise emails ke liye 1 ghante me max 3 try
    },
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



USE_S3 = os.getenv('USE_S3', 'False') == 'True'

if USE_S3:
    # AWS Credentials
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = os.getenv('AWS_S3_REGION_NAME', 'ap-south-1') # e.g., Mumbai region
    AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
    
    # S3 Settings
    AWS_S3_FILE_OVERWRITE = False
    AWS_DEFAULT_ACL = 'public-read'
    AWS_S3_OBJECT_PARAMETERS = {
        'CacheControl': 'max-age=86400',
    }

    # Media Files ko S3 par point karein
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'
else:
    # Local development ke liye
    MEDIA_URL = '/media/'
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
# Static & Media Files
STATICFILES_DIRS = [BASE_DIR / 'static']

# CORS & Custom Auth
CORS_ALLOW_ALL_ORIGINS = os.getenv('CORS_ALLOW_ALL_ORIGINS', 'True') == 'True'
if not CORS_ALLOW_ALL_ORIGINS:
    CORS_ALLOWED_ORIGINS = os.getenv('CORS_ALLOWED_ORIGINS', '').split(',')

CSRF_TRUSTED_ORIGINS = os.getenv('CSRF_TRUSTED_ORIGINS', 'http://127.0.0.1:8000').split(',')

# CSRF_TRUSTED_ORIGINS = [
#     "http://127.0.0.1:5501/news-website",
#     "http://127.0.0.1:5501",  # Aapke frontend ka port
#     "http://127.0.0.1:8000",  # <--- YEH NAYA ADD KIYA HAI (Admin Login ke liye)
#     "http://localhost:8000",
# ]
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

REDIS_URL = os.getenv('REDIS_URL', 'redis://127.0.0.1:6379')

# Redis Caching Setup
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "IGNORE_EXCEPTIONS": True,
        }
    }
}

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_URL], # Naya URL yahan pass kar diya
        },
    },
}

# Celery Setup
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE


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