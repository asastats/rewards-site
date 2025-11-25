"""Testing module for :py:mod:`trackers.config` module."""

from trackers.config import (
    PLATFORM_CONTEXT_FIELDS,
    discord_config,
    discord_guilds,
    reddit_config,
    reddit_subreddits,
    telegram_chats,
    telegram_config,
    twitter_config,
)


class TestTrackersConfig:
    """Testing class for :py:mod:`trackers.config` module."""

    # PLATFORM_CONTEXT_FIELDS
    def test_trackers_database_platform_context_fields(self):
        expected_fields = {
            "reddit": "subreddit",
            "twitter": "tweet_author",
            "telegram": "telegram_chat",
            "discord": "discord_channel",
        }
        assert PLATFORM_CONTEXT_FIELDS == expected_fields

    # discord_config
    def test_trackers_config_discord_config_for_empty_environment_variables(
        self, mocker
    ):
        mocker.patch("trackers.config.get_env_variable", return_value="")
        result = discord_config()

        expected_config = {
            "bot_user_id": "",
            "token": "",
            "auto_discover_channels": True,
            "excluded_channel_types": ["voice", "stage", "category"],
            "excluded_channels": [],
            "included_channels": [],
        }
        assert result == expected_config

    def test_trackers_config_discord_config_functionality(self, mocker):
        mock_env = mocker.patch("trackers.config.get_env_variable")
        mock_env.side_effect = lambda key, default=None: {
            "TRACKER_DISCORD_EXCLUDED_CHANNELS": "12345,6789",
            "TRACKER_DISCORD_INCLUDED_CHANNELS": "1234567",
            "TRACKER_DISCORD_BOT_ID": "bot_id",
            "TRACKER_DISCORD_BOT_TOKEN": "bot_token",
        }.get(key, default)
        result = discord_config()
        expected_config = {
            "bot_user_id": "bot_id",
            "token": "bot_token",
            "auto_discover_channels": True,
            "excluded_channel_types": ["voice", "stage", "category"],
            "excluded_channels": [12345, 6789],
            "included_channels": [1234567],
        }
        assert result == expected_config
        calls = [
            mocker.call("TRACKER_DISCORD_EXCLUDED_CHANNELS", ""),
            mocker.call("TRACKER_DISCORD_INCLUDED_CHANNELS", ""),
            mocker.call("TRACKER_DISCORD_BOT_ID", ""),
            mocker.call("TRACKER_DISCORD_BOT_TOKEN", ""),
        ]
        mock_env.assert_has_calls(calls, any_order=True)
        assert mock_env.call_count == 4

    # discord_guilds
    def test_trackers_config_discord_guilds_functionality(self, mocker):
        mock_env = mocker.patch("trackers.config.get_env_variable")
        mock_env.return_value = "1, 2, 3"

        result = discord_guilds()

        expected_list = [1, 2, 3]
        assert result == expected_list

    def test_trackers_config_discord_guilds_empty(self, mocker):
        mocker.patch("trackers.config.get_env_variable", return_value="")

        result = discord_guilds()

        assert result == []

    # reddit_config
    def test_trackers_config_reddit_config_functionality(self, mocker):
        mock_env = mocker.patch("trackers.config.get_env_variable")
        mock_env.side_effect = lambda key, default=None: {
            "TRACKER_REDDIT_CLIENT_ID": "test_client",
            "TRACKER_REDDIT_CLIENT_SECRET": "test_secret",
            "TRACKER_REDDIT_USER_AGENT": "test_agent",
            "TRACKER_REDDIT_USERNAME": "test_user",
            "TRACKER_REDDIT_PASSWORD": "test_pass",
        }.get(key, default)
        result = reddit_config()
        expected_config = {
            "client_id": "test_client",
            "client_secret": "test_secret",
            "user_agent": "test_agent",
            "username": "test_user",
            "password": "test_pass",
        }
        assert result == expected_config
        calls = [
            mocker.call("TRACKER_REDDIT_CLIENT_ID", ""),
            mocker.call("TRACKER_REDDIT_CLIENT_SECRET", ""),
            mocker.call("TRACKER_REDDIT_USER_AGENT", "SocialMentionTracker v1.0"),
            mocker.call("TRACKER_REDDIT_USERNAME", ""),
            mocker.call("TRACKER_REDDIT_PASSWORD", ""),
        ]
        mock_env.assert_has_calls(calls, any_order=True)
        assert mock_env.call_count == 5

    # reddit_subreddits
    def test_trackers_config_reddit_subreddits_functionality(self, mocker):
        mock_env = mocker.patch("trackers.config.get_env_variable")
        mock_env.return_value = "python, test, learnprogramming"

        result = reddit_subreddits()

        expected_list = ["python", "test", "learnprogramming"]
        assert result == expected_list

    def test_trackers_config_reddit_subreddits_empty(self, mocker):
        mocker.patch("trackers.config.get_env_variable", return_value="")

        result = reddit_subreddits()

        assert result == []

    # telegram_chats
    def test_trackers_config_telegram_chats_functionality(self, mocker):
        mock_env = mocker.patch("trackers.config.get_env_variable")
        mock_env.return_value = "group1, group2, @channel1"

        result = telegram_chats()

        expected_list = ["group1", "group2", "@channel1"]
        assert result == expected_list

    def test_trackers_config_telegram_chats_empty(self, mocker):
        mocker.patch("trackers.config.get_env_variable", return_value="")

        result = telegram_chats()

        assert result == []

    # telegram_config
    def test_trackers_config_telegram_config_functionality(self, mocker):
        mock_env = mocker.patch("trackers.config.get_env_variable")
        mock_env.side_effect = lambda key, default=None: {
            "TRACKER_TELEGRAM_API_ID": "test_api_id",
            "TRACKER_TELEGRAM_API_HASH": "test_api_hash",
            "TRACKER_TELEGRAM_SESSION_NAME": "test_session",
            "TRACKER_TELEGRAM_BOT_USERNAME": "TestBot",
        }.get(key, default)
        result = telegram_config()
        expected_config = {
            "api_id": "test_api_id",
            "api_hash": "test_api_hash",
            "session_name": "test_session",
            "bot_username": "testbot",  # Should be lowercased
        }
        assert result == expected_config
        calls = [
            mocker.call("TRACKER_TELEGRAM_API_ID", ""),
            mocker.call("TRACKER_TELEGRAM_API_HASH", ""),
            mocker.call("TRACKER_TELEGRAM_SESSION_NAME", "telegram_tracker"),
            mocker.call("TRACKER_TELEGRAM_BOT_USERNAME", ""),
        ]
        mock_env.assert_has_calls(calls, any_order=True)
        assert mock_env.call_count == 4

    # twitter_config
    def test_trackers_config_twitter_config_functionality(self, mocker):
        mock_env = mocker.patch("trackers.config.get_env_variable")
        mock_env.side_effect = lambda key, default=None: {
            "TRACKER_TWITTER_BEARER_TOKEN": "test_bearer",
            "TRACKER_TWITTER_CONSUMER_KEY": "test_consumer",
            "TRACKER_TWITTER_CONSUMER_SECRET": "test_secret",
            "TRACKER_TWITTER_ACCESS_TOKEN": "test_token",
            "TRACKER_TWITTER_ACCESS_TOKEN_SECRET": "test_token_secret",
        }.get(key, default)

        result = twitter_config()

        expected_config = {
            "bearer_token": "test_bearer",
            "consumer_key": "test_consumer",
            "consumer_secret": "test_secret",
            "access_token": "test_token",
            "access_token_secret": "test_token_secret",
        }
        assert result == expected_config
