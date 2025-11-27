"""Module containing social media trackers' run functions."""

import asyncio

from trackers.config import (
    discord_config,
    discord_guilds,
    reddit_config,
    reddit_subreddits,
    telegram_chats,
    telegram_config,
    twitter_config,
    twitterapiio_config,
)
from trackers.discord import DiscordTracker
from trackers.parser import MessageParser
from trackers.reddit import RedditTracker
from trackers.telegram import TelegramTracker
from trackers.twitter import TwitterTracker
from trackers.twitterapiio import TwitterapiioTracker


def run_discord_tracker():
    """Initialize related arguments and run asynchronous Discord mentions tracker.

    :var config: configuration dictionary for Discord API
    :type config: dict
    :var tracker: custom Discord tracker instance
    :type tracker: :class:`trackers.discord.DiscordTracker`
    """
    config = discord_config()
    tracker = DiscordTracker(
        parse_message_callback=MessageParser().parse,
        discord_config=config,
        guilds_collection=discord_guilds(),
    )
    asyncio.run(
        tracker.run_continuous(
            historical_check_interval=config.get("check_interval") * 60
        )
    )


def run_reddit_tracker():
    """Initialize related arguments and run Reddit mentions tracker.

    :var config: configuration dictionary for Reddit API
    :type config: dict
    :var tracker: custom Reddit tracker instance
    :type tracker: :class:`trackers.reddit.RedditTracker`
    """
    config = reddit_config()
    tracker = RedditTracker(
        parse_message_callback=MessageParser().parse,
        config=config,
        subreddits_to_track=reddit_subreddits(),
    )
    tracker.run(poll_interval_minutes=config.get("poll_interval"))


def run_telegram_tracker():
    """Initialize related arguments and run Telegram mentions tracker.

    :var config: configuration dictionary for Telegram API
    :type config: dict
    :var tracker: custom Telegram tracker instance
    :type tracker: :class:`trackers.telegram.TelegramTracker`
    """
    config = telegram_config()
    tracker = TelegramTracker(
        parse_message_callback=MessageParser().parse,
        config=config,
        chats_collection=telegram_chats(),
    )
    tracker.run(poll_interval_minutes=config.get("poll_interval"))


def run_twitter_tracker():
    """Initialize related arguments and run Twitter mentions tracker.

    :var config: configuration dictionary for X API
    :type config: dict
    :var tracker: custom Twitter tracker instance
    :type tracker: :class:`trackers.twitter.TwitterTracker`
    """
    config = twitter_config()
    tracker = TwitterTracker(
        parse_message_callback=MessageParser().parse, config=config
    )
    tracker.run(poll_interval_minutes=config.get("poll_interval"))


def run_twitterapiio_tracker():
    """Initialize related arguments and run X mentions tracker using TwitterAPI.io.

    :var config: configuration dictionary for TwitterAPI.io
    :type config: dict
    :var tracker: custom TwitterAPI.io tracker instance
    :type tracker: :class:`trackers.twitter.TwitterTracker`
    """
    config = twitterapiio_config()
    tracker = TwitterapiioTracker(
        parse_message_callback=MessageParser().parse, config=config
    )
    tracker.run(poll_interval_minutes=config.get("poll_interval"))


# if __name__ == "__main__":

#     from pathlib import Path

#     from dotenv import load_dotenv

#     load_dotenv(load_dotenv(Path(__file__).parent.parent / ".env"))
#     run_twitter_tracker()
