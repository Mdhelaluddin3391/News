from pathlib import Path
import os
import ssl
from datetime import timedelta
from dotenv import load_dotenv
from urllib.parse import urlparse
from corsheaders.defaults import default_headers

# Load environment variables from .env file
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

def _get_bool_env(name, default=False):
    return os.getenv(name, str(default)).strip().lower() == 'true'


def _get_list_env(name, default=''):
    value = os.getenv(name, default)
    return [item.strip() for item in value.split(',') if item.strip()]


# Security and Core Settings
SECRET_KEY = os.getenv('SECRET_KEY')
DEBUG = _get_bool_env('DEBUG', False)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = _get_bool_env('USE_X_FORWARDED_HOST', not DEBUG)
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
ALLOWED_HOSTS = _get_list_env('ALLOWED_HOSTS', '127.0.0.1,localhost,0.0.0.0')

WHITENOISE_MANIFEST_STRICT = False


INSTALLED_APPS = [
    'daphne',
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.postgres',
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
DATABASE_CONN_MAX_AGE = int(os.getenv('DATABASE_CONN_MAX_AGE', '60'))
DATABASE_SSL_MODE = os.getenv('DATABASE_SSL_MODE', '')
DATABASE_SSL_ROOT_CERT = os.getenv('DATABASE_SSL_ROOT_CERT', '')

if DATABASE_URL or os.getenv('POSTGRES_HOST'):
    # Agar Render par DATABASE_URL diya gaya hai, toh ye automatically URL se username, password, host nikal lega
    if DATABASE_URL:
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
        # Docker ya local PostgreSQL
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
elif DEBUG:
    # Local development ke liye SQLite use karo
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    # Production ke liye PostgreSQL
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

DATABASES['default']['CONN_MAX_AGE'] = DATABASE_CONN_MAX_AGE
if DATABASE_SSL_MODE:
    DATABASES['default'].setdefault('OPTIONS', {})['sslmode'] = DATABASE_SSL_MODE
if DATABASE_SSL_ROOT_CERT:
    DATABASES['default'].setdefault('OPTIONS', {})['sslrootcert'] = DATABASE_SSL_ROOT_CERT

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'users.authentication.CookieJWTAuthentication',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 12,
    
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle', # Bina login wale users ke liye
        'rest_framework.throttling.UserRateThrottle'  # Logged in users ke liye
    ],
    'DEFAULT_THROTTLE_RATES': {
        # If DEBUG is true, allow 5000 requests, otherwise strictly allow 200
        'anon': '5000/hour' if DEBUG else '200/hour',         
        'user': '10000/hour' if DEBUG else '1000/hour',        
        'auth': '5/minute',         
        'email_alert': '3/hour',    
        'comment_report': '10/hour', 
    
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

STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage' if not DEBUG else 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage',
    },
}

USE_S3 = _get_bool_env('USE_S3', False)

if USE_S3:
    # AWS Credentials
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = os.getenv('AWS_S3_REGION_NAME', 'ap-south-1') # e.g., Mumbai region
    AWS_S3_CUSTOM_DOMAIN = os.getenv(
        'AWS_S3_CUSTOM_DOMAIN',
        f'{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com'
    )

    AWS_S3_SIGNATURE_VERSION = 's3v4'
    AWS_S3_ADDRESSING_STYLE = 'virtual'
    AWS_S3_FILE_OVERWRITE = False
    AWS_DEFAULT_ACL = None
    AWS_QUERYSTRING_AUTH = _get_bool_env('AWS_QUERYSTRING_AUTH', False)
    AWS_LOCATION = os.getenv('AWS_LOCATION', 'media')
    AWS_S3_OBJECT_PARAMETERS = {
        'CacheControl': 'max-age=86400',
    }

    STORAGES['default'] = {
        'BACKEND': 'storages.backends.s3.S3Storage',
        'OPTIONS': {
            'location': AWS_LOCATION,
            'default_acl': None,
            'file_overwrite': AWS_S3_FILE_OVERWRITE,
            'querystring_auth': AWS_QUERYSTRING_AUTH,
        },
    }
    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/{AWS_LOCATION}/'
else:
    # Local development ke liye
    MEDIA_URL = '/media/'
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
# Static & Media Files
STATICFILES_DIRS = [BASE_DIR / 'static']

# Core CORS / redirect behavior control (fixes CORS + 301 for API clients)
APPEND_SLASH = False

# CORS config
CORS_ALLOW_ALL_ORIGINS = _get_bool_env('CORS_ALLOW_ALL_ORIGINS', DEBUG)
if CORS_ALLOW_ALL_ORIGINS:
    CORS_ALLOW_ALL_ORIGINS = True
else:
    CORS_ALLOWED_ORIGINS = _get_list_env(
        'CORS_ALLOWED_ORIGINS',
        'http://localhost,http://127.0.0.1,http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000,http://127.0.0.1:8000,http://0.0.0.0:8000'
    )

CORS_ALLOW_CREDENTIALS = _get_bool_env('CORS_ALLOW_CREDENTIALS', True)
CORS_ALLOW_HEADERS = list(default_headers) + [
    'content-type',
    'authorization',
]
CORS_EXPOSE_HEADERS = [
    'Content-Type',
    'Authorization',
]

# Allow frontend dev host for CSRF
domain_name = os.getenv('DOMAIN_NAME', 'localhost')
CSRF_TRUSTED_ORIGINS = _get_list_env(
    'CSRF_TRUSTED_ORIGINS',
    'http://localhost,http://127.0.0.1,http://localhost:3000,http://127.0.0.1:3000'
)

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
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost')
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
SITE_ID = 1

# JWT Settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=7),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_COOKIE_ACCESS': os.getenv('AUTH_COOKIE_ACCESS', 'ft_access_token'),
    'AUTH_COOKIE_REFRESH': os.getenv('AUTH_COOKIE_REFRESH', 'ft_refresh_token'),
    'AUTH_COOKIE_SECURE': _get_bool_env('AUTH_COOKIE_SECURE', not DEBUG),
    'AUTH_COOKIE_HTTP_ONLY': True,
    'AUTH_COOKIE_SAMESITE': os.getenv('AUTH_COOKIE_SAMESITE', 'Lax'),
    'AUTH_COOKIE_PATH': os.getenv('AUTH_COOKIE_PATH', '/'),
    'AUTH_COOKIE_REFRESH_PATH': os.getenv('AUTH_COOKIE_REFRESH_PATH', '/api/auth/refresh/'),
}

SENTRY_DSN = os.getenv('SENTRY_DSN', '')
SENTRY_ENVIRONMENT = os.getenv('SENTRY_ENVIRONMENT', 'development' if DEBUG else 'production')
SENTRY_RELEASE = os.getenv('SENTRY_RELEASE', '')
SENTRY_TRACES_SAMPLE_RATE = float(os.getenv('SENTRY_TRACES_SAMPLE_RATE', '0'))
SENTRY_PROFILES_SAMPLE_RATE = float(os.getenv('SENTRY_PROFILES_SAMPLE_RATE', '0'))
SENTRY_SEND_DEFAULT_PII = _get_bool_env('SENTRY_SEND_DEFAULT_PII', False)

# TinyMCE Setup
TINYMCE_DEFAULT_CONFIG = {
    "height": "700px",  # Editor ki height thodi badi kar di
    "width": "100%",
    "menubar": "file edit view insert format tools table help",
    # Saare advanced plugins add kar diye: image, media, table, lists, etc.
    "plugins": "advlist autolink lists link image charmap print preview anchor searchreplace visualblocks code fullscreen insertdatetime media table paste code help wordcount codesample directionality",
    
    # Ye wo buttons hain jo editor ke top bar par dikhenge
    "toolbar": "undo redo | formatselect | bold italic underline strikethrough | alignleft aligncenter alignright alignjustify | bullist numlist outdent indent | blockquote | link image media | forecolor backcolor | removeformat | fullscreen help",
    
    # Format options (H1, H2, H3, Blockquote etc.)
    "block_formats": "Paragraph=p; Header 1=h1; Header 2=h2; Header 3=h3; Header 4=h4; Header 5=h5; Header 6=h6; Blockquote=blockquote",
    
    "image_caption": True,
    "image_advtab": True,
    
    # 🎯 YAHAN AAPKA "NEWS QUOTE" WALA MAGIC HAI (Custom CSS inject kar rahe hain editor ke andar)
    # Taaki admin panel mein likhte waqt hi exactly waisa design dikhe jaisa website par dikhega
    "content_style": """
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; 
            font-size: 16px; line-height: 1.6; color: #333;
        }
        /* 📰 News Style Blockquote (Jaise 'Trump said...' wala left line aur italic text) */
        blockquote {
            border-left: 5px solid #d32f2f; /* Red colour ki left line */
            margin: 1.5em 10px;
            padding: 0.5em 15px;
            background-color: #f9f9f9;
            font-style: italic;
            font-size: 1.1em;
            color: #555;
            box-shadow: 2px 2px 8px rgba(0,0,0,0.05);
        }
        img { max-width: 100%; height: auto; border-radius: 8px; }
        h1, h2, h3 { font-weight: bold; color: #111; }
    """,
}

REDIS_URL = os.getenv('REDIS_URL', 'redis://127.0.0.1:6379')

if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=SENTRY_ENVIRONMENT,
        release=SENTRY_RELEASE or None,
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
        ],
        traces_sample_rate=SENTRY_TRACES_SAMPLE_RATE,
        profiles_sample_rate=SENTRY_PROFILES_SAMPLE_RATE,
        send_default_pii=SENTRY_SEND_DEFAULT_PII,
    )
REDIS_SSL_NO_VERIFY = _get_bool_env('REDIS_SSL_NO_VERIFY', True)
REDIS_CHANNEL_HOSTS = [REDIS_URL]

# Redis Caching Setup
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "IGNORE_EXCEPTIONS": True,
            # Removed the CONNECTION_POOL_KWARGS from here. We will add it conditionally.
        }
    }
}


CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": REDIS_CHANNEL_HOSTS,
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

if REDIS_URL.startswith('rediss://'):
    if REDIS_SSL_NO_VERIFY:
        # redis-py library requires the string "none" instead of Python's None type
        CACHES['default']['OPTIONS']['CONNECTION_POOL_KWARGS'] = {
            "ssl_cert_reqs": "none"
        }
        REDIS_CHANNEL_HOSTS[:] = [{
            "address": REDIS_URL,
            "ssl_cert_reqs": None,
        }]
        CELERY_BROKER_USE_SSL = {'ssl_cert_reqs': ssl.CERT_NONE}
        CELERY_REDIS_BACKEND_USE_SSL = {'ssl_cert_reqs': ssl.CERT_NONE}

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


SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True


# Jazzmin Admin Settings
JAZZMIN_SETTINGS = {
    "site_title": "Ferox Times Admin",
    "site_header": "Ferox Times",
    "site_brand": "Ferox Times Dashboard",
    "welcome_sign": "Welcome to Ferox Times Admin Panel",
    "copyright": "Ferox Times",
    "search_model": ["news.Article", "users.User"],
    "custom_css": "css/admin_custom.css",
    "topmenu_links": [
        {"name": "Home",  "url": "admin:index", "permissions": ["auth.view_user"]},
        {"name": "View Frontend Site", "url": FRONTEND_URL + "/index.html", "new_window": True},
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
