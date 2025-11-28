"""Module containing trackers app configuration."""

from django.apps import AppConfig


class TrackersConfig(AppConfig):
    """Main class for core application.

    :var TrackersConfig.name: app name
    :type TrackersConfig.name: str
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "trackers"
