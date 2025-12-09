"""Django settings module used in production."""

from .base import *

DEBUG = False

ALLOWED_HOSTS = ["*"]

MIDDLEWARE.insert(2, "django.middleware.gzip.GZipMiddleware")

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

SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "file": {
            "level": "WARNING",
            "class": "logging.FileHandler",
            "filename": BASE_DIR.parent.parent.parent / "logs" / "django-warning.log",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["file"],
            "level": "WARNING",
            "propagate": True,
        },
    },
}
