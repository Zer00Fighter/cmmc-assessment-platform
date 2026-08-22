from pathlib import Path

from django.conf import settings
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


def deployment_readiness():
    checks = []

    def add(name, ok, detail):
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    add("Debug disabled", not settings.DEBUG, "Required before public deployment")
    add(
        "Production secret",
        settings.SECRET_KEY != "development-only-change-me"
        and len(settings.SECRET_KEY) >= 50,
        "Private and at least 50 characters",
    )
    add(
        "Allowed hosts",
        bool(settings.ALLOWED_HOSTS) and "*" not in settings.ALLOWED_HOSTS,
        ", ".join(settings.ALLOWED_HOSTS),
    )
    add(
        "HTTPS base URL",
        settings.OMNI_BASE_URL.startswith("https://"),
        settings.OMNI_BASE_URL,
    )
    add(
        "Secure cookies",
        settings.SESSION_COOKIE_SECURE and settings.CSRF_COOKIE_SECURE,
        "Session and CSRF cookies",
    )
    add(
        "Session timeout",
        0 < settings.SESSION_COOKIE_AGE <= 8 * 60 * 60,
        f"{settings.SESSION_COOKIE_AGE // 60} minutes",
    )
    add(
        "HSTS",
        settings.SECURE_HSTS_SECONDS >= 31_536_000,
        f"{settings.SECURE_HSTS_SECONDS} seconds",
    )
    add(
        "Proxy trust explicit",
        not settings.SECURE_PROXY_SSL_HEADER or settings.OMNI_TRUST_PROXY_HEADERS,
        "Configured explicitly",
    )
    add(
        "PostgreSQL",
        settings.DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql",
        settings.DATABASES["default"]["ENGINE"],
    )
    add(
        "Email enabled",
        settings.OMNI_EMAIL_ENABLED and bool(settings.EMAIL_HOST_USER),
        "SMTP configured" if settings.OMNI_EMAIL_ENABLED else "Disabled",
    )
    media = Path(settings.MEDIA_ROOT)
    add("Private storage", media.exists() and media.is_dir(), str(media))
    backup = Path(settings.OMNI_BACKUP_DIR)
    add("Backup destination", backup.exists() and backup.is_dir(), str(backup))
    executor = MigrationExecutor(connection)
    add(
        "Migrations applied",
        not executor.migration_plan(executor.loader.graph.leaf_nodes()),
        "Database schema",
    )
    return checks
