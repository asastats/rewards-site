"""Django settings module used in development."""

from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

# # debug_toolbar
INSTALLED_APPS += [
    "debug_toolbar",
]
MIDDLEWARE.insert(3, "debug_toolbar.middleware.DebugToolbarMiddleware")
INTERNAL_IPS = ("127.0.0.1",)
# # debug_toolbar

# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

# # NOTE: db-based tests can't be (yet) done using database setting
#         involving "service" and "passfile" options
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": get_env_variable("DATABASE_NAME", "test"),
        "USER": get_env_variable("DATABASE_USER", "test"),
        "PASSWORD": get_env_variable("DATABASE_PASSWORD", "test"),
        "HOST": get_env_variable("DATABASE_HOST", default="127.0.0.1"),
        "PORT": get_env_variable("DATABASE_PORT", default="5432"),
    }
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    }
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {
        "allauth": {
            "handlers": ["console"],
            "level": "DEBUG",
        }
    },
}

LIVE_TEST_SERVER_ADDRESS = get_env_variable(
    "DJANGO_LIVE_TEST_SERVER_ADDRESS", "0.0.0.0:8081"
)

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

ISSUE_TRACKER_NAME = "channel"  # "rewards-site" "test"
