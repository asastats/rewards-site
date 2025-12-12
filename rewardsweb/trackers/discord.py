"""Module containing class for tracking mentions on Discord across multiple servers."""

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime, timedelta

from discord import Client, Forbidden, HTTPException, Intents

from trackers.base import BaseAsyncMentionTracker


class IDiscordClientWrapper(ABC):
    """Abstract interface for Discord client to improve testability."""

    @abstractmethod
    async def start(self, token):
        """Start the Discord client.

        :param token: Discord bot token
        :type token: str
        """
        pass

    @abstractmethod
    async def close(self):
        """Close the Discord client."""
        pass

    @abstractmethod
    def is_ready(self):
        """Check if client is ready.

        :return: whether client is ready
        :rtype: bool
        """
        pass

    @abstractmethod
    def is_closed(self):
        """Check if client is closed.

        :return: whether client is closed
        :rtype: bool
        """
        pass

    @abstractmethod
    def get_guild(self, guild_id):
        """Get guild by ID.

        :param guild_id: ID of the guild to get
        :type guild_id: int
        :return: guild object or None
        :rtype: :class:`discord.Guild` or None
        """
        pass

    @abstractmethod
    def get_channel(self, channel_id):
        """Get channel by ID.

        :param channel_id: ID of the channel to get
        :type channel_id: int
        :return: channel object or None
        :rtype: :class:`discord.abc.GuildChannel` or None
        """
        pass

    @abstractmethod
    def event(self, func):
        """Register an event handler.

        :param func: event handler function
        :type func: callable
        :return: decorated function
        :rtype: callable
        """
        pass


class DiscordClientWrapper(IDiscordClientWrapper):
    """Concrete implementation of Discord client wrapper.

    :param DiscordClientWrapper._client: wrapped Discord client instance
    :type DiscordClientWrapper._client: :class:`discord.Client`
    """

    def __init__(self, intents):
        """Initialize Discord client wrapper.

        :param intents: Discord intents configuration
        :type intents: :class:`discord.Intents`
        """
        self._client = Client(intents=intents)

    async def start(self, token):
        """Start the Discord client.

        :param token: Discord bot token
        :type token: str
        """
        await self._client.start(token)

    async def close(self):
        """Close the Discord client."""
        await self._client.close()

    def is_ready(self):
        """Check if client is ready.

        :return: whether client is ready
        :rtype: bool
        """
        return self._client.is_ready()

    def is_closed(self):
        """Check if client is closed.

        :return: whether client is closed
        :rtype: bool
        """
        return self._client.is_closed()

    def get_guild(self, guild_id):
        """Get guild by ID.

        :param guild_id: ID of the guild to get
        :type guild_id: int
        :return: guild object or None
        :rtype: :class:`discord.Guild` or None
        """
        return self._client.get_guild(guild_id)

    def get_channel(self, channel_id):
        """Get channel by ID.

        :param channel_id: ID of the channel to get
        :type channel_id: int
        :return: channel object or None
        :rtype: :class:`discord.abc.GuildChannel` or None
        """
        return self._client.get_channel(channel_id)

    def event(self, func):
        """Register an event handler.

        :param func: event handler function
        :type func: callable
        :return: decorated function
        :rtype: callable
        """
        return self._client.event(func)

    @property
    def user(self):
        """Get the client user.

        :return: client user object
        :rtype: :class:`discord.ClientUser`
        """
        return self._client.user

    @property
    def guilds(self):
        """Get the guilds the client is in.

        :return: list of guilds
        :rtype: list of :class:`discord.Guild`
        """
        return self._client.guilds


class DiscordTracker(BaseAsyncMentionTracker):
    """Discord tracker for multiple servers/guilds with automatic channel discovery.

    :param DiscordTracker.client: Discord client wrapper instance
    :type DiscordTracker.client: :class:`IDiscordClientWrapper`
    :param DiscordTracker.bot_user_id: user ID of the bot account
    :type DiscordTracker.bot_user_id: int
    :param DiscordTracker.token: Discord bot's token
    :type DiscordTracker.token: str
    :param DiscordTracker.tracked_guilds: list of guild IDs to monitor
    :type DiscordTracker.tracked_guilds: list
    :param DiscordTracker.auto_discover_channels: whether to auto-discover channels
    :type DiscordTracker.auto_discover_channels: bool
    :param DiscordTracker.excluded_channel_types: channel types to exclude
    :type DiscordTracker.excluded_channel_types: list
    """

    def __init__(
        self,
        parse_message_callback,
        discord_config,
        guilds_collection=None,
        client_wrapper=None,
    ):
        """Initialize multi-guild Discord tracker.

        :param parse_message_callback: function to call when mention is found
        :type parse_message_callback: callable
        :param discord_config: configuration dictionary for Discord API
        :type discord_config: dict
        :param guilds_collection: list of guild IDs to monitor
        :type guilds_collection: list
        :param client_wrapper: Discord client wrapper for testing
        :type client_wrapper: :class:`IDiscordClientWrapper` or None
        """
        super().__init__("discord", parse_message_callback)

        # Configure Discord intents
        intents = Intents.default()
        intents.message_content = True
        intents.messages = True
        intents.guilds = True
        intents.members = True
        intents.guild_messages = True
        intents.reactions = True

        # Use provided wrapper or create default one
        self.client = client_wrapper or DiscordClientWrapper(intents)

        # Configuration
        self.bot_user_id = discord_config.get("bot_user_id", "")
        self.token = discord_config.get("token", "")
        self.tracked_guilds = guilds_collection or []
        self.auto_discover_channels = discord_config.get("auto_discover_channels", True)
        self.excluded_channel_types = discord_config.get("excluded_channel_types", [])
        self.manually_excluded_channels = discord_config.get("excluded_channels", [])
        self.manually_included_channels = discord_config.get("included_channels", [])

        # Rate limiting and state management
        self.processed_messages = set()
        self.last_channel_check = {}
        self.guild_channels = {}
        self.all_tracked_channels = set()

        # Configuration
        self.rate_limit_delay = 1.0
        self.max_messages_per_channel = 20
        self.concurrent_channel_checks = 3
        self.channel_discovery_interval = 300

        size = str(len(guilds_collection)) if guilds_collection else "all"
        self.logger.info(f"Multi-guild Discord tracker initialized for {size} guilds")

        # Set up event handlers
        self._setup_events()

    def _setup_events(self):
        """Set up Discord event handlers."""

        @self.client.event
        async def on_ready():
            await self._handle_on_ready()

        @self.client.event
        async def on_message(message):
            await self._handle_on_message(message)

        @self.client.event
        async def on_guild_join(guild):
            await self._handle_on_guild_join(guild)

        @self.client.event
        async def on_guild_remove(guild):
            await self._handle_on_guild_remove(guild)

    async def _handle_on_ready(self):
        """Called when the bot is logged in and ready.

        :var size: nnumber of tracked huilds or all
        :type size: str
        """
        self.logger.info(f"Discord bot logged in as {self.client.user}")
        self.logger.info(f"Connected to {len(self.client.guilds)} guilds")

        # Discover channels for all guilds
        await self._discover_all_guild_channels()

        size = str(len(self.tracked_guilds)) if self.tracked_guilds else "all"
        await self.log_action_async("initialized", f"Tracking {size} guilds")
        await self.log_action_async(
            "connected",
            (
                f"Logged in as {self.client.user}, tracking "
                f"{len(self.all_tracked_channels)} channels across "
                f"{len(self.guild_channels)} guilds"
            ),
        )

    async def _handle_on_message(self, message):
        """Called when a message is sent in any channel the bot can see.

        :param message: Discord message object
        :type message: :class:`discord.Message`
        """
        await self._handle_new_message(message)

    async def _handle_on_guild_join(self, guild):
        """Called when the bot joins a new guild.

        :param guild: guild that was joined
        :type guild: :class:`discord.Guild`
        """
        self.logger.info(f"Joined new guild: {guild.name} (ID: {guild.id})")
        await self._discover_guild_channels(guild)
        await self.log_action_async("guild_joined", f"Guild: {guild.name}")

    async def _handle_on_guild_remove(self, guild):
        """Called when the bot is removed from a guild.

        :param guild: guild that was left
        :type guild: :class:`discord.Guild`
        """
        self.logger.info(f"Left guild: {guild.name} (ID: {guild.id})")
        self._remove_guild_from_tracking(guild.id)
        await self.log_action_async("guild_left", f"Guild: {guild.name}")

    def _remove_guild_from_tracking(self, guild_id):
        """Remove a guild from tracking.

        :param guild_id: ID of the guild to remove
        :type guild_id: int
        """
        if guild_id in self.guild_channels:
            del self.guild_channels[guild_id]
            self._update_all_tracked_channels()

    async def _discover_all_guild_channels(self):
        """Discover all channels across all tracked guilds.

        :var guilds_to_process: list of guilds to process for channel discovery
        :type guilds_to_process: list of :class:`discord.Guild`
        :var guild: individual guild being processed
        :type guild: :class:`discord.Guild`
        """
        guilds_to_process = self._get_guilds_to_process()

        for guild in guilds_to_process:
            await self._discover_guild_channels(guild)

    def _get_guilds_to_process(self):
        """Get list of guilds to process for channel discovery.

        :var guilds_to_process: list of guilds to process
        :type guilds_to_process: list of :class:`discord.Guild`
        :var guild_id: individual guild ID from tracked guilds
        :type guild_id: int
        :var guild: guild object retrieved by ID
        :type guild: :class:`discord.Guild` or None
        :return: list of guilds to process
        :rtype: list of :class:`discord.Guild`
        """
        guilds_to_process = []

        if self.tracked_guilds:
            # Only process specified guilds
            for guild_id in self.tracked_guilds:
                guild = self.client.get_guild(guild_id)
                if guild:
                    guilds_to_process.append(guild)
                else:
                    self.logger.warning(f"Guild {guild_id} not found")
        else:
            # Process all guilds the bot is in
            guilds_to_process = self.client.guilds

        return guilds_to_process

    async def _discover_guild_channels(self, guild):
        """Discover all trackable channels in a guild.

        :param guild: Discord guild to discover channels in
        :type guild: :class:`discord.Guild`
        :var channels: list of all channels in the guild
        :type channels: list of :class:`discord.abc.GuildChannel`
        :var trackable_channels: filtered list of channels to track
        :type trackable_channels: list of :class:`discord.TextChannel`
        :var channel: individual channel being processed
        :type channel: :class:`discord.abc.GuildChannel`
        :var channel_ids: list of channel IDs for this guild
        :type channel_ids: list of int
        """
        try:
            channels = await guild.fetch_channels()
            trackable_channels = [
                channel
                for channel in channels
                if self._is_channel_trackable(channel, guild.id)
            ]

            # Store channel IDs for this guild
            channel_ids = [channel.id for channel in trackable_channels]
            self.guild_channels[guild.id] = channel_ids
            self._update_all_tracked_channels()

            self.logger.info(
                (
                    f"Discovered {len(channel_ids)} trackable "
                    f"channels in guild '{guild.name}'"
                )
            )

        except Exception as e:
            self.logger.error(f"Error discovering channels for guild {guild.name}: {e}")

    def _is_channel_trackable(self, channel, guild_id):
        """Check if a channel should be tracked.

        :param channel: Discord channel to check
        :type channel: :class:`discord.abc.GuildChannel`
        :param guild_id: ID of the guild containing the channel
        :type guild_id: int
        :var channel_type: type of the channel as string
        :type channel_type: str
        :return: whether channel is trackable
        :rtype: bool
        """
        # Check manual inclusions first (override other checks)
        if (
            self.manually_included_channels
            and channel.id in self.manually_included_channels
        ):
            return True

        # Check manual exclusions
        if channel.id in self.manually_excluded_channels:
            return False

        # Check channel type
        channel_type = str(channel.type)
        if channel_type in self.excluded_channel_types:
            return False

        # Check permissions (for text channels)
        if hasattr(channel, "permissions_for"):
            return self._has_channel_permission(channel)

        return True

    def _has_channel_permission(self, channel):
        """Check if bot has permission to read from channel.

        :param channel: channel to check permissions for
        :type channel: :class:`discord.abc.GuildChannel`
        :var bot_member: bot member in the guild
        :type bot_member: :class:`discord.Member` or None
        :var permissions: channel permissions for bot member
        :type permissions: :class:`discord.Permissions`
        :var has_permission: whether bot has read permissions
        :type has_permission: bool
        :return: whether bot has permission to read channel
        :rtype: bool
        """
        try:
            bot_member = channel.guild.get_member(self.client.user.id)
            if not bot_member:
                return False

            permissions = channel.permissions_for(bot_member)
            has_permission = (
                permissions.read_messages and permissions.read_message_history
            )
            return has_permission

        except Exception:
            return False

    def _update_all_tracked_channels(self):
        """Update the set of all tracked channels across all guilds.

        :var all_channels: set of all channel IDs from all guilds
        :type all_channels: set of int
        """
        all_channels = set()
        for channel_list in self.guild_channels.values():
            all_channels.update(channel_list)
        self.all_tracked_channels = all_channels
        self.logger.debug(
            f"Updated tracked channels: {len(all_channels)} total channels"
        )

    async def _handle_new_message(self, message):
        """Handle incoming Discord messages across all tracked guilds.

        :param message: Discord message object
        :type message: :class:`discord.Message`
        :var is_tracked_guild: whether message is from a tracked guild
        :type is_tracked_guild: bool
        :var is_tracked_channel: whether message is from a tracked channel
        :type is_tracked_channel: bool
        :var is_bot_mentioned: whether the bot is mentioned in the message
        :type is_bot_mentioned: bool
        :var message_id: unique identifier for the message
        :type message_id: str
        :var data: extracted mention data
        :type data: dict
        """
        if not self._should_process_message(message):
            return

        message_id = f"discord_{message.guild.id}_{message.channel.id}_{message.id}"

        if not await self.is_processed_async(message_id):
            data = await self.extract_mention_data(message)
            if await self.process_mention_async(
                message_id, data, f"@{self.bot_user_id}"
            ):
                self.processed_messages.add(message_id)
                self.logger.info(
                    f"Processed mention in {message.guild.name} / {message.channel.name}"
                )

    def _should_process_message(self, message):
        """Check if a message should be processed.

        :param message: Discord message to check
        :type message: :class:`discord.Message`
        :var is_tracked_guild: whether message is from tracked guild
        :type is_tracked_guild: bool
        :var is_tracked_channel: whether message is from tracked channel
        :type is_tracked_channel: bool
        :return: whether message should be processed
        :rtype: bool
        """
        # Ignore messages from bots
        if message.author.bot:
            return False

        # Check if message is from a tracked guild
        if not message.guild:
            return False  # Skip DMs

        is_tracked_guild = (not self.tracked_guilds) or (
            message.guild.id in self.tracked_guilds
        )
        if not is_tracked_guild:
            return False

        # Check if message is from a tracked channel
        is_tracked_channel = message.channel.id in self.all_tracked_channels
        if not is_tracked_channel:
            return False

        # Check if bot is mentioned
        return self._is_bot_mentioned(message)

    def _is_bot_mentioned(self, message):
        """Check if the bot is mentioned in the message.

        :param message: message to check for mentions
        :type message: :class:`discord.Message`
        :var user_mention: user mention in the message
        :type user_mention: :class:`discord.User`
        :return: whether bot is mentioned
        :rtype: bool
        """
        return (
            any(user.id == self.bot_user_id for user in message.mentions)
            or f"<@{self.bot_user_id}>" in message.content
        )

    async def extract_mention_data(self, message):
        """Extract standardized data from Discord message.

        :param message: Discord message object
        :type message: :class:`discord.Message`
        :var author: user who sent the message
        :type author: :class:`discord.User`
        :var referenced_message: message that this message replies to
        :type referenced_message: :class:`discord.Message` or None
        :var channel: channel where message was sent
        :type channel: :class:`discord.TextChannel`
        :var guild: Discord server where message was sent
        :type guild: :class:`discord.Guild`
        :var data: extracted mention data dictionary
        :type data: dict
        :return: standardized mention data
        :rtype: dict
        """
        author = message.author
        referenced_message = message.reference.resolved if message.reference else None

        message_url = message.jump_url

        if referenced_message and hasattr(referenced_message, "jump_url"):
            contribution_url = referenced_message.jump_url
            contributor = referenced_message.author
            contribution = (
                referenced_message.content if referenced_message.content else ""
            )
        else:
            contribution_url = message_url
            contributor = author
            contribution = message.content if message.content else ""

        data = {
            "suggester": author.id,
            "suggester_username": author.name,
            "suggester_display_name": author.display_name,
            "suggestion_url": message_url,
            "contribution_url": contribution_url,
            "contributor": contributor.id,
            "contributor_username": contributor.name,
            "contributor_display_name": contributor.display_name,
            "type": "message",
            "discord_channel": message.channel.name,
            "discord_guild": message.guild.name,
            "channel_id": message.channel.id,
            "guild_id": message.guild.id,
            "content": message.content if message.content else "",
            "contribution": contribution,
            "timestamp": message.created_at.isoformat(),
            "item_id": f"discord_{message.guild.id}_{message.channel.id}_{message.id}",
        }

        return data

    async def _check_channel_history(self, channel_id, guild_id):
        """Check historical messages in a specific channel.

        :param channel_id: ID of the channel to check
        :type channel_id: int
        :param guild_id: ID of the guild containing the channel
        :type guild_id: int
        :var channel: Discord channel object
        :type channel: :class:`discord.TextChannel`
        :var mention_count: number of mentions found in this channel
        :type mention_count: int
        :var messages: historical messages from the channel
        :type messages: list of :class:`discord.Message`
        :var message: individual message from channel
        :type message: :class:`discord.Message`
        :var message_id: unique identifier for the message
        :type message_id: str
        :var data: extracted mention data
        :type data: dict
        :return: number of new mentions processed in this channel
        :rtype: int
        """
        if self._is_rate_limited(channel_id):
            return 0

        self.last_channel_check[channel_id] = datetime.now()

        channel = self.client.get_channel(channel_id)
        if not channel:
            return 0

        try:
            return await self._process_channel_messages(channel, guild_id)

        except Forbidden:
            return await self._handle_forbidden_exception(channel_id, guild_id)

        except HTTPException as e:
            return await self._handle_http_exception(e, channel_id)

        except Exception as e:
            self.logger.error(f"Error checking channel {channel_id}: {e}")
            return 0

    def _is_rate_limited(self, channel_id):
        """Check if channel is rate limited.

        :param channel_id: ID of the channel to check
        :type channel_id: int
        :var last_check: last time this channel was checked
        :type last_check: :class:`datetime.datetime`
        :return: whether channel is rate limited
        :rtype: bool
        """
        last_check = self.last_channel_check.get(channel_id)
        if last_check and (datetime.now() - last_check) < timedelta(
            seconds=self.rate_limit_delay
        ):
            return True

        return False

    async def _process_channel_messages(self, channel, guild_id):
        """Process messages in a channel and return mention count.

        :param channel: channel to process messages from
        :type channel: :class:`discord.TextChannel`
        :param guild_id: ID of the guild containing the channel
        :type guild_id: int
        :var mention_count: number of mentions found
        :type mention_count: int
        :var message: individual message from channel history
        :type message: :class:`discord.Message`
        :var message_id: unique identifier for the message
        :type message_id: str
        :var data: extracted mention data
        :type data: dict
        :return: number of mentions processed
        :rtype: int
        """
        mention_count = 0

        async for message in channel.history(limit=self.max_messages_per_channel):
            if message.author.bot:
                continue

            if self._is_bot_mentioned(message):
                message_id = f"discord_{guild_id}_{channel.id}_{message.id}"

                if not await self.is_processed_async(message_id):
                    data = await self.extract_mention_data(message)
                    if await self.process_mention_async(
                        message_id, data, f"@{self.bot_user_id}"
                    ):
                        mention_count += 1
                        self.processed_messages.add(message_id)

        return mention_count

    async def _handle_http_exception(self, exception, channel_id):
        """Handle HTTPException from Discord API.

        :param exception: HTTPException that was raised
        :type exception: :class:`discord.HTTPException`
        :param channel_id: ID of the channel being checked
        :type channel_id: int
        :var retry_after: seconds to wait before retrying
        :type retry_after: float
        :return: always returns 0 (no mentions processed)
        :rtype: int
        """
        if exception.status == 429:  # Rate limited
            retry_after = getattr(exception, "retry_after", 5)
            self.logger.warning(
                f"Rate limited on channel {channel_id}, retrying in {retry_after}s"
            )
            await asyncio.sleep(retry_after)

        else:
            self.logger.error(f"HTTP error checking channel {channel_id}: {exception}")

        return 0

    async def _handle_forbidden_exception(self, channel_id, guild_id):
        """Handle Forbidden exception (no permission).

        :param channel_id: ID of the channel that raised Forbidden
        :type channel_id: int
        :param guild_id: ID of the guild containing the channel
        :type guild_id: int
        :return: always returns 0 (no mentions processed)
        :rtype: int
        """
        self.logger.warning(f"No permission to access channel {channel_id}")
        self._remove_channel_from_tracking(channel_id, guild_id)
        return 0

    def _remove_channel_from_tracking(self, channel_id, guild_id):
        """Remove channel from tracking.

        :param channel_id: ID of the channel to remove
        :type channel_id: int
        :param guild_id: ID of the guild containing the channel
        :type guild_id: int
        """
        if (
            guild_id in self.guild_channels
            and channel_id in self.guild_channels[guild_id]
        ):
            self.guild_channels[guild_id].remove(channel_id)
            self._update_all_tracked_channels()

    async def check_mentions_async(self):
        """Asynchronously check for new mentions across all tracked channels.

        :var total_mentions: total number of new mentions found
        :type total_mentions: int
        :var semaphore: semaphore for limiting concurrent channel checks
        :type semaphore: :class:`asyncio.Semaphore`
        :var tasks: list of channel check tasks
        :type tasks: list of :class:`asyncio.Task`
        :var channel_mentions: mentions from individual channel checks
        :type channel_mentions: list of int
        :return: total number of new mentions processed
        :rtype: int
        """
        if not self.client.is_ready():
            return 0

        tasks = [
            self._check_channel_with_semaphore(channel_id, guild_id)
            for guild_id, channel_ids in self.guild_channels.items()
            for channel_id in channel_ids
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)
        return self._process_check_results(results)

    async def _check_channel_with_semaphore(self, channel_id, guild_id):
        """Check channel with semaphore for rate limiting.

        :param channel_id: ID of the channel to check
        :type channel_id: int
        :param guild_id: ID of the guild containing the channel
        :type guild_id: int
        :var semaphore: semaphore for limiting concurrent checks
        :type semaphore: :class:`asyncio.Semaphore`
        :return: number of mentions found in channel
        :rtype: int
        """
        semaphore = asyncio.Semaphore(self.concurrent_channel_checks)
        async with semaphore:
            return await self._check_channel_history(channel_id, guild_id)

    def _process_check_results(self, results):
        """Process results from channel checks.

        :param results: list of results from channel checks
        :type results: list
        :var total_mentions: running total of mentions found
        :type total_mentions: int
        :var result: individual result from channel check
        :type result: int or Exception
        :return: total number of mentions processed
        :rtype: int
        """
        total_mentions = 0
        for result in results:
            if isinstance(result, Exception):
                self.logger.error(f"Error processing channel: {result}")

            else:
                total_mentions += result

        return total_mentions

    async def run_continuous(self, historical_check_interval):
        """Run Discord tracker in continuous mode with periodic historical checks.

        Registers signal handlers for graceful shutdown, starts the Discord client
        and then runs the main loop until the client is closed or an interrupt is
        received.

        :param historical_check_interval: how often to run historical checks (seconds)
        :type historical_check_interval: int
        :var last_historical_check: timestamp of last historical check
        :type last_historical_check: :class:`datetime.datetime`
        :var last_channel_discovery: timestamp of last channel discovery
        :type last_channel_discovery: :class:`datetime.datetime`
        :var mentions_found: number of mentions found in historical check
        :type mentions_found: int
        """
        self._register_signal_handlers()

        self.logger.info("Starting multi-guild Discord tracker in continuous mode")
        await self.log_action_async("started", "Continuous multi-guild mode")

        try:
            await self.client.start(self.token)
            await self._run_main_loop(historical_check_interval)

        except KeyboardInterrupt:
            self.logger.info("Multi-guild Discord tracker stopped by user")
            await self.log_action_async("stopped", "User interrupt")

        except Exception as e:
            self.logger.error(f"Multi-guild Discord tracker error: {e}")
            await self.log_action_async("error", f"Tracker error: {str(e)}")
            raise

        finally:
            await self.client.close()
            await asyncio.sleep(0)
            await self.cleanup()

    async def cleanup(self):
        """Perform graceful cleanup for the Discord tracker."""
        self.logger.info(f"{self.platform_name} tracker cleanup completed")

    async def _run_main_loop(self, historical_check_interval):
        """Run the main tracking loop.

        Periodically performs channel discovery and historical checks while the
        client is running and no graceful shutdown has been requested.

        :param historical_check_interval: interval for historical checks
        :type historical_check_interval: int
        :var last_historical_check: timestamp of last historical check
        :type last_historical_check: :class:`datetime.datetime`
        :var last_channel_discovery: timestamp of last channel discovery
        :type last_channel_discovery: :class:`datetime.datetime`
        :var now: current timestamp
        :type now: :class:`datetime.datetime`
        :var mentions_found: total number of found mentions
        :type mentions_found: int
        """
        last_historical_check = datetime.now()
        last_channel_discovery = datetime.now()

        while not self.exit_signal and not self.client.is_closed():
            now = datetime.now()

            # Channel discovery
            if self._should_run_channel_discovery(now, last_channel_discovery):
                self.logger.debug("Running periodic channel discovery")
                await self._discover_all_guild_channels()
                last_channel_discovery = now

            # Historical checks
            if self._should_run_historical_check(
                now, last_historical_check, historical_check_interval
            ):
                self.logger.debug("Running periodic historical check")
                mentions_found = await self.check_mentions_async()
                if mentions_found > 0:
                    self.logger.info(
                        f"Found {mentions_found} new mentions in historical check"
                    )
                last_historical_check = now

            # Sleep in small async chunks so we can react to exit_signal
            await self._async_interruptible_sleep(10)

    async def _async_interruptible_sleep(self, seconds, step=1):
        """Async sleep helper that respects exit_signal and client state.

        Sleeps in small chunks so that the loop can exit promptly when
        :pyattr:`BaseMentionTracker.exit_signal` is set or when the client closes.

        :param seconds: total number of seconds to sleep
        :type seconds: int
        :param step: sleep chunk size in seconds
        :type step: int
        """
        elapsed = 0
        step = max(1, int(step))

        while (
            elapsed < seconds and not self.exit_signal and not self.client.is_closed()
        ):
            remaining = seconds - elapsed
            sleep_for = min(step, remaining)
            await asyncio.sleep(sleep_for)
            elapsed += sleep_for

    async def _handle_periodic_tasks(
        self,
        now,
        last_channel_discovery,
        last_historical_check,
        historical_check_interval,
    ):
        """Handle periodic tasks and return updated timestamps.

        :param now: current timestamp
        :type now: :class:`datetime.datetime`
        :param last_channel_discovery: timestamp of last channel discovery
        :type last_channel_discovery: :class:`datetime.datetime`
        :param last_historical_check: timestamp of last historical check
        :type last_historical_check: :class:`datetime.datetime`
        :param historical_check_interval: interval for historical checks
        :type historical_check_interval: int
        :return: updated last_channel_discovery timestamp
        :rtype: :class:`datetime.datetime`
        """
        # Channel discovery
        if self._should_run_channel_discovery(now, last_channel_discovery):
            await self._run_channel_discovery()
            last_channel_discovery = now

        # Historical checks
        if self._should_run_historical_check(
            now, last_historical_check, historical_check_interval
        ):
            await self._run_historical_check()
            last_historical_check = now

        return last_channel_discovery

    def _should_run_channel_discovery(self, now, last_channel_discovery):
        """Check if channel discovery should run.

        :param now: current timestamp
        :type now: :class:`datetime.datetime`
        :param last_channel_discovery: timestamp of last channel discovery
        :type last_channel_discovery: :class:`datetime.datetime`
        :return: whether channel discovery should run
        :rtype: bool
        """
        return (now - last_channel_discovery) > timedelta(
            seconds=self.channel_discovery_interval
        )

    def _should_run_historical_check(self, now, last_historical_check, interval):
        """Check if historical check should run.

        :param now: current timestamp
        :type now: :class:`datetime.datetime`
        :param last_historical_check: timestamp of last historical check
        :type last_historical_check: :class:`datetime.datetime`
        :param interval: historical check interval
        :type interval: int
        :return: whether historical check should run
        :rtype: bool
        """
        return (now - last_historical_check) > timedelta(seconds=interval)

    async def _run_channel_discovery(self):
        """Run channel discovery task.

        :var discovery_result: result of channel discovery
        :type discovery_result: None
        """
        self.logger.info("Running periodic channel discovery")
        await self._discover_all_guild_channels()

    async def _run_historical_check(self):
        """Run historical check task.

        :var mentions_found: number of mentions found in historical check
        :type mentions_found: int
        """
        self.logger.info("Running periodic historical check")
        mentions_found = await self.check_mentions_async()
        if mentions_found > 0:
            self.logger.info(f"Found {mentions_found} new mentions in historical check")

    def get_stats(self):
        """Get statistics about the current tracking state.

        :var stats: dictionary containing tracking statistics
        :type stats: dict
        :var guild_id: ID of guild in tracking
        :type guild_id: int
        :var channel_ids: list of channel IDs for guild
        :type channel_ids: list of int
        :var guild: guild object retrieved by ID
        :type guild: :class:`discord.Guild` or None
        :var guild_name: name of the guild or placeholder
        :type guild_name: str
        :return: tracking statistics
        :rtype: dict
        """
        stats = {
            "guilds_tracked": len(self.guild_channels),
            "channels_tracked": len(self.all_tracked_channels),
            "processed_messages": len(self.processed_messages),
            "guild_details": {},
        }

        for guild_id, channel_ids in self.guild_channels.items():
            guild = self.client.get_guild(guild_id)
            guild_name = guild.name if guild else f"Unknown ({guild_id})"
            stats["guild_details"][guild_name] = len(channel_ids)

        return stats
