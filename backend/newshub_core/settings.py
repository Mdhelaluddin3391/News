from pathlib import Path
import os
import ssl
from datetime import timedelta
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv
from urllib.parse import urlparse
from corsheaders.defaults import default_headers

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR.parent / '.env'

# Load environment variables from the repository root .env file when present.
load_dotenv(ENV_FILE)

def _get_bool_env(name, default=False):
    return os.getenv(name, str(default)).strip().lower() == 'true'


def _get_list_env(name, default=''):
    value = os.getenv(name, default)
    return [item.strip() for item in value.split(',') if item.strip()]


def _is_placeholder_secret(value):
    if value is None:
        return True

    normalized = value.strip().lower()
    placeholder_markers = (
        'replace-with',
        'change-me',
        'dummy-key-for-build-only',
        'example.com',
    )
    return not normalized or any(marker in normalized for marker in placeholder_markers)


def _derive_redis_url(url, database_number):
    parsed = urlparse(url)
    return parsed._replace(path=f'/{database_number}').geturl()


# Security and Core Settings
DEBUG = _get_bool_env('DEBUG', False)
IS_PRODUCTION = not DEBUG
APP_ENV = os.getenv('APP_ENV', 'development' if DEBUG else 'production').strip().lower()

SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = 'django-insecure-development-only-key'
    else:
        raise ImproperlyConfigured('SECRET_KEY must be set when DEBUG is false.')
elif IS_PRODUCTION and _is_placeholder_secret(SECRET_KEY):
    raise ImproperlyConfigured('SECRET_KEY must be replaced with a real production secret.')

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = _get_bool_env('USE_X_FORWARDED_HOST', not DEBUG)
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
if IS_PRODUCTION:
    SECURE_SSL_REDIRECT = _get_bool_env('SECURE_SSL_REDIRECT', True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', '31536000'))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = _get_bool_env('SECURE_HSTS_INCLUDE_SUBDOMAINS', True)
    SECURE_HSTS_PRELOAD = _get_bool_env('SECURE_HSTS_PRELOAD', True)
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True

ALLOWED_HOSTS = _get_list_env(
    'ALLOWED_HOSTS',
    'feroxtimes.com,www.feroxtimes.com,admin.feroxtimes.com' if IS_PRODUCTION else '127.0.0.1,localhost,0.0.0.0'
)
if IS_PRODUCTION and not ALLOWED_HOSTS:
    raise ImproperlyConfigured('ALLOWED_HOSTS must contain at least one hostname in production.')

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
    'django.middleware.gzip.GZipMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

ROOT_URLCONF = 'newshub_core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
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
DATABASE_CONN_HEALTH_CHECKS = _get_bool_env('DATABASE_CONN_HEALTH_CHECKS', True)
DATABASE_CONNECT_TIMEOUT = int(os.getenv('DATABASE_CONNECT_TIMEOUT', '5'))
DATABASE_STATEMENT_TIMEOUT_MS = int(os.getenv('DATABASE_STATEMENT_TIMEOUT_MS', '15000'))
DATABASE_APPLICATION_NAME = os.getenv('DATABASE_APPLICATION_NAME', 'newshub-backend')
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

if not DEBUG and DATABASES['default']['ENGINE'] == 'django.db.backends.postgresql':
    postgres_password = DATABASES['default'].get('PASSWORD')
    if _is_placeholder_secret(postgres_password):
        raise ImproperlyConfigured('POSTGRES_PASSWORD must be replaced with a real production password.')

DATABASES['default']['CONN_MAX_AGE'] = DATABASE_CONN_MAX_AGE
DATABASES['default']['CONN_HEALTH_CHECKS'] = DATABASE_CONN_HEALTH_CHECKS
if DATABASES['default']['ENGINE'] == 'django.db.backends.postgresql':
    DATABASES['default'].setdefault('OPTIONS', {})
    DATABASES['default']['OPTIONS'].setdefault('connect_timeout', DATABASE_CONNECT_TIMEOUT)
    DATABASES['default']['OPTIONS'].setdefault('application_name', DATABASE_APPLICATION_NAME)
    if DATABASE_STATEMENT_TIMEOUT_MS > 0:
        DATABASES['default']['OPTIONS'].setdefault(
            'options',
            f'-c statement_timeout={DATABASE_STATEMENT_TIMEOUT_MS}',
        )
    if DATABASE_SSL_MODE:
        DATABASES['default']['OPTIONS']['sslmode'] = DATABASE_SSL_MODE
    if DATABASE_SSL_ROOT_CERT:
        DATABASES['default']['OPTIONS']['sslrootcert'] = DATABASE_SSL_ROOT_CERT

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'users.authentication.CookieJWTAuthentication',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
    ),
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
        'contact_form': '5/hour',
        'newsletter': '10/hour',
        'poll_vote': '30/hour',
        'push_subscribe': '20/hour',
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
        'BACKEND': (
            'django.contrib.staticfiles.storage.StaticFilesStorage'
            if DEBUG
            else 'whitenoise.storage.CompressedManifestStaticFilesStorage'
        ),
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

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
# Static & Media Files
STATICFILES_DIRS = [BASE_DIR / 'static']

# Core CORS / redirect behavior control (fixes CORS + 301 for API clients)
APPEND_SLASH = False
PORT = int(os.getenv('PORT', '5000'))
PUBLIC_API_CACHE_TTL = int(os.getenv('PUBLIC_API_CACHE_TTL', '300'))
SITE_SETTINGS_CACHE_TTL = int(os.getenv('SITE_SETTINGS_CACHE_TTL', '3600'))

# CORS config
CORS_ALLOW_ALL_ORIGINS = _get_bool_env('CORS_ALLOW_ALL_ORIGINS', DEBUG)
default_cors_origins = (
    'https://feroxtimes.com,https://www.feroxtimes.com,https://admin.feroxtimes.com'
    if IS_PRODUCTION
    else 'http://localhost,http://127.0.0.1,http://localhost:3000,http://127.0.0.1:3000,http://localhost:5000,http://127.0.0.1:5000,http://0.0.0.0:5000'
)

if CORS_ALLOW_ALL_ORIGINS:
    CORS_ALLOW_ALL_ORIGINS = True
else:
    CORS_ALLOWED_ORIGINS = _get_list_env(
        'CORS_ALLOWED_ORIGINS',
        default_cors_origins
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

CSRF_TRUSTED_ORIGINS = _get_list_env(
    'CSRF_TRUSTED_ORIGINS',
    (
        'https://feroxtimes.com,https://www.feroxtimes.com,https://admin.feroxtimes.com'
        if IS_PRODUCTION
        else 'http://localhost,http://127.0.0.1,http://localhost:3000,http://127.0.0.1:3000,http://localhost:5000,http://127.0.0.1:5000'
    )
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
EMAIL_TIMEOUT = int(os.getenv('EMAIL_TIMEOUT', '15'))

# URLs and IDs
FRONTEND_URL = os.getenv(
    'FRONTEND_URL',
    'https://www.feroxtimes.com' if IS_PRODUCTION else 'http://localhost'
).rstrip('/')
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
SITE_ID = int(os.getenv('SITE_ID', '1'))

# JWT Settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
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

REDIS_URL = os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/0')
REDIS_CACHE_URL = os.getenv('REDIS_CACHE_URL', _derive_redis_url(REDIS_URL, 1))
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', _derive_redis_url(REDIS_URL, 2))
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', _derive_redis_url(REDIS_URL, 3))
CHANNEL_REDIS_URL = os.getenv('CHANNEL_REDIS_URL', _derive_redis_url(REDIS_URL, 4))

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
REDIS_CHANNEL_HOSTS = [CHANNEL_REDIS_URL]

# Redis Caching Setup
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_CACHE_URL,
        "KEY_PREFIX": os.getenv('CACHE_KEY_PREFIX', 'newshub'),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "IGNORE_EXCEPTIONS": True,
            "SOCKET_CONNECT_TIMEOUT": 5,
            "SOCKET_TIMEOUT": 5,
        }
    },
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
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_DEFAULT_QUEUE = os.getenv('CELERY_TASK_DEFAULT_QUEUE', 'default')
CELERY_TASK_ACKS_LATE = _get_bool_env('CELERY_TASK_ACKS_LATE', True)
CELERY_TASK_REJECT_ON_WORKER_LOST = _get_bool_env('CELERY_TASK_REJECT_ON_WORKER_LOST', True)
CELERY_TASK_TRACK_STARTED = _get_bool_env('CELERY_TASK_TRACK_STARTED', True)
CELERY_WORKER_PREFETCH_MULTIPLIER = int(os.getenv('CELERY_WORKER_PREFETCH_MULTIPLIER', '1'))
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_TASK_SOFT_TIME_LIMIT = int(os.getenv('CELERY_TASK_SOFT_TIME_LIMIT', '180'))
CELERY_TASK_TIME_LIMIT = int(os.getenv('CELERY_TASK_TIME_LIMIT', '240'))
CELERY_WORKER_MAX_TASKS_PER_CHILD = int(os.getenv('CELERY_WORKER_MAX_TASKS_PER_CHILD', '100'))
CELERY_TASK_ROUTES = {
    'core.tasks.send_async_email': {'queue': 'mail'},
    'news.tasks.process_article_image': {'queue': 'media'},
    'news.tasks.send_push_notifications_task': {'queue': 'notifications'},
    'news.tasks.auto_post_article_task': {'queue': 'notifications'},
    'news.tasks.auto_import_news_task': {'queue': 'default'},
    'news.tasks.cleanup_expired_flags_task': {'queue': 'default'},
}
CELERY_BEAT_SCHEDULE = {
    'auto-import-news-every-30-mins': {
        'task': 'news.tasks.auto_import_news_task',
        'schedule': 60 * 30,
    },
    'cleanup-expired-flags-every-hour': {
        'task': 'news.tasks.cleanup_expired_flags_task',
        'schedule': 60 * 60,
    },
}

if REDIS_CACHE_URL.startswith('rediss://'):
    if REDIS_SSL_NO_VERIFY:
        # redis-py library requires the string "none" instead of Python's None type
        CACHES['default']['OPTIONS']['CONNECTION_POOL_KWARGS'] = {
            "ssl_cert_reqs": "none"
        }

if CHANNEL_REDIS_URL.startswith('rediss://') and REDIS_SSL_NO_VERIFY:
    REDIS_CHANNEL_HOSTS[:] = [{
        "address": CHANNEL_REDIS_URL,
        "ssl_cert_reqs": None,
    }]

if CELERY_BROKER_URL.startswith('rediss://') and REDIS_SSL_NO_VERIFY:
    CELERY_BROKER_USE_SSL = {'ssl_cert_reqs': ssl.CERT_NONE}

if CELERY_RESULT_BACKEND.startswith('rediss://') and REDIS_SSL_NO_VERIFY:
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

LOG_LEVEL = os.getenv('LOG_LEVEL', 'DEBUG' if DEBUG else 'INFO').upper()
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s %(levelname)s %(name)s %(message)s',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': LOG_LEVEL,
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        'celery': {
            'handlers': ['console'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        'newshub': {
            'handlers': ['console'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
    },
}


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
        {"name": "View Frontend Site", "url": FRONTEND_URL + "/", "new_window": True},
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
