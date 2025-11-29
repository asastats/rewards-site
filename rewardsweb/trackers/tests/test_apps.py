"""Testing module for trackers app apps module."""

from django.apps import AppConfig

from trackers.apps import TrackersConfig


class TestWalletauthApps:
    """Testing class for :py:mod:`trackers.apps` module."""

    # # TrackersConfig
    def test_trackers_apps_trackersconfig_is_subclass_of_appconfig(self):
        assert issubclass(TrackersConfig, AppConfig)

    def test_trackers_apps_trackersconfig_sets_name(self):
        assert TrackersConfig.name == "trackers"
