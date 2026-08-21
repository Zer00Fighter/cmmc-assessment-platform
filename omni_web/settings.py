from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DEBUG = os.environ.get("OMNI_DEBUG", "1") == "1"
SECRET_KEY = os.environ.get("OMNI_SECRET_KEY", "development-only-change-me")
if not DEBUG and SECRET_KEY == "development-only-change-me":
    raise RuntimeError("OMNI_SECRET_KEY must be set when OMNI_DEBUG=0.")
ALLOWED_HOSTS = [
    host
    for host in os.environ.get("OMNI_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "webapp",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "webapp.middleware.SecurityHeadersMiddleware",
]
ROOT_URLCONF = "omni_web.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "webapp.context_processors.notification_summary",
            ],
        },
    }
]
WSGI_APPLICATION = "omni_web.wsgi.application"
DATABASES = {
    "default": {
        "ENGINE": os.environ.get("OMNI_DB_ENGINE", "django.db.backends.sqlite3"),
        "NAME": os.environ.get("OMNI_DB_NAME", str(BASE_DIR / "omni.sqlite3")),
        "USER": os.environ.get("OMNI_DB_USER", ""),
        "PASSWORD": os.environ.get("OMNI_DB_PASSWORD", ""),
        "HOST": os.environ.get("OMNI_DB_HOST", ""),
        "PORT": os.environ.get("OMNI_DB_PORT", ""),
    }
}
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LANGUAGE_CODE = "en-us"
TIME_ZONE = "America/Los_Angeles"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_ROOT = BASE_DIR / "private_uploads"
OMNI_SSP_TEMPLATE = os.environ.get("OMNI_SSP_TEMPLATE", "")
EMAIL_BACKEND = os.environ.get(
    "OMNI_EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = os.environ.get("OMNI_EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.environ.get("OMNI_EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("OMNI_EMAIL_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("OMNI_EMAIL_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("OMNI_EMAIL_USE_TLS", "1") == "1"
DEFAULT_FROM_EMAIL = os.environ.get("OMNI_DEFAULT_FROM_EMAIL", "Omni by R!SC")
OMNI_EMAIL_ENABLED = os.environ.get("OMNI_EMAIL_ENABLED", "0") == "1"
OMNI_BASE_URL = os.environ.get("OMNI_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
OMNI_BACKUP_DIR = Path(os.environ.get("OMNI_BACKUP_DIR", str(BASE_DIR / "local_backups")))
OMNI_RESTORE_STAGING_DIR = Path(os.environ.get(
    "OMNI_RESTORE_STAGING_DIR", str(BASE_DIR / "local_restore_staging")
))
OMNI_BACKUP_RETENTION_DAYS = int(os.environ.get("OMNI_BACKUP_RETENTION_DAYS", "30"))
OMNI_LOGIN_FAILURE_LIMIT = int(os.environ.get("OMNI_LOGIN_FAILURE_LIMIT", "5"))
OMNI_LOGIN_LOCKOUT_MINUTES = int(os.environ.get("OMNI_LOGIN_LOCKOUT_MINUTES", "15"))
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/accounts/login/"
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_SSL_REDIRECT = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_HSTS_SECONDS = 31_536_000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG
SECURE_REFERRER_POLICY = "same-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
FILE_UPLOAD_PERMISSIONS = 0o600
DATA_UPLOAD_MAX_MEMORY_SIZE = 30 * 1024 * 1024
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"standard": {"format": "{asctime} {levelname} {name} {message}", "style": "{"}},
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "standard"},
        "file": {
            "class": "logging.handlers.RotatingFileHandler", "formatter": "standard",
            "filename": str(BASE_DIR / "logs" / "omni.log"), "maxBytes": 5_000_000,
            "backupCount": 5,
        },
    },
    "loggers": {
        "django.request": {"handlers": ["console", "file"], "level": "WARNING", "propagate": False},
        "webapp": {"handlers": ["console", "file"], "level": "INFO", "propagate": False},
    },
}
(BASE_DIR / "logs").mkdir(exist_ok=True)
