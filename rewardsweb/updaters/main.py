"""Module containing main class for updaters management."""

from updaters.discord import DiscordUpdater
from updaters.reddit import RedditUpdater
from updaters.telegram import TelegramUpdater
from updaters.twitter import TwitterUpdater

UPDATER_PROVIDERS_REGISTRY = {
    "discord": DiscordUpdater,
    "reddit": RedditUpdater,
    "telegram": TelegramUpdater,
    "twitter": TwitterUpdater,
}


class UpdateProvider:
    """Main updater provider class that delegates to the correct platform updater.

    :var UpdateProvider.name: name of the provider to use
    :type UpdateProvider.name: str
    :var UpdateProvider.user: Django user instance
    :type UpdateProvider.user: class:`django.contrib.auth.models.User`
    :var UpdateProvider._updater_instance: instance of the updater provider
    :type UpdateProvider._updater_instance: :class:`BaseUpdater`
    """

    name = None
    _updater_instance = None

    def __init__(self, platform_name):
        """Initialize the update provider"""
        self.name = platform_name.lower()
        self._updater_instance = self._get_updater_instance()

    def _get_updater_instance(self):
        """Get the updater instance from the registry.

        :var updater_class: updater class derived from class instance's name
        :type updater_class: :class:`updaters.base.BaseUpdater`
        :return: An instance of the updater class.
        :rtype: :class:`updaters.base.BaseUpdater`
        """
        updater_class = UPDATER_PROVIDERS_REGISTRY.get(self.name)
        return updater_class()

    def __getattr__(self, name):
        """Delegate all method calls to the updater instance.

        :param name: The method name to delegate.
        :type name: str
        :return: The method from the updater instance.
        """
        return getattr(self._updater_instance, name)
