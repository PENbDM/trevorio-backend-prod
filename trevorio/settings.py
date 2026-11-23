from pathlib import Path
import os
from datetime import timedelta

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")




REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_USE_TLS = os.getenv("REDIS_USE_TLS", "false").lower() == "true"

REDIS_SCHEME = "rediss" if REDIS_USE_TLS else "redis"

CELERY_BROKER_URL = f"{REDIS_SCHEME}://{REDIS_HOST}:{REDIS_PORT}/0"
CELERY_RESULT_BACKEND = f"{REDIS_SCHEME}://{REDIS_HOST}:{REDIS_PORT}/1"

if REDIS_USE_TLS:
    CELERY_BROKER_URL += "?ssl_cert_reqs=required"
    CELERY_RESULT_BACKEND += "?ssl_cert_reqs=required"




STATIC_ROOT = BASE_DIR / "staticfiles"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")



# Security / local development
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
DEBUG = os.getenv("DJANGO_DEBUG", "False").lower() == "true"
ALLOWED_HOSTS = [
    value.strip()
    for value in os.getenv("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")
    if value.strip()
]

SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
GITHUB_CLIENT_ID = os.environ["GITHUB_CLIENT_ID"]

GITHUB_CLIENT_SECRET = os.environ[
    "GITHUB_CLIENT_SECRET"
]

GITHUB_CALLBACK_URL = os.environ[
    "GITHUB_CALLBACK_URL"
]

GITHUB_TOKEN_ENCRYPTION_KEY = os.environ[
    "GITHUB_TOKEN_ENCRYPTION_KEY"
]

FRONTEND_URL = os.environ.get(
    "FRONTEND_URL",
    "http://localhost:3000",
)
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "accounts",
    "data_sources",
    "queries",
    'integrations',
    'streaming',
    'tracking',
]





CELERY_BEAT_SCHEDULE = {
    "change-detector-15-seconds": {
        "task": 'streaming.tasks.change_detector_worker',
        "schedule": 15.0,
        # "args":(16,16),
    },
}

CELERY_TIMEZONE = "UTC"


MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "trevorio.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "trevorio.wsgi.application"
ASGI_APPLICATION = "trevorio.asgi.application"


# PostgreSQL only. There is intentionally no SQLite fallback.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME",),
        "USER": os.getenv("DB_USER",),
        "PASSWORD": os.getenv("DB_PASSWORD",),
        "HOST": os.getenv("DB_HOST",),
        "PORT": os.getenv("DB_PORT",),
        "CONN_MAX_AGE": 60,
        "CONN_HEALTH_CHECKS": True,
    }
}
CUSTOMER_QUERY_MAX_ROWS = 1000

AUTH_USER_MODEL = "accounts.User"
AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "en-gb"
TIME_ZONE = "Europe/London"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "AUTH_HEADER_TYPES": ("Bearer",),
}

CORS_ALLOWED_ORIGINS = [
    value.strip()
    for value in os.getenv(
        "FRONTEND_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if value.strip()
]
CORS_ALLOW_CREDENTIALS = True

# Local datasource credential encryption key.
LOCAL_SECRET_KEY = os.getenv(
    "LOCAL_SECRET_KEY",
    "trevor-local-datasource-secret-2026",
)

# Maximum runtime for SQL executed against a connected customer PostgreSQL DB.
CUSTOMER_QUERY_TIMEOUT_MS = int(
    os.getenv("CUSTOMER_QUERY_TIMEOUT_MS", "15000")
)
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}