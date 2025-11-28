"""Testing module for :py:mod:`trackers.telegram` module."""

import asyncio

import pytest

from trackers.telegram import TelegramTracker


@pytest.mark.django_db
class TestTrackersTelegram:
    """Testing class for :class:`trackers.telegram.TelegramTracker`."""

    # __init__
    def test_trackers_telegramtracker_init_success(
        self, mocker, telegram_config, telegram_chats
    ):
        # Mock TelegramClient to prevent actual API calls
        mock_telegram_client = mocker.patch("trackers.telegram.TelegramClient")
        mocker.patch.object(TelegramTracker, "log_action")
        # Create instance - this will call the real __init__ but with mocked TelegramClient
        instance = TelegramTracker(lambda x: None, telegram_config, telegram_chats)
        # Assert TelegramClient was called with correct parameters
        mock_telegram_client.assert_called_once_with(
            session="test_session", api_id="test_api_id", api_hash="test_api_hash"
        )
        assert instance.bot_username == "test_bot"
        assert instance.tracked_chats == telegram_chats

    # extract_mention_data
    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_extract_mention_data_with_reply(
        self, mocker, telegram_config, telegram_chats
    ):
        # Mock the parent init to avoid API calls
        mocker.patch.object(TelegramTracker, "__init__", return_value=None)
        mocker.patch.object(TelegramTracker, "log_action")
        instance = TelegramTracker(lambda x: None, telegram_config, telegram_chats)
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
        }
        mocker.patch.object(
            instance, "_get_replied_message_info", return_value=mock_replied_info
        )
        mock_message = mocker.MagicMock()
        mock_message.sender_id = 12345
        mock_message.id = 100
        mock_message.text = "Hello @test_bot!"
        mock_message.reply_to_msg_id = 99
        mock_chat = mocker.MagicMock()
        mock_chat.id = 67890
        mock_chat.title = "Test Group"
        mock_chat.username = "testgroup"
        mock_message.chat = mock_chat
        result = await instance.extract_mention_data(mock_message)
        assert result["suggester"] == 12345
        assert result["suggester_username"] == "testuser"
        assert result["suggestion_url"] == "https://t.me/testgroup/100"
        assert result["contribution_url"] == "https://t.me/testgroup/99"
        assert result["contributor"] == 54321
        assert result["contributor_username"] == "replieduser"
        assert result["type"] == "message"
        assert result["telegram_chat"] == "Test Group"
        assert result["chat_username"] == "testgroup"
        assert result["content"] == "Hello @test_bot!"

    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_extract_mention_data_no_reply(
        self, mocker, telegram_config, telegram_chats
    ):
        # Mock the parent init to avoid API calls
        mocker.patch.object(TelegramTracker, "__init__", return_value=None)
        mocker.patch.object(TelegramTracker, "log_action")
        instance = TelegramTracker(lambda x: None, telegram_config, telegram_chats)
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
        mock_chat = mocker.MagicMock()
        mock_chat.id = 67890
        mock_chat.title = "Test Group"
        mock_chat.username = None  # No username
        mock_message.chat = mock_chat
        result = await instance.extract_mention_data(mock_message)
        assert result["suggestion_url"] == "chat_67890_msg_100"
        assert result["contribution_url"] == "chat_67890_msg_100"
        assert result["contributor"] == 12345
        assert result["contributor_username"] == "testuser"

    # check_mentions
    def test_trackers_telegramtracker_check_mentions_no_client(
        self, mocker, telegram_config, telegram_chats
    ):
        # Mock TelegramClient to prevent actual API calls during initialization
        mocker.patch("trackers.telegram.TelegramClient")
        # Create instance - this will call the real __init__ and BaseMentionTracker.__init__
        instance = TelegramTracker(lambda x: None, telegram_config, telegram_chats)
        instance.logger = mocker.MagicMock()
        # Set client to None
        instance.client = None
        # Mock cleanup to ensure it's not called
        mock_cleanup = mocker.patch.object(instance, "cleanup")
        result = instance.check_mentions()
        assert result == 0
        instance.logger.error.assert_called_with("Telegram client not available")
        # Cleanup should not be called when client is None
        mock_cleanup.assert_not_called()

    def test_trackers_telegramtracker_check_mentions_success(
        self, mocker, telegram_config, telegram_chats
    ):
        # Mock TelegramClient to prevent actual API calls during initialization
        mocker.patch("trackers.telegram.TelegramClient")
        # Create instance - this will call the real __init__ and BaseMentionTracker.__init__
        instance = TelegramTracker(lambda x: None, telegram_config, telegram_chats)
        instance.client = mocker.MagicMock()
        instance.logger = mocker.MagicMock()

        # Mock asyncio event loop creation
        mock_get_running_loop = mocker.patch("asyncio.get_running_loop", side_effect=RuntimeError)
        mock_new_event_loop = mocker.patch("asyncio.new_event_loop")
        mock_set_event_loop = mocker.patch("asyncio.set_event_loop")
        mock_loop = mocker.MagicMock()
        mock_new_event_loop.return_value = mock_loop

        mock_loop.run_until_complete.return_value = 3
        result = instance.check_mentions()
        assert result == 3
        instance.client.__enter__.assert_called_once()
        instance.client.__exit__.assert_called_once()
        mock_get_running_loop.assert_called_once()
        mock_new_event_loop.assert_called_once()
        mock_set_event_loop.assert_called_once_with(mock_loop)

    def test_trackers_telegramtracker_check_mentions_exception(
        self, mocker, telegram_config, telegram_chats
    ):
        # Mock TelegramClient to prevent actual API calls during initialization
        mocker.patch("trackers.telegram.TelegramClient")
        # Create instance - this will call the real __init__ and BaseMentionTracker.__init__
        instance = TelegramTracker(lambda x: None, telegram_config, telegram_chats)
        instance.client = mocker.MagicMock()
        instance.logger = mocker.MagicMock()

        # Mock asyncio event loop creation
        mock_get_running_loop = mocker.patch("asyncio.get_running_loop", side_effect=RuntimeError)
        mock_new_event_loop = mocker.patch("asyncio.new_event_loop")
        mock_set_event_loop = mocker.patch("asyncio.set_event_loop")
        mock_loop = mocker.MagicMock()
        mock_new_event_loop.return_value = mock_loop

        instance.client.__enter__.side_effect = Exception("Connection error")
        mock_log_action = mocker.patch.object(instance, "log_action")
        result = instance.check_mentions()
        assert result == 0
        instance.logger.error.assert_called_with(
            "Error in Telegram mention check: Connection error"
        )
        mock_log_action.assert_called_with(
            "telegram_check_error", "Error: Connection error"
        )
        mock_get_running_loop.assert_called_once()
        mock_new_event_loop.assert_called_once()
        mock_set_event_loop.assert_called_once_with(mock_loop)

    def test_trackers_telegramtracker_get_chat_entity_success(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test _get_chat_entity successful chat retrieval."""
        # Mock TelegramClient
        mocker.patch("trackers.telegram.TelegramClient")
        mocker.patch.object(TelegramTracker, "log_action")
        instance = TelegramTracker(lambda x: None, telegram_config, telegram_chats)
        mock_entity = mocker.MagicMock()
        # Mock the async method properly
        instance.client.get_entity = mocker.AsyncMock(return_value=mock_entity)
        # Test successful chat retrieval
        result = asyncio.run(instance._get_chat_entity("test_chat"))
        instance.client.get_entity.assert_called_once_with("test_chat")
        assert result == mock_entity

    def test_trackers_telegramtracker_get_chat_entity_exception(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test _get_chat_entity exception handling."""
        # Mock TelegramClient
        mocker.patch("trackers.telegram.TelegramClient")
        mocker.patch.object(TelegramTracker, "log_action")
        instance = TelegramTracker(lambda x: None, telegram_config, telegram_chats)
        instance.logger = mocker.MagicMock()
        # Mock the async method to raise exception
        instance.client.get_entity = mocker.AsyncMock(
            side_effect=Exception("Chat not found")
        )
        # Test exception handling
        result = asyncio.run(instance._get_chat_entity("invalid_chat"))
        assert result is None
        instance.logger.error.assert_called_once()

    # # run
    def test_trackers_telegramtracker_run_no_client(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test run method when client is None."""
        # Mock TelegramClient
        mocker.patch("trackers.telegram.TelegramClient")
        mocker.patch.object(TelegramTracker, "log_action")
        instance = TelegramTracker(lambda x: None, telegram_config, telegram_chats)
        instance.logger = mocker.MagicMock()
        # Set client to None
        instance.client = None
        # Mock cleanup to ensure it's not called
        mock_cleanup = mocker.patch.object(instance, "cleanup")
        # Run should return early
        instance.run(poll_interval_minutes=30, max_iterations=1)
        # Should log error and return early
        instance.logger.error.assert_called_with(
            "Cannot start Telegram tracker - client not available"
        )
        # Cleanup should not be called when client is None
        mock_cleanup.assert_not_called()

    def test_trackers_telegramtracker_run_wrapper_calls_base_run(
        self, mocker, telegram_config, telegram_chats
    ):
        mocker.patch("trackers.telegram.TelegramClient")
        mocker.patch.object(TelegramTracker, "log_action")
        # Patch BaseMentionTracker.run so no real loop runs
        mocked_base_run = mocker.patch("trackers.twitter.BaseMentionTracker.run")
        # Create instance (MessageParser.parse mocked out)
        tracker = TelegramTracker(lambda x: None, telegram_config, telegram_chats)
        # Call the wrapper
        tracker.run(poll_interval_minutes=10, max_iterations=5)
        # Ensure BaseMentionTracker.run was called once with correct args
        mocked_base_run.assert_called_once_with(
            poll_interval_minutes=10,
            max_iterations=5,
        )

    # # _check_chat_mentions
    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_check_chat_mentions_no_chat(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test _check_chat_mentions when chat entity is None."""
        # Mock TelegramClient
        mocker.patch("trackers.telegram.TelegramClient")
        mocker.patch.object(TelegramTracker, "log_action")
        instance = TelegramTracker(lambda x: None, telegram_config, telegram_chats)
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
        mocker.patch.object(TelegramTracker, "log_action")
        instance = TelegramTracker(lambda x: None, telegram_config, telegram_chats)
        mock_chat = mocker.MagicMock()
        mocker.patch.object(instance, "_get_chat_entity", return_value=mock_chat)
        mock_message = mocker.MagicMock()
        mock_message.text = "@test_bot hello"
        mock_message.id = 123
        mock_chat.id = 456

        # Mock async iter_messages properly
        async def mock_iter_messages(*args, **kwargs):
            yield mock_message

        instance.client.iter_messages = mock_iter_messages
        # Mock the async extract_mention_data method
        mock_extract_data = mocker.patch.object(
            instance, "extract_mention_data", return_value={}
        )
        mock_process_mention = mocker.patch.object(
            instance, "process_mention", return_value=True
        )
        mocker.patch.object(instance, "is_processed", return_value=False)
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
        mocker.patch.object(TelegramTracker, "log_action")
        instance = TelegramTracker(lambda x: None, telegram_config, telegram_chats)
        instance.logger = mocker.MagicMock()
        mock_chat = mocker.MagicMock()
        mocker.patch.object(instance, "_get_chat_entity", return_value=mock_chat)

        # Mock async method to raise exception
        async def mock_iter_messages_error(*args, **kwargs):
            raise Exception("API error")

        instance.client.iter_messages = mock_iter_messages_error
        # Test exception handling
        result = await instance._check_chat_mentions("problem_chat")
        assert result == 0
        instance.logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_check_chat_mentions_condition_not_met(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test _check_chat_mentions when mention condition is not met."""
        # Mock TelegramClient
        mocker.patch("trackers.telegram.TelegramClient")
        mocker.patch.object(TelegramTracker, "log_action")
        instance = TelegramTracker(lambda x: None, telegram_config, telegram_chats)
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
        mock_process_mention = mocker.patch.object(instance, "process_mention")
        mock_is_processed = mocker.patch.object(instance, "is_processed")
        result = await instance._check_chat_mentions("test_chat")
        # Should return 0 because condition not met
        assert result == 0
        mock_process_mention.assert_not_called()
        # is_processed should not be called when bot username not in message
        mock_is_processed.assert_not_called()

    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_check_chat_mentions_already_processed(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test _check_chat_mentions when message is already processed."""
        # Mock TelegramClient
        mocker.patch("trackers.telegram.TelegramClient")
        mocker.patch.object(TelegramTracker, "log_action")
        instance = TelegramTracker(lambda x: None, telegram_config, telegram_chats)
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
        mock_process_mention = mocker.patch.object(instance, "process_mention")
        # Message is already processed
        mock_is_processed = mocker.patch.object(
            instance, "is_processed", return_value=True
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
        instance = TelegramTracker(lambda x: None, telegram_config, telegram_chats)
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
            instance, "process_mention", return_value=False
        )
        mocker.patch.object(instance, "is_processed", return_value=False)
        result = await instance._check_chat_mentions("test_chat")
        # Should return 0 because process_mention returned False
        assert result == 0
        mock_process_mention.assert_called_once()

    def test_trackers_telegramtracker_check_mentions_async_no_client(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test check_mentions_async when client is None."""
        # Mock TelegramClient
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(lambda x: None, telegram_config, telegram_chats)
        # Set client to None
        instance.client = None
        result = asyncio.run(instance.check_mentions_async())
        # Should return 0 when client is None
        assert result == 0

    def test_trackers_telegramtracker_check_mentions_async_success(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test check_mentions_async successful execution with multiple chats."""
        # Mock TelegramClient
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(lambda x: None, telegram_config, telegram_chats)
        # Track sleep calls to verify delay between chats
        sleep_calls = []

        async def mock_sleep(delay):
            sleep_calls.append(delay)

        mocker.patch("asyncio.sleep", side_effect=mock_sleep)
        # Mock _check_chat_mentions to return different counts for different chats
        mock_check_chat = mocker.patch.object(instance, "_check_chat_mentions")
        mock_check_chat.side_effect = [2, 1]  # Different counts for 2 chats
        result = asyncio.run(instance.check_mentions_async())
        # Should return total mentions (2 + 1 = 3)
        assert result == 3
        # Should call _check_chat_mentions for each tracked chat
        assert mock_check_chat.call_count == len(telegram_chats)
        # Should sleep after each chat (2 sleeps for 2 chats)
        assert len(sleep_calls) == len(telegram_chats)
        assert all(sleep == 60 for sleep in sleep_calls)

    def test_trackers_telegramtracker_check_mentions_async_empty_chats(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test check_mentions_async with empty tracked_chats list."""
        # Mock TelegramClient
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(lambda x: None, telegram_config, telegram_chats)
        # Set tracked_chats to empty list
        instance.tracked_chats = []
        # Track sleep calls
        sleep_calls = []

        async def mock_sleep(delay):
            sleep_calls.append(delay)

        mocker.patch("asyncio.sleep", side_effect=mock_sleep)
        result = asyncio.run(instance.check_mentions_async())
        # Should return 0 when no chats to track
        assert result == 0
        # Should not sleep when there are no chats
        assert len(sleep_calls) == 0

    def test_trackers_telegramtracker_check_mentions_async_single_chat(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test check_mentions_async with single chat (no sleep between chats)."""
        # Mock TelegramClient
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(lambda x: None, telegram_config, telegram_chats)
        # Set tracked_chats to single chat
        instance.tracked_chats = ["single_chat"]
        # Track sleep calls
        sleep_calls = []

        async def mock_sleep(delay):
            sleep_calls.append(delay)

        mocker.patch("asyncio.sleep", side_effect=mock_sleep)
        mocker.patch.object(instance, "_check_chat_mentions", return_value=3)
        result = asyncio.run(instance.check_mentions_async())
        # Should return mentions from single chat
        assert result == 3
        # Should sleep even for single chat (sleep runs after every chat)
        assert len(sleep_calls) == 1
        assert sleep_calls[0] == 60

    def test_trackers_telegramtracker_check_mentions_async_three_chats(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test check_mentions_async with three chats."""
        # Mock TelegramClient
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(lambda x: None, telegram_config, telegram_chats)
        # Set tracked_chats to three chats
        instance.tracked_chats = ["chat1", "chat2", "chat3"]
        # Track sleep calls
        sleep_calls = []

        async def mock_sleep(delay):
            sleep_calls.append(delay)

        mocker.patch("asyncio.sleep", side_effect=mock_sleep)
        mock_check_chat = mocker.patch.object(instance, "_check_chat_mentions")
        mock_check_chat.side_effect = [1, 2, 3]  # Different counts for 3 chats
        result = asyncio.run(instance.check_mentions_async())
        # Should return total mentions (1 + 2 + 3 = 6)
        assert result == 6
        # Should call _check_chat_mentions for each tracked chat
        assert mock_check_chat.call_count == 3
        # Should sleep after each chat (3 sleeps for 3 chats)
        assert len(sleep_calls) == 3
        assert all(sleep == 60 for sleep in sleep_calls)

    def test_trackers_telegramtracker_check_chat_mentions_no_bot_username(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test _check_chat_mentions when bot_username is empty."""
        # Mock TelegramClient
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(lambda x: None, telegram_config, telegram_chats)
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
        mock_process_mention = mocker.patch.object(instance, "process_mention")
        mock_is_processed = mocker.patch.object(instance, "is_processed")
        result = asyncio.run(instance._check_chat_mentions("test_chat"))
        # Should return 0 when bot_username is empty
        assert result == 0
        mock_process_mention.assert_not_called()
        mock_is_processed.assert_not_called()

    def test_trackers_telegramtracker_check_chat_mentions_message_no_text(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test _check_chat_mentions when message has no text."""
        # Mock TelegramClient
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(lambda x: None, telegram_config, telegram_chats)
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
        mock_process_mention = mocker.patch.object(instance, "process_mention")
        mock_is_processed = mocker.patch.object(instance, "is_processed")
        result = asyncio.run(instance._check_chat_mentions("test_chat"))
        # Should return 0 when message has no text
        assert result == 0
        mock_process_mention.assert_not_called()
        mock_is_processed.assert_not_called()

    def test_trackers_telegramtracker_run_mentions_found_logging(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test run method when mentions_found > 0."""
        # Mock TelegramClient
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(lambda x: None, telegram_config, telegram_chats)
        instance.logger = mocker.MagicMock()
        # Mock check_mentions to return positive number
        mocker.patch.object(instance, "check_mentions", return_value=5)
        mocker.patch("time.sleep", side_effect=StopIteration)
        # Run one iteration
        try:
            instance.run(poll_interval_minutes=0.1, max_iterations=1)
        except StopIteration:
            pass
        # Should log that mentions were found
        instance.logger.info.assert_any_call("Found 5 new mentions")

    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_get_sender_info_success(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test _get_sender_info successful retrieval."""
        # Mock TelegramClient
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(lambda x: None, telegram_config, telegram_chats)
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
        instance = TelegramTracker(lambda x: None, telegram_config, telegram_chats)
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
        instance = TelegramTracker(lambda x: None, telegram_config, telegram_chats)
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
        instance = TelegramTracker(lambda x: None, telegram_config, telegram_chats)
        mock_message = mocker.MagicMock()
        mock_message.reply_to_msg_id = 99
        mock_message.chat_id = 123
        mock_replied_message = mocker.MagicMock()
        mock_replied_message.id = 99
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
        instance.client.get_messages.assert_called_once_with(123, ids=99)

    @pytest.mark.asyncio
    async def test_trackers_telegramtracker_get_replied_message_info_no_reply(
        self, mocker, telegram_config, telegram_chats
    ):
        """Test _get_replied_message_info when no reply exists."""
        # Mock TelegramClient
        mocker.patch("trackers.telegram.TelegramClient")
        instance = TelegramTracker(lambda x: None, telegram_config, telegram_chats)
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
        instance = TelegramTracker(lambda x: None, telegram_config, telegram_chats)
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
        instance = TelegramTracker(lambda x: None, telegram_config, telegram_chats)
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
        instance = TelegramTracker(lambda x: None, telegram_config, telegram_chats)
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
        instance = TelegramTracker(lambda x: None, telegram_config, telegram_chats)
        mock_chat = mocker.MagicMock()
        mock_chat.id = 12345
        mock_chat.username = None
        result = instance._generate_message_url(mock_chat, 100)
        assert result == "chat_12345_msg_100"
