"""Testing module for :py:mod:`trackers.base` module."""

import signal
from pathlib import Path
from unittest import mock

import pytest
import requests

import trackers.base
from trackers.base import BaseMentionTracker


class TestTrackersBaseMentionTracker:
    """Testing class for :class:`trackers.base.BaseMentionTracker` class."""

    # __init__
    def test_base_basementiontracker_init_success(self, mocker):
        mock_setup_logging = mocker.patch.object(BaseMentionTracker, "setup_logging")
        mock_setup_database = mocker.patch.object(BaseMentionTracker, "setup_database")

        def callback(data):
            pass

        instance = BaseMentionTracker("test_platform", callback)
        assert instance.platform_name == "test_platform"
        assert instance.parse_message_callback == callback
        mock_setup_logging.assert_called_once()
        mock_setup_database.assert_called_once()

    # setup_database
    def test_base_basementiontracker_setup_database_success(self, mocker):
        mock_database_manager = mocker.patch("trackers.base.MentionDatabaseManager")
        instance = BaseMentionTracker("test_platform", lambda x: None)
        mock_database_manager.reset_mock()
        instance.setup_database()
        mock_database_manager.assert_called_once()
        assert instance.db == mock_database_manager.return_value

    # setup_logging
    def test_base_basementiontracker_setup_logging_creates_directory(self, mocker):
        mock_basic_config = mocker.patch("logging.basicConfig")
        mock_get_logger = mocker.patch("logging.getLogger")
        mock_logger = mocker.MagicMock()
        mock_get_logger.return_value = mock_logger
        instance = BaseMentionTracker("test_platform", lambda x: None)
        mock_basic_config.reset_mock()
        mock_get_logger.reset_mock()
        with mock.patch(
            "os.path.exists", return_value=False
        ) as mock_exists, mock.patch("os.makedirs") as mock_makedirs:
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
        instance = BaseMentionTracker("test_platform", lambda x: None)
        mock_db = mocker.MagicMock()
        mock_db.is_processed.return_value = True
        instance.db = mock_db
        result = instance.is_processed("test_item_id")
        assert result is True
        mock_db.is_processed.assert_called_once_with("test_item_id", "test_platform")

    def test_base_basementiontracker_is_processed_false(self, mocker):
        instance = BaseMentionTracker("test_platform", lambda x: None)
        mock_db = mocker.MagicMock()
        mock_db.is_processed.return_value = False
        instance.db = mock_db
        result = instance.is_processed("test_item_id")
        assert result is False

    # mark_processed
    def test_base_basementiontracker_mark_processed_success(self, mocker):
        instance = BaseMentionTracker("test_platform", lambda x: None)
        mock_db = mocker.MagicMock()
        instance.db = mock_db
        test_data = {
            "suggester": "test_user",
            "subreddit": "test_subreddit",
        }
        instance.mark_processed("test_item_id", test_data)
        mock_db.mark_processed.assert_called_once_with(
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
        mock_mark_processed = mocker.patch.object(BaseMentionTracker, "mark_processed")
        mock_log_action = mocker.patch.object(BaseMentionTracker, "log_action")
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
        mock_log_action = mocker.patch.object(BaseMentionTracker, "log_action")
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
        instance = BaseMentionTracker("test_platform", lambda x: None)
        mock_db = mocker.MagicMock()
        instance.db = mock_db
        instance.log_action("test_action", "test_details")
        mock_db.log_action.assert_called_once_with(
            "test_platform", "test_action", "test_details"
        )

    # prepare_contribution_data
    def test_base_basementiontracker_prepare_contribution_data_success(self, mocker):
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

    def test_base_basementiontracker_prepare_contribution_data_no_contributor(
        self, mocker
    ):
        mock_social_platform_prefixes = mocker.patch(
            "trackers.base.social_platform_prefixes"
        )
        mock_social_platform_prefixes.return_value = [("Testplatform", "TP_")]
        instance = BaseMentionTracker("testplatform123", lambda x: None)
        parsed_message = {"title": "Test Title", "description": "Test Description"}
        message_data = {"contribution_url": "http://example.com"}  # No contributor
        result = instance.prepare_contribution_data(parsed_message, message_data)
        expected = {
            "title": "Test Title",
            "description": "Test Description",
            "username": "TP_None",
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
        mocker.patch.object(BaseMentionTracker, "setup_database")
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
        mocker.patch.object(BaseMentionTracker, "setup_database")
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
        mocker.patch.object(BaseMentionTracker, "setup_database")
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
        mocker.patch.object(BaseMentionTracker, "setup_database")
        instance = BaseMentionTracker("test_platform", lambda x: None)
        mock_sleep = mocker.patch("time.sleep")
        instance._interruptible_sleep(5)
        # Should call sleep only once because exit_signal becomes True
        assert mock_sleep.call_count == 5

    # check_mentions
    def test_base_basementiontracker_check_mentions_not_implemented(self, mocker):
        mocker.patch.object(BaseMentionTracker, "setup_logging")
        mocker.patch.object(BaseMentionTracker, "setup_database")
        instance = BaseMentionTracker("test_platform", lambda x: None)
        with pytest.raises(NotImplementedError):
            instance.check_mentions()

    # run
    def test_base_basementiontracker_run_success(self, mocker):
        """Test successful run loop with multiple iterations."""
        # Prevent real setup side effects
        mocker.patch.object(BaseMentionTracker, "setup_logging")
        mocker.patch.object(BaseMentionTracker, "setup_database")
        instance = BaseMentionTracker("test_platform", lambda x: None)
        instance.logger = mocker.MagicMock()
        # Mock helpers
        mock_register_signals = mocker.patch.object(
            instance, "_register_signal_handlers"
        )
        mock_check_mentions = mocker.patch.object(instance, "check_mentions")
        mock_check_mentions.return_value = 0  # no mentions found
        mock_sleep = mocker.patch.object(instance, "_interruptible_sleep")
        mock_log_action = mocker.patch.object(instance, "log_action")
        mock_cleanup = mocker.patch.object(instance, "cleanup")
        # Run for exactly 2 iterations
        instance.run(poll_interval_minutes=0.1, max_iterations=2)
        assert mock_register_signals.call_count == 1
        assert mock_check_mentions.call_count == 2
        assert mock_sleep.call_count == 2
        mock_log_action.assert_any_call("started", "Poll interval: 0.1 minutes")
        mock_cleanup.assert_called_once()

    def test_base_basementiontracker_run_keyboard_interrupt(self, mocker):
        """Test run loop handling of KeyboardInterrupt during sleep."""
        mocker.patch.object(BaseMentionTracker, "setup_logging")
        mocker.patch.object(BaseMentionTracker, "setup_database")
        instance = BaseMentionTracker("test_platform", lambda x: None)
        instance.logger = mocker.MagicMock()
        mocker.patch.object(instance, "_register_signal_handlers")
        mock_check_mentions = mocker.patch.object(instance, "check_mentions")
        mock_check_mentions.return_value = 0
        mock_sleep = mocker.patch.object(instance, "_interruptible_sleep")
        mock_sleep.side_effect = KeyboardInterrupt
        mock_log_action = mocker.patch.object(instance, "log_action")
        instance.run(poll_interval_minutes=30, max_iterations=5)
        instance.logger.info.assert_called_with("test_platform tracker stopped by user")
        mock_log_action.assert_called_with("stopped", "User interrupt")

    def test_base_basementiontracker_run_exception(self, mocker):
        """Test run loop logging and re-raising unexpected exceptions."""
        mocker.patch.object(BaseMentionTracker, "setup_logging")
        mocker.patch.object(BaseMentionTracker, "setup_database")
        instance = BaseMentionTracker("test_platform", lambda x: None)
        instance.logger = mocker.MagicMock()
        mocker.patch.object(instance, "_register_signal_handlers")
        mock_check_mentions = mocker.patch.object(instance, "check_mentions")
        mock_check_mentions.side_effect = Exception("Test error")
        mock_log_action = mocker.patch.object(instance, "log_action")
        mock_cleanup = mocker.patch.object(instance, "cleanup")
        with pytest.raises(Exception, match="Test error"):
            instance.run(poll_interval_minutes=30, max_iterations=1)
        instance.logger.error.assert_called_with(
            "test_platform tracker error: Test error"
        )
        mock_log_action.assert_called_with("error", "Tracker error: Test error")
        mock_cleanup.assert_called_once()

    def test_base_basementiontracker_run_mentions_found_logging(self, mocker):
        """Test run loop logging when mentions are found."""
        mocker.patch.object(BaseMentionTracker, "setup_logging")
        mocker.patch.object(BaseMentionTracker, "setup_database")
        mocker.patch.object(BaseMentionTracker, "log_action")
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

    # cleanup
    def test_base_basementiontracker_cleanup_with_db(self, mocker):
        mocker.patch.object(BaseMentionTracker, "setup_logging")
        mocker.patch.object(BaseMentionTracker, "setup_database")
        instance = BaseMentionTracker("test_platform", lambda x: None)
        mock_db = mocker.MagicMock()
        instance.db = mock_db
        instance.cleanup()
        mock_db.cleanup.assert_called_once()

    def test_base_basementiontracker_cleanup_no_db(self, mocker):
        mocker.patch.object(BaseMentionTracker, "setup_logging")
        mocker.patch.object(BaseMentionTracker, "setup_database")
        instance = BaseMentionTracker("test_platform", lambda x: None)
        # Should not raise an exception
        instance.cleanup()
