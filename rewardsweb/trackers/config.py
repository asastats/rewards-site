"""Module containing trackers configuration."""

from utils.helpers import get_env_variable

PLATFORM_CONTEXT_FIELDS = {
    "reddit": "subreddit",
    "twitter": "tweet_author",
    "telegram": "telegram_chat",
    "discord": "discord_channel",
}
REWARDS_API_BASE_URL = get_env_variable(
    "REWARDS_API_BASE_URL", "http://127.0.0.1:8000/api"
)


def discord_config():
    """Return Discord configuration from environment variables.

    :var excluded_channels_str: comma separated list of excluded channels
    :type excluded_channels_str: str
    :var excluded_channels: formatted collection of excluded channel IDs
    :type excluded_channels: list
    :var included_channels_str: comma separated list of included channels
    :type included_channels_str: str
    :var included_channels: formatted collection of included channel IDs
    :type included_channels: list
    :return: Discord configuration dictionary
    :rtype: dict
    """
    excluded_channels_str = get_env_variable("TRACKER_DISCORD_EXCLUDED_CHANNELS", "")
    excluded_channels = [
        int(channel.strip())
        for channel in excluded_channels_str.split(",")
        if channel.strip()
    ]
    included_channels_str = get_env_variable("TRACKER_DISCORD_INCLUDED_CHANNELS", "")
    included_channels = [
        int(channel.strip())
        for channel in included_channels_str.split(",")
        if channel.strip()
    ]

    return {
        "bot_user_id": get_env_variable("TRACKER_DISCORD_BOT_ID", ""),
        "token": get_env_variable("TRACKER_DISCORD_BOT_TOKEN", ""),
        "auto_discover_channels": True,
        "excluded_channel_types": ["voice", "stage", "category"],
        "excluded_channels": excluded_channels,
        "included_channels": included_channels,
    }


def discord_guilds():
    """Return list of Discord guilds/channels to track from environment variable.

    :var guilds_str: comma-separated list of guilds from environment
    :type guilds_str: str
    :return: list of discord guild IDs
    :rtype: list
    """
    guilds_str = get_env_variable("TRACKER_DISCORD_GUILDS", "")
    return [int(guild.strip()) for guild in guilds_str.split(",") if guild.strip()]


def reddit_config():
    """Return Reddit configuration from environment variables.

    :return: Reddit configuration dictionary
    :rtype: dict
    """
    return {
        "client_id": get_env_variable("TRACKER_REDDIT_CLIENT_ID", ""),
        "client_secret": get_env_variable("TRACKER_REDDIT_CLIENT_SECRET", ""),
        "user_agent": get_env_variable(
            "TRACKER_REDDIT_USER_AGENT", "SocialMentionTracker v1.0"
        ),
        "username": get_env_variable("TRACKER_REDDIT_USERNAME", ""),
        "password": get_env_variable("TRACKER_REDDIT_PASSWORD", ""),
    }


def reddit_subreddits():
    """Return list of subreddits to track from environment variable.

    :var subreddits_str: comma-separated list of subreddits from environment
    :type subreddits_str: str
    :return: list of subreddit names
    :rtype: list
    """
    subreddits_str = get_env_variable("TRACKER_REDDIT_SUBREDDITS", "")
    return [sub.strip() for sub in subreddits_str.split(",") if sub.strip()]


def telegram_chats():
    """Return list of Telegram chats to track from environment variable.

    :var chats_str: comma-separated list of chat usernames or IDs from environment
    :type chats_str: str
    :return: list of chat identifiers
    :rtype: list
    """
    chats_str = get_env_variable("TRACKER_TELEGRAM_CHATS", "")
    return [chat.strip() for chat in chats_str.split(",") if chat.strip()]


def telegram_config():
    """Return Telegram configuration from environment variables.

    :return: Telegram configuration dictionary
    :rtype: dict
    """
    return {
        "api_id": get_env_variable("TRACKER_TELEGRAM_API_ID", ""),
        "api_hash": get_env_variable("TRACKER_TELEGRAM_API_HASH", ""),
        "session_name": get_env_variable(
            "TRACKER_TELEGRAM_SESSION_NAME", "telegram_tracker"
        ),
        "bot_username": get_env_variable("TRACKER_TELEGRAM_BOT_USERNAME", "").lower(),
    }


def twitter_config():
    """Return Twitter configuration from environment variables.

    :return: Twitter configuration dictionary
    :rtype: dict
    """
    return {
        "bearer_token": get_env_variable("TRACKER_TWITTER_BEARER_TOKEN", ""),
        "consumer_key": get_env_variable("TRACKER_TWITTER_CONSUMER_KEY", ""),
        "consumer_secret": get_env_variable("TRACKER_TWITTER_CONSUMER_SECRET", ""),
        "access_token": get_env_variable("TRACKER_TWITTER_ACCESS_TOKEN", ""),
        "access_token_secret": get_env_variable(
            "TRACKER_TWITTER_ACCESS_TOKEN_SECRET", ""
        ),
    }
