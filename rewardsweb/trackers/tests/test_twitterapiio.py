"""Testing module for :py:mod:`trackers.twitterapiio` module."""

import json
import logging
from unittest.mock import MagicMock, call

import pytest
import requests

from trackers.twitterapiio import TwitterapiioTracker


class TestTrackersTwitterApiIOTracker:
    """Testing class for :class:`trackers.twitterapiio.TwitterapiioTracker`."""

    # # __init__
    def test_trackers_twitterapiiotracker_init_success(
        self, mocker, twitterapiio_config
    ):
        """Test successful initialization of TwitterapiioTracker."""
        mocker.patch("trackers.base.MentionDatabaseManager")
        instance = TwitterapiioTracker(lambda x: None, twitterapiio_config)
        assert instance.api_key == twitterapiio_config["api_key"]
        assert instance.target_handle == twitterapiio_config["target_handle"]
        assert instance.batch_size == twitterapiio_config["batch_size"]

    # # _twitter_created_at_to_unix
    def test_trackers_twitterapiiotracker_twitter_created_at_to_unix(self):
        """Test the static method _twitter_created_at_to_unix."""
        created_at = "Sat Nov 22 04:28:58 +0000 2025"
        unix_timestamp = TwitterapiioTracker._twitter_created_at_to_unix(created_at)
        assert unix_timestamp == 1763785738

    # # _get_tweets_by_ids
    def test_trackers_twitterapiiotracker_get_tweets_by_ids_success(
        self, mocker, twitterapiio_config
    ):
        """Test _get_tweets_by_ids with a successful API response."""
        mocker.patch("trackers.base.MentionDatabaseManager")
        mock_requests_get = mocker.patch("requests.get")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "tweets": [{"id": "123"}, {"id": "456"}],
        }
        mock_requests_get.return_value = mock_response

        tracker = TwitterapiioTracker(lambda x: True, twitterapiio_config)
        tweets = tracker._get_tweets_by_ids(["123", "456"])

        assert len(tweets) == 2
        assert "123" in tweets

    def test_trackers_twitterapiiotracker_get_tweets_by_ids_no_ids(
        self, mocker, twitterapiio_config
    ):
        """Test _get_tweets_by_ids with no tweet IDs."""
        mocker.patch("trackers.base.MentionDatabaseManager")
        mock_requests_get = mocker.patch("requests.get")
        tracker = TwitterapiioTracker(lambda x: True, twitterapiio_config)
        tweets = tracker._get_tweets_by_ids([])

        assert tweets == {}
        mock_requests_get.assert_not_called()

    def test_trackers_twitterapiiotracker_get_tweets_by_ids_api_error(
        self, mocker, twitterapiio_config
    ):
        """Test _get_tweets_by_ids with an API error."""
        mocker.patch("trackers.base.MentionDatabaseManager")
        mock_requests_get = mocker.patch("requests.get")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "error", "message": "API Error"}
        mock_requests_get.return_value = mock_response

        tracker = TwitterapiioTracker(lambda x: True, twitterapiio_config)
        tweets = tracker._get_tweets_by_ids(["123"])

        assert tweets == {}

    def test_trackers_twitterapiiotracker_get_tweets_by_ids_request_exception(
        self, mocker, twitterapiio_config
    ):
        """Test _get_tweets_by_ids with a request exception."""
        mocker.patch("trackers.base.MentionDatabaseManager")
        mocker.patch("requests.get", side_effect=requests.exceptions.RequestException)
        tracker = TwitterapiioTracker(lambda x: True, twitterapiio_config)
        tweets = tracker._get_tweets_by_ids(["123"])

        assert tweets == {}

    def test_trackers_twitterapiiotracker_get_tweets_by_ids_json_decode_error(
        self, mocker, twitterapiio_config
    ):
        """Test _get_tweets_by_ids with a JSON decode error."""
        mocker.patch("trackers.base.MentionDatabaseManager")
        mock_requests_get = mocker.patch("requests.get")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError
        mock_requests_get.return_value = mock_response

        tracker = TwitterapiioTracker(lambda x: True, twitterapiio_config)
        tweets = tracker._get_tweets_by_ids(["123"])

        assert tweets == {}

    # # _get_all_mentions
    def test_trackers_twitterapiiotracker_get_all_mentions_success(
        self, mocker, twitterapiio_config
    ):
        """Test _get_all_mentions with multiple pages."""
        mocker.patch("trackers.base.MentionDatabaseManager")
        mock_requests_get = mocker.patch("requests.get")

        mock_response_page1 = MagicMock()
        mock_response_page1.status_code = 200
        mock_response_page1.json.return_value = {
            "status": "success",
            "tweets": [{"id": "123", "isReply": False}],
            "has_next_page": True,
            "next_cursor": "cursor123",
        }

        mock_response_page2 = MagicMock()
        mock_response_page2.status_code = 200
        mock_response_page2.json.return_value = {
            "status": "success",
            "tweets": [{"id": "456", "isReply": False}],
            "has_next_page": False,
        }

        mock_requests_get.side_effect = [mock_response_page1, mock_response_page2]

        tracker = TwitterapiioTracker(lambda x: True, twitterapiio_config)
        tracker.batch_size = 1
        mentions = list(tracker._get_all_mentions())

        assert len(mentions) == 2
        assert mock_requests_get.call_count == 2

    def test_trackers_twitterapiiotracker_get_all_mentions_small_batch(
        self, mocker, twitterapiio_config
    ):
        """Test _get_all_mentions with multiple pages."""
        mocker.patch("trackers.base.MentionDatabaseManager")
        mock_requests_get = mocker.patch("requests.get")

        mock_response_page1 = MagicMock()
        mock_response_page1.status_code = 200
        mock_response_page1.json.return_value = {
            "status": "success",
            "tweets": [{"id": "123", "isReply": False}],
            "has_next_page": True,
            "next_cursor": "cursor123",
        }

        mock_response_page2 = MagicMock()
        mock_response_page2.status_code = 200
        mock_response_page2.json.return_value = {
            "status": "success",
            "tweets": [{"id": "456", "isReply": False}],
            "has_next_page": False,
        }

        mock_requests_get.side_effect = [mock_response_page1, mock_response_page2]
        tracker = TwitterapiioTracker(lambda x: True, twitterapiio_config)
        tracker.batch_size = 3
        mentions = list(tracker._get_all_mentions())

        assert len(mentions) == 2
        assert mock_requests_get.call_count == 2

    def test_trackers_twitterapiiotracker_get_all_mentions_provided_sincetime(
        self, mocker, twitterapiio_config
    ):
        """Test _get_all_mentions when there is no next cursor."""
        mocker.patch("trackers.base.MentionDatabaseManager")
        mock_requests_get = mocker.patch("requests.get")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "tweets": [{"id": "123", "isReply": False}],
            "has_next_page": False,
            "next_cursor": "",
        }
        mock_requests_get.return_value = mock_response
        since_time = 123456789
        tracker = TwitterapiioTracker(lambda x: True, twitterapiio_config)
        mentions = list(tracker._get_all_mentions(since_time=since_time))
        assert len(mentions) == 1
        params = {
            "userName": tracker.target_handle,
            "sinceTime": since_time,
            "cursor": "",
        }
        mock_requests_get.assert_called_once_with(
            "https://api.twitterapi.io/twitter/user/mentions",
            headers={"X-API-Key": tracker.api_key},
            params=params,
        )

    def test_trackers_twitterapiiotracker_get_all_mentions_no_next_cursor(
        self, mocker, twitterapiio_config
    ):
        """Test _get_all_mentions when there is no next cursor."""
        mocker.patch("trackers.base.MentionDatabaseManager")
        mock_requests_get = mocker.patch("requests.get")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "tweets": [{"id": "123", "isReply": False}],
            "has_next_page": False,
            "next_cursor": "",
        }
        mock_requests_get.return_value = mock_response

        tracker = TwitterapiioTracker(lambda x: True, twitterapiio_config)
        mentions = list(tracker._get_all_mentions())

        assert len(mentions) == 1

    def test_trackers_twitterapiiotracker_get_all_mentions_reply_parent_found(
        self, mocker, twitterapiio_config
    ):
        """Test _get_all_mentions with a reply, but parent tweet is not found."""
        mocker.patch("trackers.base.MentionDatabaseManager")
        tracker = TwitterapiioTracker(lambda x: True, twitterapiio_config)
        mocker.patch.object(tracker, "_get_tweets_by_ids", return_value={"456": "789"})

        mentions_data = [
            {
                "id": "123",
                "isReply": True,
                "inReplyToId": "456",
            }
        ]

        mock_requests_get = mocker.patch("requests.get")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "tweets": mentions_data,
            "has_next_page": False,
        }
        mock_requests_get.return_value = mock_response

        mentions = list(tracker._get_all_mentions())
        assert len(mentions) == 1
        assert "parent_tweet" in mentions[0]

    def test_trackers_twitterapiiotracker_get_all_mentions_reply_parent_not_found(
        self, mocker, twitterapiio_config
    ):
        """Test _get_all_mentions with a reply, but parent tweet is not found."""
        mocker.patch("trackers.base.MentionDatabaseManager")
        tracker = TwitterapiioTracker(lambda x: True, twitterapiio_config)
        mocker.patch.object(tracker, "_get_tweets_by_ids", return_value={})

        mentions_data = [
            {
                "id": "123",
                "isReply": True,
                "inReplyToId": "456",
            }
        ]

        mock_requests_get = mocker.patch("requests.get")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "tweets": mentions_data,
            "has_next_page": False,
        }
        mock_requests_get.return_value = mock_response

        mentions = list(tracker._get_all_mentions())
        assert len(mentions) == 1
        assert "parent_tweet" not in mentions[0]

    def test_trackers_twitterapiiotracker_get_all_mentions_api_error(
        self, mocker, twitterapiio_config
    ):
        """Test _get_all_mentions with an API error."""
        mocker.patch("trackers.base.MentionDatabaseManager")
        mock_requests_get = mocker.patch("requests.get")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "error", "message": "API Error"}
        mock_requests_get.return_value = mock_response

        tracker = TwitterapiioTracker(lambda x: True, twitterapiio_config)
        mentions = list(tracker._get_all_mentions())

        assert len(mentions) == 0

    # # is_processed
    def test_trackers_twitterapiiotracker_is_processed(
        self, mocker, twitterapiio_config
    ):
        """Test is_processed method."""
        mocker.patch("trackers.base.MentionDatabaseManager")
        mock_db = MagicMock()
        tracker = TwitterapiioTracker(lambda x: True, twitterapiio_config)
        tracker.db = mock_db

        tracker.is_processed("123")
        mock_db.is_processed.assert_called_once_with("123", tracker.platform_name)

    # # extract_mention_data
    def test_trackers_twitterapiiotracker_extract_mention_data_simple(
        self, mocker, twitterapiio_config
    ):
        """Test extract_mention_data with a simple mention."""
        mocker.patch("trackers.base.MentionDatabaseManager")
        tracker = TwitterapiioTracker(lambda x: True, twitterapiio_config)
        mention = {
            "id": "123",
            "text": "Test mention",
            "author": {"userName": "testuser"},
            "createdAt": "Sat Nov 22 04:28:58 +0000 2025",
        }
        data = tracker.extract_mention_data(mention)
        assert data["suggester"] == "testuser"
        assert data["item_id"] == "123"
        assert data["contributor"] == "testuser"
        assert data["contribution_url"] == "https://twitter.com/i/web/status/123"

    def test_trackers_twitterapiiotracker_extract_mention_data_with_parent(
        self, mocker, twitterapiio_config
    ):
        """Test extract_mention_data with a mention that has a parent tweet."""
        mocker.patch("trackers.base.MentionDatabaseManager")
        tracker = TwitterapiioTracker(lambda x: True, twitterapiio_config)
        mention = {
            "id": "123",
            "text": "Test mention",
            "author": {"userName": "testuser"},
            "createdAt": "Sat Nov 22 04:28:58 +0000 2025",
            "parent_tweet": {"id": "456", "author": {"userName": "parentuser"}},
        }
        data = tracker.extract_mention_data(mention)
        assert data["contributor"] == "parentuser"
        assert data["contribution_url"] == "https://twitter.com/i/web/status/456"

    # process_mention
    def test_trackers_twitterapiiotracker_process_mention_callback_true(
        self, mocker, twitterapiio_config
    ):
        """Test process_mention when callback returns True."""
        mocker.patch("trackers.base.MentionDatabaseManager")
        mock_db = MagicMock()
        callback = MagicMock(return_value=True)
        tracker = TwitterapiioTracker(callback, twitterapiio_config)
        tracker.db = mock_db
        data = {"item_id": "123"}
        result = tracker.process_mention("123", data)
        assert result is True
        callback.assert_called_once_with(data)
        mock_db.mark_processed.assert_called_once_with(
            "123", tracker.platform_name, data
        )

    def test_trackers_twitterapiiotracker_process_mention_callback_false(
        self, mocker, twitterapiio_config
    ):
        """Test process_mention when callback returns False."""
        mocker.patch("trackers.base.MentionDatabaseManager")
        mock_db = MagicMock()
        callback = MagicMock(return_value=False)
        tracker = TwitterapiioTracker(callback, twitterapiio_config)
        tracker.db = mock_db
        data = {"item_id": "123"}
        result = tracker.process_mention("123", data)
        assert result is False
        callback.assert_called_once_with(data)
        mock_db.mark_processed.assert_not_called()

    # # check_mentions
    def test_trackers_twitterapiiotracker_check_mentions_no_new_mentions(
        self, mocker, twitterapiio_config
    ):
        """Test check_mentions when there are no new mentions."""
        mocker.patch("trackers.base.MentionDatabaseManager")
        tracker = TwitterapiioTracker(lambda x: True, twitterapiio_config)
        mocker.patch.object(tracker, "_get_all_mentions", return_value=[])

        mentions_found = tracker.check_mentions()

        assert mentions_found == 0

    def test_trackers_twitterapiiotracker_check_mentions_with_new_mentions(
        self, mocker, twitterapiio_config
    ):
        """Test check_mentions when there are new mentions."""
        mocker.patch("trackers.base.MentionDatabaseManager")
        tracker = TwitterapiioTracker(lambda x: True, twitterapiio_config)
        mentions_data = [{"id": "123"}]
        mocker.patch.object(tracker, "_get_all_mentions", return_value=mentions_data)
        mocker.patch.object(tracker, "is_processed", return_value=False)
        mocker.patch.object(
            tracker, "extract_mention_data", return_value={"data": "data"}
        )
        mocker.patch.object(tracker, "process_mention", return_value=True)

        mentions_found = tracker.check_mentions()

        assert mentions_found == 1
        tracker.is_processed.assert_called_once_with("123")
        tracker.extract_mention_data.assert_called_once_with(mentions_data[0])
        tracker.process_mention.assert_called_once_with("123", {"data": "data"})

    def test_trackers_twitterapiiotracker_check_mentions_process_mention_false(
        self, mocker, twitterapiio_config
    ):
        """Test check_mentions when there are new mentions."""
        mocker.patch("trackers.base.MentionDatabaseManager")
        tracker = TwitterapiioTracker(lambda x: True, twitterapiio_config)
        mentions_data = [{"id": "123"}]
        mocker.patch.object(tracker, "_get_all_mentions", return_value=mentions_data)
        mocker.patch.object(tracker, "is_processed", return_value=False)
        mocker.patch.object(
            tracker, "extract_mention_data", return_value={"data": "data"}
        )
        mocker.patch.object(tracker, "process_mention", return_value=False)

        mentions_found = tracker.check_mentions()

        assert mentions_found == 0
        tracker.is_processed.assert_called_once_with("123")
        tracker.extract_mention_data.assert_called_once_with(mentions_data[0])
        tracker.process_mention.assert_called_once_with("123", {"data": "data"})

    def test_trackers_twitterapiiotracker_check_mentions_already_processed(
        self, mocker, twitterapiio_config
    ):
        """Test check_mentions with mentions that have already been processed."""
        mocker.patch("trackers.base.MentionDatabaseManager")
        tracker = TwitterapiioTracker(lambda x: True, twitterapiio_config)
        mentions_data = [{"id": "123"}]
        mocker.patch.object(tracker, "_get_all_mentions", return_value=mentions_data)
        mocker.patch.object(tracker, "is_processed", return_value=True)
        mock_extract = mocker.patch.object(tracker, "extract_mention_data")
        mock_process = mocker.patch.object(tracker, "process_mention")

        mentions_found = tracker.check_mentions()

        assert mentions_found == 0
        tracker.is_processed.assert_called_once_with("123")
        mock_extract.assert_not_called()
        mock_process.assert_not_called()

    def test_trackers_twitterapiiotracker_check_mentions_exception(
        self, mocker, twitterapiio_config
    ):
        """Test check_mentions with an exception during mention retrieval."""
        mocker.patch("trackers.base.MentionDatabaseManager")
        tracker = TwitterapiioTracker(lambda x: True, twitterapiio_config)
        mocker.patch.object(
            tracker, "_get_all_mentions", side_effect=Exception("API error")
        )
        mock_log_action = mocker.patch.object(tracker, "log_action")

        mentions_found = tracker.check_mentions()

        assert mentions_found == 0
        mock_log_action.assert_has_calls(
            [
                call("mentions_check_error", "Error: API error"),
                call("mentions_checked", "Found 0 new mentions"),
            ]
        )

    # # run
    def test_trackers_twitterapiiotracker_run_wrapper_calls_base_run(
        self, mocker, twitterapiio_config
    ):
        """Test that the run method calls the base class's run method."""
        mocker.patch("trackers.base.MentionDatabaseManager")
        mocked_base_run = mocker.patch("trackers.base.BaseMentionTracker.run")
        tracker = TwitterapiioTracker(
            parse_message_callback=lambda x: x, config=twitterapiio_config
        )

        tracker.run(poll_interval_minutes=10, max_iterations=5)

        mocked_base_run.assert_called_once_with(
            poll_interval_minutes=10, max_iterations=5
        )

    def test_trackers_twitterapiiotracker_init_no_batch_size(
        self, mocker, twitterapiio_config
    ):
        """Test initialization without batch_size in config."""
        mocker.patch("trackers.base.MentionDatabaseManager")
        config = twitterapiio_config.copy()
        del config["batch_size"]
        instance = TwitterapiioTracker(lambda x: None, config)
        assert instance.batch_size == 20

    def test_trackers_twitterapiiotracker_get_all_mentions_json_decode_error(
        self, mocker, twitterapiio_config
    ):
        """Test _get_all_mentions with a JSON decode error."""
        mocker.patch("trackers.base.MentionDatabaseManager")

        # Create a mock response object directly
        mock_response_obj = MagicMock(status_code=200)
        mock_response_obj.json.side_effect = json.JSONDecodeError(
            "Expecting value", "char 0", 0
        )

        # Patch requests.get to return this pre-configured mock object
        mocker.patch("requests.get", return_value=mock_response_obj)

        tracker = TwitterapiioTracker(lambda x: True, twitterapiio_config)
        mentions = list(tracker._get_all_mentions())

        assert len(mentions) == 0

    def test_trackers_twitterapiiotracker_get_all_mentions_api_error_status(
        self, mocker, twitterapiio_config
    ):
        """Test _get_all_mentions with an API error status."""
        mocker.patch("trackers.base.MentionDatabaseManager")
        mock_requests_get = mocker.patch("requests.get")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "error", "message": "API Error"}
        mock_requests_get.return_value = mock_response

        tracker = TwitterapiioTracker(lambda x: True, twitterapiio_config)
        mentions = list(tracker._get_all_mentions())

        assert len(mentions) == 0

    def test_trackers_twitterapiiotracker_check_mentions_no_last_timestamp(
        self, mocker, twitterapiio_config
    ):
        """Test check_mentions when no last timestamp is found."""
        mocker.patch("trackers.base.MentionDatabaseManager")
        mock_db = MagicMock()
        mock_db.last_processed_timestamp.return_value = None
        tracker = TwitterapiioTracker(lambda x: True, twitterapiio_config)
        tracker.db = mock_db
        mocker.patch.object(tracker, "_get_all_mentions", return_value=[])

        tracker.check_mentions()

        tracker._get_all_mentions.assert_called_with(since_time=None)

    def test_trackers_twitterapiiotracker_run_mentions_found_logging(
        self, mocker, twitterapiio_config
    ):
        mocker.patch("trackers.base.MentionDatabaseManager")
        mock_logger_info = mocker.patch.object(logging.Logger, "info")
        tracker = TwitterapiioTracker(lambda x: True, twitterapiio_config)
        mocker.patch.object(tracker, "check_mentions", return_value=5)
        mocker.patch.object(tracker, "_interruptible_sleep")

        tracker.run(max_iterations=1)

        assert any(
            "Found 5 new mentions" in call.args[0]
            for call in mock_logger_info.call_args_list
        )

    def test_trackers_twitterapiiotracker_run_keyboard_interrupt(
        self, mocker, twitterapiio_config
    ):
        """Test that run method handles KeyboardInterrupt gracefully."""
        mocker.patch("trackers.base.MentionDatabaseManager")
        mock_tracker_logger_info = mocker.patch.object(logging.Logger, "info")
        mock_tracker_log_action = mocker.patch.object(TwitterapiioTracker, "log_action")
        mock_cleanup = mocker.patch.object(TwitterapiioTracker, "cleanup")

        tracker = TwitterapiioTracker(lambda x: True, twitterapiio_config)
        mocker.patch.object(tracker, "check_mentions", side_effect=KeyboardInterrupt)

        tracker.run(max_iterations=1)

        mock_tracker_logger_info.assert_any_call(
            f"{tracker.platform_name} tracker stopped by user"
        )
        mock_tracker_log_action.assert_any_call("stopped", "User interrupt")
        mock_cleanup.assert_called_once()

    def test_trackers_twitterapiiotracker_run_exception(
        self, mocker, twitterapiio_config
    ):
        """Test that run method handles a generic Exception."""
        mocker.patch("trackers.base.MentionDatabaseManager")
        mock_logger_error = mocker.patch.object(logging.Logger, "error")
        mock_log_action = mocker.patch.object(TwitterapiioTracker, "log_action")
        mock_cleanup = mocker.patch.object(TwitterapiioTracker, "cleanup")

        tracker = TwitterapiioTracker(lambda x: True, twitterapiio_config)
        # Simulate an exception during check_mentions
        mocker.patch.object(
            tracker, "check_mentions", side_effect=ValueError("Simulated error")
        )

        with pytest.raises(ValueError, match="Simulated error"):
            tracker.run(max_iterations=1)

        mock_logger_error.assert_any_call(
            f"{tracker.platform_name} tracker error: Simulated error"
        )
        mock_log_action.assert_any_call("error", "Tracker error: Simulated error")
        mock_cleanup.assert_called_once()

    def test_trackers_twitterapiiotracker_get_tweets_by_ids_value_error(
        self, mocker, twitterapiio_config
    ):
        """Test _get_tweets_by_ids with a ValueError during JSON decoding."""
        mocker.patch("trackers.base.MentionDatabaseManager")
        mock_requests_get = mocker.patch("requests.get")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("decoding failed")
        mock_requests_get.return_value = mock_response

        tracker = TwitterapiioTracker(lambda x: True, twitterapiio_config)
        mock_logger_error = mocker.patch.object(tracker.logger, "error")
        tweets = tracker._get_tweets_by_ids(["123"])

        assert tweets == {}
        mock_logger_error.assert_called_with(
            "Failed to decode JSON from response: decoding failed"
        )

    def test_trackers_twitterapiiotracker_run_no_new_mentions_logging(
        self, mocker, twitterapiio_config
    ):
        mocker.patch("trackers.base.MentionDatabaseManager")
        mock_logger_info = mocker.patch.object(logging.Logger, "info")
        tracker = TwitterapiioTracker(lambda x: True, twitterapiio_config)
        mocker.patch.object(tracker, "check_mentions", return_value=0)
        mocker.patch.object(tracker, "_interruptible_sleep")

        tracker.run(max_iterations=1)

        assert not any(
            "Found 0 new mentions" in call.args[0]
            for call in mock_logger_info.call_args_list
        )
