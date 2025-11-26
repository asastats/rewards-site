"""Django settings module used in production."""

from .base import *

DEBUG = False

ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
]

MIDDLEWARE.insert(2, "django.middleware.gzip.GZipMiddleware")
"""
NOTE: nginx setup:

location /static/ {
    alias /path/to/static/;
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_buffers 16 8k;
    gzip_http_version 1.1;
}
"""

CSRF_TRUSTED_ORIGINS = [
    f"https://*.{PROJECT_DOMAIN.split('.', 1)[1]}",
    f"https://{PROJECT_DOMAIN}"
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

SESSION_ENGINE = "django.contrib.sessions.backends.cache"

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

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
