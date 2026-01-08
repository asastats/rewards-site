"""Django settings module used in production."""

from .base import *

DEBUG = False

ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
    "144.91.85.65",
    "rewards.asastats.com",
]

MIDDLEWARE.insert(2, "django.middleware.gzip.GZipMiddleware")

CSRF_TRUSTED_ORIGINS = [
    f"https://*.{PROJECT_DOMAIN.split('.', 1)[1]}",
    f"https://{PROJECT_DOMAIN}",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "OPTIONS": {
            "service": "rewardsweb_service",
            "passfile": str(Path.home() / ".pgpass"),
        },
    }
}

MESSAGE_STORAGE = "django.contrib.messages.storage.session.SessionStorage"

COOKIE_ARGUMENTS = {"domain": PROJECT_DOMAIN}

CSRF_COOKIE_SAMESITE = "Lax"  # or 'Strict'
SESSION_COOKIE_SAMESITE = "Lax"

ACCOUNT_DEFAULT_HTTP_PROTOCOL = "https"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "file": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": BASE_DIR.parent.parent.parent / "logs" / "django-warning.log",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["file"],
            "level": "INFO",
            "propagate": True,
        },
    },
}

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
