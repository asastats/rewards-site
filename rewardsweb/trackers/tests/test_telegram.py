"""Testing module for :py:mod:`trackers.telegram` module."""

import asyncio
from pathlib import Path

import pytest
from telethon.errors import SessionPasswordNeededError

import trackers.telegram
from trackers.base import BaseAsyncMentionTracker
from trackers.telegram import TelegramTracker


class TestTrackersTelegram:
    """Testing class for :class:`trackers.telegram.TelegramTracker`."""

    def test_trackers_telegram_telegramtracker_is_subclass_of_baseasyncmentiontracker(
        self,
    ):
        assert issubclass(TelegramTracker, BaseAsyncMentionTracker)

    # __init__
    def test_trackers_telegramtracker_init_success(
        self, mocker, telegram_config, telegram_chats
    ):
        # Mock TelegramClient to prevent actual API calls
        mock_telegram_client = mocker.patch("trackers.telegram.TelegramClient")
        mocker.patch.object(TelegramTracker, "log_action_async")
        # Create instance - this will call the real __init__ but with mocked TelegramClient
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        # Assert TelegramClient was called with correct parameters
        session_path = (
            Path(trackers.telegram.__file__).resolve().parent.parent
            / "fixtures"
            / "test_session.session"
        )
        mock_telegram_client.assert_called_once_with(
            session=session_path, api_id="test_api_id", api_hash="test_api_hash"
        )
        assert instance.bot_username == "test_bot"
        assert instance.tracked_chats == telegram_chats
        assert instance._is_connected is False

    # extract_mention_data
    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_extract_mention_data_with_reply(
        self, mocker, telegram_config, telegram_chats
    ):
        # Mock the parent init to avoid API calls
        mocker.patch.object(TelegramTracker, "__init__", return_value=None)
        mocker.patch.object(TelegramTracker, "log_action_async")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        # Mock the async methods
        mock_sender_info = {
            "user_id": 12345,
            "username": "testuser",
            "display_name": "Test User",
        }
        mocker.patch.object(instance, "_get_sender_info", return_value=mock_sender_info)
        mock_replied_info = {
            "message_id": 99,
            "sender_info": {
                "user_id": 54321,
                "username": "replieduser",
                "display_name": "Replied User",
            },
            "text": "This is the original message.",
        }
        mocker.patch.object(
            instance, "_get_replied_message_info", return_value=mock_replied_info
        )
        mock_message = mocker.MagicMock()
        mock_message.sender_id = 12345
        mock_message.id = 100
        mock_message.text = "Hello @test_bot!"
        mock_message.reply_to_msg_id = 99
        mock_message.date = mocker.MagicMock()
        mock_message.date.isoformat.return_value = "2023-01-01T00:00:00"
        mock_chat = mocker.MagicMock()
        mock_chat.id = 67890
        mock_chat.title = "Test Group"
        mock_chat.username = "testgroup"
        mock_message.chat = mock_chat
        result = await instance.extract_mention_data(mock_message)
        # Updated assertions to match new implementation
        assert result["suggester"] == "testuser"  # Uses username first
        assert result["suggestion_url"] == "https://t.me/testgroup/100"
        assert result["contribution_url"] == "https://t.me/testgroup/99"
        assert result["contributor"] == "replieduser"  # Uses username first
        assert result["type"] == "message"
        assert result["telegram_chat"] == "Test Group"
        assert result["chat_username"] == "testgroup"
        assert result["content"] == "Hello @test_bot!"
        assert result["contribution"] == "This is the original message."
        assert result["timestamp"] == "2023-01-01T00:00:00"

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_extract_mention_data_no_reply(
        self, mocker, telegram_config, telegram_chats
    ):
        # Mock the parent init to avoid API calls
        mocker.patch.object(TelegramTracker, "__init__", return_value=None)
        mocker.patch.object(TelegramTracker, "log_action_async")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        # Mock the async methods
        mock_sender_info = {
            "user_id": 12345,
            "username": "testuser",
            "display_name": "Test User",
        }
        mocker.patch.object(instance, "_get_sender_info", return_value=mock_sender_info)
        mocker.patch.object(instance, "_get_replied_message_info", return_value=None)
        mock_message = mocker.MagicMock()
        mock_message.sender_id = 12345
        mock_message.id = 100
        mock_message.text = "Hello @test_bot!"
        mock_message.reply_to_msg_id = None  # No reply
        mock_message.date = mocker.MagicMock()
        mock_message.date.isoformat.return_value = "2023-01-01T00:00:00"
        mock_chat = mocker.MagicMock()
        mock_chat.id = 67890
        mock_chat.title = "Test Group"
        mock_chat.username = None  # No username
        mock_message.chat = mock_chat
        result = await instance.extract_mention_data(mock_message)
        assert result["suggestion_url"] == "chat_67890_msg_100"
        assert result["contribution_url"] == "chat_67890_msg_100"
        assert result["contributor"] == "testuser"  # Uses username first
        assert result["contribution"] == "Hello @test_bot!"

    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_extract_mention_data_no_username(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test extract_mention_data when sender has no username."""
        # Mock the parent init to avoid API calls
        mocker.patch.object(TelegramTracker, "__init__", return_value=None)
        mocker.patch.object(TelegramTracker, "log_action_async")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        # Mock the async methods - no username
        mock_sender_info = {
            "user_id": 12345,
            "username": None,
            "display_name": "Test User",
        }
        mocker.patch.object(instance, "_get_sender_info", return_value=mock_sender_info)
        mocker.patch.object(instance, "_get_replied_message_info", return_value=None)
        mock_message = mocker.MagicMock()
        mock_message.sender_id = 12345
        mock_message.id = 100
        mock_message.text = "Hello @test_bot!"
        mock_message.reply_to_msg_id = None
        mock_message.date = mocker.MagicMock()
        mock_message.date.isoformat.return_value = "2023-01-01T00:00:00"
        mock_chat = mocker.MagicMock()
        mock_chat.id = 67890
        mock_chat.title = "Test Group"
        mock_chat.username = "testgroup"
        mock_message.chat = mock_chat
        result = await instance.extract_mention_data(mock_message)
        # Should use display_name when username is None
        assert result["suggester"] == "Test User"
        assert result["contributor"] == "Test User"

    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_extract_mention_data_no_username_or_display(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test extract_mention_data when sender has neither username nor display_name."""
        # Mock the parent init to avoid API calls
        mocker.patch.object(TelegramTracker, "__init__", return_value=None)
        mocker.patch.object(TelegramTracker, "log_action_async")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        # Mock the async methods - no username or display_name
        mock_sender_info = {
            "user_id": 12345,
            "username": None,
            "display_name": None,
        }
        mocker.patch.object(instance, "_get_sender_info", return_value=mock_sender_info)
        mocker.patch.object(instance, "_get_replied_message_info", return_value=None)
        mock_message = mocker.MagicMock()
        mock_message.sender_id = 12345
        mock_message.id = 100
        mock_message.text = "Hello @test_bot!"
        mock_message.reply_to_msg_id = None
        mock_message.date = mocker.MagicMock()
        mock_message.date.isoformat.return_value = "2023-01-01T00:00:00"
        mock_chat = mocker.MagicMock()
        mock_chat.id = 67890
        mock_chat.title = "Test Group"
        mock_chat.username = "testgroup"
        mock_message.chat = mock_chat
        result = await instance.extract_mention_data(mock_message)
        # Should use user_id when neither username nor display_name
        assert result["suggester"] == "12345"  # Now converted to string
        assert result["contributor"] == "12345"  # Now converted to string

    # check_mentions
    def test_trackers_telegramtracker_check_mentions(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test check_mentions method."""
        # Mock TelegramClient
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        instance._is_connected = True

        # Mock async methods
        mocker.patch.object(instance, "_ensure_connected")
        mocker.patch.object(instance, "check_mentions_async", return_value=3)

        result = instance.check_mentions()
        assert result == 3

    def test_trackers_telegramtracker_check_mentions_no_connection(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test check_mentions when not connected."""
        # Mock TelegramClient
        mocker.patch("trackers.telegram.TelegramClient")
        mocker.patch("trackers.telegram.TelegramTracker.log_action_async")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        instance._is_connected = False

        # Mock _ensure_connected to raise exception
        mocker.patch.object(
            instance, "_ensure_connected", side_effect=Exception("Connection failed")
        )
        instance.logger = mocker.MagicMock()

        result = instance.check_mentions()
        assert result == 0
        instance.logger.error.assert_called()

    def test_trackers_telegramtracker_check_mentions_no_client(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test check_mentions when self.client is None (early exit)."""
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        instance.logger = mocker.MagicMock()
        instance.client = None  # Explicitly set client to None

        result = instance.check_mentions()

        assert result == 0
        instance.logger.error.assert_called_once_with("Telegram client not available")

    # run
    def test_trackers_telegramtracker_run_no_client(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test run method when client is None."""
        # Mock TelegramClient
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        instance.logger = mocker.MagicMock()
        # Set client to None
        instance.client = None
        instance.run(poll_interval_minutes=1)
        # Should log error and return early
        instance.logger.error.assert_called_with(
            "Cannot start Telegram tracker - client not available"
        )

    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_run_async_connect_and_exit(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test successful connection and immediate exit from the polling loop."""
        # Mock TelegramClient (still needed for init)
        mocker.patch("trackers.telegram.TelegramClient")
        mocker.patch("trackers.telegram.TelegramTracker.log_action_async")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        instance.client = mocker.MagicMock()
        instance._is_connected = False
        instance.logger = mocker.MagicMock()

        # Mock async methods - use AsyncMock
        mock_ensure_connected = mocker.patch.object(
            instance, "_ensure_connected", new_callable=mocker.AsyncMock
        )
        # Mock check_mentions_async to stop the polling loop immediately
        mock_check_mentions = mocker.patch.object(
            instance,
            "check_mentions_async",
            new_callable=mocker.AsyncMock,
            side_effect=asyncio.CancelledError(),
        )
        mock_cleanup = mocker.patch.object(
            instance, "cleanup", new_callable=mocker.AsyncMock
        )

        # Run the async method. We expect it to be cancelled almost immediately.
        with pytest.raises(asyncio.CancelledError):
            await instance.run_async(poll_interval_minutes=0.01)

        # Assertions
        mock_ensure_connected.assert_called_once()
        mock_check_mentions.assert_called_once()
        mock_cleanup.assert_called_once()
        instance.logger.info.assert_any_call("Telegram tracker cancelled")

    def test_trackers_telegramtracker_run_no_client_config(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test run() when client is not available (early exit)."""
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        instance.client = None
        instance.logger = mocker.MagicMock()

        instance.run()

        instance.logger.error.assert_called_once_with(
            "Cannot start Telegram tracker - client not available"
        )

    def test_trackers_telegramtracker_run_keyboardinterrupt(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test synchronous run method when KeyboardInterrupt occurs during run_until_complete."""
        # Mock TelegramClient
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        instance.client = mocker.MagicMock()
        instance.logger = mocker.MagicMock()

        # Mock event loop related calls
        mock_loop = mocker.MagicMock()
        mocker.patch("asyncio.new_event_loop", return_value=mock_loop)
        mocker.patch("asyncio.set_event_loop")

        # Mock run_async (its return value is the coroutine passed to run_until_complete)
        mocker.patch.object(instance, "run_async", new_callable=mocker.AsyncMock)

        mock_cleanup = mocker.patch.object(
            instance, "cleanup", new_callable=mocker.AsyncMock
        )

        # Mock run_until_complete to raise KeyboardInterrupt on the first call (for run_async)
        # and return None on the second call (for cleanup).
        mock_loop.run_until_complete.side_effect = [KeyboardInterrupt(), None]

        # Reset the logger before running to isolate this test's logging
        instance.logger.info.reset_mock()

        # run() catches the synchronous KeyboardInterrupt
        instance.run(poll_interval_minutes=0.01)

        # Assert KeyboardInterrupt was caught and logged
        instance.logger.info.assert_called_once_with("Telegram tracker stopped by user")

        # Assert the cleanup coroutine was run and the loop was closed
        mock_cleanup.assert_called_once()
        mock_loop.close.assert_called_once()

    # _check_chat_mentions
    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_check_chat_mentions_no_chat(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test _check_chat_mentions when chat entity is None."""
        # Mock TelegramClient
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        instance._is_connected = True
        # Mock _get_chat_entity to return None
        mocker.patch.object(instance, "_get_chat_entity", return_value=None)
        # Test when chat is not found
        result = await instance._check_chat_mentions("nonexistent_chat")
        assert result == 0

    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_check_chat_mentions_success(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test _check_chat_mentions successful message processing."""
        # Mock TelegramClient
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        instance._is_connected = True
        mock_chat = mocker.MagicMock()
        mock_chat.id = 456
        mocker.patch.object(instance, "_get_chat_entity", return_value=mock_chat)
        mock_message = mocker.MagicMock()
        mock_message.text = "@test_bot hello"
        mock_message.id = 123
        mock_message.date = mocker.MagicMock()

        # Mock async iter_messages properly
        async def mock_iter_messages(*args, **kwargs):
            yield mock_message

        instance.client.iter_messages = mock_iter_messages
        # Mock the async extract_mention_data method
        mock_extract_data = mocker.patch.object(
            instance, "extract_mention_data", return_value={}
        )
        mock_process_mention = mocker.patch.object(
            instance, "process_mention_async", return_value=True
        )
        mocker.patch.object(instance, "is_processed_async", return_value=False)
        # Test successful message processing
        result = await instance._check_chat_mentions("test_chat")
        assert result == 1
        mock_process_mention.assert_called_once_with(
            f"telegram_456_{mock_message.id}",
            {},
            f"@{instance.bot_username}",
        )
        mock_extract_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_check_chat_mentions_exception(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test _check_chat_mentions exception handling."""
        # Mock TelegramClient
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        instance._is_connected = True
        instance.logger = mocker.MagicMock()
        mock_chat = mocker.MagicMock()
        mocker.patch.object(instance, "_get_chat_entity", return_value=mock_chat)

        # Mock async method to raise exception
        async def mock_iter_messages_error(*args, **kwargs):
            raise Exception("API error")

        instance.client.iter_messages = mock_iter_messages_error
        mock_log_action = mocker.patch.object(instance, "log_action_async")
        # Test exception handling
        result = await instance._check_chat_mentions("problem_chat")
        assert result == 0
        instance.logger.error.assert_called_once()
        mock_log_action.assert_called_once()

    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_check_chat_mentions_condition_not_met(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test _check_chat_mentions when mention condition is not met."""
        # Mock TelegramClient
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        instance._is_connected = True
        mock_chat = mocker.MagicMock()
        mocker.patch.object(instance, "_get_chat_entity", return_value=mock_chat)
        # Message doesn't contain bot username
        mock_message = mocker.MagicMock()
        mock_message.text = "Hello everyone!"
        mock_message.id = 123
        mock_chat.id = 456

        # Mock async iter_messages
        async def mock_iter_messages(*args, **kwargs):
            yield mock_message

        instance.client.iter_messages = mock_iter_messages
        mock_process_mention = mocker.patch.object(
            instance, "process_mention_async", new_callable=mocker.AsyncMock
        )
        result = await instance._check_chat_mentions("test_chat")
        # Should return 0 because condition not met
        assert result == 0
        mock_process_mention.assert_not_called()

    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_check_chat_mentions_already_processed(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test _check_chat_mentions when message is already processed."""
        # Mock TelegramClient
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        instance._is_connected = True
        mock_chat = mocker.MagicMock()
        mocker.patch.object(instance, "_get_chat_entity", return_value=mock_chat)
        mock_message = mocker.MagicMock()
        mock_message.text = "@test_bot hello"
        mock_message.id = 123
        mock_chat.id = 456

        # Mock async iter_messages
        async def mock_iter_messages(*args, **kwargs):
            yield mock_message

        instance.client.iter_messages = mock_iter_messages
        mock_process_mention = mocker.patch.object(instance, "process_mention_async")
        # Message is already processed
        mock_is_processed = mocker.patch.object(
            instance, "is_processed_async", return_value=True
        )
        result = await instance._check_chat_mentions("test_chat")
        # Should return 0 because already processed
        assert result == 0
        mock_is_processed.assert_called_once_with("telegram_456_123")
        mock_process_mention.assert_not_called()

    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_check_chat_mentions_process_mention_false(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test _check_chat_mentions when process_mention returns False."""
        # Mock TelegramClient
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        instance._is_connected = True
        mock_chat = mocker.MagicMock()
        mocker.patch.object(instance, "_get_chat_entity", return_value=mock_chat)
        mock_message = mocker.MagicMock()
        mock_message.text = "@test_bot hello"
        mock_message.id = 123
        mock_chat.id = 456

        # Mock async iter_messages
        async def mock_iter_messages(*args, **kwargs):
            yield mock_message

        instance.client.iter_messages = mock_iter_messages
        # process_mention returns False
        mock_process_mention = mocker.patch.object(
            instance, "process_mention_async", return_value=False
        )
        mocker.patch.object(instance, "is_processed_async", return_value=False)
        result = await instance._check_chat_mentions("test_chat")
        # Should return 0 because process_mention returned False
        assert result == 0
        mock_process_mention.assert_called_once()

    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_check_chat_mentions_no_bot_username(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test _check_chat_mentions when bot_username is empty."""
        # Mock TelegramClient
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        instance._is_connected = True
        # Set bot_username to empty string
        instance.bot_username = ""
        mock_chat = mocker.MagicMock()
        mocker.patch.object(instance, "_get_chat_entity", return_value=mock_chat)
        mock_message = mocker.MagicMock()
        mock_message.text = "Some message"
        mock_message.id = 123
        mock_chat.id = 456

        # Mock async iter_messages
        async def mock_iter_messages(*args, **kwargs):
            yield mock_message

        instance.client.iter_messages = mock_iter_messages
        mock_process_mention = mocker.patch.object(
            instance, "process_mention_async", new_callable=mocker.AsyncMock
        )
        result = await instance._check_chat_mentions("test_chat")
        # Should return 0 when bot_username is empty
        assert result == 0
        mock_process_mention.assert_not_called()

    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_check_chat_mentions_message_no_text(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test _check_chat_mentions when message has no text."""
        # Mock TelegramClient
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        instance._is_connected = True
        mock_chat = mocker.MagicMock()
        mocker.patch.object(instance, "_get_chat_entity", return_value=mock_chat)
        # Message with no text (e.g., photo message)
        mock_message = mocker.MagicMock()
        mock_message.text = None
        mock_message.id = 123
        mock_chat.id = 456

        # Mock async iter_messages
        async def mock_iter_messages(*args, **kwargs):
            yield mock_message

        instance.client.iter_messages = mock_iter_messages
        mock_process_mention = mocker.patch.object(
            instance, "process_mention_async", new_callable=mocker.AsyncMock
        )
        result = await instance._check_chat_mentions("test_chat")
        # Should return 0 when message has no text
        assert result == 0
        mock_process_mention.assert_not_called()

    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_check_chat_mentions_bot_not_mentioned(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test _check_chat_mentions when bot username not in message."""
        # Mock TelegramClient
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        instance._is_connected = True
        mock_chat = mocker.MagicMock()
        mocker.patch.object(instance, "_get_chat_entity", return_value=mock_chat)
        # Message doesn't mention bot
        mock_message = mocker.MagicMock()
        mock_message.text = "Hello everyone without mentioning bot"
        mock_message.id = 123
        mock_chat.id = 456

        # Mock async iter_messages
        async def mock_iter_messages(*args, **kwargs):
            yield mock_message

        instance.client.iter_messages = mock_iter_messages
        mock_process_mention = mocker.patch.object(
            instance, "process_mention_async", new_callable=mocker.AsyncMock
        )
        result = await instance._check_chat_mentions("test_chat")
        # Should return 0 when bot not mentioned
        assert result == 0
        mock_process_mention.assert_not_called()

    # check_mentions_async
    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_check_mentions_async_no_connection(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test check_mentions_async when not connected."""
        # Mock TelegramClient
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        instance._is_connected = False
        result = await instance.check_mentions_async()
        # Should return 0 when not connected
        assert result == 0

    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_check_mentions_async_success(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test check_mentions_async successful execution with multiple chats."""
        # Mock TelegramClient
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        instance._is_connected = True
        # Track sleep calls to verify delay between chats
        sleep_calls = []

        async def mock_sleep(delay):
            sleep_calls.append(delay)

        mocker.patch("asyncio.sleep", side_effect=mock_sleep)
        # Mock _check_chat_mentions to return different counts for different chats
        mock_check_chat = mocker.patch.object(
            instance, "_check_chat_mentions", new_callable=mocker.AsyncMock
        )
        mock_check_chat.side_effect = [2, 1]  # Different counts for 2 chats
        result = await instance.check_mentions_async()
        # Should return total mentions (2 + 1 = 3)
        assert result == 3
        # Should call _check_chat_mentions for each tracked chat
        assert mock_check_chat.call_count == len(telegram_chats)
        # Should sleep after each chat (2 sleeps for 2 chats)
        assert len(sleep_calls) == len(telegram_chats)
        assert all(sleep == 2 for sleep in sleep_calls)  # Updated to 2 seconds

    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_check_mentions_async_empty_chats(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test check_mentions_async with empty tracked_chats list."""
        # Mock TelegramClient
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        instance._is_connected = True
        # Set tracked_chats to empty list
        instance.tracked_chats = []
        # Track sleep calls
        sleep_calls = []

        async def mock_sleep(delay):
            sleep_calls.append(delay)

        mocker.patch("asyncio.sleep", side_effect=mock_sleep)
        result = await instance.check_mentions_async()
        # Should return 0 when no chats to track
        assert result == 0
        # Should not sleep when there are no chats
        assert len(sleep_calls) == 0

    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_check_mentions_async_single_chat(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test check_mentions_async with single chat."""
        # Mock TelegramClient
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        instance._is_connected = True
        # Set tracked_chats to single chat
        instance.tracked_chats = ["single_chat"]
        # Track sleep calls
        sleep_calls = []

        async def mock_sleep(delay):
            sleep_calls.append(delay)

        mocker.patch("asyncio.sleep", side_effect=mock_sleep)
        mocker.patch.object(
            instance,
            "_check_chat_mentions",
            new_callable=mocker.AsyncMock,
            return_value=3,
        )
        result = await instance.check_mentions_async()
        # Should return mentions from single chat
        assert result == 3
        # Should sleep after the chat
        assert len(sleep_calls) == 1
        assert sleep_calls[0] == 2  # Updated to 2 seconds

    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_check_mentions_async_three_chats(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test check_mentions_async with three chats."""
        # Mock TelegramClient
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        instance._is_connected = True
        # Set tracked_chats to three chats
        instance.tracked_chats = ["chat1", "chat2", "chat3"]
        # Track sleep calls
        sleep_calls = []

        async def mock_sleep(delay):
            sleep_calls.append(delay)

        mocker.patch("asyncio.sleep", side_effect=mock_sleep)
        mock_check_chat = mocker.patch.object(
            instance, "_check_chat_mentions", new_callable=mocker.AsyncMock
        )
        mock_check_chat.side_effect = [1, 2, 3]  # Different counts for 3 chats
        result = await instance.check_mentions_async()
        # Should return total mentions (1 + 2 + 3 = 6)
        assert result == 6
        # Should call _check_chat_mentions for each tracked chat
        assert mock_check_chat.call_count == 3
        # Should sleep after each chat (3 sleeps for 3 chats)
        assert len(sleep_calls) == 3
        assert all(sleep == 2 for sleep in sleep_calls)  # Updated to 2 seconds

    # _get_chat_entity
    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_get_chat_entity_success(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test _get_chat_entity successful chat retrieval."""
        # Mock TelegramClient
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        instance._is_connected = True
        mock_entity = mocker.MagicMock()
        # Mock the async method properly
        instance.client.get_entity = mocker.AsyncMock(return_value=mock_entity)
        # Test successful chat retrieval
        result = await instance._get_chat_entity("test_chat")
        instance.client.get_entity.assert_called_once_with("test_chat")
        assert result == mock_entity

    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_get_chat_entity_exception(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test _get_chat_entity exception handling."""
        # Mock TelegramClient
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        instance._is_connected = True
        instance.logger = mocker.MagicMock()
        # Mock the async method to raise exception
        instance.client.get_entity = mocker.AsyncMock(
            side_effect=Exception("Chat not found")
        )
        # Test exception handling
        result = await instance._get_chat_entity("invalid_chat")
        assert result is None
        instance.logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_get_chat_entity_success_by_username(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test _get_chat_entity success when identifier is a standard username."""
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        instance.client = mocker.MagicMock()
        mock_entity = mocker.MagicMock()

        # Mock get_entity to succeed on first call
        mock_get_entity = mocker.AsyncMock(return_value=mock_entity)
        instance.client.get_entity = mock_get_entity

        username = "@some_channel_name"
        result = await instance._get_chat_entity(username)

        mock_get_entity.assert_called_once_with(username)
        assert result == mock_entity

    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_get_chat_entity_value_error_success(
        self, mocker, telegram_config, telegram_chats
    ):
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        instance.client = mocker.MagicMock()
        mock_entity = mocker.MagicMock()

        # Mock get_entity: first call raises ValueError, second succeeds
        mock_get_entity = mocker.AsyncMock()
        mock_get_entity.side_effect = [
            ValueError("Not a username"),  # First call
            mock_entity,  # Second call with int conversion
        ]
        instance.client.get_entity = mock_get_entity

        string_id = "-10012345678"
        result = await instance._get_chat_entity(string_id)

        # Should be called twice: first with string, second with int
        mock_get_entity.assert_has_calls(
            [
                mocker.call(string_id),
                mocker.call(-10012345678),
            ]
        )
        assert result == mock_entity

    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_get_chat_entity_value_error_int_id(
        self, mocker, telegram_config, telegram_chats
    ):
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        instance.client = mocker.MagicMock()
        mock_entity = mocker.MagicMock()

        # Mock get_entity: first call raises ValueError, second succeeds
        mock_get_entity = mocker.AsyncMock()
        mock_get_entity.side_effect = [
            ValueError("Not a username"),  # First call
            mock_entity,  # Second call with same int
        ]
        instance.client.get_entity = mock_get_entity

        int_id = 12345678
        result = await instance._get_chat_entity(int_id)

        # Should be called twice: both with the same integer
        mock_get_entity.assert_has_calls(
            [
                mocker.call(int_id),
                mocker.call(int_id),
            ]
        )
        assert result == mock_entity

    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_get_chat_entity_value_exception(
        self, mocker, telegram_config, telegram_chats
    ):
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        instance.client = mocker.MagicMock()
        instance.logger = mocker.MagicMock()

        # Mock get_entity: first raises ValueError, second raises another exception (caught silently)
        mock_get_entity = mocker.AsyncMock()
        mock_get_entity.side_effect = [
            ValueError("Not a username"),  # First call
            Exception("Peer ID invalid"),  # Second call - caught by inner except
        ]
        instance.client.get_entity = mock_get_entity

        identifier = "-12345"
        result = await instance._get_chat_entity(identifier)

        # Should return None
        assert result is None

        # Outer exception logger should NOT be called (only for general exceptions)
        instance.logger.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_get_chat_entity_value_error_string(
        self, mocker, telegram_config, telegram_chats
    ):
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        instance.client = mocker.MagicMock()
        instance.logger = mocker.MagicMock()

        # Mock get_entity to raise ValueError
        mock_get_entity = mocker.AsyncMock(side_effect=ValueError("Not a username"))
        instance.client.get_entity = mock_get_entity

        # Non-digit string that can't be converted to int
        identifier = "@invalid_chat_name"
        result = await instance._get_chat_entity(identifier)

        # Should be called once and return None
        mock_get_entity.assert_called_once_with(identifier)
        assert result is None

        # Outer exception logger should NOT be called
        instance.logger.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_get_chat_entity_general_exception(
        self, mocker, telegram_config, telegram_chats
    ):
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        instance.client = mocker.MagicMock()
        instance.logger = mocker.MagicMock()

        # Mock get_entity to raise a general Exception (not ValueError)
        mock_get_entity = mocker.AsyncMock(
            side_effect=Exception("API connection failed")
        )
        instance.client.get_entity = mock_get_entity

        identifier = "@some_username"
        result = await instance._get_chat_entity(identifier)

        assert result is None
        instance.logger.error.assert_called_once_with(
            f"Error getting chat entity for {identifier}: API connection failed"
        )

    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_get_chat_entity_empty_string(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test _get_chat_entity with empty string identifier."""
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        instance.client = mocker.MagicMock()
        instance.logger = mocker.MagicMock()

        # Mock get_entity to raise ValueError for empty string
        mock_get_entity = mocker.AsyncMock(side_effect=ValueError("Empty string"))
        instance.client.get_entity = mock_get_entity

        identifier = ""
        result = await instance._get_chat_entity(identifier)

        mock_get_entity.assert_called_once_with(identifier)
        assert result is None

    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_get_chat_entity_none_value(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test _get_chat_entity with None identifier."""
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        instance.client = mocker.MagicMock()
        instance.logger = mocker.MagicMock()

        # Mock get_entity
        mock_get_entity = mocker.AsyncMock()
        instance.client.get_entity = mock_get_entity

        await instance._get_chat_entity(None)

        # Should call get_entity with None and likely raise an exception
        mock_get_entity.assert_called_once_with(None)
        # The exact behavior depends on Telethon's handling of None

    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_get_chat_entity_success_by_string_id(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test _get_chat_entity fallthrough success on string ID (e.g., '-10012345678')."""
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        instance.client = mocker.MagicMock()
        mock_entity = mocker.MagicMock()

        # Explicitly patch the method as AsyncMock for cleaner side_effect handling
        mock_get_entity = mocker.patch.object(
            instance.client, "get_entity", new_callable=mocker.AsyncMock
        )

        # Mocking: First get_entity raises ValueError, second call (with int) succeeds
        mock_get_entity.side_effect = [
            ValueError("Not a username"),
            mock_entity,
        ]

        result = await instance._get_chat_entity("-10012345678")

        # Assert the fallthrough logic was executed correctly
        mock_get_entity.assert_has_calls(
            [
                mocker.call("-10012345678"),
                mocker.call(-10012345678),
            ]
        )
        assert result == mock_entity

    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_get_chat_entity_success_by_int_id(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test _get_chat_entity fallthrough success on integer ID."""
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        instance.client = mocker.MagicMock()
        mock_entity = mocker.MagicMock()

        # Explicitly patch the method as AsyncMock for cleaner side_effect handling
        mock_get_entity = mocker.patch.object(
            instance.client, "get_entity", new_callable=mocker.AsyncMock
        )

        # Mocking: First get_entity raises ValueError, second call succeeds
        mock_get_entity.side_effect = [
            ValueError("Not a username"),
            mock_entity,
        ]

        result = await instance._get_chat_entity(12345678)

        # Assert the fallthrough logic was executed correctly
        mock_get_entity.assert_has_calls(
            [
                mocker.call(12345678),
                mocker.call(12345678),
            ]
        )
        assert result == mock_entity

    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_get_chat_entity_failure_by_id_silently_caught(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test _get_chat_entity when lookup by ID fails with a silently-caught inner exception."""
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        instance.client = mocker.MagicMock()
        instance.logger = mocker.MagicMock()

        # Explicitly patch the method as AsyncMock
        mock_get_entity = mocker.patch.object(
            instance.client, "get_entity", new_callable=mocker.AsyncMock
        )

        # Mocking: First raises ValueError, second raises an Exception (caught by inner except)
        mock_get_entity.side_effect = [
            ValueError("Not a username"),
            Exception(
                "Peer ID invalid"
            ),  # This exception is caught by `except Exception: pass`
        ]

        result = await instance._get_chat_entity("-12345")

        assert result is None
        # Assert the outer exception logger was NOT called
        instance.logger.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_get_chat_entity_failure_by_general_exception(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test _get_chat_entity when initial lookup fails with a general Exception (logged)."""
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        instance.client = mocker.MagicMock()
        instance.logger = mocker.MagicMock()

        # Explicitly patch the method as AsyncMock
        mock_get_entity = mocker.patch.object(
            instance.client, "get_entity", new_callable=mocker.AsyncMock
        )

        # Mocking: The initial get_entity call raises a general Exception (not ValueError)
        mock_get_entity.side_effect = Exception("API connection failed")

        result = await instance._get_chat_entity("@some_username")

        assert result is None
        instance.logger.error.assert_called_once_with(
            "Error getting chat entity for @some_username: API connection failed"
        )

    # Other helper methods
    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_get_sender_info_success(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test _get_sender_info successful retrieval."""
        # Mock TelegramClient
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        mock_message = mocker.MagicMock()
        mock_sender = mocker.MagicMock()
        mock_sender.id = 12345
        mock_sender.username = "testuser"
        mock_sender.first_name = "Test User"
        # Mock the async method
        mock_message.get_sender = mocker.AsyncMock(return_value=mock_sender)
        result = await instance._get_sender_info(mock_message)
        assert result["user_id"] == 12345
        assert result["username"] == "testuser"
        assert result["display_name"] == "Test User"

    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_get_sender_info_exception(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test _get_sender_info exception handling."""
        # Mock TelegramClient
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        mock_message = mocker.MagicMock()
        mock_message.sender_id = 12345
        # Mock the async method to raise exception
        mock_message.get_sender = mocker.AsyncMock(side_effect=Exception("API error"))
        result = await instance._get_sender_info(mock_message)
        # Should return fallback info
        assert result["user_id"] == 12345
        assert result["username"] is None
        assert result["display_name"] is None

    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_get_sender_info_no_sender(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test _get_sender_info when get_sender returns None."""
        # Mock TelegramClient
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        mock_message = mocker.MagicMock()
        mock_message.sender_id = 12345
        # Mock the async method to return None
        mock_message.get_sender = mocker.AsyncMock(return_value=None)
        result = await instance._get_sender_info(mock_message)
        # Should return fallback info when sender is None
        assert result["user_id"] == 12345
        assert result["username"] is None
        assert result["display_name"] is None

    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_get_replied_message_info_success(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test _get_replied_message_info successful retrieval."""
        # Mock TelegramClient
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        mock_message = mocker.MagicMock()
        mock_message.reply_to_msg_id = 99
        mock_message.chat_id = 123
        mock_replied_message = mocker.MagicMock()
        mock_replied_message.id = 99
        mock_replied_message.text = "This is the original message."
        # Mock get_messages
        instance.client.get_messages = mocker.AsyncMock(
            return_value=mock_replied_message
        )
        # Mock _get_sender_info for the replied message
        mock_sender_info = {
            "user_id": 54321,
            "username": "replieduser",
            "display_name": "Replied User",
        }
        mocker.patch.object(instance, "_get_sender_info", return_value=mock_sender_info)
        result = await instance._get_replied_message_info(mock_message)
        assert result["message_id"] == 99
        assert result["sender_info"] == mock_sender_info
        assert result["text"] == "This is the original message."
        instance.client.get_messages.assert_called_once_with(123, ids=99)

    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_get_replied_message_info_no_reply(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test _get_replied_message_info when no reply exists."""
        # Mock TelegramClient
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        mock_message = mocker.MagicMock()
        mock_message.reply_to_msg_id = None
        result = await instance._get_replied_message_info(mock_message)
        assert result is None

    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_get_replied_message_info_no_replied_message(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test _get_replied_message_info when get_messages returns None."""
        # Mock TelegramClient
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        mock_message = mocker.MagicMock()
        mock_message.reply_to_msg_id = 99
        mock_message.chat_id = 123
        # Mock get_messages to return None (message not found)
        instance.client.get_messages = mocker.AsyncMock(return_value=None)
        result = await instance._get_replied_message_info(mock_message)
        # Should return None when replied message is not found
        assert result is None
        instance.client.get_messages.assert_called_once_with(123, ids=99)

    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_get_replied_message_info_exception(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test _get_replied_message_info exception handling."""
        # Mock TelegramClient
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        mock_message = mocker.MagicMock()
        mock_message.reply_to_msg_id = 99
        mock_message.chat_id = 123
        # Mock get_messages to raise exception
        instance.client.get_messages = mocker.AsyncMock(
            side_effect=Exception("Message not found")
        )
        result = await instance._get_replied_message_info(mock_message)
        # Should return None on exception
        assert result is None
        instance.client.get_messages.assert_called_once_with(123, ids=99)

    def test_trackers_telegramtracker_generate_message_url_with_username(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test _generate_message_url with chat username."""
        # Mock TelegramClient
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        mock_chat = mocker.MagicMock()
        mock_chat.id = 12345
        mock_chat.username = "testchat"
        result = instance._generate_message_url(mock_chat, 100)
        assert result == "https://t.me/testchat/100"

    def test_trackers_telegramtracker_generate_message_url_no_username(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test _generate_message_url without chat username."""
        # Mock TelegramClient
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        mock_chat = mocker.MagicMock()
        mock_chat.id = 12345
        mock_chat.username = None
        result = instance._generate_message_url(mock_chat, 100)
        assert result == "chat_12345_msg_100"

    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_post_init_setup(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test _post_init_setup method."""
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        mock_log_action = mocker.patch.object(instance, "log_action_async")
        await instance._post_init_setup(telegram_chats)
        mock_log_action.assert_called_once_with(
            "initialized", f"Tracking {len(telegram_chats)} chats"
        )

    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_cleanup_connected(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test cleanup method when client is connected."""
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        instance.client = mocker.MagicMock()
        instance._is_connected = True
        instance.client.disconnect = mocker.AsyncMock()
        instance.logger = mocker.MagicMock()
        await instance.cleanup()
        instance.client.disconnect.assert_called_once()
        instance.logger.info.assert_called_with("Disconnecting Telegram client")
        assert instance._is_connected is False

    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_cleanup_success(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test successful cleanup."""
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        instance.client = mocker.MagicMock()
        instance._is_connected = True
        instance.logger = mocker.MagicMock()

        # Mock disconnect as AsyncMock
        mock_disconnect = mocker.AsyncMock()
        instance.client.disconnect = mock_disconnect

        await instance.cleanup()

        mock_disconnect.assert_called_once()
        assert instance._is_connected is False

    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_cleanup_not_connected(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test cleanup when client is not connected."""
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        instance.client = mocker.MagicMock()
        instance._is_connected = False

        await instance.cleanup()

        instance.client.disconnect.assert_not_called()

    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_cleanup_no_client(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test cleanup when client is None."""
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        instance.client = None
        instance._is_connected = False

        await instance.cleanup()

        # Should not raise an error

    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_is_processed_async(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test is_processed_async method."""
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        mock_is_processed = mocker.patch.object(
            instance, "is_processed", return_value=True
        )
        result = await instance.is_processed_async("some_id")
        assert result is True
        mock_is_processed.assert_called_once_with("some_id")

    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_process_mention_async(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test process_mention_async method."""
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(
            lambda x, y=None: {"parsed": "data"}, telegram_config, telegram_chats
        )

        # Mock the parent class's process_mention method which is called by process_mention_async
        mocker.patch.object(
            BaseAsyncMentionTracker, "process_mention", return_value=True
        )

        # Mock is_processed_async to return False
        mocker.patch.object(instance, "is_processed_async", return_value=False)

        # Mock post_new_contribution_async
        mocker.patch.object(instance, "post_new_contribution_async", return_value={})

        # Mock mark_processed_async
        mocker.patch.object(instance, "mark_processed_async")

        # Mock log_action_async
        mocker.patch.object(instance, "log_action_async")

        result = await instance.process_mention_async(
            "some_id", {"content": "test"}, "user"
        )
        assert result is True

    # # _ensure_connected
    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_ensure_connected_success(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test successful connection."""
        # 1. Patch the TelegramClient class and capture its mock return value
        mock_client_class = mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )

        # 2. Get the mock instance assigned to instance.client
        mock_client_instance = mock_client_class.return_value

        # 3. Setup and assign the dedicated AsyncMock for the methods
        mock_connect = mocker.AsyncMock()
        mock_is_user_authorized = mocker.AsyncMock(return_value=True)
        mock_client_instance.connect = mock_connect
        mock_client_instance.is_user_authorized = mock_is_user_authorized

        instance._is_connected = False

        # Mock _get_chat_entity
        mock_entity = mocker.MagicMock(id=1234)
        mocker.patch.object(
            instance,
            "_get_chat_entity",
            new_callable=mocker.AsyncMock,
            return_value=mock_entity,
        )

        await instance._ensure_connected()

        # Assertions
        mock_connect.assert_called_once()
        mock_is_user_authorized.assert_called_once()
        assert instance._is_connected is True

    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_ensure_connected_password_error(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test connection failure due to SessionPasswordNeededError."""
        mock_client_class = mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        instance.logger = mocker.MagicMock()

        # Get the mock instance
        mock_client_instance = mock_client_class.return_value

        # Setup and assign the dedicated AsyncMock for methods
        mock_connect = mocker.AsyncMock()
        mock_is_user_authorized = mocker.AsyncMock(return_value=False)
        mock_send_code_request = mocker.AsyncMock()

        # First sign_in raises SessionPasswordNeededError, second succeeds
        mock_sign_in = mocker.AsyncMock()
        mock_sign_in.side_effect = [
            SessionPasswordNeededError("Need password"),  # First call
            None,  # Second call with password
        ]

        mock_client_instance.connect = mock_connect
        mock_client_instance.is_user_authorized = mock_is_user_authorized
        mock_client_instance.send_code_request = mock_send_code_request
        mock_client_instance.sign_in = mock_sign_in

        instance._is_connected = False

        # Mock input to avoid hanging - need two inputs (phone/code) then password
        input_calls = ["123456789", "123456", "2fapassword"]
        mocker.patch("builtins.input", side_effect=input_calls)

        await instance._ensure_connected()

        # Assertions
        mock_connect.assert_called_once()
        mock_is_user_authorized.assert_called_once()
        mock_send_code_request.assert_called_once()

        # Check sign_in was called twice
        assert mock_sign_in.call_count == 2

        # First call with phone and code
        mock_sign_in.assert_any_call("123456789", "123456")

        # Second call with password only
        mock_sign_in.assert_any_call(password="2fapassword")

        assert instance._is_connected is True

    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_ensure_connected_general_error(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test connection failure due to a general exception."""
        mock_client_class = mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        instance.logger = mocker.MagicMock()

        # Get the mock instance
        mock_client_instance = mock_client_class.return_value

        # Setup and assign the dedicated AsyncMock for connect
        mock_connect = mocker.AsyncMock(side_effect=Exception("General API error"))
        mock_client_instance.connect = mock_connect

        instance._is_connected = False

        # The method should raise the exception
        with pytest.raises(Exception, match="General API error"):
            await instance._ensure_connected()

        # Assertions
        mock_connect.assert_called_once()
        instance.logger.error.assert_called_once_with(
            "Error connecting Telegram client: General API error"
        )
        assert instance._is_connected is False

    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_ensure_connected_already_connected(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test _ensure_connected when already connected."""
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        instance._is_connected = True
        instance.client = mocker.MagicMock()
        mock_connect = mocker.AsyncMock()
        instance.client.connect = mock_connect

        await instance._ensure_connected()
        mock_connect.assert_not_called()

    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_ensure_connected_authorization_needed(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test _ensure_connected when authorization is needed."""
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        instance.client = mocker.MagicMock()
        instance.client.connect = mocker.AsyncMock()
        instance.client.is_user_authorized = mocker.AsyncMock(return_value=False)
        instance.client.send_code_request = mocker.AsyncMock()
        instance.client.sign_in = mocker.AsyncMock()

        # Mock input to avoid hanging in tests
        mocker.patch("builtins.input", side_effect=["123456789", "12345"])

        await instance._ensure_connected()
        assert instance._is_connected is True
        instance.client.connect.assert_called_once()
        instance.client.is_user_authorized.assert_called_once()

    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_ensure_connected_session_password(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test _ensure_connected with session password needed."""
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        instance.client = mocker.MagicMock()
        instance.client.connect = mocker.AsyncMock()
        instance.client.is_user_authorized = mocker.AsyncMock(return_value=False)
        instance.client.send_code_request = mocker.AsyncMock()
        # Create a proper SessionPasswordNeededError instance
        session_error = SessionPasswordNeededError(request=mocker.MagicMock())
        instance.client.sign_in = mocker.AsyncMock(side_effect=[session_error, None])

        # Mock input to avoid hanging in tests
        mocker.patch(
            "builtins.input", side_effect=["123456789", "12345", "2fapassword"]
        )

        await instance._ensure_connected()
        assert instance._is_connected is True
        instance.client.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_ensure_connected_exception(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test _ensure_connected exception handling."""
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        instance.client = mocker.MagicMock()
        instance.client.connect = mocker.AsyncMock(
            side_effect=Exception("Connection failed")
        )
        instance.logger = mocker.MagicMock()

        with pytest.raises(Exception, match="Connection failed"):
            await instance._ensure_connected()
        assert instance._is_connected is False
        instance.logger.error.assert_called_once()

    # run_async
    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_run_async_success(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test run_async successful execution."""
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        instance._is_connected = False

        # Mock dependencies
        mock_ensure = mocker.patch.object(instance, "_ensure_connected")
        mock_log_action = mocker.patch.object(instance, "log_action_async")
        mock_check = mocker.patch.object(
            instance,
            "check_mentions_async",
            new_callable=mocker.AsyncMock,
            return_value=2,
        )
        mock_sleep = mocker.patch("asyncio.sleep")

        # Set exit_signal after first iteration
        def set_exit_signal(*args, **kwargs):
            instance.exit_signal = True

        mock_sleep.side_effect = set_exit_signal

        await instance.run_async(
            poll_interval_minutes=1
        )  # Use integer to avoid float issues

        mock_ensure.assert_called_once()
        mock_log_action.assert_called_with(
            "started", f"Tracking {len(telegram_chats)} chats"
        )
        mock_check.assert_called_once()
        mock_sleep.assert_called()

    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_run_async_mentions_found(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test run_async when mentions are found."""
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        instance._is_connected = False
        instance.logger = mocker.MagicMock()

        # Mock dependencies
        mocker.patch.object(instance, "_ensure_connected")
        mocker.patch.object(instance, "log_action_async")

        # Return 3 mentions on first check, then set exit_signal
        check_count = 0

        async def mock_check():
            nonlocal check_count
            check_count += 1
            if check_count == 1:
                return 3
            instance.exit_signal = True
            return 0

        mocker.patch.object(instance, "check_mentions_async", side_effect=mock_check)
        mocker.patch("asyncio.sleep")

        await instance.run_async(
            poll_interval_minutes=1
        )  # Use integer to avoid float issues

        # Should log that mentions were found
        instance.logger.info.assert_any_call("Found 3 new mentions")

    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_run_async_cancelled(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test run_async when cancelled."""
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        instance._is_connected = False
        instance.client = mocker.MagicMock()
        instance.logger = mocker.MagicMock()

        # Mock _ensure_connected to avoid actual connection
        mocker.patch.object(
            instance, "_ensure_connected", new_callable=mocker.AsyncMock
        )

        # Mock log_action_async
        mocker.patch.object(instance, "log_action_async", new_callable=mocker.AsyncMock)

        # Mock check_mentions_async to raise CancelledError immediately
        mocker.patch.object(
            instance,
            "check_mentions_async",
            new_callable=mocker.AsyncMock,
            side_effect=asyncio.CancelledError(),
        )

        # Mock cleanup
        mocker.patch.object(instance, "cleanup", new_callable=mocker.AsyncMock)

        # Should raise CancelledError (due to re-raise in run_async's except block)
        with pytest.raises(asyncio.CancelledError):
            await instance.run_async(poll_interval_minutes=1)

        instance.logger.info.assert_any_call("Telegram tracker cancelled")

    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_run_async_exception(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test run_async when exception occurs."""
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        instance._is_connected = False
        instance.logger = mocker.MagicMock()

        # Mock dependencies
        mocker.patch.object(instance, "_ensure_connected")
        mocker.patch.object(instance, "log_action_async")
        mock_cleanup = mocker.patch.object(
            instance, "cleanup", new_callable=mocker.AsyncMock
        )

        mocker.patch.object(
            instance,
            "check_mentions_async",
            new_callable=mocker.AsyncMock,
            side_effect=Exception("Test error"),
        )

        with pytest.raises(Exception, match="Test error"):
            await instance.run_async(poll_interval_minutes=1)

        instance.logger.error.assert_called_once_with(
            "Telegram tracker error: Test error"
        )
        mock_cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_run_async_no_client(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test run_async when self.client is None (early exit)."""
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        instance.logger = mocker.MagicMock()
        instance.client = None  # Explicitly set client to None
        mock_cleanup = mocker.patch.object(
            instance, "cleanup", new_callable=mocker.AsyncMock
        )

        await instance.run_async(poll_interval_minutes=1)

        # Should log error and return immediately, skipping the cleanup finally block
        instance.logger.error.assert_called_once_with("Telegram client not available")
        mock_cleanup.assert_not_called()

    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_run_async_keyboardinterrupt(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test run_async when a KeyboardInterrupt occurs (caught branch)."""
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(
            lambda x, y=None: None, telegram_config, telegram_chats
        )
        instance._is_connected = False
        instance.client = mocker.MagicMock()
        instance.logger = mocker.MagicMock()

        # Mock dependencies
        mocker.patch.object(
            instance, "_ensure_connected", new_callable=mocker.AsyncMock
        )
        mocker.patch.object(instance, "log_action_async", new_callable=mocker.AsyncMock)

        # Mock check_mentions_async to raise KeyboardInterrupt immediately
        mocker.patch.object(
            instance,
            "check_mentions_async",
            new_callable=mocker.AsyncMock,
            side_effect=KeyboardInterrupt(),
        )

        mock_cleanup = mocker.patch.object(
            instance, "cleanup", new_callable=mocker.AsyncMock
        )

        # run_async catches KeyboardInterrupt and logs it
        await instance.run_async(poll_interval_minutes=1)

        # Assert the KeyboardInterrupt was caught and logged
        instance.logger.info.assert_any_call("Telegram tracker stopped by user")
        # Assert cleanup was called in the finally block
        mock_cleanup.assert_called_once()
