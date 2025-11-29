"""Testing module for :py:mod:`trackers.twitterapiio` module."""

import json
import logging

import pytest
import requests

from trackers.twitterapiio import TwitterapiioTracker


@pytest.mark.django_db
class TestTrackersTwitterApiIOTracker:
    """Testing class for :class:`trackers.twitterapiio.TwitterapiioTracker`."""

    # # __init__
    def test_trackers_twitterapiiotracker_init_success(
        self, mocker, twitterapiio_config
    ):
        """Test successful initialization of TwitterapiioTracker."""

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

        mock_requests_get = mocker.patch("requests.get")
        mock_response = mocker.MagicMock()
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

        mock_requests_get = mocker.patch("requests.get")
        tracker = TwitterapiioTracker(lambda x: True, twitterapiio_config)
        tweets = tracker._get_tweets_by_ids([])
        assert tweets == {}
        mock_requests_get.assert_not_called()

    def test_trackers_twitterapiiotracker_get_tweets_by_ids_api_error(
        self, mocker, twitterapiio_config
    ):
        """Test _get_tweets_by_ids with an API error."""

        mock_requests_get = mocker.patch("requests.get")
        mock_response = mocker.MagicMock()
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

        mocker.patch("requests.get", side_effect=requests.exceptions.RequestException)
        tracker = TwitterapiioTracker(lambda x: True, twitterapiio_config)
        tweets = tracker._get_tweets_by_ids(["123"])
        assert tweets == {}

    def test_trackers_twitterapiiotracker_get_tweets_by_ids_json_decode_error(
        self, mocker, twitterapiio_config
    ):
        """Test _get_tweets_by_ids with a JSON decode error."""

        mock_requests_get = mocker.patch("requests.get")
        mock_response = mocker.MagicMock()
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

        mock_requests_get = mocker.patch("requests.get")
        mock_response_page1 = mocker.MagicMock()
        mock_response_page1.status_code = 200
        mock_response_page1.json.return_value = {
            "status": "success",
            "tweets": [{"id": "123", "isReply": False}],
            "has_next_page": True,
            "next_cursor": "cursor123",
        }
        mock_response_page2 = mocker.MagicMock()
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

        mock_requests_get = mocker.patch("requests.get")
        mock_response_page1 = mocker.MagicMock()
        mock_response_page1.status_code = 200
        mock_response_page1.json.return_value = {
            "status": "success",
            "tweets": [{"id": "123", "isReply": False}],
            "has_next_page": True,
            "next_cursor": "cursor123",
        }
        mock_response_page2 = mocker.MagicMock()
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

        mock_requests_get = mocker.patch("requests.get")
        mock_response = mocker.MagicMock()
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
        mock_requests_get.assert_called_once_with(
            "https://api.twitterapi.io/twitter/user/mentions",
            params={
                "userName": tracker.target_handle,
                "sinceTime": since_time,
                "cursor": "",
            },
            headers={"X-API-Key": tracker.api_key},
        )

    def test_trackers_twitterapiiotracker_get_all_mentions_no_next_cursor(
        self, mocker, twitterapiio_config
    ):
        """Test _get_all_mentions when there is no next cursor."""

        mock_requests_get = mocker.patch("requests.get")
        mock_response = mocker.MagicMock()
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
        mock_response = mocker.MagicMock()
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
        mock_response = mocker.MagicMock()
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

        mock_requests_get = mocker.patch("requests.get")
        mock_response = mocker.MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "error", "message": "API Error"}
        mock_requests_get.return_value = mock_response
        tracker = TwitterapiioTracker(lambda x: True, twitterapiio_config)
        mentions = list(tracker._get_all_mentions())
        assert len(mentions) == 0

    # # extract_mention_data
    def test_trackers_twitterapiiotracker_extract_mention_data_simple(
        self, mocker, twitterapiio_config
    ):
        """Test extract_mention_data with a simple mention."""

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
        assert data["contribution"] == ""

    def test_trackers_twitterapiiotracker_extract_mention_data_with_parent(
        self, mocker, twitterapiio_config
    ):
        """Test extract_mention_data with a mention that has a parent tweet."""

        tracker = TwitterapiioTracker(lambda x: True, twitterapiio_config)
        mention = {
            "id": "123",
            "text": "Test mention",
            "author": {"userName": "testuser"},
            "createdAt": "Sat Nov 22 04:28:58 +0000 2025",
            "parent_tweet": {
                "id": "456",
                "author": {"userName": "parentuser"},
                "text": "This is the parent tweet.",
            },
        }
        data = tracker.extract_mention_data(mention)
        assert data["contributor"] == "parentuser"
        assert data["contribution_url"] == "https://twitter.com/i/web/status/456"
        assert data["contribution"] == "This is the parent tweet."

    # # check_mentions
    def test_trackers_twitterapiiotracker_check_mentions_no_new_mentions(
        self, mocker, twitterapiio_config
    ):
        """Test check_mentions when there are no new mentions."""

        mocker.patch(
            "trackers.models.Mention.objects.last_processed_timestamp",
            new=mocker.MagicMock(return_value=None),
        )
        tracker = TwitterapiioTracker(lambda x: True, twitterapiio_config)
        mocker.patch.object(tracker, "_get_all_mentions", return_value=[])
        mentions_found = tracker.check_mentions()
        assert mentions_found == 0

    def test_trackers_twitterapiiotracker_check_mentions_with_new_mentions(
        self, mocker, twitterapiio_config
    ):
        """Test check_mentions when there are new mentions."""

        mocker.patch(
            "trackers.models.Mention.objects.last_processed_timestamp",
            new=mocker.MagicMock(return_value=None),
        )
        tracker = TwitterapiioTracker(lambda x: True, twitterapiio_config)
        mentions_data = [{"id": "123"}]
        mocker.patch.object(tracker, "_get_all_mentions", return_value=mentions_data)
        mocker.patch.object(
            tracker, "is_processed", new=mocker.MagicMock(return_value=False)
        )
        mocker.patch.object(
            tracker, "extract_mention_data", return_value={"data": "data"}
        )
        mocker.patch.object(
            tracker, "process_mention", new=mocker.MagicMock(return_value=True)
        )
        mentions_found = tracker.check_mentions()
        assert mentions_found == 1
        tracker.is_processed.assert_called_once_with("123")
        tracker.extract_mention_data.assert_called_once_with(mentions_data[0])
        tracker.process_mention.assert_called_once_with(
            "123", {"data": "data"}, f"@{twitterapiio_config['target_handle']}"
        )

    def test_trackers_twitterapiiotracker_check_mentions_process_mention_false(
        self, mocker, twitterapiio_config
    ):
        """Test check_mentions when there are new mentions."""
        mocker.patch(
            "trackers.models.Mention.objects.last_processed_timestamp",
            new=mocker.MagicMock(return_value=None),
        )
        tracker = TwitterapiioTracker(lambda x: True, twitterapiio_config)
        mentions_data = [{"id": "123"}]
        mocker.patch.object(tracker, "_get_all_mentions", return_value=mentions_data)
        mocker.patch.object(
            tracker, "is_processed", new=mocker.MagicMock(return_value=False)
        )
        mocker.patch.object(
            tracker, "extract_mention_data", return_value={"data": "data"}
        )
        mocker.patch.object(
            tracker, "process_mention", new=mocker.MagicMock(return_value=False)
        )
        mentions_found = tracker.check_mentions()
        assert mentions_found == 0
        tracker.is_processed.assert_called_once_with("123")
        tracker.extract_mention_data.assert_called_once_with(mentions_data[0])
        tracker.process_mention.assert_called_once_with(
            "123", {"data": "data"}, f"@{twitterapiio_config['target_handle']}"
        )

    def test_trackers_twitterapiiotracker_check_mentions_already_processed(
        self, mocker, twitterapiio_config
    ):
        """Test check_mentions with mentions that have already been processed."""
        mocker.patch(
            "trackers.models.Mention.objects.last_processed_timestamp",
            new=mocker.MagicMock(return_value=None),
        )
        tracker = TwitterapiioTracker(lambda x: True, twitterapiio_config)
        mentions_data = [{"id": "123"}]
        mocker.patch.object(tracker, "_get_all_mentions", return_value=mentions_data)
        mocker.patch.object(
            tracker, "is_processed", new=mocker.MagicMock(return_value=True)
        )
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
        mocker.patch(
            "trackers.models.Mention.objects.last_processed_timestamp",
            new=mocker.MagicMock(return_value=None),
        )
        tracker = TwitterapiioTracker(lambda x: True, twitterapiio_config)
        mocker.patch.object(
            tracker, "_get_all_mentions", side_effect=Exception("API error")
        )
        mock_log_action = mocker.patch.object(
            tracker, "log_action", new=mocker.MagicMock()
        )
        mentions_found = tracker.check_mentions()
        assert mentions_found == 0
        mock_log_action.assert_has_calls(
            [
                mocker.call("mentions_check_error", "Error: API error"),
                mocker.call("mentions_checked", "Found 0 new mentions"),
            ]
        )

    def test_trackers_twitterapiiotracker_get_all_mentions_json_decode_error(
        self, mocker, twitterapiio_config
    ):
        """Test _get_all_mentions with a JSON decode error."""

        # Create a mock response object directly
        mock_response_obj = mocker.MagicMock(status_code=200)
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

        mock_requests_get = mocker.patch("requests.get")
        mock_response = mocker.MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "error", "message": "API Error"}
        mock_requests_get.return_value = mock_response
        tracker = TwitterapiioTracker(lambda x: True, twitterapiio_config)
        mentions = list(tracker._get_all_mentions())
        assert len(mentions) == 0

    def test_trackers_twitterapiiotracker_get_all_mentions_chunking(
        self, mocker, twitterapiio_config
    ):
        """Test _get_all_mentions with chunking of parent tweet IDs."""

        tracker = TwitterapiioTracker(lambda x: True, twitterapiio_config)
        tracker.batch_size = 2
        mock_get_tweets = mocker.patch.object(
            tracker, "_get_tweets_by_ids", return_value={}
        )
        mentions_data = [
            {"id": "1", "isReply": True, "inReplyToId": "101"},
            {"id": "2", "isReply": True, "inReplyToId": "102"},
            {"id": "3", "isReply": True, "inReplyToId": "103"},
        ]
        mock_requests_get = mocker.patch("requests.get")
        mock_response = mocker.MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "tweets": mentions_data,
            "has_next_page": False,
        }
        mock_requests_get.return_value = mock_response
        list(tracker._get_all_mentions())
        assert mock_get_tweets.call_count == 2
        mock_get_tweets.assert_any_call(["101", "102"])
        mock_get_tweets.assert_any_call(["103"])

    def test_trackers_twitterapiiotracker_check_mentions_last_timestamp(
        self, mocker, twitterapiio_config
    ):
        last_timestamp = 12349
        mock_last_processed = mocker.patch(
            "trackers.models.Mention.objects.last_processed_timestamp",
            new=mocker.MagicMock(return_value=last_timestamp),
        )
        tracker = TwitterapiioTracker(lambda x: True, twitterapiio_config)
        mocker.patch.object(tracker, "_get_all_mentions", return_value=[])
        tracker.check_mentions()
        tracker._get_all_mentions.assert_called_with(since_time=12350)
        mock_last_processed.assert_called_once_with(tracker.platform_name)

    def test_trackers_twitterapiiotracker_check_mentions_no_last_timestamp(
        self, mocker, twitterapiio_config
    ):
        mock_last_processed = mocker.patch(
            "trackers.models.Mention.objects.last_processed_timestamp",
            new=mocker.MagicMock(return_value=None),
        )
        tracker = TwitterapiioTracker(lambda x: True, twitterapiio_config)
        mocker.patch.object(tracker, "_get_all_mentions", return_value=[])
        tracker.check_mentions()
        tracker._get_all_mentions.assert_called_with(since_time=None)
        mock_last_processed.assert_called_once_with(tracker.platform_name)

    def test_trackers_twitterapiiotracker_run_mentions_found_logging(
        self, mocker, twitterapiio_config
    ):

        mock_logger_info = mocker.patch.object(logging.Logger, "info")
        tracker = TwitterapiioTracker(lambda x: True, twitterapiio_config)
        mocker.patch.object(
            tracker, "check_mentions", new=mocker.MagicMock(return_value=5)
        )
        mocker.patch.object(tracker, "_interruptible_sleep")
        tracker.run(max_iterations=1)
        assert any(
            "Found 5 new mentions" in c.args[0] for c in mock_logger_info.call_args_list
        )

    def test_trackers_twitterapiiotracker_run_keyboard_interrupt(
        self, mocker, twitterapiio_config
    ):
        """Test that run method handles KeyboardInterrupt gracefully."""

        mock_tracker_logger_info = mocker.patch.object(logging.Logger, "info")
        mock_tracker_log_action = mocker.patch.object(
            TwitterapiioTracker, "log_action", new=mocker.MagicMock()
        )
        tracker = TwitterapiioTracker(lambda x: True, twitterapiio_config)
        mocker.patch.object(
            tracker,
            "check_mentions",
            new=mocker.MagicMock(side_effect=KeyboardInterrupt),
        )
        tracker.run(max_iterations=1)
        mock_tracker_logger_info.assert_any_call(
            f"{tracker.platform_name} tracker stopped by user"
        )
        mock_tracker_log_action.assert_any_call("stopped", "User interrupt")

    def test_trackers_twitterapiiotracker_run_exception(
        self, mocker, twitterapiio_config
    ):
        """Test that run method handles a generic Exception."""

        mock_logger_error = mocker.patch.object(logging.Logger, "error")
        mock_log_action = mocker.patch.object(
            TwitterapiioTracker, "log_action", new=mocker.MagicMock()
        )
        tracker = TwitterapiioTracker(lambda x: True, twitterapiio_config)
        # Simulate an exception during check_mentions
        mocker.patch.object(
            tracker,
            "check_mentions",
            new=mocker.MagicMock(side_effect=ValueError("Simulated error")),
        )
        with pytest.raises(ValueError, match="Simulated error"):
            tracker.run(max_iterations=1)
        mock_logger_error.assert_any_call(
            f"{tracker.platform_name} tracker error: Simulated error"
        )
        mock_log_action.assert_any_call("error", "Tracker error: Simulated error")

    def test_trackers_twitterapiiotracker_get_tweets_by_ids_value_error(
        self, mocker, twitterapiio_config
    ):
        """Test _get_tweets_by_ids with a ValueError during JSON decoding."""

        mock_requests_get = mocker.patch("requests.get")
        mock_response = mocker.MagicMock()
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

        mock_logger_info = mocker.patch.object(logging.Logger, "info")
        tracker = TwitterapiioTracker(lambda x: True, twitterapiio_config)
        mocker.patch.object(
            tracker, "check_mentions", new=mocker.MagicMock(return_value=0)
        )
        mocker.patch.object(tracker, "_interruptible_sleep")
        tracker.run(max_iterations=1)
        assert not any(
            "Found 0 new mentions" in c.args[0] for c in mock_logger_info.call_args_list
        )
