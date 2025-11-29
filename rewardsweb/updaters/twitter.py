"""Module containing class for retrieving and adding X/Twitter messages."""

from trackers.models import Mention
from updaters.base import BaseUpdater


class TwitterUpdater(BaseUpdater):
    """Main class for retrieving and adding X/Twitter messages."""

    def add_reaction_to_message(self, url, reaction_name):
        """Add reaction to message.

        NOTE: not implemented yet

        :param url: URL of the message to react to
        :type url: str
        :param reaction_name: name of the reaction to add (e.g. "duplicate")
        :type reaction_name: str
        """
        return None

    def add_reply_to_message(self, url, text):
        """Add reply to message.

        NOTE: not implemented yet

        :param url: URL of the message to reply to
        :type url: str
        :param text: text to reply with
        :type text: str
        """
        return None

    def message_from_url(self, url):
        """Retrieve message content from provided Twitter `url`.

        :param url: twitter URL to get message from
        :type url: str
        :return: dictionary with message data
        :rtype: dict
        """
        return Mention.objects.message_from_url(url)
