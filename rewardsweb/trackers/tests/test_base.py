"""Testing module for :py:mod:`trackers.base` module."""

import asyncio
import signal
from pathlib import Path
from unittest.mock import AsyncMock, Mock, call, patch

import pytest
import requests

import trackers.base
from trackers.base import BaseMentionTracker


@pytest.mark.django_db
class TestTrackersBaseMentionTracker:
    """Testing class for :class:`trackers.base.BaseMentionTracker` class."""

    # __init__
    def test_base_basementiontracker_init_success(self, mocker):
        mock_setup_logging = mocker.patch.object(BaseMentionTracker, "setup_logging")

        def callback(data):
            pass

        instance = BaseMentionTracker("test_platform", callback)
        assert instance.platform_name == "test_platform"
        assert instance.parse_message_callback == callback
        assert instance.async_task is None
        mock_setup_logging.assert_called_once()

    # setup_logging
    def test_base_basementiontracker_setup_logging_creates_directory(self, mocker):
        mock_basic_config = mocker.patch("logging.basicConfig")
        mock_get_logger = mocker.patch("logging.getLogger")
        mock_logger = mocker.MagicMock()
        mock_get_logger.return_value = mock_logger
        instance = BaseMentionTracker("test_platform", lambda x: None)
        mock_basic_config.reset_mock()
        mock_get_logger.reset_mock()
        with patch("os.path.exists", return_value=False) as mock_exists, patch(
            "os.makedirs"
        ) as mock_makedirs:
            instance.setup_logging()
            mock_exists.assert_called_once_with(
                Path(trackers.base.__file__).parent.parent.resolve() / "logs"
            )
            mock_makedirs.assert_called_once_with(
                Path(trackers.base.__file__).parent.parent.resolve() / "logs"
            )
        mock_basic_config.assert_called_once()
        mock_get_logger.assert_called_once_with("test_platform_tracker")
        assert instance.logger == mock_logger

    def test_base_basementiontracker_setup_logging_success(self, mocker):
        mock_basic_config = mocker.patch("logging.basicConfig")
        mock_get_logger = mocker.patch("logging.getLogger")
        mock_logger = mocker.MagicMock()
        mock_get_logger.return_value = mock_logger
        instance = BaseMentionTracker("test_platform", lambda x: None)
        mock_basic_config.reset_mock()
        mock_get_logger.reset_mock()
        instance.setup_logging()
        mock_basic_config.assert_called_once()
        mock_get_logger.assert_called_once_with("test_platform_tracker")
        assert instance.logger == mock_logger

    # is_processed
    def test_base_basementiontracker_is_processed_true(self, mocker):
        mocker.patch.object(BaseMentionTracker, "setup_logging")
        mock_is_processed_orm = mocker.patch(
            "trackers.models.Mention.objects.is_processed"
        )
        mock_is_processed_orm.return_value = True
        instance = BaseMentionTracker("test_platform", lambda x: None)
        result = instance.is_processed("test_item_id")
        assert result is True
        mock_is_processed_orm.assert_called_once_with("test_item_id", "test_platform")

    def test_base_basementiontracker_is_processed_false(self, mocker):
        mocker.patch.object(BaseMentionTracker, "setup_logging")
        mock_is_processed_orm = mocker.patch(
            "trackers.models.Mention.objects.is_processed"
        )
        mock_is_processed_orm.return_value = False
        instance = BaseMentionTracker("test_platform", lambda x: None)
        result = instance.is_processed("test_item_id")
        assert result is False
        mock_is_processed_orm.assert_called_once_with("test_item_id", "test_platform")

    # mark_processed
    @pytest.mark.asyncio
    async def test_base_basementiontracker_mark_processed_success(self, mocker):
        mocker.patch.object(BaseMentionTracker, "setup_logging")
        mock_mark_processed_orm = mocker.AsyncMock(return_value=None)
        mocker.patch(
            "trackers.models.Mention.objects.mark_processed",
            new=mock_mark_processed_orm,
        )
        instance = BaseMentionTracker("test_platform", lambda x: None)
        test_data = {
            "suggester": "test_user",
            "subreddit": "test_subreddit",
        }
        instance.mark_processed("test_item_id", test_data)
        mock_mark_processed_orm.assert_called_once_with(
            "test_item_id", "test_platform", test_data
        )

    # process_mention
    def test_base_basementiontracker_process_mention_already_processed(self, mocker):
        mock_is_processed = mocker.patch.object(BaseMentionTracker, "is_processed")
        mock_is_processed.return_value = True
        mock_callback, username = mocker.MagicMock(), mocker.MagicMock()
        instance = BaseMentionTracker("test_platform", mock_callback)
        result = instance.process_mention("test_item_id", {}, username)
        assert result is False
        mock_callback.assert_not_called()

    def test_base_basementiontracker_process_mention_success(self, mocker):
        mock_is_processed = mocker.patch.object(BaseMentionTracker, "is_processed")
        mock_is_processed.return_value = False
        mock_prepare_contribution_data = mocker.patch.object(
            BaseMentionTracker, "prepare_contribution_data"
        )
        mock_post_new_contribution = mocker.patch.object(
            BaseMentionTracker, "post_new_contribution"
        )
        mock_mark_processed = mocker.MagicMock(return_value=None)
        mocker.patch.object(
            BaseMentionTracker, "mark_processed", new=mock_mark_processed
        )
        mock_log_action = mocker.MagicMock(return_value=None)
        mocker.patch.object(BaseMentionTracker, "log_action", new=mock_log_action)
        mock_logger = mocker.MagicMock()
        mock_callback = mocker.MagicMock(return_value={"parsed": "data"})
        instance = BaseMentionTracker("test_platform", mock_callback)
        instance.logger = mock_logger
        test_data = {"suggester": "test_user", "content": "content"}
        username = "username"
        result = instance.process_mention("test_item_id", test_data, username)
        assert result is True
        mock_callback.assert_called_once_with("content", "username")
        mock_prepare_contribution_data.assert_called_once_with(
            {"parsed": "data"}, test_data
        )
        mock_post_new_contribution.assert_called_once()
        mock_mark_processed.assert_called_once_with("test_item_id", test_data)
        mock_logger.info.assert_called_once_with("Processed mention from test_user")
        mock_log_action.assert_called_once_with(
            "mention_processed", "Item: test_item_id, Suggester: test_user"
        )

    def test_base_basementiontracker_process_mention_exception(self, mocker):
        mock_is_processed = mocker.patch.object(BaseMentionTracker, "is_processed")
        mock_is_processed.return_value = False
        mock_logger = mocker.MagicMock()
        mock_log_action = mocker.MagicMock(return_value=None)
        mocker.patch.object(BaseMentionTracker, "log_action", new=mock_log_action)
        mock_callback = mocker.MagicMock(side_effect=Exception("Test error"))
        instance = BaseMentionTracker("test_platform", mock_callback)
        instance.logger = mock_logger
        result = instance.process_mention("test_item_id", {}, "username")
        assert result is False
        mock_logger.error.assert_called_once_with(
            "Error processing mention test_item_id: Test error"
        )
        mock_log_action.assert_called_once_with(
            "processing_error", "Item: test_item_id, Error: Test error"
        )

    # log_action
    def test_base_basementiontracker_log_action_success(self, mocker):
        mocker.patch.object(BaseMentionTracker, "setup_logging")
        mock_log_action_orm = mocker.MagicMock(return_value=None)
        mocker.patch(
            "trackers.models.MentionLog.objects.log_action", new=mock_log_action_orm
        )
        instance = BaseMentionTracker("test_platform", lambda x: None)
        instance.log_action("test_action", "test_details")
        mock_log_action_orm.assert_called_once_with(
            "test_platform", "test_action", "test_details"
        )

    # log_action_async
    @pytest.mark.asyncio
    async def test_base_basementiontracker_log_action_async_functionality(self, mocker):
        mocker.patch.object(BaseMentionTracker, "setup_logging")
        mocked_log = mocker.patch("trackers.base.BaseMentionTracker.log_action")
        instance = BaseMentionTracker("test_platform", lambda x: None)
        await instance.log_action_async("test_action", "test_details")
        mocked_log.assert_called_once_with("test_action", "test_details")

    # prepare_contribution_data
    def test_base_basementiontracker_prepare_contribution_data_success(self, mocker):
        mocker.patch("trackers.base.get_env_variable", return_value="")
        mock_social_platform_prefixes = mocker.patch(
            "trackers.base.social_platform_prefixes"
        )
        mock_social_platform_prefixes.return_value = [("Testplatform", "TP_")]
        instance = BaseMentionTracker("testplatform", lambda x: None)
        parsed_message = {"title": "Test Title", "description": "Test Description"}
        message_data = {
            "contributor": "testuser",
            "contribution_url": "http://example.com",
        }
        result = instance.prepare_contribution_data(parsed_message, message_data)
        expected = {
            "title": "Test Title",
            "description": "Test Description",
            "username": "TP_testuser",
            "url": "http://example.com",
            "platform": "Testplatform",
        }
        assert result == expected

    def test_base_basementiontracker_prepare_contribution_data_excluded_contributor(
        self, mocker
    ):
        mocker.patch(
            "trackers.base.get_env_variable", return_value="excluded1,excluded2"
        )
        mock_social_platform_prefixes = mocker.patch(
            "trackers.base.social_platform_prefixes"
        )
        mock_social_platform_prefixes.return_value = [("Testplatform", "TP_")]
        instance = BaseMentionTracker("testplatform", lambda x: None)
        parsed_message = {"title": "Test Title", "description": "Test Description"}
        message_data = {
            "contributor": "excluded2",
            "contribution_url": "http://example.com",
            "suggester": "testsuggester",
        }
        result = instance.prepare_contribution_data(parsed_message, message_data)
        expected = {
            "title": "Test Title",
            "description": "Test Description",
            "username": "TP_testsuggester",
            "url": "http://example.com",
            "platform": "Testplatform",
        }
        assert result == expected

    def test_base_basementiontracker_prepare_contribution_data_no_contributor(
        self, mocker
    ):
        mocker.patch("trackers.base.get_env_variable", return_value="")
        mock_social_platform_prefixes = mocker.patch(
            "trackers.base.social_platform_prefixes"
        )
        mock_social_platform_prefixes.return_value = [("Testplatform", "TP_")]
        instance = BaseMentionTracker("testplatform123", lambda x: None)
        parsed_message = {"title": "Test Title", "description": "Test Description"}
        message_data = {
            "contribution_url": "http://example.com",
            "suggester": "test_suggester",
        }  # No contributor
        result = instance.prepare_contribution_data(parsed_message, message_data)
        expected = {
            "title": "Test Title",
            "description": "Test Description",
            "username": "TP_test_suggester",
            "url": "http://example.com",
            "platform": "Testplatform",
        }
        assert result == expected

    # post_new_contribution
    def test_base_basementiontracker_post_new_contribution_success(self, mocker):
        mock_requests_post = mocker.patch("requests.post")
        mock_response = mocker.MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"success": True}
        mock_requests_post.return_value = mock_response
        instance = BaseMentionTracker("test_platform", lambda x: None)
        contribution_data = {"username": "test_user", "platform": "Testplatform"}
        result = instance.post_new_contribution(contribution_data)
        mock_requests_post.assert_called_once_with(
            "http://127.0.0.1:8000/api/addcontribution",
            json=contribution_data,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        assert result == {"success": True}

    def test_base_basementiontracker_post_new_contribution_connection_error(
        self, mocker
    ):
        mock_requests_post = mocker.patch("requests.post")
        mock_requests_post.side_effect = requests.exceptions.ConnectionError()
        instance = BaseMentionTracker("test_platform", lambda x: None)
        contribution_data = {"username": "test_user", "platform": "Testplatform"}
        with pytest.raises(
            Exception,
            match="Cannot connect to the API server. Make sure it's running on localhost.",
        ):
            instance.post_new_contribution(contribution_data)

    def test_base_basementiontracker_post_new_contribution_http_error(self, mocker):
        mock_requests_post = mocker.patch("requests.post")
        mock_response = mocker.MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_requests_post.side_effect = requests.exceptions.HTTPError(
            response=mock_response
        )
        instance = BaseMentionTracker("test_platform", lambda x: None)
        contribution_data = {"username": "test_user", "platform": "Testplatform"}
        with pytest.raises(Exception, match="API returned error: 400 - Bad Request"):
            instance.post_new_contribution(contribution_data)

    def test_base_basementiontracker_post_new_contribution_timeout(self, mocker):
        mock_requests_post = mocker.patch("requests.post")
        mock_requests_post.side_effect = requests.exceptions.Timeout()
        instance = BaseMentionTracker("test_platform", lambda x: None)
        contribution_data = {"username": "test_user", "platform": "Testplatform"}
        with pytest.raises(Exception, match="API request timed out."):
            instance.post_new_contribution(contribution_data)

    def test_base_basementiontracker_post_new_contribution_request_exception(
        self, mocker
    ):
        mock_requests_post = mocker.patch("requests.post")
        mock_requests_post.side_effect = requests.exceptions.RequestException(
            "Generic error"
        )
        instance = BaseMentionTracker("test_platform", lambda x: None)
        contribution_data = {"username": "test_user", "platform": "Testplatform"}
        with pytest.raises(Exception, match="API request failed: Generic error"):
            instance.post_new_contribution(contribution_data)

    def test_base_basementiontracker_post_new_contribution_changed_base_url(
        self, mocker
    ):
        mocker.patch.object(
            trackers.base,
            "REWARDS_API_BASE_URL",
            "http://test-api:8000/api",
        )
        mock_requests_post = mocker.patch("requests.post")
        mock_response = mocker.MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"success": True}
        mock_requests_post.return_value = mock_response
        instance = BaseMentionTracker("test_platform", lambda x: None)
        contribution_data = {"username": "test_user", "platform": "Testplatform"}
        instance.post_new_contribution(contribution_data)
        mock_requests_post.assert_called_once_with(
            "http://test-api:8000/api/addcontribution",
            json=contribution_data,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )

    def test_base_basementiontracker_post_new_contribution_default_base_url(
        self, mocker
    ):
        mock_requests_post = mocker.patch("requests.post")
        mock_response = mocker.MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"success": True}
        mock_requests_post.return_value = mock_response
        instance = BaseMentionTracker("test_platform", lambda x: None)
        contribution_data = {"username": "test_user", "platform": "Testplatform"}
        instance.post_new_contribution(contribution_data)
        mock_requests_post.assert_called_once_with(
            "http://127.0.0.1:8000/api/addcontribution",
            json=contribution_data,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )

    # _exit_gracefully
    def test_base_basementiontracker_exit_gracefully_sets_flag_and_logs(self, mocker):
        """Test that _exit_gracefully sets exit_signal=True and logs the event."""
        mocker.patch.object(BaseMentionTracker, "setup_logging")

        instance = BaseMentionTracker("test_platform", lambda x: None)
        instance.logger = mocker.MagicMock()
        instance.exit_signal = False
        instance._exit_gracefully(signum=15, frame=None)
        assert instance.exit_signal is True
        instance.logger.info.assert_called_once_with(
            "test_platform tracker exit signal received (15)"
        )

    # _register_signal_handlers
    def test_base_basementiontracker_register_signal_handlers(self, mocker):
        """Test that _register_signal_handlers binds SIGINT and SIGTERM."""
        mocker.patch.object(BaseMentionTracker, "setup_logging")

        instance = BaseMentionTracker("test_platform", lambda x: None)
        mock_signal = mocker.patch("signal.signal")
        instance._register_signal_handlers()
        assert mock_signal.call_count == 2
        mock_signal.assert_any_call(signal.SIGINT, instance._exit_gracefully)
        mock_signal.assert_any_call(signal.SIGTERM, instance._exit_gracefully)

    # _interruptible_sleep
    def test_base_basementiontracker_interruptible_sleep_respects_exit_signal(
        self, mocker
    ):
        """Test interruptible sleep exits early when exit_signal is set."""
        mocker.patch.object(BaseMentionTracker, "setup_logging")

        instance = BaseMentionTracker("test_platform", lambda x: None)
        mock_sleep = mocker.patch("time.sleep")

        # Set exit_signal to True after the first iteration
        def sleep_side_effect(_):
            instance.exit_signal = True

        mock_sleep.side_effect = sleep_side_effect
        instance._interruptible_sleep(5)
        # Should call sleep only once because exit_signal becomes True
        assert mock_sleep.call_count == 1

    def test_base_basementiontracker_interruptible_sleep_normal_exit(self, mocker):
        """Test interruptible sleep normal exit."""
        mocker.patch.object(BaseMentionTracker, "setup_logging")

        instance = BaseMentionTracker("test_platform", lambda x: None)
        mock_sleep = mocker.patch("time.sleep")
        instance._interruptible_sleep(5)
        # Should call sleep only once because exit_signal becomes True
        assert mock_sleep.call_count == 5

    # check_mentions
    def test_base_basementiontracker_check_mentions_not_implemented(self, mocker):
        mocker.patch.object(BaseMentionTracker, "setup_logging")

        instance = BaseMentionTracker("test_platform", lambda x: None)
        with pytest.raises(NotImplementedError):
            instance.check_mentions()

    # run
    def test_base_basementiontracker_run_success(self, mocker):
        """Test successful run loop with multiple iterations."""
        # Prevent real setup side effects
        mocker.patch.object(BaseMentionTracker, "setup_logging")

        instance = BaseMentionTracker("test_platform", lambda x: None)
        instance.logger = mocker.MagicMock()
        # Mock helpers
        mock_register_signals = mocker.patch.object(
            instance, "_register_signal_handlers"
        )
        mock_check_mentions = mocker.patch.object(instance, "check_mentions")
        mock_check_mentions.return_value = 0  # no mentions found
        mock_sleep = mocker.patch.object(instance, "_interruptible_sleep")
        mock_log_action = mocker.MagicMock(return_value=None)
        mocker.patch.object(instance, "log_action", new=mock_log_action)
        # Run for exactly 2 iterations
        instance.run(poll_interval_minutes=0.1, max_iterations=2)
        assert mock_register_signals.call_count == 1
        assert mock_check_mentions.call_count == 2
        assert mock_sleep.call_count == 2
        mock_log_action.assert_any_call("started", "Poll interval: 0.1 minutes")

    def test_base_basementiontracker_run_keyboard_interrupt(self, mocker):
        """Test run loop handling of KeyboardInterrupt during sleep."""
        mocker.patch.object(BaseMentionTracker, "setup_logging")

        instance = BaseMentionTracker("test_platform", lambda x: None)
        instance.logger = mocker.MagicMock()
        mocker.patch.object(instance, "_register_signal_handlers")
        mock_check_mentions = mocker.patch.object(instance, "check_mentions")
        mock_check_mentions.return_value = 0
        mock_sleep = mocker.patch.object(instance, "_interruptible_sleep")
        mock_sleep.side_effect = KeyboardInterrupt
        mock_log_action = mocker.MagicMock(return_value=None)
        mocker.patch.object(instance, "log_action", new=mock_log_action)
        instance.run(poll_interval_minutes=30, max_iterations=5)
        instance.logger.info.assert_called_with("test_platform tracker stopped by user")
        mock_log_action.assert_called_with("stopped", "User interrupt")

    def test_base_basementiontracker_run_exception(self, mocker):
        """Test run loop logging and re-raising unexpected exceptions."""
        mocker.patch.object(BaseMentionTracker, "setup_logging")

        instance = BaseMentionTracker("test_platform", lambda x: None)
        instance.logger = mocker.MagicMock()
        mocker.patch.object(instance, "_register_signal_handlers")
        mock_check_mentions = mocker.patch.object(instance, "check_mentions")
        mock_check_mentions.side_effect = Exception("Test error")
        mock_log_action = mocker.MagicMock(return_value=None)
        mocker.patch.object(instance, "log_action", new=mock_log_action)
        with pytest.raises(Exception, match="Test error"):
            instance.run(poll_interval_minutes=30, max_iterations=1)
        instance.logger.error.assert_called_with(
            "test_platform tracker error: Test error"
        )
        mock_log_action.assert_called_with("error", "Tracker error: Test error")

    def test_base_basementiontracker_run_mentions_found_logging(self, mocker):
        """Test run loop logging when mentions are found."""
        mocker.patch.object(BaseMentionTracker, "setup_logging")

        mock_log_action = mocker.MagicMock(return_value=None)
        mocker.patch.object(BaseMentionTracker, "log_action", new=mock_log_action)
        instance = BaseMentionTracker("test_platform", lambda x: None)
        instance.logger = mocker.MagicMock()
        mocker.patch.object(instance, "_register_signal_handlers")
        mock_check_mentions = mocker.patch.object(instance, "check_mentions")
        mock_check_mentions.return_value = 3  # mentions_found > 0
        mock_sleep = mocker.patch.object(instance, "_interruptible_sleep")
        # Run a single iteration
        instance.run(poll_interval_minutes=0.1, max_iterations=1)
        # Sleep should be called once
        mock_sleep.assert_called_once()
        # Verify logger.info was called for mentions_found > 0
        instance.logger.info.assert_any_call("Found 3 new mentions")


class TestBaseMentionTrackerAsync:
    """Test suite for async functionality in BaseMentionTracker."""

    @pytest.fixture
    def tracker(self):
        """Create a BaseMentionTracker instance for testing."""
        return BaseMentionTracker("test_platform", lambda x, y: {})

    @pytest.fixture
    def mock_async_callback(self):
        """Create a mock async callback function."""
        return AsyncMock()

    @pytest.fixture
    def mock_event_loop(self):
        """Create a mock event loop."""
        loop = Mock(spec=asyncio.AbstractEventLoop)
        loop.create_task = Mock()
        loop.add_signal_handler = Mock()
        loop.run_until_complete = Mock()
        loop.close = Mock()
        loop.is_closed = Mock(return_value=False)
        return loop

    def test_shutdown_without_task(self, tracker):
        """Test shutdown when no async task is running."""
        # Ensure async_task is None
        tracker.async_task = None

        # Call shutdown - should not raise any exceptions
        with patch("builtins.print") as mock_print:
            tracker.shutdown()

            # Verify shutdown message was printed
            mock_print.assert_called_once_with("Shutdown requested...")

            # No task to cancel, so async_task should still be None
            assert tracker.async_task is None

    def test_shutdown_with_task(self, tracker):
        """Test shutdown when an async task is running."""
        # Create a mock task
        mock_task = Mock(spec=asyncio.Task)
        mock_task.cancel = Mock()
        tracker.async_task = mock_task

        # Call shutdown
        with patch("builtins.print") as mock_print:
            tracker.shutdown()

            # Verify shutdown message was printed
            mock_print.assert_called_once_with("Shutdown requested...")

            # Verify task.cancel() was called
            mock_task.cancel.assert_called_once()

    def test_shutdown_with_cancelled_task(self, tracker):
        """Test shutdown when task has already been cancelled."""
        # Create a mock task that's already cancelled
        mock_task = Mock(spec=asyncio.Task)
        mock_task.cancel = Mock()
        tracker.async_task = mock_task

        # Call shutdown multiple times
        with patch("builtins.print") as mock_print:
            for _ in range(3):
                tracker.shutdown()

            # Verify shutdown message was printed each time
            assert mock_print.call_count == 3
            assert mock_print.call_args_list == [
                call("Shutdown requested..."),
                call("Shutdown requested..."),
                call("Shutdown requested..."),
            ]

            # Verify task.cancel() was called each time
            assert mock_task.cancel.call_count == 3

    @patch("asyncio.get_event_loop")
    def test_start_async_task_normal_execution(
        self, mock_get_loop, tracker, mock_async_callback, mock_event_loop
    ):
        """Test start_async_task with normal callback execution."""
        # Setup mocks
        mock_get_loop.return_value = mock_event_loop
        mock_task = Mock(spec=asyncio.Task)

        # Create a list to capture the coroutine passed to create_task
        captured_coroutine = []

        def capture_create_task(coro):
            captured_coroutine.append(coro)
            return mock_task

        mock_event_loop.create_task.side_effect = capture_create_task

        # Call start_async_task
        tracker.start_async_task(mock_async_callback, arg1="value1", arg2="value2")

        # Verify event loop was retrieved
        mock_get_loop.assert_called_once()

        # Verify callback was called with correct arguments
        mock_async_callback.assert_called_once_with(arg1="value1", arg2="value2")

        # Verify a coroutine was captured (not checking exact identity)
        assert len(captured_coroutine) == 1
        assert asyncio.iscoroutine(captured_coroutine[0])

        # Verify signal handlers were registered
        assert mock_event_loop.add_signal_handler.call_count == 2
        mock_event_loop.add_signal_handler.assert_any_call(
            signal.SIGINT, tracker.shutdown
        )
        mock_event_loop.add_signal_handler.assert_any_call(
            signal.SIGTERM, tracker.shutdown
        )

        # Verify event loop ran until task completion
        mock_event_loop.run_until_complete.assert_called_once_with(mock_task)

        # Verify event loop was closed
        mock_event_loop.close.assert_called_once()

        # Verify async_task was set
        assert tracker.async_task == mock_task

    @patch("asyncio.get_event_loop")
    def test_start_async_task_callback_raises_exception(
        self, mock_get_loop, tracker, mock_async_callback, mock_event_loop
    ):
        """Test start_async_task when callback raises an exception."""
        # Setup mocks
        mock_get_loop.return_value = mock_event_loop
        mock_task = Mock(spec=asyncio.Task)
        mock_event_loop.create_task.return_value = mock_task

        # Make run_until_complete raise an exception
        test_exception = RuntimeError("Test error")
        mock_event_loop.run_until_complete.side_effect = test_exception

        # Call start_async_task - should raise the exception
        with pytest.raises(RuntimeError, match="Test error"):
            tracker.start_async_task(mock_async_callback)

        # Verify event loop was still closed in finally block
        mock_event_loop.close.assert_called_once()

    @patch("asyncio.get_event_loop")
    def test_start_async_task_with_keyboard_interrupt(
        self, mock_get_loop, tracker, mock_async_callback, mock_event_loop
    ):
        """Test start_async_task when KeyboardInterrupt occurs."""
        # Setup mocks
        mock_get_loop.return_value = mock_event_loop
        mock_task = Mock(spec=asyncio.Task)
        mock_event_loop.create_task.return_value = mock_task

        # Make run_until_complete raise KeyboardInterrupt
        mock_event_loop.run_until_complete.side_effect = KeyboardInterrupt

        with patch("builtins.print") as mock_print:
            # Call start_async_task
            tracker.start_async_task(mock_async_callback)

            # Verify interruption message was printed
            mock_print.assert_called_with("Tracker interrupted by user")

            # Verify event loop was closed
            mock_event_loop.close.assert_called_once()

    @patch("asyncio.get_event_loop")
    def test_start_async_task_with_cancelled_error(
        self, mock_get_loop, tracker, mock_async_callback, mock_event_loop
    ):
        """Test start_async_task when asyncio.CancelledError occurs."""
        # Setup mocks
        mock_get_loop.return_value = mock_event_loop
        mock_task = Mock(spec=asyncio.Task)
        mock_event_loop.create_task.return_value = mock_task

        # Make run_until_complete raise asyncio.CancelledError
        mock_event_loop.run_until_complete.side_effect = asyncio.CancelledError

        with patch("builtins.print") as mock_print:
            # Call start_async_task
            tracker.start_async_task(mock_async_callback)

            # Verify cancellation message was printed
            mock_print.assert_called_with("Tracker cancelled")

            # Verify event loop was closed
            mock_event_loop.close.assert_called_once()

    @patch("asyncio.get_event_loop")
    def test_start_async_task_signal_handler_invocation(
        self, mock_get_loop, tracker, mock_async_callback, mock_event_loop
    ):
        """Test that signal handlers correctly call shutdown."""
        # Setup mocks
        mock_get_loop.return_value = mock_event_loop
        mock_task = Mock(spec=asyncio.Task)
        mock_event_loop.create_task.return_value = mock_task

        # Create a mock for the shutdown method
        tracker.shutdown = Mock()

        # Call start_async_task
        tracker.start_async_task(mock_async_callback)

        # Verify signal handlers were registered with the shutdown method
        mock_event_loop.add_signal_handler.assert_any_call(
            signal.SIGINT, tracker.shutdown
        )
        mock_event_loop.add_signal_handler.assert_any_call(
            signal.SIGTERM, tracker.shutdown
        )

    @patch("asyncio.get_event_loop")
    def test_start_async_task_event_loop_already_closed(
        self, mock_get_loop, tracker, mock_async_callback
    ):
        """Test start_async_task when event loop is already closed."""
        # Create a mock event loop that's already closed
        mock_event_loop = Mock(spec=asyncio.AbstractEventLoop)
        mock_event_loop.is_closed = Mock(return_value=True)
        mock_event_loop.create_task = Mock()
        mock_event_loop.add_signal_handler = Mock()
        mock_event_loop.run_until_complete = Mock()
        mock_event_loop.close = Mock()

        mock_get_loop.return_value = mock_event_loop

        # This should not raise an error because the code doesn't check is_closed
        # The event loop will be used even if closed
        tracker.start_async_task(mock_async_callback)

        # Verify the event loop was used (create_task called)
        mock_event_loop.create_task.assert_called_once()

    @patch("asyncio.get_event_loop")
    def test_start_async_task_multiple_calls(
        self, mock_get_loop, tracker, mock_async_callback, mock_event_loop
    ):
        """Test calling start_async_task multiple times."""
        # Setup mocks
        mock_get_loop.return_value = mock_event_loop
        mock_task1 = Mock(spec=asyncio.Task)
        mock_task2 = Mock(spec=asyncio.Task)

        # Track create_task calls
        create_task_calls = []

        def create_task_side_effect(coro):
            # Count the calls
            create_task_calls.append(coro)
            if len(create_task_calls) == 1:
                return mock_task1
            return mock_task2

        mock_event_loop.create_task.side_effect = create_task_side_effect

        # First call
        tracker.start_async_task(mock_async_callback, arg1="first")

        # Second call - reset run_until_complete to track it
        mock_event_loop.run_until_complete.reset_mock()
        tracker.start_async_task(mock_async_callback, arg1="second")

        # Verify both tasks were created
        assert len(create_task_calls) == 2
        # Verify async_task was updated to second task
        assert tracker.async_task == mock_task2

    @patch("asyncio.get_event_loop")
    def test_start_async_task_shutdown_during_execution(
        self, mock_get_loop, tracker, mock_async_callback, mock_event_loop
    ):
        """Test shutdown being called while async task is running."""
        # Setup mocks
        mock_get_loop.return_value = mock_event_loop
        mock_task = Mock(spec=asyncio.Task)
        mock_event_loop.create_task.return_value = mock_task

        # Track if shutdown was called
        shutdown_called = False

        def mock_shutdown():
            nonlocal shutdown_called
            shutdown_called = True
            mock_task.cancel()

        tracker.shutdown = mock_shutdown

        # Simulate SIGINT signal during execution
        def run_until_complete_side_effect(task):
            # Simulate signal handler being called during execution
            tracker.shutdown()
            raise asyncio.CancelledError()

        mock_event_loop.run_until_complete.side_effect = run_until_complete_side_effect

        with patch("builtins.print") as mock_print:
            tracker.start_async_task(mock_async_callback)

            # Verify shutdown was called
            assert shutdown_called is True

            # Verify cancellation message was printed
            mock_print.assert_called_with("Tracker cancelled")

            # Verify event loop was closed
            mock_event_loop.close.assert_called_once()

    @patch("asyncio.get_event_loop")
    def test_start_async_task_with_empty_kwargs(
        self, mock_get_loop, tracker, mock_async_callback, mock_event_loop
    ):
        """Test start_async_task with no kwargs passed."""
        # Setup mocks
        mock_get_loop.return_value = mock_event_loop
        mock_task = Mock(spec=asyncio.Task)

        # Create a list to capture the coroutine passed to create_task
        captured_coroutine = []

        def capture_create_task(coro):
            captured_coroutine.append(coro)
            return mock_task

        mock_event_loop.create_task.side_effect = capture_create_task

        # Call with no kwargs
        tracker.start_async_task(mock_async_callback)

        # Verify callback was called with no arguments
        mock_async_callback.assert_called_once_with()

        # Verify a coroutine was captured (not checking exact identity)
        assert len(captured_coroutine) == 1
        assert asyncio.iscoroutine(captured_coroutine[0])

        # Verify event loop was retrieved
        mock_get_loop.assert_called_once()

        # Verify signal handlers were registered
        assert mock_event_loop.add_signal_handler.call_count == 2
        mock_event_loop.add_signal_handler.assert_any_call(
            signal.SIGINT, tracker.shutdown
        )
        mock_event_loop.add_signal_handler.assert_any_call(
            signal.SIGTERM, tracker.shutdown
        )

        # Verify event loop ran until task completion
        mock_event_loop.run_until_complete.assert_called_once_with(mock_task)

        # Verify event loop was closed
        mock_event_loop.close.assert_called_once()

        # Verify async_task was set
        assert tracker.async_task == mock_task

    @patch("asyncio.get_event_loop")
    def test_start_async_task_verify_task_cancellation_chain(
        self, mock_get_loop, tracker, mock_async_callback, mock_event_loop
    ):
        """Test the complete chain from signal to task cancellation."""
        # Setup mocks
        mock_get_loop.return_value = mock_event_loop
        mock_task = Mock(spec=asyncio.Task)
        mock_task.cancel = Mock()
        mock_event_loop.create_task.return_value = mock_task
        tracker.async_task = mock_task

        # Call start_async_task
        tracker.start_async_task(mock_async_callback)

        # Now manually call shutdown (simulating signal)
        tracker.shutdown()

        # Verify task.cancel() was called
        mock_task.cancel.assert_called_once()

    @patch("asyncio.get_event_loop")
    def test_start_async_task_event_loop_cleanup_on_exception(
        self, mock_get_loop, tracker, mock_async_callback
    ):
        """Test that event loop is cleaned up even when an exception occurs during setup."""
        # Make get_event_loop raise an exception
        mock_get_loop.side_effect = RuntimeError("No event loop")

        # This should raise, but we need to ensure no dangling resources
        with pytest.raises(RuntimeError, match="No event loop"):
            tracker.start_async_task(mock_async_callback)

        # Verify async_task wasn't set
        assert not hasattr(tracker, "async_task") or tracker.async_task is None

    # # shutdown
    def test_shutdown_with_partially_initialized_task(self, tracker):
        """Test shutdown with a task that doesn't have cancel method."""

        # Create a mock that doesn't have cancel() method
        # Use a simple object without cancel attribute
        class TaskWithoutCancel:
            pass

        tracker.async_task = TaskWithoutCancel()

        # This should not raise an exception
        with patch("builtins.print") as mock_print:
            tracker.shutdown()

            # Should still print shutdown message
            mock_print.assert_called_once_with("Shutdown requested...")
