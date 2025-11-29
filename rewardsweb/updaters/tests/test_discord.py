"""Testing module for :py:mod:`updaters.discord` module."""

from unittest import mock

import pytest

from rewardsbot.config import DISCORD_TOKEN, GUILD_IDS
from updaters.discord import DiscordUpdater
from utils.constants.core import DISCORD_EMOJIS


class TestUpdatersDiscordDiscordupdater:
    """Testing class for :py:mod:`updaters.discord.DiscordUpdater` class."""

    def setup_method(self):
        """Set up test method."""
        self.updater = DiscordUpdater()

    # # _parse_discord_url
    @pytest.mark.parametrize(
        "url",
        [
            "http://discord.com/channels/906917846754418770/1028021510453084161/1353382023309562020",
            "https://github.com/asastats/channel/issues/587",
            "https://trello.com/c/mgeYvP0Z",
            "https://twitter.com/username/status/1507097109320769539",
            "https://www.reddit.com/r/asastats/comments/u0uvjp/new_staking_platform_will_you_add_it/",
            "http://discord.com/channels/1028021510453084161/1353382023309562020",
            "https://discord.com/channels/a/1020298428061847612/1022852395757211728",
            "https://discord.com/channels/906917846754418770/b/1022852395757211728",
            "https://discord.com/channels/906917846754418770/1020298428061847612/c",
            "https://discord.com/channels/906917846754418770/1020298428061847612/1022852395757211728a",
            "https://discord.com/channels/906917846754418770/1028021510453084161/",
            "https://example.com/channels/906917846754418770/1028021510453084161/1353382023309562020",
        ],
    )
    def test_updaters_discord_discordupdater_parse_discord_url_for_wrong_pattern(
        self, url
    ):
        assert self.updater._parse_discord_url(url) == (False, False)

    def test_updaters_discord_discordupdater_parse_discord_url_for_wrong_server(self):
        url = "https://discord.com/channels/906917846754418771/1028021510453084161/1353382117823746178"
        assert self.updater._parse_discord_url(url) == (False, False)

    def test_updaters_discord_discordupdater_parse_discord_url_for_valid_message(self):
        url = "https://discord.com/channels/906917846754418770/1028021510453084161/1353382023309562020"
        returned = self.updater._parse_discord_url(url)
        assert returned == (
            "1028021510453084161",
            "1353382023309562020",
        )

    # # add_reaction_to_message
    def test_updaters_discord_discordupdater_add_reaction_to_message_for_wrong_reaction(
        self,
    ):
        channel_id, message_id, reaction_name = (
            "1028021510453084161",
            "1353382023309562020",
            "foobar",
        )
        url = (
            f"https://discord.com/channels/906917846754418770/{channel_id}/{message_id}"
        )
        with mock.patch("updaters.discord.requests.put") as mocked_put, mock.patch(
            "updaters.discord.logger"
        ) as mocked_logger:
            returned = self.updater.add_reaction_to_message(url, reaction_name)
            assert returned is False
            mocked_put.assert_not_called()
            mocked_logger.assert_not_called()

    def test_updaters_discord_discordupdater_add_reaction_to_message_for_wrong_url(
        self,
    ):
        channel_id, message_id, reaction_name = (
            "1028021510453084161",
            "1353382023309562020",
            "duplicate",
        )
        url = f"https://discord.com/channels/{channel_id}/{message_id}"
        with mock.patch("updaters.discord.requests.put") as mocked_put, mock.patch(
            "updaters.discord.logger"
        ) as mocked_logger:
            returned = self.updater.add_reaction_to_message(url, reaction_name)
            assert returned is False
            mocked_put.assert_not_called()
            mocked_logger.assert_not_called()

    def test_updaters_discord_discordupdater_add_reaction_to_message_for_error(self):
        channel_id, message_id, reaction_name = (
            "1028021510453084161",
            "1353382023309562020",
            "duplicate",
        )
        url = (
            f"https://discord.com/channels/906917846754418770/{channel_id}/{message_id}"
        )
        headers = {"Authorization": "Bot " + DISCORD_TOKEN}
        api_url = (
            f"https://discord.com/api/v10/channels/{channel_id}/"
            f"messages/{message_id}/reactions/{DISCORD_EMOJIS[reaction_name]}/@me"
        )
        with mock.patch("updaters.discord.requests.put") as mocked_put, mock.patch(
            "updaters.discord.logger"
        ) as mocked_logger:
            mocked_put.return_value.status_code = 505
            mocked_put.return_value.text = "error text"
            returned = self.updater.add_reaction_to_message(url, reaction_name)
            assert returned is False
            mocked_put.assert_called_once_with(api_url, headers=headers)
            mocked_logger.error.assert_called_once_with(
                "Failed to add reaction: 505 - error text"
            )

    def test_updaters_discord_discordupdater_add_reaction_to_message_functionality(
        self,
    ):
        channel_id, message_id, reaction_name = (
            "1028021510453084161",
            "1353382023309562020",
            "wontfix",
        )
        url = (
            f"https://discord.com/channels/906917846754418770/{channel_id}/{message_id}"
        )
        headers = {"Authorization": "Bot " + DISCORD_TOKEN}
        api_url = (
            f"https://discord.com/api/v10/channels/{channel_id}/"
            f"messages/{message_id}/reactions/{DISCORD_EMOJIS[reaction_name]}/@me"
        )
        with mock.patch("updaters.discord.requests.put") as mocked_put, mock.patch(
            "updaters.discord.logger"
        ) as mocked_logger:
            mocked_put.return_value.status_code = 204
            returned = self.updater.add_reaction_to_message(url, reaction_name)
            assert returned is True
            mocked_put.assert_called_once_with(api_url, headers=headers)
            mocked_logger.info.assert_called_once_with(
                f"Emoji {reaction_name} added successfully!"
            )

    # # add_reply_to_message
    def test_updaters_discord_discordupdater_add_reply_to_message_for_wrong_url(self):
        """Test add_reply_to_message returns False for invalid Discord URL."""
        message_id, comment = ("1353382023309562020", "This is a test reply")
        url = f"https://discord.com/channels/906917846754418770/{message_id}"
        with mock.patch("updaters.discord.requests.post") as mocked_post, mock.patch(
            "updaters.discord.logger"
        ) as mocked_logger:
            returned = self.updater.add_reply_to_message(url, comment)
            assert returned is False
            mocked_post.assert_not_called()
            mocked_logger.assert_not_called()

    def test_updaters_discord_discordupdater_add_reply_to_message_for_api_error(self):
        """Test add_reply_to_message handles API errors correctly."""
        guild_id, channel_id, message_id, comment = (
            GUILD_IDS.split(",")[0],
            "1028021510453084161",
            "1353382023309562020",
            "This is a test reply",
        )
        url = f"https://discord.com/channels/{guild_id}/{channel_id}/{message_id}"
        headers = {
            "Authorization": "Bot " + DISCORD_TOKEN,
            "Content-Type": "application/json",
        }
        api_url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
        payload = {
            "content": comment,
            "message_reference": {"channel_id": channel_id, "message_id": message_id},
        }
        with mock.patch("updaters.discord.requests.post") as mocked_post, mock.patch(
            "updaters.discord.logger"
        ) as mocked_logger:
            mocked_post.return_value.status_code = 403
            mocked_post.return_value.text = "Forbidden"
            returned = self.updater.add_reply_to_message(url, comment)
            assert returned is False
            mocked_post.assert_called_once_with(api_url, headers=headers, json=payload)
            mocked_logger.error.assert_called_once_with(
                "Failed to add reply: 403 - Forbidden"
            )

    def test_updaters_discord_discordupdater_add_reply_to_message_functionality(self):
        """Test add_reply_to_message successfully adds reply."""
        guild_id, channel_id, message_id, comment = (
            GUILD_IDS.split(",")[0],
            "1028021510453084161",
            "1353382023309562020",
            "This is a test reply",
        )
        url = f"https://discord.com/channels/{guild_id}/{channel_id}/{message_id}"
        headers = {
            "Authorization": "Bot " + DISCORD_TOKEN,
            "Content-Type": "application/json",
        }
        api_url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
        payload = {
            "content": comment,
            "message_reference": {"channel_id": channel_id, "message_id": message_id},
        }
        with mock.patch("updaters.discord.requests.post") as mocked_post, mock.patch(
            "updaters.discord.logger"
        ) as mocked_logger:
            mocked_post.return_value.status_code = 200
            returned = self.updater.add_reply_to_message(url, comment)
            assert returned is True
            mocked_post.assert_called_once_with(api_url, headers=headers, json=payload)
            mocked_logger.info.assert_called_once_with(
                f"Reply added successfully to message {message_id}!"
            )

    def test_updaters_discord_discordupdater_add_reply_to_message_with_different_codes(
        self,
    ):
        """Test add_reply_to_message handles various HTTP status codes."""
        guild_id, channel_id, message_id, comment = (
            GUILD_IDS.split(",")[0],
            "1028021510453084161",
            "1353382023309562020",
            "This is a test reply",
        )
        url = f"https://discord.com/channels/{guild_id}/{channel_id}/{message_id}"

        # Test with 201 status code (should return False as we expect 200)
        with mock.patch("updaters.discord.requests.post") as mocked_post, mock.patch(
            "updaters.discord.logger"
        ) as mocked_logger:
            mocked_post.return_value.status_code = 201
            mocked_post.return_value.text = "Created"
            returned = self.updater.add_reply_to_message(url, comment)
            assert returned is False
            mocked_logger.error.assert_called_once()

    # # message_from_url
    def test_updaters_discord_discordupdater_message_from_url_for_wrong_url(self):
        channel_id, message_id = "1028021510453084161", "1353382023309562020"
        url = f"https://discord.com/channels/{channel_id}/{message_id}"
        with mock.patch("updaters.discord.requests.get") as mocked_get:
            returned = self.updater.message_from_url(url)
            assert returned == {"success": False, "error": "Invalid URL"}
            mocked_get.assert_not_called()

    def test_updaters_discord_discordupdater_message_from_url_for_error(self):
        channel_id, message_id = "1028021510453084161", "1353382023309562020"
        url = (
            f"https://discord.com/channels/906917846754418770/{channel_id}/{message_id}"
        )
        headers = {"Authorization": "Bot " + DISCORD_TOKEN}
        api_url = (
            f"https://discord.com/api/v10/channels/{channel_id}/messages/{message_id}"
        )
        with mock.patch("updaters.discord.requests.get") as mocked_get:
            mocked_get.return_value.status_code = 505
            mocked_get.return_value.text = "error text"
            returned = self.updater.message_from_url(url)
            assert returned == {
                "success": False,
                "error": "API Error: 505",
                "response_text": "error text",
            }
            mocked_get.assert_called_once_with(api_url, headers=headers)

    def test_updaters_discord_discordupdater_message_from_url_for_deafult_message_data(
        self,
    ):
        channel_id, message_id = "1028021510453084161", "1353382023309562020"
        url = (
            f"https://discord.com/channels/906917846754418770/{channel_id}/{message_id}"
        )
        headers = {"Authorization": "Bot " + DISCORD_TOKEN}
        api_url = (
            f"https://discord.com/api/v10/channels/{channel_id}/messages/{message_id}"
        )
        message_data = {
            "channel_id": channel_id,
            "message_id": message_id,
        }
        with mock.patch("updaters.discord.requests.get") as mocked_get:
            mocked_get.return_value.status_code = 200
            mocked_get.return_value.json.return_value = message_data
            returned = self.updater.message_from_url(url)
            assert returned == {
                "success": True,
                "contribution": "",
                "author": "Unknown",
                "timestamp": "",
                "channel_id": channel_id,
                "message_id": message_id,
                "raw_data": message_data,
            }
            mocked_get.assert_called_once_with(api_url, headers=headers)

    def test_updaters_discord_discordupdater_message_from_url_functionality(self):
        channel_id, message_id = "1028021510453084161", "1353382023309562020"
        url = (
            f"https://discord.com/channels/906917846754418770/{channel_id}/{message_id}"
        )
        headers = {"Authorization": "Bot " + DISCORD_TOKEN}
        api_url = (
            f"https://discord.com/api/v10/channels/{channel_id}/messages/{message_id}"
        )
        message_data = {
            "content": "message content",
            "author": {"username": "Author"},
            "timestamp": "message timestamp",
            "channel_id": channel_id,
            "message_id": message_id,
        }
        with mock.patch("updaters.discord.requests.get") as mocked_get:
            mocked_get.return_value.status_code = 200
            mocked_get.return_value.json.return_value = message_data
            returned = self.updater.message_from_url(url)
            assert returned == {
                "success": True,
                "contribution": "message content",
                "author": "Author",
                "timestamp": "message timestamp",
                "channel_id": channel_id,
                "message_id": message_id,
                "raw_data": message_data,
            }
            mocked_get.assert_called_once_with(api_url, headers=headers)
