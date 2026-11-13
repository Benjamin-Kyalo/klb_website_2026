"""
Django settings for the KLB website backend.

The project reads configuration from environment variables (see backend/.env.example).
Defaults are safe for local development only. In production set DJANGO_DEBUG=False,
a strong DJANGO_SECRET_KEY, DJANGO_ALLOWED_HOSTS and DJANGO_CSRF_TRUSTED_ORIGINS.
"""
import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load backend/.env when present (never commit that file).
load_dotenv(BASE_DIR / ".env")


def env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "insecure-local-development-key-change-me")
DEBUG = env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")

CSRF_TRUSTED_ORIGINS = env_list(
    "DJANGO_CSRF_TRUSTED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000,http://127.0.0.1:8000",
)

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.staticfiles",
    "rest_framework",
    "apps.accounts",
    "apps.catalogue",
    "apps.content",
    "apps.enquiries",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.content.middleware.SecurityHeadersMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ---------------------------------------------------------------------------
# Database - PostgreSQL through DATABASE_URL
# ---------------------------------------------------------------------------
_database_url = os.getenv(
    "DATABASE_URL",
    "postgres://klb:klb_dev_password@127.0.0.1:5432/klb",
).strip()
if _database_url.startswith("https://") or _database_url.startswith("http://"):
    raise RuntimeError(
        "DATABASE_URL must be a PostgreSQL connection string, not an HTTP URL. "
        "For Supabase, use: postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres?sslmode=require"
    )

DATABASES = {
    "default": dj_database_url.parse(
        _database_url,
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

SESSION_COOKIE_NAME = "klb_session"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
# Inactivity timeout. Each request resets the clock when
# SESSION_SAVE_EVERY_REQUEST is True, so active users stay signed in.
SESSION_COOKIE_AGE = int(os.getenv("SESSION_TIMEOUT_SECONDS", "1800"))
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = env_bool("SESSION_EXPIRE_AT_BROWSER_CLOSE", False)
CSRF_COOKIE_HTTPONLY = False  # the React client reads this token
CSRF_COOKIE_SAMESITE = "Lax"

if env_bool("DJANGO_SECURE_COOKIES", False):
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# ---------------------------------------------------------------------------
# REST framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_PAGINATION_CLASS": "apps.catalogue.pagination.CataloguePagination",
    "PAGE_SIZE": 24,
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    # The activity-log export uses ?format=csv|xlsx|pdf. DRF treats a "format"
    # query parameter as a renderer override by default, which would return a
    # 404 before the export view runs. The export view handles the parameter.
    "URL_FORMAT_OVERRIDE": None,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/min",
        "user": "120/min",
        "login": "5/min",
        "enquiry": "10/min",
        "newsletter": "5/min",
    },
    "EXCEPTION_HANDLER": "config.exceptions.api_exception_handler",
}

# ---------------------------------------------------------------------------
# Internationalisation
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-ke"
TIME_ZONE = "Africa/Nairobi"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static and media files
# ---------------------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
# Media and backups share one persistent Render disk in production. Keeping the
# two directories configurable also makes local development and other hosts
# straightforward.
MEDIA_ROOT = Path(os.getenv("MEDIA_DIR", str(BASE_DIR / "media"))).resolve()

# Backups must not live inside MEDIA_ROOT because that directory is served
# publicly. On Render, point BACKUP_DIR at a persistent disk mount.
BACKUP_ROOT = Path(os.getenv("BACKUP_DIR", str(BASE_DIR / "backups"))).resolve()
BACKUP_MAX_UPLOAD_BYTES = int(os.getenv("BACKUP_MAX_UPLOAD_BYTES", 1024 * 1024 * 1024))
# Refuse to unpack an archive larger than this during a restore.
BACKUP_MAX_RESTORE_BYTES = int(os.getenv("BACKUP_MAX_RESTORE_BYTES", 4 * 1024 * 1024 * 1024))

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# Built React application. Django serves these files in production.
FRONTEND_DIST = BASE_DIR.parent / "frontend" / "dist"

# ---------------------------------------------------------------------------
# Rate limiting (DRF throttling) - merged with pagination settings above
# ---------------------------------------------------------------------------
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Security headers (production)
# ---------------------------------------------------------------------------
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

if not DEBUG:
    SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL", True)
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# ---------------------------------------------------------------------------
# Environment validation (fail fast on missing critical config in production)
# ---------------------------------------------------------------------------
if not DEBUG:
    _required = ["DJANGO_SECRET_KEY", "DATABASE_URL"]
    _missing = [key for key in _required if not os.getenv(key)]
    if _missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(_missing)}")
    if SECRET_KEY == "insecure-local-development-key-change-me":
        raise RuntimeError("DJANGO_SECRET_KEY must be set to a strong value in production.")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "{levelname} {asctime} {name}: {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
    },
    "root": {"handlers": ["console"], "level": os.getenv("DJANGO_LOG_LEVEL", "INFO")},
}
