"""Discord updater."""

import logging
import re

import requests

from rewardsbot.config import DISCORD_TOKEN, GUILD_IDS
from updaters.base import BaseUpdater
from utils.constants.core import DISCORD_EMOJIS

logger = logging.getLogger(__name__)


class DiscordUpdater(BaseUpdater):
    """Discord updater."""

    def __init__(self, *args, **kwargs):
        """Initialize updater."""
        super().__init__(*args, **kwargs)
        self.guild_ids = GUILD_IDS
        self.discord_token = DISCORD_TOKEN

    def _parse_discord_url(self, url):
        """Return Discord server, channel, and message IDs parsed from provided `url`.

        :param url: URL of the Discord message to validate
        :type url: str
        :var pattern: Discord URL regex pattern
        :type pattern: str
        :var match: regex match instance
        :type match: :class:`re.Match`
        :var guild_id: ID of the Discord server/guild containing the message
        :type guild_id: str
        :var channel_id: ID of the channel containing the message
        :type channel_id: str
        :var message_id: ID of the message to react to
        :type message_id: str
        :return: two-tuple
        """
        pattern = r"^https://discord\.com/channels/(\d+)/(\d+)/(\d+)$"
        match = re.match(pattern, url)
        if not match:
            return False, False

        guild_id, channel_id, message_id = match.groups()
        if guild_id not in self.guild_ids.split(","):
            return False, False

        return channel_id, message_id

    def add_reaction_to_message(self, url, reaction_name):
        """Add a reaction to an existing Discord message

        :param url: Discord message's URL
        :type url: str
        :param reaction_name: name of the reaction to add (e.g. "duplicate")
        :type reaction_name: str
        :var channel_id: ID of the channel containing the message
        :type channel_id: str
        :var message_id: ID of the message to react to
        :type message_id: str
        :var headers: headers instance carrying bot token
        :type headers: dict
        :var api_url: fully formatted API URL to add reaction to the message
        :type api_url: str
        :var response: HTTP response instance
        :type response: :class:`requests.Response`
        :return: Boolean
        """
        channel_id, message_id = self._parse_discord_url(url)
        if not channel_id:
            return False

        emoji = DISCORD_EMOJIS.get(reaction_name)
        if not emoji:
            logger.error(f"Invalid reaction name: {reaction_name}")
            return False

        headers = {"Authorization": f"Bot {self.discord_token}"}
        url = (
            f"https://discord.com/api/v10/channels/{channel_id}/"
            f"messages/{message_id}/reactions/{emoji}/@me"
        )
        response = requests.put(url, headers=headers)
        if response.status_code == 204:
            logger.info(f"Emoji {reaction_name} added successfully!")
            return True

        else:
            logger.error(
                f"Failed to add reaction: {response.status_code} - {response.text}"
            )
            return False

    def add_reply_to_message(self, url, comment):
        """Add a reply to an existing Discord message

        :param url: Discord message URL
        :type url: str
        :param comment: reply message content
        :type comment: str
        :var headers: headers instance carrying bot token and content type
        :type headers: dict
        :var api_url: fully formatted API URL to create message in channel
        :type api_url: str
        :var payload: request payload containing reply message data
        :type payload: dict
        :var response: HTTP response instance
        :type response: :class:`requests.Response`
        :return: Boolean indicating success
        :rtype: bool
        """
        channel_id, message_id = self._parse_discord_url(url)
        if not channel_id:
            return False

        headers = {
            "Authorization": f"Bot {self.discord_token}",
            "Content-Type": "application/json",
        }
        api_url = f"https://discord.com/api/v10/channels/{channel_id}/messages"

        payload = {
            "content": comment,
            "message_reference": {"channel_id": channel_id, "message_id": message_id},
        }

        response = requests.post(api_url, headers=headers, json=payload)
        if response.status_code == 200:
            logger.info(f"Reply added successfully to message {message_id}!")
            return True
        else:
            logger.error(
                f"Failed to add reply: {response.status_code} - {response.text}"
            )
            return False

    def message_from_url(self, url):
        """Retrieve message content from provided Discord `url`.

        :var channel_id: ID of the channel containing the message
        :type channel_id: str
        :param message_id: ID of the message to react to
        :type message_id: str
        :var headers: headers instance carrying bot token
        :type headers: dict
        :var api_url: fully formatted API URL to retrieve message
        :type api_url: str
        :var response: HTTP response instance
        :type response: :class:`requests.Response`
        :var message_data: Discord message data
        :type message_data: cict
        :return: Boolean
        """
        channel_id, message_id = self._parse_discord_url(url)
        if not channel_id:
            return {"success": False, "error": "Invalid URL"}

        headers = {"Authorization": f"Bot {self.discord_token}"}
        api_url = (
            f"https://discord.com/api/v10/channels/{channel_id}/messages/{message_id}"
        )

        response = requests.get(api_url, headers=headers)
        if response.status_code == 200:
            message_data = response.json()
            return {
                "success": True,
                "content": message_data.get("content", ""),
                "author": message_data.get("author", {}).get("username", "Unknown"),
                "timestamp": message_data.get("timestamp", ""),
                "channel_id": channel_id,
                "message_id": message_id,
                "raw_data": message_data,
            }
        else:
            return {
                "success": False,
                "error": f"API Error: {response.status_code}",
                "response_text": response.text,
            }
