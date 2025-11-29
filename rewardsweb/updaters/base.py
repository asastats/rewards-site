"""Base classes for updating social media messages."""

from abc import ABC, abstractmethod


class BaseUpdater(ABC):
    """Base class for all social media message updaters."""

    @abstractmethod
    def add_reaction_to_message(self, url, reaction_name):
        """Add reaction to message.

        :param url: URL of the message to react to
        :type url: str
        :param reaction_name: name of the reaction to add (e.g. "duplicate")
        :type reaction_name: str
        """
        pass

    @abstractmethod
    def add_reply_to_message(self, url, text):
        """Add reply to message.

        :param url: URL of the message to reply to
        :type url: str
        :param text: text to reply with
        :type text: str
        """
        pass

    @abstractmethod
    def message_from_url(self, url):
        """Get message from URL.

        :param url: URL to get message from
        :type url: str
        """
        pass
