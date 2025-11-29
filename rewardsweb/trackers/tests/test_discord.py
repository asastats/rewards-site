"""Testing module for :py:mod:`trackers.discord` module."""

from datetime import datetime, timedelta
from unittest import mock

import discord
import pytest

from trackers.discord import (
    DiscordClientWrapper,
    DiscordTracker,
    IDiscordClientWrapper,
)


class DummyDiscordClient(IDiscordClientWrapper):

    async def start(self, token):
        await super().start(token)
        return f"started:{token}"

    async def close(self):
        await super().close()
        return "closed"

    def is_ready(self):
        super().is_ready()
        return True

    def is_closed(self):
        super().is_closed()
        return False

    def get_guild(self, guild_id):
        super().get_guild(guild_id)
        return f"guild:{guild_id}"

    def get_channel(self, channel_id):
        super().get_channel(channel_id)
        return f"channel:{channel_id}"

    def event(self, func):
        super().event(func)
        return func


class MockDiscordClientWrapper(IDiscordClientWrapper):
    """Mock Discord client wrapper for testing."""

    def __init__(self):
        self.start_called = False
        self.close_called = False
        self.ready = False
        self.closed = False
        self.user = mock.MagicMock()
        self.guilds = []
        self._event_handlers = {}

        # Create proper MagicMock objects for these methods
        self.get_guild = mock.MagicMock()
        self.get_channel = mock.MagicMock()

    async def start(self, token):
        self.start_called = True
        self.ready = True
        self.closed = False

    async def close(self):
        self.close_called = True
        self.ready = False
        self.closed = True

    def is_ready(self):
        return self.ready

    def is_closed(self):
        return self.closed

    def event(self, func):
        self._event_handlers[func.__name__] = func
        return func

    def get_guild(self, guild_id):
        return self.get_guild_return

    def get_channel(self, channel_id):
        return self.get_channel_return


class TestIDiscordClientWrapper:
    """Testing class for :class:`trackers.discord.IDiscordClientWrapper` abstract interface."""

    def test_trackers_discord_idiscordclientwrapper_is_abstract(self):
        """Test that IDiscordClientWrapper cannot be instantiated directly."""
        with pytest.raises(TypeError) as exc_info:
            IDiscordClientWrapper()

        assert "Can't instantiate abstract class" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_trackers_discord_idiscordclientwrapper_start(self):
        c = DummyDiscordClient()
        assert await c.start("ABC") == "started:ABC"

    @pytest.mark.asyncio
    async def test_trackers_discord_idiscordclientwrapper_close(self):
        c = DummyDiscordClient()
        assert await c.close() == "closed"

    def test_trackers_discord_idiscordclientwrapper_is_ready(self):
        c = DummyDiscordClient()
        assert c.is_ready() is True

    def test_trackers_discord_idiscordclientwrapper_is_closed(self):
        c = DummyDiscordClient()
        assert c.is_closed() is False

    def test_trackers_discord_idiscordclientwrapper_get_guild(self):
        c = DummyDiscordClient()
        assert c.get_guild(1) == "guild:1"

    def test_trackers_discord_idiscordclientwrapper_get_channel(self):
        c = DummyDiscordClient()
        assert c.get_channel(55) == "channel:55"

    def test_trackers_discord_idiscordclientwrapper_event(self):
        c = DummyDiscordClient()

        @c.event
        def handler():
            return "ok"

        assert handler() == "ok"


class TestDiscordClientWrapper:
    """Testing class for :class:`trackers.discord.DiscordClientWrapper` concrete implementation."""

    def test_trackers_discord_client_wrapper_init(self):
        """Test DiscordClientWrapper initialization."""
        # Use real Intents instead of MagicMock
        intents = discord.Intents.default()
        intents.messages = True
        intents.message_content = True

        wrapper = DiscordClientWrapper(intents)

        assert wrapper._client is not None
        assert isinstance(wrapper._client, discord.Client)

    def test_trackers_discord_client_wrapper_implements_interface(self):
        """Test that DiscordClientWrapper implements IDiscordClientWrapper interface."""
        # Use real Intents
        intents = discord.Intents.default()
        intents.messages = True

        wrapper = DiscordClientWrapper(intents)

        assert isinstance(wrapper, IDiscordClientWrapper)

    @pytest.mark.asyncio
    async def test_trackers_discord_client_wrapper_start(self):
        """Test DiscordClientWrapper.start method."""
        intents = discord.Intents.default()
        intents.messages = True

        wrapper = DiscordClientWrapper(intents)

        # Mock the underlying client's start method
        wrapper._client.start = mock.AsyncMock()

        test_token = "test_token_123"
        await wrapper.start(test_token)

        wrapper._client.start.assert_called_once_with(test_token)

    @pytest.mark.asyncio
    async def test_trackers_discord_client_wrapper_close(self):
        """Test DiscordClientWrapper.close method."""
        intents = discord.Intents.default()
        intents.messages = True

        wrapper = DiscordClientWrapper(intents)

        # Mock the underlying client's close method
        wrapper._client.close = mock.AsyncMock()

        await wrapper.close()

        wrapper._client.close.assert_called_once()

    def test_trackers_discord_client_wrapper_is_ready(self):
        """Test DiscordClientWrapper.is_ready method."""
        intents = discord.Intents.default()
        intents.messages = True

        wrapper = DiscordClientWrapper(intents)

        # Test when ready
        wrapper._client.is_ready = mock.Mock(return_value=True)
        assert wrapper.is_ready() is True

        # Test when not ready
        wrapper._client.is_ready = mock.Mock(return_value=False)
        assert wrapper.is_ready() is False

    def test_trackers_discord_client_wrapper_is_closed(self):
        """Test DiscordClientWrapper.is_closed method."""
        intents = discord.Intents.default()
        intents.messages = True

        wrapper = DiscordClientWrapper(intents)

        # Test when closed
        wrapper._client.is_closed = mock.Mock(return_value=True)
        assert wrapper.is_closed() is True

        # Test when not closed
        wrapper._client.is_closed = mock.Mock(return_value=False)
        assert wrapper.is_closed() is False

    def test_trackers_discord_client_wrapper_get_guild(self):
        """Test DiscordClientWrapper.get_guild method."""
        intents = discord.Intents.default()
        intents.messages = True

        wrapper = DiscordClientWrapper(intents)

        test_guild_id = 123456789012345678
        mock_guild = mock.MagicMock()
        wrapper._client.get_guild = mock.Mock(return_value=mock_guild)

        result = wrapper.get_guild(test_guild_id)

        wrapper._client.get_guild.assert_called_once_with(test_guild_id)
        assert result is mock_guild

    def test_trackers_discord_client_wrapper_get_guild_not_found(self):
        """Test DiscordClientWrapper.get_guild when guild not found."""
        intents = discord.Intents.default()
        intents.messages = True

        wrapper = DiscordClientWrapper(intents)

        test_guild_id = 123456789012345678
        wrapper._client.get_guild = mock.Mock(return_value=None)

        result = wrapper.get_guild(test_guild_id)

        wrapper._client.get_guild.assert_called_once_with(test_guild_id)
        assert result is None

    def test_trackers_discord_client_wrapper_get_channel(self):
        """Test DiscordClientWrapper.get_channel method."""
        intents = discord.Intents.default()
        intents.messages = True

        wrapper = DiscordClientWrapper(intents)

        test_channel_id = 123456789012345678
        mock_channel = mock.MagicMock()
        wrapper._client.get_channel = mock.Mock(return_value=mock_channel)

        result = wrapper.get_channel(test_channel_id)

        wrapper._client.get_channel.assert_called_once_with(test_channel_id)
        assert result is mock_channel

    def test_trackers_discord_client_wrapper_get_channel_not_found(self):
        """Test DiscordClientWrapper.get_channel when channel not found."""
        intents = discord.Intents.default()
        intents.messages = True

        wrapper = DiscordClientWrapper(intents)

        test_channel_id = 123456789012345678
        wrapper._client.get_channel = mock.Mock(return_value=None)

        result = wrapper.get_channel(test_channel_id)

        wrapper._client.get_channel.assert_called_once_with(test_channel_id)
        assert result is None

    def test_trackers_discord_client_wrapper_event(self):
        """Test DiscordClientWrapper.event decorator."""
        intents = discord.Intents.default()
        intents.messages = True

        wrapper = DiscordClientWrapper(intents)

        # Mock the client.event decorator
        mock_decorator = mock.MagicMock()
        mock_decorator.return_value = "decorated_function"
        wrapper._client.event = mock_decorator

        def test_function():
            pass

        result = wrapper.event(test_function)

        mock_decorator.assert_called_once_with(test_function)
        assert result == "decorated_function"

    def test_trackers_discord_client_wrapper_user_property(self):
        """Test DiscordClientWrapper.user property."""
        intents = discord.Intents.default()
        intents.messages = True

        wrapper = DiscordClientWrapper(intents)

        # The user property is read-only in discord.Client, so we test that it returns the same value
        assert wrapper.user is wrapper._client.user

    def test_trackers_discord_client_wrapper_guilds_property(self):
        """Test DiscordClientWrapper.guilds property."""
        intents = discord.Intents.default()
        intents.messages = True

        wrapper = DiscordClientWrapper(intents)

        # The guilds property returns a SequenceProxy, so we test that they contain the same data
        # by converting to list and comparing
        assert list(wrapper.guilds) == list(wrapper._client.guilds)

    def test_trackers_discord_client_wrapper_all_methods_implemented(self):
        """Test that DiscordClientWrapper implements all abstract methods."""
        intents = discord.Intents.default()
        intents.messages = True

        wrapper = DiscordClientWrapper(intents)

        # These should all exist and be callable
        assert hasattr(wrapper, "start")
        assert callable(wrapper.start)

        assert hasattr(wrapper, "close")
        assert callable(wrapper.close)

        assert hasattr(wrapper, "is_ready")
        assert callable(wrapper.is_ready)

        assert hasattr(wrapper, "is_closed")
        assert callable(wrapper.is_closed)

        assert hasattr(wrapper, "get_guild")
        assert callable(wrapper.get_guild)

        assert hasattr(wrapper, "get_channel")
        assert callable(wrapper.get_channel)

        assert hasattr(wrapper, "event")
        assert callable(wrapper.event)

    @pytest.mark.asyncio
    async def test_trackers_discord_client_wrapper_start_exception(self):
        """Test DiscordClientWrapper.start with exception."""
        intents = discord.Intents.default()
        intents.messages = True

        wrapper = DiscordClientWrapper(intents)

        test_token = "test_token_123"
        wrapper._client.start = mock.AsyncMock(
            side_effect=Exception("Connection failed")
        )

        with pytest.raises(Exception) as exc_info:
            await wrapper.start(test_token)

        assert "Connection failed" in str(exc_info.value)
        wrapper._client.start.assert_called_once_with(test_token)

    @pytest.mark.asyncio
    async def test_trackers_discord_client_wrapper_close_exception(self):
        """Test DiscordClientWrapper.close with exception."""
        intents = discord.Intents.default()
        intents.messages = True

        wrapper = DiscordClientWrapper(intents)

        wrapper._client.close = mock.AsyncMock(side_effect=Exception("Close failed"))

        with pytest.raises(Exception) as exc_info:
            await wrapper.close()

        assert "Close failed" in str(exc_info.value)
        wrapper._client.close.assert_called_once()

    def test_trackers_discord_client_wrapper_property_consistency(self):
        """Test that DiscordClientWrapper properties match underlying client."""
        intents = discord.Intents.default()
        intents.messages = True

        wrapper = DiscordClientWrapper(intents)

        # Test user property consistency - both should return the same object
        assert wrapper.user is wrapper._client.user

        # Test guilds property consistency - they should contain the same guilds
        # (even though they're different SequenceProxy instances)
        assert list(wrapper.guilds) == list(wrapper._client.guilds)

        # Test is_ready method consistency
        wrapper._client.is_ready = mock.Mock(return_value=True)
        assert wrapper.is_ready() is True
        wrapper._client.is_ready.assert_called_once()

        # Test is_closed method consistency
        wrapper._client.is_closed = mock.Mock(return_value=False)
        assert wrapper.is_closed() is False
        wrapper._client.is_closed.assert_called_once()


@pytest.mark.django_db
class TestDiscordTracker:
    """Testing class for :class:`trackers.discord.DiscordTracker`."""

    # Fixtures
    @pytest.fixture
    def discord_config(self):
        """Provide Discord configuration."""
        return {
            "bot_user_id": 123456789012345678,
            "token": "test_token",
            "auto_discover_channels": True,
            "excluded_channel_types": ["voice", "stage"],
            "excluded_channels": [999999999999999999],
            "included_channels": [888888888888888888],
        }

    @pytest.fixture
    def guilds_collection(self):
        """Provide guild list."""
        return [111111111111111111, 222222222222222222]

    @pytest.fixture
    def mock_client_wrapper(self):
        """Provide mock client wrapper."""
        return MockDiscordClientWrapper()

    @pytest.fixture
    def mock_message(self, mocker):
        """Create a mock Discord message."""
        message = mocker.MagicMock(spec=discord.Message)
        message.author.bot = False
        message.guild = mocker.MagicMock()
        message.guild.id = 111111111111111111
        message.guild.name = "Test Guild"
        message.channel.id = 123456789012345678
        message.channel.name = "test-channel"
        message.id = 987654321098765432
        message.content = "Hello <@123456789012345678>"
        message.mentions = []
        message.reference = None
        message.jump_url = "https://discord.com/channels/111111111111111111/123456789012345678/987654321098765432"
        message.created_at = datetime.now()
        return message

    @pytest.fixture
    def mock_guild(self, mocker):
        """Create a mock Discord guild."""
        guild = mocker.MagicMock(spec=discord.Guild)
        guild.id = 111111111111111111
        guild.name = "Test Guild"
        return guild

    @pytest.fixture
    def mock_channel(self, mocker):
        """Create a mock Discord channel."""
        channel = mocker.MagicMock(spec=discord.TextChannel)
        channel.id = 123456789012345678
        channel.name = "test-channel"
        channel.type = discord.ChannelType.text
        channel.guild = mocker.MagicMock()
        channel.guild.id = 111111111111111111
        # Ensure consistent mocking by setting a specific ID for the mock
        channel._mock_name = "MockTextChannel"
        return channel

    # Initialization tests
    def test_trackers_discord_init_with_guilds_collection(
        self, discord_config, guilds_collection, mock_client_wrapper
    ):
        """Test initialization with guild list and custom client wrapper."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        assert instance.bot_user_id == 123456789012345678
        assert instance.token == "test_token"
        assert instance.tracked_guilds == guilds_collection
        assert instance.auto_discover_channels is True
        assert instance.excluded_channel_types == ["voice", "stage"]
        assert instance.client == mock_client_wrapper

    def test_trackers_discord_init_without_guilds_collection(
        self, discord_config, mock_client_wrapper
    ):
        """Test initialization without guild list."""
        instance = DiscordTracker(
            lambda x: None, discord_config, client_wrapper=mock_client_wrapper
        )

        assert instance.tracked_guilds == []
        assert instance.auto_discover_channels is True

    def test_trackers_discord_init_default_client(
        self, discord_config, guilds_collection
    ):
        """Test initialization with default client wrapper."""
        instance = DiscordTracker(lambda x: None, discord_config, guilds_collection)

        assert instance.client is not None
        assert isinstance(instance.client, DiscordClientWrapper)

    # Event handler tests
    def test_trackers_discord_setup_events(
        self, discord_config, guilds_collection, mock_client_wrapper
    ):
        """Test _setup_events method."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        instance._setup_events()

        # Verify event handlers were registered
        assert "_on_ready" in mock_client_wrapper._event_handlers
        assert "_on_message" in mock_client_wrapper._event_handlers
        assert "_on_guild_join" in mock_client_wrapper._event_handlers
        assert "_on_guild_remove" in mock_client_wrapper._event_handlers

    # Fix the first test - test_trackers_discord_on_ready

    @pytest.mark.asyncio
    async def test_trackers_discord_on_ready(
        self, discord_config, guilds_collection, mock_client_wrapper, mocker
    ):
        """Test _on_ready event handler."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        # Mock dependencies
        instance.logger = mock.MagicMock()
        mock_discover = mock.AsyncMock()
        instance._discover_all_guild_channels = mock_discover
        mock_log_action = mocker.patch(
            "trackers.discord.DiscordTracker.log_action", new_callable=mock.AsyncMock
        )
        instance.log_action = mock_log_action

        # Setup client state - create a proper mock with name attribute
        mock_user = mock.MagicMock()
        mock_user.name = "TestBot"
        # Set the string representation to show the name
        mock_user.__str__ = mock.Mock(return_value="TestBot")
        mock_client_wrapper.user = mock_user
        mock_client_wrapper.guilds = [mock.MagicMock(), mock.MagicMock()]

        # Setup tracking state
        instance.guild_channels = {111111111111111111: [123456789012345678]}
        instance.all_tracked_channels = {123456789012345678}

        await instance._on_ready()

        # Verify behavior - check that the calls were made with the expected content
        # Get the actual string arguments that were passed to logger.info
        logged_messages = []
        for call in instance.logger.info.call_args_list:
            # Extract the first argument (the message string)
            if call.args:
                logged_messages.append(str(call.args[0]))

        # Check if our expected messages are in the logged messages
        assert any(
            "Discord bot logged in as" in msg and "TestBot" in msg
            for msg in logged_messages
        )
        assert any("Connected to 2 guilds" in msg for msg in logged_messages)
        mock_discover.assert_called_once()
        mock_log_action.assert_any_call(
            "connected", "Logged in as TestBot, tracking 1 channels across 1 guilds"
        )

    @pytest.mark.asyncio
    async def test_trackers_discord_on_message(
        self,
        discord_config,
        guilds_collection,
        mock_client_wrapper,
        mock_message,
        mocker,
    ):
        """Test _on_message event handler."""
        mock_log_action = mocker.patch(
            "trackers.discord.DiscordTracker.log_action", new_callable=mock.AsyncMock
        )
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )
        instance.log_action = mock_log_action

        mock_handle = mock.AsyncMock()
        instance._handle_new_message = mock_handle

        await instance._on_message(mock_message)

        mock_handle.assert_called_once_with(mock_message)

    @pytest.mark.asyncio
    async def test_trackers_discord_on_guild_join(
        self, discord_config, guilds_collection, mock_client_wrapper, mock_guild, mocker
    ):
        """Test _on_guild_join event handler."""
        mock_log_action = mocker.patch(
            "trackers.discord.DiscordTracker.log_action", new_callable=mock.AsyncMock
        )
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )
        instance.log_action = mock_log_action

        instance.logger = mock.MagicMock()
        mock_discover = mock.AsyncMock()
        instance._discover_guild_channels = mock_discover

        mock_guild.name = "New Guild"
        mock_guild.id = 333333333333333333

        await instance._on_guild_join(mock_guild)

        instance.logger.info.assert_called_once_with(
            "Joined new guild: New Guild (ID: 333333333333333333)"
        )
        mock_discover.assert_called_once_with(mock_guild)
        assert mock_log_action.call_count == 1
        mock_log_action.assert_called_with("guild_joined", "Guild: New Guild")

    @pytest.mark.asyncio
    async def test_trackers_discord_on_guild_remove(
        self, discord_config, guilds_collection, mock_client_wrapper, mock_guild, mocker
    ):
        """Test _on_guild_remove event handler."""
        mock_log_action = mocker.patch(
            "trackers.discord.DiscordTracker.log_action", new_callable=mock.AsyncMock
        )
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )
        instance.log_action = mock_log_action

        instance.logger = mock.MagicMock()

        # Add guild to tracking
        instance.guild_channels = {mock_guild.id: [123456789012345678]}
        instance._update_all_tracked_channels()

        mock_guild.name = "Old Guild"
        mock_guild.id = 333333333333333333

        await instance._on_guild_remove(mock_guild)

        instance.logger.info.assert_called_once_with(
            "Left guild: Old Guild (ID: 333333333333333333)"
        )
        # Guild should be removed from tracking
        assert mock_guild.id not in instance.guild_channels
        assert mock_log_action.call_count == 1
        mock_log_action.assert_called_with("guild_left", "Guild: Old Guild")

    # Guild and channel management tests
    def test_trackers_discord_remove_guild_from_tracking(
        self, discord_config, guilds_collection, mock_client_wrapper
    ):
        """Test _remove_guild_from_tracking method."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        # Setup tracking state
        instance.guild_channels = {
            111111111111111111: [123456789012345678],
            222222222222222222: [234567890123456789],
        }
        instance._update_all_tracked_channels()

        initial_channel_count = len(instance.all_tracked_channels)

        instance._remove_guild_from_tracking(111111111111111111)

        # Verify guild was removed
        assert 111111111111111111 not in instance.guild_channels
        assert 222222222222222222 in instance.guild_channels
        assert len(instance.all_tracked_channels) == initial_channel_count - 1

    def test_trackers_discord_remove_guild_from_tracking_not_present(
        self, discord_config, guilds_collection, mock_client_wrapper
    ):
        """Test _remove_guild_from_tracking when guild not in tracking."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        # Setup tracking state
        instance.guild_channels = {111111111111111111: [123456789012345678]}
        instance._update_all_tracked_channels()

        initial_guild_count = len(instance.guild_channels)
        initial_channel_count = len(instance.all_tracked_channels)

        # Remove guild that's not in tracking
        instance._remove_guild_from_tracking(999999999999999999)

        # Verify no changes
        assert len(instance.guild_channels) == initial_guild_count
        assert len(instance.all_tracked_channels) == initial_channel_count

    # Update the test that uses the old get_guild pattern

    def test_trackers_discord_get_guilds_to_process_specific_guilds(
        self, discord_config, guilds_collection, mock_client_wrapper
    ):
        """Test _get_guilds_to_process with specific guild list."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        # Mock guild retrieval
        mock_guild1 = mock.MagicMock()

        # Use the MagicMock properly
        def get_guild_side_effect(guild_id):
            if guild_id == 111111111111111111:
                return mock_guild1
            return None

        mock_client_wrapper.get_guild.side_effect = get_guild_side_effect

        guilds = instance._get_guilds_to_process()

        # Should only include guilds that were found
        assert len(guilds) == 1
        assert mock_guild1 in guilds

    def test_trackers_discord_get_guilds_to_process_all_guilds(
        self, discord_config, mock_client_wrapper
    ):
        """Test _get_guilds_to_process without specific guild list."""
        instance = DiscordTracker(
            lambda x: None, discord_config, client_wrapper=mock_client_wrapper
        )

        # Mock client guilds
        mock_guild1 = mock.MagicMock()
        mock_guild2 = mock.MagicMock()
        mock_client_wrapper.guilds = [mock_guild1, mock_guild2]

        guilds = instance._get_guilds_to_process()

        # Should return all client guilds
        assert guilds == [mock_guild1, mock_guild2]

    # Channel trackability tests
    def test_trackers_discord_is_channel_trackable_manually_included(
        self, discord_config, guilds_collection, mock_client_wrapper
    ):
        """Test _is_channel_trackable with manually included channel."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        mock_channel = mock.MagicMock()
        mock_channel.id = 888888888888888888  # In included_channels

        result = instance._is_channel_trackable(mock_channel, 111111111111111111)

        # Should return True immediately for manually included channels
        assert result is True

    def test_trackers_discord_is_channel_trackable_manually_excluded(
        self, discord_config, guilds_collection, mock_client_wrapper
    ):
        """Test _is_channel_trackable with manually excluded channel."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        mock_channel = mock.MagicMock()
        mock_channel.id = 999999999999999999  # In excluded_channels

        result = instance._is_channel_trackable(mock_channel, 111111111111111111)

        # Should return False for manually excluded channels
        assert result is False

    def test_trackers_discord_is_channel_trackable_excluded_type(
        self, discord_config, guilds_collection, mock_client_wrapper
    ):
        """Test _is_channel_trackable with excluded channel type."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        mock_channel = mock.MagicMock()
        mock_channel.id = 123456789012345678
        mock_channel.type = discord.ChannelType.voice  # In excluded_channel_types

        result = instance._is_channel_trackable(mock_channel, 111111111111111111)

        # Should return False for excluded channel types
        assert result is False

    def test_trackers_discord_is_channel_trackable_no_permissions(
        self, discord_config, guilds_collection, mock_client_wrapper
    ):
        """Test _is_channel_trackable without permissions."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        mock_channel = mock.MagicMock()
        mock_channel.id = 123456789012345678
        mock_channel.type = discord.ChannelType.text
        mock_channel.permissions_for = mock.MagicMock()

        # Mock bot member exists but no permissions
        mock_bot_member = mock.MagicMock()
        mock_permissions = mock.MagicMock()
        mock_permissions.read_messages = False
        mock_permissions.read_message_history = False
        mock_channel.permissions_for.return_value = mock_permissions
        mock_channel.guild.get_member.return_value = mock_bot_member
        mock_client_wrapper.user.id = 123456789012345678

        result = instance._is_channel_trackable(mock_channel, 111111111111111111)

        # Should return False when no read permissions
        assert result is False
        mock_channel.permissions_for.assert_called_once_with(mock_bot_member)

    def test_trackers_discord_is_channel_trackable_no_bot_member(
        self, discord_config, guilds_collection, mock_client_wrapper
    ):
        """Test _is_channel_trackable when bot member not found."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        mock_channel = mock.MagicMock()
        mock_channel.id = 123456789012345678
        mock_channel.type = discord.ChannelType.text
        mock_channel.permissions_for = mock.MagicMock()

        # Mock bot member not found
        mock_channel.guild.get_member.return_value = None
        mock_client_wrapper.user.id = 123456789012345678

        result = instance._is_channel_trackable(mock_channel, 111111111111111111)

        # Should return False when bot member not found
        assert result is False

    def test_trackers_discord_is_channel_trackable_permission_exception(
        self, discord_config, guilds_collection, mock_client_wrapper
    ):
        """Test _is_channel_trackable when permission check raises exception."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        mock_channel = mock.MagicMock()
        mock_channel.id = 123456789012345678
        mock_channel.type = discord.ChannelType.text
        mock_channel.permissions_for = mock.MagicMock(
            side_effect=Exception("Permission error")
        )

        result = instance._is_channel_trackable(mock_channel, 111111111111111111)

        # Should return False on exception
        assert result is False

    def test_trackers_discord_is_channel_trackable_no_permission_method(
        self, discord_config, guilds_collection, mock_client_wrapper
    ):
        """Test _is_channel_trackable with channel that has no permissions_for."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        mock_channel = mock.MagicMock()
        mock_channel.id = 123456789012345678
        mock_channel.type = discord.ChannelType.text
        # Remove permissions_for method
        del mock_channel.permissions_for

        result = instance._is_channel_trackable(mock_channel, 111111111111111111)

        # Should return True for channels without permission checks
        assert result is True

    def test_trackers_discord_has_channel_permission_success(
        self, discord_config, guilds_collection, mock_client_wrapper
    ):
        """Test _has_channel_permission with successful permission check."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        mock_channel = mock.MagicMock()
        mock_channel.permissions_for = mock.MagicMock()

        # Mock bot member with permissions
        mock_bot_member = mock.MagicMock()
        mock_permissions = mock.MagicMock()
        mock_permissions.read_messages = True
        mock_permissions.read_message_history = True
        mock_channel.permissions_for.return_value = mock_permissions
        mock_channel.guild.get_member.return_value = mock_bot_member
        mock_client_wrapper.user.id = 123456789012345678

        result = instance._has_channel_permission(mock_channel)

        assert result is True
        mock_channel.permissions_for.assert_called_once_with(mock_bot_member)

    # Message processing tests
    def test_trackers_discord_should_process_message_bot_message(
        self, discord_config, guilds_collection, mock_client_wrapper, mock_message
    ):
        """Test _should_process_message with bot message."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        mock_message.author.bot = True

        result = instance._should_process_message(mock_message)

        assert result is False

    def test_trackers_discord_should_process_message_direct_message(
        self, discord_config, guilds_collection, mock_client_wrapper, mock_message
    ):
        """Test _should_process_message with direct message."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        mock_message.guild = None  # Direct message

        result = instance._should_process_message(mock_message)

        assert result is False

    def test_trackers_discord_should_process_message_untracked_guild(
        self, discord_config, guilds_collection, mock_client_wrapper, mock_message
    ):
        """Test _should_process_message from untracked guild."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        mock_message.guild.id = 999999999999999999  # Not in tracked_guilds

        result = instance._should_process_message(mock_message)

        assert result is False

    def test_trackers_discord_should_process_message_untracked_channel(
        self, discord_config, guilds_collection, mock_client_wrapper, mock_message
    ):
        """Test _should_process_message from untracked channel."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        instance.all_tracked_channels = {999999999999999999}  # Different channel

        result = instance._should_process_message(mock_message)

        assert result is False

    def test_trackers_discord_should_process_message_no_mention(
        self, discord_config, guilds_collection, mock_client_wrapper, mock_message
    ):
        """Test _should_process_message without bot mention."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        instance.all_tracked_channels = {mock_message.channel.id}
        mock_message.content = "Hello everyone"  # No mention
        mock_message.mentions = []

        result = instance._should_process_message(mock_message)

        assert result is False

    def test_trackers_discord_should_process_message_success(
        self, discord_config, guilds_collection, mock_client_wrapper, mock_message
    ):
        """Test _should_process_message with valid conditions."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        instance.all_tracked_channels = {mock_message.channel.id}

        result = instance._should_process_message(mock_message)

        assert result is True

    def test_trackers_discord_is_bot_mentioned_user_mention(
        self, discord_config, guilds_collection, mock_client_wrapper, mock_message
    ):
        """Test _is_bot_mentioned with user mention."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        mock_user = mock.MagicMock()
        mock_user.id = 123456789012345678
        mock_message.mentions = [mock_user]
        mock_message.content = "Hello"

        result = instance._is_bot_mentioned(mock_message)

        assert result is True

    def test_trackers_discord_is_bot_mentioned_string_mention(
        self, discord_config, guilds_collection, mock_client_wrapper, mock_message
    ):
        """Test _is_bot_mentioned with string mention."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        mock_message.mentions = []
        mock_message.content = "Hello <@123456789012345678>"

        result = instance._is_bot_mentioned(mock_message)

        assert result is True

    def test_trackers_discord_is_bot_mentioned_no_mention(
        self, discord_config, guilds_collection, mock_client_wrapper, mock_message
    ):
        """Test _is_bot_mentioned without mention."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        mock_message.mentions = []
        mock_message.content = "Hello everyone"

        result = instance._is_bot_mentioned(mock_message)

        assert result is False

    @pytest.mark.asyncio
    async def test_trackers_discord_handle_new_message_success(
        self,
        discord_config,
        guilds_collection,
        mock_client_wrapper,
        mock_message,
        mocker,
    ):
        """Test _handle_new_message successful processing."""
        mock_log_action = mocker.patch(
            "trackers.discord.DiscordTracker.log_action", new_callable=mock.AsyncMock
        )
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )
        instance.log_action = mock_log_action

        instance.logger = mock.MagicMock()
        instance.all_tracked_channels = {mock_message.channel.id}

        # Mock dependencies
        mock_extract = mock.AsyncMock(return_value={})
        instance.extract_mention_data = mock_extract
        mock_process = mock.MagicMock(return_value=True)
        instance.process_mention = mock_process
        mock_is_processed = mock.MagicMock(return_value=False)
        instance.is_processed = mock_is_processed

        await instance._handle_new_message(mock_message)

        mock_extract.assert_called_once_with(mock_message)
        mock_process.assert_called_once_with(
            (
                f"discord_{mock_message.guild.id}_"
                f"{mock_message.channel.id}_{mock_message.id}"
            ),
            {},
            f"@{instance.bot_user_id}",
        )
        mock_is_processed.assert_called_once()
        assert len(instance.processed_messages) == 1

    @pytest.mark.asyncio
    async def test_trackers_discord_handle_new_message_already_processed(
        self,
        discord_config,
        guilds_collection,
        mock_client_wrapper,
        mock_message,
        mocker,
    ):
        """Test _handle_new_message with already processed message."""
        mock_log_action = mocker.patch(
            "trackers.discord.DiscordTracker.log_action", new_callable=mock.AsyncMock
        )
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )
        instance.log_action = mock_log_action

        instance.all_tracked_channels = {mock_message.channel.id}

        # Mock message already processed
        message_id = f"discord_{mock_message.guild.id}_{mock_message.channel.id}_{mock_message.id}"
        instance.processed_messages = {message_id}

        mock_extract = mock.AsyncMock()
        instance.extract_mention_data = mock_extract
        mock_process = mock.MagicMock()
        instance.process_mention = mock_process
        mock_is_processed = mock.MagicMock(return_value=True)
        instance.is_processed = mock_is_processed

        await instance._handle_new_message(mock_message)

        mock_extract.assert_not_called()
        mock_process.assert_not_called()

    @pytest.mark.asyncio
    async def test_trackers_discord_handle_new_message_process_mention_false(
        self,
        discord_config,
        guilds_collection,
        mock_client_wrapper,
        mock_message,
        mocker,
    ):
        """Test _handle_new_message when process_mention returns False."""
        mock_log_action = mocker.patch(
            "trackers.discord.DiscordTracker.log_action", new_callable=mock.AsyncMock
        )
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )
        instance.log_action = mock_log_action

        instance.all_tracked_channels = {mock_message.channel.id}

        # Mock dependencies
        mock_extract = mock.AsyncMock(return_value={})
        instance.extract_mention_data = mock_extract
        mock_process = mock.MagicMock(return_value=False)
        instance.process_mention = mock_process
        mock_is_processed = mock.MagicMock(return_value=False)
        instance.is_processed = mock_is_processed

        await instance._handle_new_message(mock_message)

        mock_extract.assert_called_once()
        mock_process.assert_called_once()
        # Message should NOT be added to processed_messages when process_mention returns False
        assert len(instance.processed_messages) == 0

    # Extract mention data tests
    @pytest.mark.asyncio
    async def test_trackers_discord_extract_mention_data_with_reply(
        self,
        discord_config,
        guilds_collection,
        mock_client_wrapper,
        mock_message,
        mocker,
    ):
        """Test extract_mention_data with message reply."""
        mock_log_action = mocker.patch(
            "trackers.discord.DiscordTracker.log_action", new_callable=mock.AsyncMock
        )
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )
        instance.log_action = mock_log_action

        # Create replied message
        mock_replied = mock.MagicMock()
        mock_replied.jump_url = "https://discord.com/channels/111111111111111111/123456789012345678/111111111111111111"
        mock_replied.author.id = 555555555555555555
        mock_replied.author.name = "replied_user"
        mock_replied.author.display_name = "Replied User"
        mock_replied.content = "This is the replied message content."

        mock_message.reference = mock.MagicMock()
        mock_message.reference.resolved = mock_replied

        result = await instance.extract_mention_data(mock_message)

        assert result["suggester"] == mock_message.author.id
        assert result["contributor"] == 555555555555555555
        assert result["contribution_url"] == mock_replied.jump_url
        assert result["discord_guild"] == "Test Guild"
        assert result["discord_channel"] == "test-channel"
        assert result["contribution"] == "This is the replied message content."

    @pytest.mark.asyncio
    async def test_trackers_discord_extract_mention_data_no_reply(
        self, discord_config, guilds_collection, mock_client_wrapper, mock_message
    ):
        """Test extract_mention_data without reply."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        mock_message.reference = None
        mock_message.content = "This is a standalone message."

        result = await instance.extract_mention_data(mock_message)

        assert result["suggester"] == mock_message.author.id
        assert result["contributor"] == mock_message.author.id
        assert result["contribution_url"] == mock_message.jump_url
        assert result["contribution"] == "This is a standalone message."

    @pytest.mark.asyncio
    async def test_trackers_discord_extract_mention_data_reply_no_jump_url(
        self, discord_config, guilds_collection, mock_client_wrapper, mock_message
    ):
        """Test extract_mention_data with reply that has no jump_url."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        # Create replied message without jump_url
        mock_replied = mock.MagicMock()
        mock_replied.author.id = 555555555555555555
        mock_replied.author.name = "replied_user"
        mock_replied.author.display_name = "Replied User"
        mock_replied.content = "This is the replied message."

        # Remove jump_url attribute
        del mock_replied.jump_url

        mock_message.reference = mock.MagicMock()
        mock_message.reference.resolved = mock_replied
        mock_message.content = "This is the original message."

        result = await instance.extract_mention_data(mock_message)

        # Should fall back to current message URL
        assert result["contribution_url"] == mock_message.jump_url
        assert result["contributor"] == mock_message.author.id
        assert result["contribution"] == "This is the original message."

    @pytest.mark.asyncio
    async def test_trackers_discord_extract_mention_data_empty_content(
        self, discord_config, guilds_collection, mock_client_wrapper, mock_message
    ):
        """Test extract_mention_data with empty message content."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        mock_message.content = None
        mock_message.reference = None

        result = await instance.extract_mention_data(mock_message)

        assert result["content"] == ""
        assert result["contribution"] == ""

    # Channel history checking tests
    def test_trackers_discord_is_rate_limited_true(
        self, discord_config, guilds_collection, mock_client_wrapper
    ):
        """Test _is_rate_limited when rate limited."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        # Set recent last check
        instance.last_channel_check[123456789012345678] = datetime.now()

        result = instance._is_rate_limited(123456789012345678)

        assert result is True

    def test_trackers_discord_is_rate_limited_false(
        self, discord_config, guilds_collection, mock_client_wrapper
    ):
        """Test _is_rate_limited when not rate limited."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        # Set old last check
        instance.last_channel_check[123456789012345678] = datetime.now() - timedelta(
            seconds=10
        )

        result = instance._is_rate_limited(123456789012345678)

        assert result is False

    def test_trackers_discord_is_rate_limited_no_previous_check(
        self, discord_config, guilds_collection, mock_client_wrapper
    ):
        """Test _is_rate_limited when no previous check."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        result = instance._is_rate_limited(123456789012345678)

        assert result is False

    @pytest.mark.asyncio
    async def test_trackers_discord_check_channel_history_rate_limited(
        self, discord_config, guilds_collection, mock_client_wrapper
    ):
        """Test _check_channel_history when rate limited."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        # Set rate limited
        instance.last_channel_check[123456789012345678] = datetime.now()

        result = await instance._check_channel_history(
            123456789012345678, 111111111111111111
        )

        assert result == 0

    # Historical message processing tests
    @pytest.mark.asyncio
    async def test_trackers_discord_process_channel_messages_success(
        self, discord_config, guilds_collection, mock_client_wrapper, mock_message
    ):
        """Test _process_channel_messages with successful mentions."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        # Mock channel history
        mock_channel = mock.MagicMock()
        mock_channel.history.return_value.__aiter__.return_value = [mock_message]

        # Mock dependencies
        mock_extract = mock.AsyncMock(return_value={})
        instance.extract_mention_data = mock_extract
        mock_process = mock.MagicMock(return_value=True)
        instance.process_mention = mock_process
        mock_is_processed = mock.MagicMock(return_value=False)
        instance.is_processed = mock_is_processed

        result = await instance._process_channel_messages(
            mock_channel, 111111111111111111
        )

        assert result == 1
        mock_extract.assert_called_once_with(mock_message)
        mock_process.assert_called_once_with(
            f"discord_111111111111111111_{mock_channel.id}_{mock_message.id}",
            {},
            f"@{instance.bot_user_id}",
        )

    @pytest.mark.asyncio
    async def test_trackers_discord_process_channel_messages_bot_message(
        self, discord_config, guilds_collection, mock_client_wrapper, mock_message
    ):
        """Test _process_channel_messages with bot message."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        mock_message.author.bot = True

        # Mock channel history
        mock_channel = mock.MagicMock()
        mock_channel.history.return_value.__aiter__.return_value = [mock_message]

        result = await instance._process_channel_messages(
            mock_channel, 111111111111111111
        )

        assert result == 0  # Bot messages should be skipped

    @pytest.mark.asyncio
    async def test_trackers_discord_process_channel_messages_no_mention(
        self, discord_config, guilds_collection, mock_client_wrapper, mock_message
    ):
        """Test _process_channel_messages without bot mention."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        mock_message.content = "Hello everyone"  # No mention
        mock_message.mentions = []

        # Mock channel history
        mock_channel = mock.MagicMock()
        mock_channel.history.return_value.__aiter__.return_value = [mock_message]

        result = await instance._process_channel_messages(
            mock_channel, 111111111111111111
        )

        assert result == 0  # Messages without mentions should be skipped

    @pytest.mark.asyncio
    async def test_trackers_discord_process_channel_messages_already_processed(
        self, discord_config, guilds_collection, mock_client_wrapper, mock_message
    ):
        """Test _process_channel_messages with already processed message."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        # Mock channel history
        mock_channel = mock.MagicMock()
        mock_channel.history.return_value.__aiter__.return_value = [mock_message]

        # Mock message already processed
        message_id = f"discord_111111111111111111_{mock_channel.id}_{mock_message.id}"
        instance.processed_messages = {message_id}

        mock_is_processed = mock.MagicMock(return_value=True)
        instance.is_processed = mock_is_processed

        result = await instance._process_channel_messages(
            mock_channel, 111111111111111111
        )

        assert result == 0  # Already processed messages should be skipped

    @pytest.mark.asyncio
    async def test_trackers_discord_process_channel_messages_process_false(
        self, discord_config, guilds_collection, mock_client_wrapper, mock_message
    ):
        """Test _process_channel_messages when process_mention returns False."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        # Mock channel history
        mock_channel = mock.MagicMock()
        mock_channel.history.return_value.__aiter__.return_value = [mock_message]

        # Mock dependencies
        mock_extract = mock.AsyncMock(return_value={})
        instance.extract_mention_data = mock_extract
        mock_process = mock.MagicMock(return_value=False)
        instance.process_mention = mock_process
        mock_is_processed = mock.MagicMock(return_value=False)
        instance.is_processed = mock_is_processed

        result = await instance._process_channel_messages(
            mock_channel, 111111111111111111
        )

        assert result == 0  # Should not count when process_mention returns False

    # HTTP Exception handling tests
    @pytest.mark.asyncio
    async def test_trackers_discord_handle_http_exception_rate_limit(
        self, discord_config, guilds_collection, mock_client_wrapper
    ):
        """Test _handle_http_exception with rate limit."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        mock_exception = mock.MagicMock()
        mock_exception.status = 429
        mock_exception.retry_after = 2.5

        with mock.patch("asyncio.sleep") as mock_sleep:
            result = await instance._handle_http_exception(
                mock_exception, 123456789012345678
            )

        assert result == 0
        mock_sleep.assert_called_once_with(2.5)

    @pytest.mark.asyncio
    async def test_trackers_discord_handle_http_exception_other_error(
        self, discord_config, guilds_collection, mock_client_wrapper
    ):
        """Test _handle_http_exception with non-rate-limit error."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        instance.logger = mock.MagicMock()

        mock_exception = mock.MagicMock()
        mock_exception.status = 500
        mock_exception.retry_after = None

        result = await instance._handle_http_exception(
            mock_exception, 123456789012345678
        )

        assert result == 0
        instance.logger.error.assert_called_once()

    # Forbidden exception handling tests
    @pytest.mark.asyncio
    async def test_trackers_discord_handle_forbidden_exception(
        self, discord_config, guilds_collection, mock_client_wrapper
    ):
        """Test _handle_forbidden_exception."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        instance.logger = mock.MagicMock()

        # Add channel to tracking first
        instance.guild_channels = {111111111111111111: [123456789012345678]}
        instance._update_all_tracked_channels()

        result = await instance._handle_forbidden_exception(
            123456789012345678, 111111111111111111
        )

        assert result == 0
        instance.logger.warning.assert_called_once()
        # Channel should be removed from tracking
        assert 123456789012345678 not in instance.guild_channels.get(
            111111111111111111, []
        )

    # Channel removal tests
    def test_trackers_discord_remove_channel_from_tracking(
        self, discord_config, guilds_collection, mock_client_wrapper
    ):
        """Test _remove_channel_from_tracking."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        # Setup tracking state
        instance.guild_channels = {
            111111111111111111: [123456789012345678, 234567890123456789]
        }
        instance._update_all_tracked_channels()

        initial_channel_count = len(instance.all_tracked_channels)

        instance._remove_channel_from_tracking(123456789012345678, 111111111111111111)

        # Verify channel was removed
        assert 123456789012345678 not in instance.guild_channels[111111111111111111]
        assert 234567890123456789 in instance.guild_channels[111111111111111111]
        assert len(instance.all_tracked_channels) == initial_channel_count - 1

    def test_trackers_discord_remove_channel_from_tracking_not_present(
        self, discord_config, guilds_collection, mock_client_wrapper
    ):
        """Test _remove_channel_from_tracking when channel not in tracking."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        # Setup tracking state
        instance.guild_channels = {111111111111111111: [123456789012345678]}
        instance._update_all_tracked_channels()

        initial_channel_count = len(instance.all_tracked_channels)

        # Remove channel that's not in tracking
        instance._remove_channel_from_tracking(999999999999999999, 111111111111111111)

        # Verify no changes
        assert len(instance.guild_channels[111111111111111111]) == 1
        assert len(instance.all_tracked_channels) == initial_channel_count

    def test_trackers_discord_remove_channel_from_tracking_guild_not_present(
        self, discord_config, guilds_collection, mock_client_wrapper
    ):
        """Test _remove_channel_from_tracking when guild not in tracking."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        # Setup tracking state with different guild
        instance.guild_channels = {222222222222222222: [123456789012345678]}
        instance._update_all_tracked_channels()

        initial_channel_count = len(instance.all_tracked_channels)

        # Remove channel from guild that's not in tracking
        instance._remove_channel_from_tracking(123456789012345678, 111111111111111111)

        # Verify no changes
        assert len(instance.guild_channels[222222222222222222]) == 1
        assert len(instance.all_tracked_channels) == initial_channel_count

    # Async channel checking tests
    @pytest.mark.asyncio
    async def test_trackers_discord_check_channel_with_semaphore(
        self, discord_config, guilds_collection, mock_client_wrapper
    ):
        """Test _check_channel_with_semaphore."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        mock_check = mock.AsyncMock(return_value=3)
        instance._check_channel_history = mock_check

        result = await instance._check_channel_with_semaphore(
            123456789012345678, 111111111111111111
        )

        assert result == 3
        mock_check.assert_called_once_with(123456789012345678, 111111111111111111)

    @pytest.mark.asyncio
    async def test_trackers_discord_check_mentions_async_not_ready(
        self, discord_config, guilds_collection, mock_client_wrapper
    ):
        """Test check_mentions_async when client not ready."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        mock_client_wrapper.ready = False

        result = await instance.check_mentions_async()

        assert result == 0

    @pytest.mark.asyncio
    async def test_trackers_discord_check_mentions_async_success(
        self, discord_config, guilds_collection, mock_client_wrapper
    ):
        """Test check_mentions_async with successful results."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        mock_client_wrapper.ready = True

        # Setup tracking state
        instance.guild_channels = {
            111111111111111111: [123456789012345678, 234567890123456789],
            222222222222222222: [345678901234567890],
        }

        # Mock the semaphore method to return test values
        async def mock_check_with_semaphore(channel_id, guild_id):
            return 1  # Each channel finds 1 mention

        instance._check_channel_with_semaphore = mock_check_with_semaphore

        result = await instance.check_mentions_async()

        # Should process 3 channels, each returning 1 mention
        assert result == 3

    @pytest.mark.asyncio
    async def test_trackers_discord_check_mentions_async_with_exceptions(
        self, discord_config, guilds_collection, mock_client_wrapper
    ):
        """Test check_mentions_async with exceptions in some channels."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        instance.logger = mock.MagicMock()
        mock_client_wrapper.ready = True

        # Setup tracking state
        instance.guild_channels = {
            111111111111111111: [123456789012345678, 234567890123456789]
        }

        # Mock mixed results: one success, one exception
        async def mock_check_with_semaphore(channel_id, guild_id):
            if channel_id == 123456789012345678:
                return 2
            else:
                raise Exception("Test error")

        instance._check_channel_with_semaphore = mock_check_with_semaphore

        result = await instance.check_mentions_async()

        # Should only count successful results (2), log the error
        assert result == 2
        instance.logger.error.assert_called_once()

    # Result processing tests
    def test_trackers_discord_process_check_results_all_success(
        self, discord_config, guilds_collection, mock_client_wrapper
    ):
        """Test _process_check_results with all successful results."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        instance.logger = mock.MagicMock()

        results = [2, 3, 1, 0]  # Mentions from different channels
        total_mentions = instance._process_check_results(results)

        assert total_mentions == 6
        instance.logger.error.assert_not_called()

    def test_trackers_discord_process_check_results_with_exceptions(
        self, discord_config, guilds_collection, mock_client_wrapper
    ):
        """Test _process_check_results with exceptions."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        instance.logger = mock.MagicMock()

        results = [2, Exception("Test error 1"), 1, Exception("Test error 2")]
        total_mentions = instance._process_check_results(results)

        assert total_mentions == 3  # Only count successful results
        assert instance.logger.error.call_count == 2  # Log each exception

    # Periodic task tests
    def test_trackers_discord_should_run_channel_discovery_true(
        self, discord_config, guilds_collection, mock_client_wrapper
    ):
        """Test _should_run_channel_discovery when should run."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        now = datetime.now()
        last_discovery = now - timedelta(seconds=400)  # Over interval

        result = instance._should_run_channel_discovery(now, last_discovery)

        assert result is True

    def test_trackers_discord_should_run_channel_discovery_false(
        self, discord_config, guilds_collection, mock_client_wrapper
    ):
        """Test _should_run_channel_discovery when should not run."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        now = datetime.now()
        last_discovery = now - timedelta(seconds=100)  # Under interval

        result = instance._should_run_channel_discovery(now, last_discovery)

        assert result is False

    def test_trackers_discord_should_run_historical_check_true(
        self, discord_config, guilds_collection, mock_client_wrapper
    ):
        """Test _should_run_historical_check when should run."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        now = datetime.now()
        last_check = now - timedelta(seconds=400)  # Over interval
        interval = 300

        result = instance._should_run_historical_check(now, last_check, interval)

        assert result is True

    def test_trackers_discord_should_run_historical_check_false(
        self, discord_config, guilds_collection, mock_client_wrapper
    ):
        """Test _should_run_historical_check when should not run."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        now = datetime.now()
        last_check = now - timedelta(seconds=100)  # Under interval
        interval = 300

        result = instance._should_run_historical_check(now, last_check, interval)

        assert result is False

    @pytest.mark.asyncio
    async def test_trackers_discord_run_channel_discovery(
        self, discord_config, guilds_collection, mock_client_wrapper
    ):
        """Test _run_channel_discovery."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        instance.logger = mock.MagicMock()
        mock_discover = mock.AsyncMock()
        instance._discover_all_guild_channels = mock_discover

        await instance._run_channel_discovery()

        instance.logger.info.assert_called_once_with(
            "Running periodic channel discovery"
        )
        mock_discover.assert_called_once()

    @pytest.mark.asyncio
    async def test_trackers_discord_run_historical_check(
        self, discord_config, guilds_collection, mock_client_wrapper
    ):
        """Test _run_historical_check."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        instance.logger = mock.MagicMock()
        mock_check = mock.AsyncMock(return_value=5)
        instance.check_mentions_async = mock_check

        await instance._run_historical_check()

        instance.logger.info.assert_any_call("Running periodic historical check")
        instance.logger.info.assert_any_call("Found 5 new mentions in historical check")
        mock_check.assert_called_once()

    @pytest.mark.asyncio
    async def test_trackers_discord_run_historical_check_no_mentions(
        self, discord_config, guilds_collection, mock_client_wrapper
    ):
        """Test _run_historical_check with no mentions found."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        instance.logger = mock.MagicMock()
        mock_check = mock.AsyncMock(return_value=0)
        instance.check_mentions_async = mock_check

        await instance._run_historical_check()

        instance.logger.info.assert_called_once_with(
            "Running periodic historical check"
        )
        # Should not log "Found X new mentions" when 0 mentions
        calls = [call.args[0] for call in instance.logger.info.call_args_list]
        assert "Found" not in " ".join(calls)

    @pytest.mark.asyncio
    async def test_discordtracker_async_interruptible_sleep_full_duration(
        self, discord_config, guilds_collection, mock_client_wrapper, mocker
    ):
        """Test _async_interruptible_sleep sleeps the full duration when no exit conditions occur."""

        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        # No exit interruption
        instance.exit_signal = False
        mock_client_wrapper.is_closed = lambda: False

        sleep_calls = []

        async def fake_sleep(s):
            sleep_calls.append(s)

        mocker.patch("asyncio.sleep", side_effect=fake_sleep)

        await instance._async_interruptible_sleep(seconds=5, step=1)

        # Should sleep 5 times with step=1
        assert sleep_calls == [1, 1, 1, 1, 1]

    @pytest.mark.asyncio
    async def test_discordtracker_async_interruptible_sleep_exit_signal(
        self, discord_config, guilds_collection, mock_client_wrapper, mocker
    ):
        """Test _async_interruptible_sleep stops early when exit_signal becomes True."""

        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        instance.exit_signal = False
        mock_client_wrapper.is_closed = lambda: False

        sleep_calls = []

        async def fake_sleep(s):
            sleep_calls.append(s)
            instance.exit_signal = True  # Trigger exit after first sleep

        mocker.patch("asyncio.sleep", side_effect=fake_sleep)

        await instance._async_interruptible_sleep(seconds=10, step=1)

        # Should sleep only once because exit_signal was set after first chunk
        assert sleep_calls == [1]

    @pytest.mark.asyncio
    async def test_discordtracker_async_interruptible_sleep_client_closed(
        self, discord_config, guilds_collection, mock_client_wrapper, mocker
    ):
        """Test _async_interruptible_sleep stops early when the Discord client closes."""

        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        instance.exit_signal = False

        # Client starts open, closes after one iteration
        mock_client_wrapper.closed = False
        mock_client_wrapper.is_closed = lambda: mock_client_wrapper.closed

        sleep_calls = []

        async def fake_sleep(s):
            sleep_calls.append(s)
            mock_client_wrapper.closed = True  # Close client after first sleep

        mocker.patch("asyncio.sleep", side_effect=fake_sleep)

        await instance._async_interruptible_sleep(seconds=10, step=1)

        # Only one chunk should be slept because client closes after first
        assert sleep_calls == [1]

    # Main loop and continuous operation tests
    @pytest.mark.asyncio
    async def test_trackers_discord_handle_periodic_tasks_both_run(
        self, discord_config, guilds_collection, mock_client_wrapper
    ):
        """Test _handle_periodic_tasks when both tasks should run."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        now = datetime.now()
        last_discovery = now - timedelta(seconds=400)
        last_check = now - timedelta(seconds=400)
        interval = 300

        mock_discovery = mock.AsyncMock()
        instance._run_channel_discovery = mock_discovery
        mock_historical = mock.AsyncMock()
        instance._run_historical_check = mock_historical

        result = await instance._handle_periodic_tasks(
            now, last_discovery, last_check, interval
        )

        mock_discovery.assert_called_once()
        mock_historical.assert_called_once()
        assert result == now  # Should update last_discovery

    @pytest.mark.asyncio
    async def test_trackers_discord_run_main_loop(
        self, discord_config, guilds_collection, mock_client_wrapper
    ):
        """Test _run_main_loop basic operation with interruptible async sleep."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        # Mock client to close after first iteration
        mock_client_wrapper.closed = False

        async def sleep_side_effect(seconds, step=1):
            # After first call, mark client closed so loop exits
            mock_client_wrapper.closed = True

        mock_client_wrapper.is_closed = lambda: mock_client_wrapper.closed

        with mock.patch.object(
            instance, "_async_interruptible_sleep", side_effect=sleep_side_effect
        ) as mock_sleep:
            await instance._run_main_loop(300)

        # Verify our async sleep helper was called with the expected interval
        mock_sleep.assert_called_once_with(10)

    @pytest.mark.asyncio
    async def test_trackers_discord_run_continuous_success(
        self, discord_config, guilds_collection, mock_client_wrapper, mocker
    ):
        """Test run_continuous successful operation with graceful shutdown helpers."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        instance.logger = mocker.MagicMock()
        instance.log_action = mocker.AsyncMock()

        # Track signal registration
        with mock.patch.object(
            instance, "_register_signal_handlers"
        ) as mock_register_signals:
            # Mock client operations
            start_called = False
            close_called = False

            async def mock_start(token):
                nonlocal start_called
                start_called = True
                mock_client_wrapper.ready = True

            async def mock_close():
                nonlocal close_called
                close_called = True
                mock_client_wrapper.closed = True

            mock_client_wrapper.start = mock_start
            mock_client_wrapper.close = mock_close

            # Mock the main loop to raise KeyboardInterrupt immediately
            with mock.patch.object(instance, "_run_main_loop") as mock_loop:
                mock_loop.side_effect = KeyboardInterrupt("Test interrupt")

                await instance.run_continuous(300)

        # Signal handlers should be registered once
        mock_register_signals.assert_called_once()

        instance.logger.info.assert_any_call(
            "Starting multi-guild Discord tracker in continuous mode"
        )
        instance.logger.info.assert_any_call(
            "Multi-guild Discord tracker stopped by user"
        )
        instance.log_action.assert_any_call("started", "Continuous multi-guild mode")
        instance.log_action.assert_any_call("stopped", "User interrupt")
        assert start_called
        assert close_called

    @pytest.mark.asyncio
    async def test_trackers_discord_run_continuous_error(
        self, discord_config, guilds_collection, mock_client_wrapper, mocker
    ):
        """Test run_continuous with error."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        instance.logger = mocker.MagicMock()
        instance.log_action = mocker.AsyncMock()
        instance.cleanup = mocker.AsyncMock()

        test_error = Exception("Test error")

        async def mock_start(token):
            raise test_error

        mock_client_wrapper.start = mock_start

        with mock.patch.object(
            instance, "_register_signal_handlers"
        ) as mock_register_signals:
            with pytest.raises(Exception) as exc_info:
                await instance.run_continuous(300)

        assert exc_info.value == test_error
        mock_register_signals.assert_called_once()
        instance.logger.error.assert_called_once_with(
            "Multi-guild Discord tracker error: Test error"
        )
        instance.log_action.assert_called_with("error", "Tracker error: Test error")
        instance.cleanup.assert_called_once()

    # Statistics tests
    def test_trackers_discord_get_stats(
        self, discord_config, guilds_collection, mock_client_wrapper
    ):
        """Test get_stats method."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        # Setup tracking state
        instance.guild_channels = {
            111111111111111111: [123456789012345678, 234567890123456789],
            222222222222222222: [345678901234567890],
        }
        instance._update_all_tracked_channels()
        instance.processed_messages = {"msg1", "msg2", "msg3"}

        # Mock guild retrieval
        mock_guild1 = mock.MagicMock()
        mock_guild1.name = "Test Guild 1"
        mock_guild2 = mock.MagicMock()
        mock_guild2.name = "Test Guild 2"

        def get_guild_side_effect(guild_id):
            if guild_id == 111111111111111111:
                return mock_guild1
            elif guild_id == 222222222222222222:
                return mock_guild2
            return None

        mock_client_wrapper.get_guild = get_guild_side_effect

        stats = instance.get_stats()

        assert stats["guilds_tracked"] == 2
        assert stats["channels_tracked"] == 3
        assert stats["processed_messages"] == 3
        assert "Test Guild 1" in stats["guild_details"]
        assert "Test Guild 2" in stats["guild_details"]
        assert stats["guild_details"]["Test Guild 1"] == 2
        assert stats["guild_details"]["Test Guild 2"] == 1

    def test_trackers_discord_get_stats_unknown_guild(
        self, discord_config, guilds_collection, mock_client_wrapper
    ):
        """Test get_stats with unknown guild."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        # Setup tracking state with guild that can't be retrieved
        instance.guild_channels = {111111111111111111: [123456789012345678]}
        instance._update_all_tracked_channels()
        instance.processed_messages = set()

        # Mock guild not found - use side_effect instead of return_value
        mock_client_wrapper.get_guild = mock.MagicMock(return_value=None)

        stats = instance.get_stats()

        assert stats["guilds_tracked"] == 1
        assert stats["channels_tracked"] == 1
        assert "Unknown (111111111111111111)" in stats["guild_details"]
        assert stats["guild_details"]["Unknown (111111111111111111)"] == 1

    # Channel discovery tests
    @pytest.mark.asyncio
    async def test_trackers_discord_discover_guild_channels_success(
        self,
        discord_config,
        guilds_collection,
        mock_client_wrapper,
        mock_guild,
        mock_channel,
    ):
        """Test _discover_guild_channels successful discovery."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        instance.logger = mock.MagicMock()

        # Mock guild channels
        mock_guild.fetch_channels = mock.AsyncMock(return_value=[mock_channel])

        # Mock channel trackability
        mock_trackable = mock.MagicMock(return_value=True)
        instance._is_channel_trackable = mock_trackable

        await instance._discover_guild_channels(mock_guild)

        instance.logger.info.assert_called_once_with(
            f"Discovered 1 trackable channels in guild '{mock_guild.name}'"
        )
        assert mock_guild.id in instance.guild_channels
        assert instance.guild_channels[mock_guild.id] == [mock_channel.id]

    @pytest.mark.asyncio
    async def test_trackers_discord_discover_guild_channels_exception(
        self, discord_config, guilds_collection, mock_client_wrapper, mock_guild
    ):
        """Test _discover_guild_channels with exception."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        instance.logger = mock.MagicMock()

        # Mock guild channels to raise exception
        mock_guild.fetch_channels = mock.AsyncMock(side_effect=Exception("Fetch error"))

        await instance._discover_guild_channels(mock_guild)

        instance.logger.error.assert_called_once_with(
            f"Error discovering channels for guild {mock_guild.name}: Fetch error"
        )

    # Additional edge case tests
    @pytest.mark.asyncio
    async def test_trackers_discord_check_channel_history_channel_not_found(
        self, discord_config, guilds_collection, mock_client_wrapper
    ):
        """Test _check_channel_history when channel not found."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        mock_client_wrapper.get_channel_return = None

        result = await instance._check_channel_history(
            123456789012345678, 111111111111111111
        )

        assert result == 0

    @pytest.mark.asyncio
    async def test_trackers_discord_check_channel_history_channel_not_found_early(
        self, discord_config, guilds_collection, mock_client_wrapper
    ):
        """Test _check_channel_history when channel is not found."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        instance.logger = mock.MagicMock()

        # Mock get_channel to return None (channel not found)
        mock_client_wrapper.get_channel.return_value = None

        # Ensure not rate limited
        instance.last_channel_check = {}

        result = await instance._check_channel_history(
            123456789012345678, 111111111111111111
        )

        assert result == 0
        mock_client_wrapper.get_channel.assert_called_once_with(123456789012345678)
        # Should not proceed to process messages if channel is None

    @pytest.mark.asyncio
    async def test_trackers_discord_check_channel_history_success(
        self, discord_config, guilds_collection, mock_client_wrapper, mock_channel
    ):
        """Test _check_channel_history successful check."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        # Ensure channel is not rate limited
        instance.last_channel_check = {}

        # Mock the get_channel method to return our specific mock_channel
        mock_client_wrapper.get_channel.return_value = mock_channel

        mock_process = mock.AsyncMock(return_value=2)
        instance._process_channel_messages = mock_process

        result = await instance._check_channel_history(
            123456789012345678, 111111111111111111
        )

        assert result == 2
        # Check that _process_channel_messages was called
        assert mock_process.called
        call_args = mock_process.call_args
        assert call_args[0][1] == 111111111111111111  # Check the guild ID
        assert 123456789012345678 in instance.last_channel_check

    def test_trackers_discord_update_all_tracked_channels(
        self, discord_config, guilds_collection, mock_client_wrapper
    ):
        """Test _update_all_tracked_channels."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        instance.logger = mock.MagicMock()

        # Setup guild channels
        instance.guild_channels = {
            111111111111111111: [1, 2, 3],
            222222222222222222: [4, 5],
            333333333333333333: [6],
        }

        instance._update_all_tracked_channels()

        assert instance.all_tracked_channels == {1, 2, 3, 4, 5, 6}
        instance.logger.debug.assert_called_once_with(
            "Updated tracked channels: 6 total channels"
        )

    # Tests for _discover_all_guild_channels
    @pytest.mark.asyncio
    async def test_trackers_discord_discover_all_guild_channels_success(
        self, discord_config, guilds_collection, mock_client_wrapper, mock_guild
    ):
        """Test _discover_all_guild_channels with successful discovery."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        instance.logger = mock.MagicMock()

        # Mock _get_guilds_to_process to return our test guild
        mock_guilds = [mock_guild]
        instance._get_guilds_to_process = mock.MagicMock(return_value=mock_guilds)

        # Mock _discover_guild_channels
        mock_discover = mock.AsyncMock()
        instance._discover_guild_channels = mock_discover

        await instance._discover_all_guild_channels()

        instance._get_guilds_to_process.assert_called_once()
        mock_discover.assert_called_once_with(mock_guild)

    # Tests for _should_process_message early return
    @pytest.mark.asyncio
    async def test_trackers_discord_handle_new_message_should_not_process(
        self, discord_config, guilds_collection, mock_client_wrapper, mock_message
    ):
        """Test _handle_new_message when _should_process_message returns False."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        instance.logger = mock.MagicMock()

        # Mock _should_process_message to return False
        instance._should_process_message = mock.MagicMock(return_value=False)

        # Mock methods that should NOT be called
        mock_extract = mock.AsyncMock()
        instance.extract_mention_data = mock_extract
        mock_process = mock.MagicMock()
        instance.process_mention = mock_process
        mock_is_processed = mock.MagicMock()
        instance.is_processed = mock_is_processed

        await instance._handle_new_message(mock_message)

        # Verify early return - these methods should not be called
        instance._should_process_message.assert_called_once_with(mock_message)
        mock_extract.assert_not_called()
        mock_process.assert_not_called()
        mock_is_processed.assert_not_called()

    @pytest.mark.asyncio
    async def test_trackers_discord_handle_new_message_should_process(
        self, discord_config, guilds_collection, mock_client_wrapper, mock_message
    ):
        """Test _handle_new_message when _should_process_message returns True."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        instance.logger = mock.MagicMock()

        # Mock _should_process_message to return True
        instance._should_process_message = mock.MagicMock(return_value=True)

        # Mock methods that should be called
        mock_extract = mock.AsyncMock(return_value={})
        instance.extract_mention_data = mock_extract
        mock_process = mock.MagicMock(return_value=True)
        instance.process_mention = mock_process
        mock_is_processed = mock.MagicMock(return_value=False)
        instance.is_processed = mock_is_processed

        await instance._handle_new_message(mock_message)

        # Verify normal processing flow
        instance._should_process_message.assert_called_once_with(mock_message)
        mock_extract.assert_called_once_with(mock_message)
        mock_process.assert_called_once()
        mock_is_processed.assert_called_once()

    @pytest.mark.asyncio
    async def test_trackers_discord_check_channel_history_channel_found(
        self, discord_config, guilds_collection, mock_client_wrapper, mock_channel
    ):
        """Test _check_channel_history when channel is found."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        instance.logger = mock.MagicMock()

        # Mock get_channel to return a channel
        mock_client_wrapper.get_channel.return_value = mock_channel

        # Mock _process_channel_messages
        mock_process = mock.AsyncMock(return_value=3)
        instance._process_channel_messages = mock_process

        # Ensure not rate limited
        instance.last_channel_check = {}

        result = await instance._check_channel_history(
            123456789012345678, 111111111111111111
        )

        assert result == 3
        mock_client_wrapper.get_channel.assert_called_once_with(123456789012345678)
        mock_process.assert_called_once_with(mock_channel, 111111111111111111)

    @pytest.mark.asyncio
    async def test_trackers_discord_check_channel_history_http_exception_rate_limit(
        self, discord_config, guilds_collection, mock_client_wrapper, mock_channel
    ):
        """Test _check_channel_history with HTTPException 429 (rate limit)."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        instance.logger = mock.MagicMock()

        # Mock get_channel to return a channel
        mock_client_wrapper.get_channel.return_value = mock_channel

        # Mock _process_channel_messages to raise HTTPException with status 429
        http_exception = discord.HTTPException(mock.MagicMock(), "Rate limited")
        http_exception.status = 429
        http_exception.retry_after = 2.5
        instance._process_channel_messages = mock.AsyncMock(side_effect=http_exception)

        # Mock _handle_http_exception
        mock_handle_http = mock.AsyncMock(return_value=0)
        instance._handle_http_exception = mock_handle_http

        # Ensure not rate limited
        instance.last_channel_check = {}

        result = await instance._check_channel_history(
            123456789012345678, 111111111111111111
        )

        assert result == 0
        mock_handle_http.assert_called_once_with(http_exception, 123456789012345678)

    @pytest.mark.asyncio
    async def test_trackers_discord_check_channel_history_forbidden_exception(
        self,
        discord_config,
        guilds_collection,
        mock_client_wrapper,
        mock_channel,
        mocker,
    ):
        """Test _check_channel_history with Forbidden exception."""

        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        instance.logger = mock.MagicMock()

        # Mock get_channel to return a channel
        mock_client_wrapper.get_channel.return_value = mock_channel

        mocker.patch(
            "trackers.discord.DiscordTracker._process_channel_messages",
            side_effect=discord.Forbidden(mock.MagicMock(), "Forbidden"),
        )
        # Mock _handle_forbidden_exception
        mock_handle_forbidden = mocker.patch(
            "trackers.discord.DiscordTracker._handle_forbidden_exception"
        )

        # Ensure not rate limited
        instance.last_channel_check = {}

        result = await instance._check_channel_history(
            123456789012345678, 111111111111111111
        )

        assert result == mock.ANY
        mock_handle_forbidden.assert_called_once_with(
            123456789012345678, 111111111111111111
        )

    @pytest.mark.asyncio
    async def test_trackers_discord_check_channel_history_generic_exception(
        self, discord_config, guilds_collection, mock_client_wrapper, mock_channel
    ):
        """Test _check_channel_history with generic Exception."""
        instance = DiscordTracker(
            lambda x: None,
            discord_config,
            guilds_collection,
            client_wrapper=mock_client_wrapper,
        )

        instance.logger = mock.MagicMock()

        # Mock get_channel to return a channel
        mock_client_wrapper.get_channel.return_value = mock_channel

        # Mock _process_channel_messages to raise generic Exception
        test_exception = Exception("Test generic error")
        instance._process_channel_messages = mock.AsyncMock(side_effect=test_exception)

        # Ensure not rate limited
        instance.last_channel_check = {}

        result = await instance._check_channel_history(
            123456789012345678, 111111111111111111
        )

        assert result == 0
        instance.logger.error.assert_called_once_with(
            "Error checking channel 123456789012345678: Test generic error"
        )
