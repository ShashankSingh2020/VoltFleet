from datetime import timedelta
import os
from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),  # Production-safe default
    DJANGO_ALLOWED_HOSTS=(list, ["127.0.0.1", "localhost", "0.0.0.0"]),
)

ROOT_DIR = BASE_DIR.parent
ENV_FILE = ROOT_DIR / ".env"
if ENV_FILE.exists():
    environ.Env.read_env(str(ENV_FILE))

SECRET_KEY = env("DJANGO_SECRET_KEY", default="insecure-placeholder-key-for-dev")
DEBUG = env("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS", default=["127.0.0.1", "localhost", "0.0.0.0"])

DJANGO_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "drf_spectacular",
    "django_celery_beat",
    "channels",
]

LOCAL_APPS = [
    "apps.authentication.apps.AuthenticationConfig",
    "apps.vehicles.apps.VehiclesConfig",
    "apps.telemetry.apps.TelemetryConfig",
    "apps.analytics.apps.AnalyticsConfig",
    "apps.charging.apps.ChargingConfig",
    "apps.optimizer.apps.OptimizerConfig",
    "apps.anomalies.apps.AnomaliesConfig",
    "apps.ai_assistant.apps.AiAssistantConfig",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

AUTH_USER_MODEL = "authentication.User"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "voltfleet.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "voltfleet.wsgi.application"
ASGI_APPLICATION = "voltfleet.asgi.application"

# Database Configuration: parses DATABASE_URL or constructs from split DB_*
db_url = env("DATABASE_URL", default=None)
if not db_url:
    db_name = env("DB_NAME", default="voltfleet")
    db_user = env("DB_USER", default="postgres")
    db_password = env("DB_PASSWORD", default="postgres")
    db_host = env("DB_HOST", default="127.0.0.1")
    db_port = env("DB_PORT", default="5432")
    db_url = f"postgres://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

DATABASES = {
    "default": env.db_url_config(db_url)
}

# Redis configuration
redis_url = env("REDIS_URL", default="redis://127.0.0.1:6379")

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": f"{redis_url}/1",
    }
}

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [f"{redis_url}/2"],
        },
    },
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ],
)
CORS_ALLOW_CREDENTIALS = True

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/minute",
        "user": "1000/minute",
        "ai_chat": "15/minute",
    },
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "AUTH_HEADER_TYPES": ("Bearer",),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "VoltFleet EV Intelligence API",
    "DESCRIPTION": "Multi-tenant EV Telemetry, Smart Charging, and AI Assistant.",
    "VERSION": "1.0.0",
}

CELERY_BROKER_URL = env("CELERY_BROKER_URL", default=f"{redis_url}/0")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default=f"{redis_url}/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"

CELERY_BEAT_SCHEDULE = {
    "periodic-anomaly-scan-every-60s": {
        "task": "apps.anomalies.tasks.run_scheduled_anomaly_scans",
        "schedule": 60.0,
    },
}

GEMINI_API_KEY = env("GEMINI_API_KEY", default="")
GEMINI_MODEL_NAME = env("GEMINI_MODEL_NAME", default="gemini-2.5-flash")
