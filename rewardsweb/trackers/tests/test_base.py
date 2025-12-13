"""Testing module for :py:mod:`trackers.base` module."""

import asyncio
import signal
from pathlib import Path
from unittest import mock
from unittest.mock import AsyncMock, Mock, call, patch

import aiohttp
import pytest
import requests

import trackers.base
from trackers.base import BaseAsyncMentionTracker, BaseMentionTracker


@pytest.mark.django_db
class TestTrackersBaseMentionTracker:
    """Testing class for :class:`trackers.base.BaseMentionTracker` class."""

    # __init__
    def test_trackers_base_basementiontracker_init_success(self, mocker):
        mock_setup_logging = mocker.patch.object(BaseMentionTracker, "setup_logging")

        def callback(data):
            pass

        instance = BaseMentionTracker("test_platform", callback)
        assert instance.platform_name == "test_platform"
        assert instance.parse_message_callback == callback
        assert instance.async_task is None
        mock_setup_logging.assert_called_once()

    # setup_logging
    def test_trackers_base_basementiontracker_setup_logging_creates_directory(
        self, mocker
    ):
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

    def test_trackers_base_basementiontracker_setup_logging_success(self, mocker):
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
    def test_trackers_base_basementiontracker_is_processed_true(self, mocker):
        mocker.patch.object(BaseMentionTracker, "setup_logging")
        mock_is_processed_orm = mocker.patch(
            "trackers.models.Mention.objects.is_processed"
        )
        mock_is_processed_orm.return_value = True
        instance = BaseMentionTracker("test_platform", lambda x: None)
        result = instance.is_processed("test_item_id")
        assert result is True
        mock_is_processed_orm.assert_called_once_with("test_item_id", "test_platform")

    def test_trackers_base_basementiontracker_is_processed_false(self, mocker):
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
    async def test_trackers_base_basementiontracker_mark_processed_success(
        self, mocker
    ):
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
    def test_trackers_base_basementiontracker_process_mention_already_processed(
        self, mocker
    ):
        mock_is_processed = mocker.patch.object(BaseMentionTracker, "is_processed")
        mock_is_processed.return_value = True
        mock_callback, username = mocker.MagicMock(), mocker.MagicMock()
        instance = BaseMentionTracker("test_platform", mock_callback)
        result = instance.process_mention("test_item_id", {}, username)
        assert result is False
        mock_callback.assert_not_called()

    def test_trackers_base_basementiontracker_process_mention_success(self, mocker):
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

    def test_trackers_base_basementiontracker_process_mention_exception(self, mocker):
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
    def test_trackers_base_basementiontracker_log_action_success(self, mocker):
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

    # prepare_contribution_data
    def test_trackers_base_basementiontracker_prepare_contribution_data_success(
        self, mocker
    ):
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

    def test_trackers_base_basementiontracker_prepare_contribution_data_excluded_contributor(
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

    def test_trackers_base_basementiontracker_prepare_contribution_data_no_contributor(
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
    def test_trackers_base_basementiontracker_post_new_contribution_success(
        self, mocker
    ):
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

    def test_trackers_base_basementiontracker_post_new_contribution_connection_error(
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

    def test_trackers_base_basementiontracker_post_new_contribution_http_error(
        self, mocker
    ):
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

    def test_trackers_base_basementiontracker_post_new_contribution_timeout(
        self, mocker
    ):
        mock_requests_post = mocker.patch("requests.post")
        mock_requests_post.side_effect = requests.exceptions.Timeout()
        instance = BaseMentionTracker("test_platform", lambda x: None)
        contribution_data = {"username": "test_user", "platform": "Testplatform"}
        with pytest.raises(Exception, match="API request timed out."):
            instance.post_new_contribution(contribution_data)

    def test_trackers_base_basementiontracker_post_new_contribution_request_exception(
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

    def test_trackers_base_basementiontracker_post_new_contribution_changed_base_url(
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

    def test_trackers_base_basementiontracker_post_new_contribution_default_base_url(
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
    def test_trackers_base_basementiontracker_exit_gracefully_sets_flag_and_logs(
        self, mocker
    ):
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
    def test_trackers_base_basementiontracker_register_signal_handlers(self, mocker):
        """Test that _register_signal_handlers binds SIGINT and SIGTERM."""
        mocker.patch.object(BaseMentionTracker, "setup_logging")

        instance = BaseMentionTracker("test_platform", lambda x: None)
        mock_signal = mocker.patch("signal.signal")
        instance._register_signal_handlers()
        assert mock_signal.call_count == 2
        mock_signal.assert_any_call(signal.SIGINT, instance._exit_gracefully)
        mock_signal.assert_any_call(signal.SIGTERM, instance._exit_gracefully)

    # _interruptible_sleep
    def test_trackers_base_basementiontracker_interruptible_sleep_respects_exit_signal(
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

    def test_trackers_base_basementiontracker_interruptible_sleep_normal_exit(
        self, mocker
    ):
        """Test interruptible sleep normal exit."""
        mocker.patch.object(BaseMentionTracker, "setup_logging")

        instance = BaseMentionTracker("test_platform", lambda x: None)
        mock_sleep = mocker.patch("time.sleep")
        instance._interruptible_sleep(5)
        # Should call sleep only once because exit_signal becomes True
        assert mock_sleep.call_count == 5

    # check_mentions
    def test_trackers_base_basementiontracker_check_mentions_not_implemented(
        self, mocker
    ):
        mocker.patch.object(BaseMentionTracker, "setup_logging")

        instance = BaseMentionTracker("test_platform", lambda x: None)
        with pytest.raises(NotImplementedError):
            instance.check_mentions()

    # run
    def test_trackers_base_basementiontracker_run_success(self, mocker):
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

    def test_trackers_base_basementiontracker_run_keyboard_interrupt(self, mocker):
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

    def test_trackers_base_basementiontracker_run_exception(self, mocker):
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

    def test_trackers_base_basementiontracker_run_mentions_found_logging(self, mocker):
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


class TestBaseAsyncMentionTracker:
    """Test suite for :class:`trackers.base.BaseAsyncMentionTracker`."""

    @pytest.fixture
    def tracker(self):
        """Create a BaseAsyncMentionTracker instance for testing."""
        return BaseAsyncMentionTracker("test_platform", lambda x, y: {})

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

    def test_trackers_base_baseasyncmentiontracker_is_subclass_of_basementiontracker(
        self,
    ):
        assert issubclass(BaseAsyncMentionTracker, BaseMentionTracker)

    # __init__
    def test_trackers_base_baseasyncmentiontracker_init_sets_session_to_none(
        self, tracker
    ):
        assert tracker.session is None

    # check_mentions_async
    @pytest.mark.asyncio
    async def test_trackers_base_baseasyncmentiontracker_check_mentions_async_not_implemented(
        self,
    ):
        instance = BaseAsyncMentionTracker("test_platform", lambda x: None)
        with pytest.raises(NotImplementedError):
            await instance.check_mentions_async()

    # cleanup
    @pytest.mark.asyncio
    async def test_trackers_base_baseasyncmentiontracker_cleanup_functionality(
        self, mocker
    ):
        mocker.patch.object(BaseAsyncMentionTracker, "setup_logging")
        mock_logger = mocker.MagicMock()
        mocked_close = mocker.patch(
            "trackers.base.BaseAsyncMentionTracker.close_session"
        )
        instance = BaseAsyncMentionTracker("test_platform", lambda x: None)
        instance.logger = mock_logger
        await instance.cleanup()
        mocked_close.assert_called_once_with()
        mock_logger.info.assert_called_once_with(
            "test_platform tracker async cleanup completed"
        )

    # close_session
    @pytest.mark.asyncio
    async def test_trackers_base_baseasyncmentiontracker_close_session_for_session_none(
        self, mocker
    ):
        mocker.patch.object(BaseAsyncMentionTracker, "setup_logging")
        instance = BaseAsyncMentionTracker("test_platform", lambda x: None)
        await instance.close_session()
        assert instance.session is None

    @pytest.mark.asyncio
    async def test_trackers_base_baseasyncmentiontracker_close_session_functionality(
        self, mocker
    ):
        mocker.patch.object(BaseAsyncMentionTracker, "setup_logging")
        instance = BaseAsyncMentionTracker("test_platform", lambda x: None)
        instance.session = mocker.AsyncMock()
        await instance.close_session()
        assert instance.session is None

    # is_processed_async
    @pytest.mark.asyncio
    async def test_trackers_base_baseasyncmentiontracker_is_processed_async_true(
        self, mocker
    ):
        mocker.patch.object(BaseAsyncMentionTracker, "setup_logging")
        mock_is_processed_orm = mocker.patch(
            "trackers.models.Mention.objects.is_processed"
        )
        mock_is_processed_orm.return_value = True
        instance = BaseAsyncMentionTracker("test_platform", lambda x: None)
        result = await instance.is_processed_async("test_item_id")
        assert result is True
        mock_is_processed_orm.assert_called_once_with("test_item_id", "test_platform")

    @pytest.mark.asyncio
    async def test_trackers_base_baseasyncmentiontracker_is_processed_async_false(
        self, mocker
    ):
        mocker.patch.object(BaseAsyncMentionTracker, "setup_logging")
        mock_is_processed_orm = mocker.patch(
            "trackers.models.Mention.objects.is_processed"
        )
        mock_is_processed_orm.return_value = False
        instance = BaseAsyncMentionTracker("test_platform", lambda x: None)
        result = await instance.is_processed_async("test_item_id")
        assert result is False
        mock_is_processed_orm.assert_called_once_with("test_item_id", "test_platform")

    # log_action_async
    @pytest.mark.asyncio
    async def test_trackers_base_baseasyncmentiontracker_log_action_async_functionality(
        self, mocker
    ):
        mocker.patch.object(BaseAsyncMentionTracker, "setup_logging")
        mocked_log = mocker.patch("trackers.base.BaseAsyncMentionTracker.log_action")
        instance = BaseAsyncMentionTracker("test_platform", lambda x: None)
        await instance.log_action_async("test_action", "test_details")
        mocked_log.assert_called_once_with("test_action", "test_details")

    # mark_processed_async
    @pytest.mark.asyncio
    async def test_trackers_base_baseasyncmentiontracker_mark_processed_async_success(
        self, mocker
    ):
        mocker.patch.object(BaseAsyncMentionTracker, "setup_logging")
        mock_mark_processed_orm = mocker.AsyncMock(return_value=None)
        mocker.patch(
            "trackers.models.Mention.objects.mark_processed",
            new=mock_mark_processed_orm,
        )
        instance = BaseAsyncMentionTracker("test_platform", lambda x: None)
        test_data = {
            "suggester": "test_user",
            "subreddit": "test_subreddit",
        }
        await instance.mark_processed_async("test_item_id", test_data)
        mock_mark_processed_orm.assert_called_once_with(
            "test_item_id", "test_platform", test_data
        )

    # process_mention_async
    @pytest.mark.asyncio
    async def test_trackers_base_baseasyncmentiontracker_process_mention_processed(
        self, mocker
    ):
        mock_is_processed = mocker.patch.object(
            BaseAsyncMentionTracker, "is_processed_async"
        )
        mock_is_processed.return_value = True
        mock_callback, username = mocker.MagicMock(), mocker.MagicMock()
        instance = BaseAsyncMentionTracker("test_platform", mock_callback)
        result = await instance.process_mention_async("test_item_id", {}, username)
        assert result is False
        mock_callback.assert_not_called()

    @pytest.mark.asyncio
    async def test_trackers_base_baseasyncmentiontracker_process_mention_async_success(
        self, mocker
    ):
        mock_is_processed = mocker.patch.object(
            BaseAsyncMentionTracker, "is_processed_async"
        )
        mock_is_processed.return_value = False
        mock_prepare_contribution_data = mocker.patch.object(
            BaseAsyncMentionTracker, "prepare_contribution_data"
        )
        mock_new_contribution = mocker.AsyncMock(return_value=None)
        mock_post_new_contribution = mocker.patch.object(
            BaseAsyncMentionTracker,
            "post_new_contribution_async",
            new=mock_new_contribution,
        )
        mock_mark_processed = mocker.AsyncMock(return_value=None)
        mocker.patch.object(
            BaseAsyncMentionTracker, "mark_processed_async", new=mock_mark_processed
        )
        mock_log_action = mocker.AsyncMock(return_value=None)
        mocker.patch.object(
            BaseAsyncMentionTracker, "log_action_async", new=mock_log_action
        )
        mock_logger = mocker.MagicMock()
        mock_callback = mocker.MagicMock(return_value={"parsed": "data"})
        instance = BaseAsyncMentionTracker("test_platform", mock_callback)
        instance.logger = mock_logger
        test_data = {"suggester": "test_user", "content": "content"}
        username = "username"
        result = await instance.process_mention_async(
            "test_item_id", test_data, username
        )
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

    @pytest.mark.asyncio
    async def test_trackers_base_baseasyncmentiontracker_process_mention_async_exception(
        self, mocker
    ):
        mock_is_processed = mocker.patch.object(
            BaseAsyncMentionTracker, "is_processed_async"
        )
        mock_is_processed.return_value = False
        mock_logger = mocker.MagicMock()
        mock_log_action = mocker.AsyncMock(return_value=None)
        mocker.patch.object(
            BaseAsyncMentionTracker, "log_action_async", new=mock_log_action
        )
        mock_callback = mocker.MagicMock(side_effect=Exception("Test error"))
        instance = BaseAsyncMentionTracker("test_platform", mock_callback)
        instance.logger = mock_logger
        result = await instance.process_mention_async("test_item_id", {}, "username")
        assert result is False
        mock_logger.error.assert_called_once_with(
            "Error processing mention test_item_id: Test error"
        )
        mock_log_action.assert_called_once_with(
            "processing_error", "Item: test_item_id, Error: Test error"
        )

    @pytest.mark.asyncio
    async def test_trackers_base_baseasyncmentiontracker_post_new_contribution_success(
        self, mocker
    ):
        """Test successful async post_new_contribution_async."""
        # Create the instance
        instance = BaseAsyncMentionTracker("test_platform", lambda x: None)
        instance.logger = mock.MagicMock()

        # 1. Create a mock that behaves like an async context manager
        # This is the response object that will be returned by session.post()
        mock_response_context = mock.AsyncMock()

        # The response object itself needs to have status, raise_for_status, json
        mock_response = mock.AsyncMock()
        mock_response.status = 200
        mock_response.raise_for_status = mock.AsyncMock()
        mock_response.json = mock.AsyncMock(return_value={"success": True})

        # Make the context manager return the response when entered
        mock_response_context.__aenter__ = mock.AsyncMock(return_value=mock_response)
        mock_response_context.__aexit__ = mock.AsyncMock(return_value=None)

        # 2. Create a mock session whose post() returns our async context manager
        mock_session = mock.MagicMock()

        # Make post() return the async context manager (not an AsyncMock!)
        mock_session.post = mock.Mock(return_value=mock_response_context)

        # 3. Patch the aiohttp.ClientSession to return our mock session
        # Use autospec=True to maintain the proper interface
        mock_client_session = mocker.patch(
            "trackers.base.aiohttp.ClientSession", autospec=True
        )
        mock_client_session.return_value = mock_session

        # 4. Patch ClientTimeout
        mock_client_timeout = mocker.patch(
            "trackers.base.aiohttp.ClientTimeout", autospec=True
        )
        mock_timeout_instance = mock.MagicMock()
        mock_client_timeout.return_value = mock_timeout_instance

        # 5. Mock the initialize_session to set our session
        # We need to patch the actual initialize_session method
        async def mock_initialize():
            instance.session = mock_session

        mocker.patch.object(instance, "initialize_session", side_effect=mock_initialize)

        # Call the method
        contribution_data = {"username": "test_user", "platform": "Testplatform"}
        result = await instance.post_new_contribution_async(contribution_data)

        # Verify
        # Check that post was called with correct arguments
        mock_session.post.assert_called_once_with(
            "http://127.0.0.1:8000/api/addcontribution",
            json=contribution_data,
            headers={"Content-Type": "application/json"},
            timeout=mock_timeout_instance,
        )

        # Check that the async context manager was entered
        mock_response_context.__aenter__.assert_called_once()
        mock_response.raise_for_status.assert_called_once()
        mock_response.json.assert_called_once()

        assert result == {"success": True}

        # Verify logging
        logged_info_messages = [
            call[0][0] if call[0] else str(call)
            for call in instance.logger.info.call_args_list
        ]

        assert any(
            "🌐 Async API Request: POST" in str(msg) for msg in logged_info_messages
        )
        assert any(
            "📡 Async API Response Status: 200" in str(msg)
            for msg in logged_info_messages
        )
        assert any(
            "✅ Async API Response received:" in str(msg)
            for msg in logged_info_messages
        )

    @pytest.mark.asyncio
    async def test_trackers_base_baseasyncmentiontracker_post_new_contribution_connect(
        self, mocker
    ):
        """Test async post_new_contribution_async with connection error."""
        instance = BaseAsyncMentionTracker("test_platform", lambda x: None)
        instance.logger = mock.MagicMock()

        mock_session = mock.MagicMock()
        mock_session.post = mock.Mock(side_effect=aiohttp.ClientConnectionError())

        mock_client_session = mocker.patch(
            "trackers.base.aiohttp.ClientSession", autospec=True
        )
        mock_client_session.return_value = mock_session

        mock_client_timeout = mocker.patch(
            "trackers.base.aiohttp.ClientTimeout", autospec=True
        )
        mock_timeout_instance = mock.MagicMock()
        mock_client_timeout.return_value = mock_timeout_instance

        async def mock_initialize():
            instance.session = mock_session

        mocker.patch.object(instance, "initialize_session", side_effect=mock_initialize)

        contribution_data = {"username": "test_user", "platform": "Testplatform"}

        with pytest.raises(
            Exception,
            match="Cannot connect to the API server. Make sure it's running on localhost.",
        ):
            await instance.post_new_contribution_async(contribution_data)

        instance.logger.error.assert_called_once_with(
            (
                "❌ Async API connection error: Cannot connect to "
                "the API server. Make sure it's running on localhost."
            )
        )

    @pytest.mark.asyncio
    async def test_trackers_base_baseasyncmentiontracker_post_new_contribution_http(
        self, mocker
    ):
        """Test async post_new_contribution_async with HTTP error."""
        instance = BaseAsyncMentionTracker("test_platform", lambda x: None)
        instance.logger = mock.MagicMock()

        # Create a mock response that will raise ClientResponseError
        # We need to simulate the full async with pattern

        # Create async context manager that raises on __aenter__
        class RaisingAsyncContextManager:
            async def __aenter__(self):
                # Create request info
                request_info = mock.MagicMock()
                request_info.headers = {}
                request_info.url = "http://127.0.0.1:8000/api/addcontribution"
                request_info.method = "POST"

                # Raise ClientResponseError when entering context
                raise aiohttp.ClientResponseError(
                    request_info=request_info,
                    history=(),
                    status=400,
                    message="Bad Request",
                    headers={},
                )

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        mock_session = mock.MagicMock()
        mock_session.post = mock.Mock(return_value=RaisingAsyncContextManager())

        mock_client_session = mocker.patch(
            "trackers.base.aiohttp.ClientSession", autospec=True
        )
        mock_client_session.return_value = mock_session

        mock_client_timeout = mocker.patch(
            "trackers.base.aiohttp.ClientTimeout", autospec=True
        )
        mock_timeout_instance = mock.MagicMock()
        mock_client_timeout.return_value = mock_timeout_instance

        async def mock_initialize():
            instance.session = mock_session

        mocker.patch.object(instance, "initialize_session", side_effect=mock_initialize)

        contribution_data = {"username": "test_user", "platform": "Testplatform"}

        with pytest.raises(Exception, match="API returned error: 400 - Bad Request"):
            await instance.post_new_contribution_async(contribution_data)

        instance.logger.error.assert_called_once_with(
            "❌ Async API HTTP error: API returned error: 400 - Bad Request"
        )

    @pytest.mark.asyncio
    async def test_trackers_base_baseasyncmentiontracker_post_new_contribution_timeout(
        self, mocker
    ):
        """Test async post_new_contribution_async with timeout error."""
        instance = BaseAsyncMentionTracker("test_platform", lambda x: None)
        instance.logger = mock.MagicMock()

        mock_session = mock.MagicMock()
        mock_session.post = mock.Mock(side_effect=asyncio.TimeoutError())

        mock_client_session = mocker.patch(
            "trackers.base.aiohttp.ClientSession", autospec=True
        )
        mock_client_session.return_value = mock_session

        mock_client_timeout = mocker.patch(
            "trackers.base.aiohttp.ClientTimeout", autospec=True
        )
        mock_timeout_instance = mock.MagicMock()
        mock_client_timeout.return_value = mock_timeout_instance

        async def mock_initialize():
            instance.session = mock_session

        mocker.patch.object(instance, "initialize_session", side_effect=mock_initialize)

        contribution_data = {"username": "test_user", "platform": "Testplatform"}

        with pytest.raises(Exception, match="API request timed out."):
            await instance.post_new_contribution_async(contribution_data)

        instance.logger.error.assert_called_once_with(
            "❌ Async API timeout error: API request timed out."
        )

    @pytest.mark.asyncio
    async def test_trackers_base_baseasyncmentiontracker_post_new_contribution_client(
        self, mocker
    ):
        """Test async post_new_contribution_async with generic client error."""
        instance = BaseAsyncMentionTracker("test_platform", lambda x: None)
        instance.logger = mock.MagicMock()

        mock_session = mock.MagicMock()
        mock_session.post = mock.Mock(
            side_effect=aiohttp.ClientError("Generic client error")
        )

        mock_client_session = mocker.patch(
            "trackers.base.aiohttp.ClientSession", autospec=True
        )
        mock_client_session.return_value = mock_session

        mock_client_timeout = mocker.patch(
            "trackers.base.aiohttp.ClientTimeout", autospec=True
        )
        mock_timeout_instance = mock.MagicMock()
        mock_client_timeout.return_value = mock_timeout_instance

        async def mock_initialize():
            instance.session = mock_session

        mocker.patch.object(instance, "initialize_session", side_effect=mock_initialize)

        contribution_data = {"username": "test_user", "platform": "Testplatform"}

        with pytest.raises(Exception, match="API request failed: Generic client error"):
            await instance.post_new_contribution_async(contribution_data)

        instance.logger.error.assert_called_once_with(
            "❌ Async API client error: API request failed: Generic client error"
        )

    @pytest.mark.asyncio
    async def test_trackers_base_baseasyncmentiontracker_post_new_contribution_error(
        self, mocker
    ):
        """Test async post_new_contribution_async with unexpected error."""
        instance = BaseAsyncMentionTracker("test_platform", lambda x: None)
        instance.logger = mock.MagicMock()

        mock_session = mock.MagicMock()
        mock_session.post = mock.Mock(side_effect=ValueError("Unexpected value error"))

        mock_client_session = mocker.patch(
            "trackers.base.aiohttp.ClientSession", autospec=True
        )
        mock_client_session.return_value = mock_session

        mock_client_timeout = mocker.patch(
            "trackers.base.aiohttp.ClientTimeout", autospec=True
        )
        mock_timeout_instance = mock.MagicMock()
        mock_client_timeout.return_value = mock_timeout_instance

        async def mock_initialize():
            instance.session = mock_session

        mocker.patch.object(instance, "initialize_session", side_effect=mock_initialize)

        contribution_data = {"username": "test_user", "platform": "Testplatform"}

        with pytest.raises(
            Exception, match="Unexpected API error: Unexpected value error"
        ):
            await instance.post_new_contribution_async(contribution_data)

        instance.logger.error.assert_called_once_with(
            "❌ Async API unexpected error: Unexpected API error: Unexpected value error"
        )

    @pytest.mark.asyncio
    async def test_trackers_base_baseasyncmentiontracker_post_new_contribution_url(
        self, mocker
    ):
        """Test async post_new_contribution_async with custom base URL."""
        # Patch the base URL constant
        mocker.patch.object(
            trackers.base,
            "REWARDS_API_BASE_URL",
            "http://test-api:8000/api",
        )

        instance = BaseAsyncMentionTracker("test_platform", lambda x: None)
        instance.logger = mock.MagicMock()

        mock_response_context = mock.AsyncMock()
        mock_response = mock.AsyncMock()
        mock_response.status = 200
        mock_response.raise_for_status = mock.AsyncMock()
        mock_response.json = mock.AsyncMock(return_value={"success": True})
        mock_response_context.__aenter__ = mock.AsyncMock(return_value=mock_response)
        mock_response_context.__aexit__ = mock.AsyncMock(return_value=None)

        mock_session = mock.MagicMock()
        mock_session.post = mock.Mock(return_value=mock_response_context)

        mock_client_session = mocker.patch(
            "trackers.base.aiohttp.ClientSession", autospec=True
        )
        mock_client_session.return_value = mock_session

        mock_client_timeout = mocker.patch(
            "trackers.base.aiohttp.ClientTimeout", autospec=True
        )
        mock_timeout_instance = mock.MagicMock()
        mock_client_timeout.return_value = mock_timeout_instance

        async def mock_initialize():
            instance.session = mock_session

        mocker.patch.object(instance, "initialize_session", side_effect=mock_initialize)

        contribution_data = {"username": "test_user", "platform": "Testplatform"}
        await instance.post_new_contribution_async(contribution_data)

        # Verify custom URL is used
        mock_session.post.assert_called_once_with(
            "http://test-api:8000/api/addcontribution",
            json=contribution_data,
            headers={"Content-Type": "application/json"},
            timeout=mock_timeout_instance,
        )

    @pytest.mark.asyncio
    async def test_trackers_base_baseasyncmentiontracker_post_new_contribution_init(
        self, mocker
    ):
        """Test that session is initialized only once."""
        # Track session creation
        session_creation_count = 0

        def create_mock_session():
            nonlocal session_creation_count
            session_creation_count += 1

            mock_response_context = mock.AsyncMock()
            mock_response = mock.AsyncMock()
            mock_response.status = 200
            mock_response.raise_for_status = mock.AsyncMock()
            mock_response.json = mock.AsyncMock(return_value={"success": True})
            mock_response_context.__aenter__ = mock.AsyncMock(
                return_value=mock_response
            )
            mock_response_context.__aexit__ = mock.AsyncMock(return_value=None)

            mock_session = mock.MagicMock()
            mock_session.post = mock.Mock(return_value=mock_response_context)
            return mock_session

        # Patch BEFORE creating instances
        mock_client_session = mocker.patch(
            "trackers.base.aiohttp.ClientSession",
            autospec=True,
            side_effect=create_mock_session,
        )

        mock_client_timeout = mocker.patch(
            "trackers.base.aiohttp.ClientTimeout", autospec=True
        )
        mock_timeout_instance = mock.MagicMock()
        mock_client_timeout.return_value = mock_timeout_instance

        # First instance
        instance = BaseAsyncMentionTracker("test_platform", lambda x: None)
        instance.logger = mock.MagicMock()

        contribution_data = {"username": "test_user", "platform": "Testplatform"}

        # First call
        await instance.post_new_contribution_async(contribution_data)
        assert session_creation_count == 1

        # Second call should reuse session
        await instance.post_new_contribution_async(contribution_data)
        assert session_creation_count == 1  # Still only 1

        # Second instance - should create new session
        instance2 = BaseAsyncMentionTracker("test_platform2", lambda x: None)
        instance2.logger = mock.MagicMock()

        await instance2.post_new_contribution_async(contribution_data)
        assert session_creation_count == 2  # New instance created new session

    # # shutdown
    def test_reackers_base_baseasyncmentiontracker_shutdown_with_partially_init_task(
        self, tracker
    ):
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

    def test_reackers_base_baseasyncmentiontracker_shutdown_without_task(self, tracker):
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

    def test_reackers_base_baseasyncmentiontracker_shutdown_with_task(self, tracker):
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

    def test_reackers_base_baseasyncmentiontracker_shutdown_with_cancelled_task(
        self, tracker
    ):
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

    # # start_async_task
    @patch("asyncio.get_event_loop")
    def test_reackers_base_baseasyncmentiontracker_start_async_task_normal_execution(
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
    def test_reackers_base_baseasyncmentiontracker_start_async_task_callback_exception(
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
    def test_reackers_base_baseasyncmentiontracker_start_async_task_keyboard_interrupt(
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
    def test_reackers_base_baseasyncmentiontracker_start_async_task_with_cancelled_error(
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
    def test_reackers_base_baseasyncmentiontracker_start_async_task_signal_handler(
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
    def test_reackers_base_baseasyncmentiontracker_start_async_task_loop_already_closed(
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
    def test_reackers_base_baseasyncmentiontracker_start_async_task_multiple_calls(
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
    def test_reackers_base_baseasyncmentiontracker_start_async_task_shutdown(
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
    def test_reackers_base_baseasyncmentiontracker_start_async_task_with_empty_kwargs(
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
    def test_reackers_base_baseasyncmentiontracker_start_async_task_verify_task_cancel(
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
    def test_reackers_base_baseasyncmentiontracker_start_async_task_cleanup_on_exception(
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
