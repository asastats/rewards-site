"""Telegram updater."""

from trackers.database import MentionDatabaseManager
from updaters.base import BaseUpdater


class TelegramUpdater(BaseUpdater):
    """Telegram updater."""

    def __init__(self, *args, **kwargs):
        """Initialize updater."""
        super().__init__(*args, **kwargs)
        self.db_manager = MentionDatabaseManager()

    def add_reaction_to_message(self, url, reaction_name):
        """Add reaction to message.

        :param url: URL of the message to react to
        :type url: str
        :param reaction_name: name of the reaction to add (e.g. "duplicate")
        :type reaction_name: str
        """
        raise NotImplementedError

    def add_reply_to_message(self, url, text):
        """Add reply to message.

        :param url: URL of the message to reply to
        :type url: str
        :param text: text to reply with
        :type text: str
        """
        raise NotImplementedError

    def message_from_url(self, url):
        """Retrieve message content from provided Telegram `url`.

        :param url: Telegram URL to get message from
        :type url: str
        :var message_data: Telegram message data from database
        :type message_data: dict
        :return: dictionary with message data
        :rtype: dict
        """
        message_data = self.db_manager.mention_raw_data_by_url(url)

        if message_data:
            return {
                "success": True,
                "content": message_data.get("content", ""),
                "author": message_data.get("contributor", "Unknown"),
                "timestamp": message_data.get("timestamp", ""),
                "message_id": message_data.get("item_id"),
                "raw_data": message_data,
            }
        else:
            return {
                "success": False,
                "error": f"Message not found for URL: {url}",
            }