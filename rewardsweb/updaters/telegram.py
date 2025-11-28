"""Module containing class for retrieving and adding Reddit post and comments."""

from datetime import datetime, timezone

from trackers.models import Mention
from updaters.base import BaseUpdater


class TelegramUpdater(BaseUpdater):
    """Main class for retrieving and adding Telegram messages."""

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
        :var mention: Telegram mention data from database
        :type mention: :class:`trackers.models.Mention`
        :return: dictionary with message data
        :rtype: dict
        """
        mention = Mention.objects.get_mention_by_url(url)

        if mention:
            timestamp = mention.raw_data.get("timestamp")
            if timestamp:
                dt_object = datetime.fromtimestamp(timestamp, tz=timezone.utc)
                timestamp_str = dt_object.isoformat()
            else:
                timestamp_str = ""
            return {
                "success": True,
                "content": mention.raw_data.get("content", ""),
                "author": mention.raw_data.get("contributor", "Unknown"),
                "timestamp": timestamp_str,
                "message_id": mention.item_id,
                "raw_data": mention.raw_data,
            }
        else:
            return {
                "success": False,
                "error": f"Message not found for URL: {url}",
            }
