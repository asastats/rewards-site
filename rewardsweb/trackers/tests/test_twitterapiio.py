"""Testing module for :py:mod:`trackers.twitterapiio` module."""

from datetime import datetime

from trackers.twitterapiio import TwitterapiioTracker


class TestTrackersTwitter:
    """Testing class for :class:`trackers.twitter.TwitterapiioTracker`."""

    # __init__
    def test_trackers_twittertracker_init_success(self, twitterapiio_config):
        instance = TwitterapiioTracker(lambda x: None, twitterapiio_config)
        assert instance.api_key == twitterapiio_config["api_key"]
        assert instance.target_handle == twitterapiio_config["target_handle"]
        assert instance.batch_size == twitterapiio_config["batch_size"]

    # _get_original_tweet_info
    def test_trackers_twittertracker_get_original_tweet_info_success(
        self, mocker, twitterapiio_config
    ):
        mocker.patch("tweepy.Client")
        instance = TwitterapiioTracker(lambda x: None, twitterapiio_config)

        mock_tweet_data = mocker.MagicMock()
        mock_tweet_data.id = "original_tweet_123"
        mock_tweet_data.author_id = "original_user_id"
        mock_user = mocker.MagicMock()
        mock_user.id = "original_user_id"
        mock_user.username = "original_user"
        mock_includes = {"users": [mock_user]}

        mock_response = mocker.MagicMock()
        mock_response.data = mock_tweet_data
        mock_response.includes = mock_includes
        instance.client.get_tweet.return_value = mock_response

        contribution_url, contributor = instance._get_original_tweet_info(
            "ref_tweet_123"
        )

        assert contribution_url == "https://twitter.com/i/web/status/original_tweet_123"
        assert contributor == "original_user"
        instance.client.get_tweet.assert_called_once_with(
            "ref_tweet_123",
            tweet_fields=["created_at", "author_id", "text"],
            expansions=["author_id"],
        )

    def test_trackers_twittertracker_get_original_tweet_info_no_data(
        self, mocker, twitterapiio_config
    ):
        mocker.patch("tweepy.Client")
        instance = TwitterapiioTracker(lambda x: None, twitterapiio_config)

        mock_response = mocker.MagicMock()
        mock_response.data = None
        instance.client.get_tweet.return_value = mock_response

        contribution_url, contributor = instance._get_original_tweet_info(
            "ref_tweet_123"
        )

        assert contribution_url == ""
        assert contributor == ""

    def test_trackers_twittertracker_get_original_tweet_info_no_users(
        self, mocker, twitterapiio_config
    ):
        mocker.patch("tweepy.Client")
        instance = TwitterapiioTracker(lambda x: None, twitterapiio_config)

        mock_tweet_data = mocker.MagicMock()
        mock_tweet_data.id = "original_tweet_123"
        mock_tweet_data.author_id = "original_user_id"
        mock_response = mocker.MagicMock()
        mock_response.data = mock_tweet_data
        mock_response.includes = {}
        instance.client.get_tweet.return_value = mock_response

        contribution_url, contributor = instance._get_original_tweet_info(
            "ref_tweet_123"
        )

        assert contribution_url == "https://twitter.com/i/web/status/original_tweet_123"
        assert contributor == ""

    def test_trackers_twittertracker_get_original_tweet_info_user_not_found(
        self, mocker, twitterapiio_config
    ):
        mocker.patch("tweepy.Client")
        instance = TwitterapiioTracker(lambda x: None, twitterapiio_config)

        mock_tweet_data = mocker.MagicMock()
        mock_tweet_data.id = "original_tweet_123"
        mock_tweet_data.author_id = "different_user_id"  # Different from included user
        mock_user = mocker.MagicMock()
        mock_user.id = "some_other_user_id"
        mock_user.username = "other_user"
        mock_includes = {"users": [mock_user]}

        mock_response = mocker.MagicMock()
        mock_response.data = mock_tweet_data
        mock_response.includes = mock_includes
        instance.client.get_tweet.return_value = mock_response

        contribution_url, contributor = instance._get_original_tweet_info(
            "ref_tweet_123"
        )

        assert contribution_url == "https://twitter.com/i/web/status/original_tweet_123"
        assert contributor == ""  # Author not found in users

    def test_trackers_twittertracker_get_original_tweet_info_exception(
        self, mocker, twitterapiio_config
    ):
        mocker.patch("tweepy.Client")
        instance = TwitterapiioTracker(lambda x: None, twitterapiio_config)
        instance.logger = mocker.MagicMock()

        instance.client.get_tweet.side_effect = Exception("API error")

        contribution_url, contributor = instance._get_original_tweet_info(
            "ref_tweet_123"
        )

        assert contribution_url == ""
        assert contributor == ""
        instance.logger.warning.assert_called_once_with(
            "Failed to get original tweet ref_tweet_123: API error"
        )

    # _extract_reply_mention_data
    def test_trackers_twittertracker_extract_reply_mention_data_with_reply(
        self, mocker, twitterapiio_config
    ):
        mocker.patch("tweepy.Client")
        instance = TwitterapiioTracker(lambda x: None, twitterapiio_config)

        mock_tweet = mocker.MagicMock()
        mock_ref_tweet = mocker.MagicMock()
        mock_ref_tweet.type = "replied_to"
        mock_ref_tweet.id = "ref_tweet_123"
        mock_tweet.referenced_tweets = [mock_ref_tweet]

        mock_get_original_info = mocker.patch.object(
            instance, "_get_original_tweet_info"
        )
        mock_get_original_info.return_value = (
            "https://twitter.com/i/web/status/original_123",
            "original_user",
        )

        user_map = {"user123": "test_user"}
        contribution_url, contributor = instance._extract_reply_mention_data(
            mock_tweet, user_map
        )

        assert contribution_url == "https://twitter.com/i/web/status/original_123"
        assert contributor == "original_user"
        mock_get_original_info.assert_called_once_with("ref_tweet_123")

    def test_trackers_twittertracker_extract_reply_mention_data_no_referenced_tweets(
        self, mocker, twitterapiio_config
    ):
        mocker.patch("tweepy.Client")
        instance = TwitterapiioTracker(lambda x: None, twitterapiio_config)

        mock_tweet = mocker.MagicMock()
        mock_tweet.referenced_tweets = None

        user_map = {"user123": "test_user"}
        contribution_url, contributor = instance._extract_reply_mention_data(
            mock_tweet, user_map
        )

        assert contribution_url == ""
        assert contributor == ""

    def test_trackers_twittertracker_extract_reply_mention_data_no_reply_type(
        self, mocker, twitterapiio_config
    ):
        mocker.patch("tweepy.Client")
        instance = TwitterapiioTracker(lambda x: None, twitterapiio_config)

        mock_tweet = mocker.MagicMock()
        mock_ref_tweet = mocker.MagicMock()
        mock_ref_tweet.type = "quoted"  # Not a reply
        mock_ref_tweet.id = "ref_tweet_123"
        mock_tweet.referenced_tweets = [mock_ref_tweet]

        mock_get_original_info = mocker.patch.object(
            instance, "_get_original_tweet_info"
        )

        user_map = {"user123": "test_user"}
        contribution_url, contributor = instance._extract_reply_mention_data(
            mock_tweet, user_map
        )

        assert contribution_url == ""
        assert contributor == ""
        mock_get_original_info.assert_not_called()

    # _get_content_preview
    def test_trackers_twittertracker_get_content_preview_with_text(
        self, mocker, twitterapiio_config
    ):
        mocker.patch("tweepy.Client")
        instance = TwitterapiioTracker(lambda x: None, twitterapiio_config)

        mock_tweet = mocker.MagicMock()
        mock_tweet.text = (
            "This is a test tweet with some content that might be longer than 200 characters. "
            * 3
        )

        result = instance._get_content_preview(mock_tweet)

        assert result == mock_tweet.text[:200]
        assert len(result) == 200

    def test_trackers_twittertracker_get_content_preview_no_text(
        self, mocker, twitterapiio_config
    ):
        mocker.patch("tweepy.Client")
        instance = TwitterapiioTracker(lambda x: None, twitterapiio_config)

        mock_tweet = mocker.MagicMock()
        mock_tweet.text = None

        result = instance._get_content_preview(mock_tweet)

        assert result == ""

    def test_trackers_twittertracker_get_content_preview_empty_text(
        self, mocker, twitterapiio_config
    ):
        mocker.patch("tweepy.Client")
        instance = TwitterapiioTracker(lambda x: None, twitterapiio_config)

        mock_tweet = mocker.MagicMock()
        mock_tweet.text = ""

        result = instance._get_content_preview(mock_tweet)

        assert result == ""

    def test_trackers_twittertracker_get_content_preview_no_text_attr(
        self, mocker, twitterapiio_config
    ):
        mocker.patch("tweepy.Client")
        instance = TwitterapiioTracker(lambda x: None, twitterapiio_config)

        # Create a simple mock without MagicMock's automatic attribute creation
        class SimpleMock:
            pass

        mock_tweet = SimpleMock()

        result = instance._get_content_preview(mock_tweet)

        assert result == ""

    # _get_timestamp
    def test_trackers_twittertracker_get_timestamp_with_created_at(
        self, mocker, twitterapiio_config
    ):
        mocker.patch("tweepy.Client")
        instance = TwitterapiioTracker(lambda x: None, twitterapiio_config)

        mock_tweet = mocker.MagicMock()
        mock_tweet.created_at = datetime(2023, 1, 1, 12, 0, 0)

        result = instance._get_timestamp(mock_tweet)

        assert result == "2023-01-01T12:00:00"

    def test_trackers_twittertracker_get_timestamp_no_created_at(
        self, mocker, twitterapiio_config
    ):
        mocker.patch("tweepy.Client")
        instance = TwitterapiioTracker(lambda x: None, twitterapiio_config)

        mock_tweet = mocker.MagicMock()
        mock_tweet.created_at = None

        result = instance._get_timestamp(mock_tweet)

        assert "T" in result  # Should be ISO format with T
        assert len(result) > 0

    def test_trackers_twittertracker_get_timestamp_no_created_at_attr(
        self, mocker, twitterapiio_config
    ):
        mocker.patch("tweepy.Client")
        instance = TwitterapiioTracker(lambda x: None, twitterapiio_config)

        # Create a simple mock without MagicMock's automatic attribute creation
        class SimpleMock:
            pass

        mock_tweet = SimpleMock()

        result = instance._get_timestamp(mock_tweet)

        assert "T" in result  # Should be ISO format with T
        assert len(result) > 0

    # extract_mention_data
    def test_trackers_twittertracker_extract_mention_data_reply(
        self, mocker, twitterapiio_config
    ):
        mocker.patch("tweepy.Client")
        instance = TwitterapiioTracker(lambda x: None, twitterapiio_config)

        mock_tweet = mocker.MagicMock()
        mock_tweet.author_id = "user123"
        mock_tweet.id = "tweet123"
        mock_tweet.text = "Hello @test_bot!"
        mock_tweet.created_at = datetime(2023, 1, 1, 12, 0, 0)

        mock_extract_reply_data = mocker.patch.object(
            instance, "_extract_reply_mention_data"
        )
        mock_extract_reply_data.return_value = (
            "https://twitter.com/i/web/status/original_123",
            "original_user",
        )

        user_map = {"user123": "suggester_user"}
        result = instance.extract_mention_data(mock_tweet, user_map)

        assert result["suggester"] == "suggester_user"
        assert result["suggestion_url"] == "https://twitter.com/i/web/status/tweet123"
        assert (
            result["contribution_url"]
            == "https://twitter.com/i/web/status/original_123"
        )
        assert result["contributor"] == "original_user"
        assert result["type"] == "tweet"
        assert result["content_preview"] == "Hello @test_bot!"
        assert result["item_id"] == "tweet123"

    def test_trackers_twittertracker_extract_mention_data_no_reply(
        self, mocker, twitterapiio_config
    ):
        mocker.patch("tweepy.Client")
        instance = TwitterapiioTracker(lambda x: None, twitterapiio_config)

        mock_tweet = mocker.MagicMock()
        mock_tweet.author_id = "user123"
        mock_tweet.id = "tweet123"
        mock_tweet.text = "Hello @test_bot!"
        mock_tweet.created_at = datetime(2023, 1, 1, 12, 0, 0)

        mock_extract_reply_data = mocker.patch.object(
            instance, "_extract_reply_mention_data"
        )
        mock_extract_reply_data.return_value = ("", "")  # No reply data

        user_map = {"user123": "suggester_user"}
        result = instance.extract_mention_data(mock_tweet, user_map)

        assert result["suggester"] == "suggester_user"
        assert result["contribution_url"] == "https://twitter.com/i/web/status/tweet123"
        assert result["contributor"] == "suggester_user"  # Falls back to suggester

    def test_trackers_twittertracker_extract_mention_data_no_contributor_in_reply(
        self, mocker, twitterapiio_config
    ):
        mocker.patch("tweepy.Client")
        instance = TwitterapiioTracker(lambda x: None, twitterapiio_config)

        mock_tweet = mocker.MagicMock()
        mock_tweet.author_id = "user123"
        mock_tweet.id = "tweet123"
        mock_tweet.text = "Hello @test_bot!"
        mock_tweet.created_at = datetime(2023, 1, 1, 12, 0, 0)

        mock_extract_reply_data = mocker.patch.object(
            instance, "_extract_reply_mention_data"
        )
        mock_extract_reply_data.return_value = (
            "https://twitter.com/i/web/status/original_123",
            "",
        )  # No contributor

        user_map = {"user123": "suggester_user"}
        result = instance.extract_mention_data(mock_tweet, user_map)

        assert result["contributor"] == "suggester_user"  # Falls back to suggester

    def test_trackers_twittertracker_extract_mention_data_no_suggester_in_user_map(
        self, mocker, twitterapiio_config
    ):
        mocker.patch("tweepy.Client")
        instance = TwitterapiioTracker(lambda x: None, twitterapiio_config)

        mock_tweet = mocker.MagicMock()
        mock_tweet.author_id = "unknown_user"
        mock_tweet.id = "tweet123"
        mock_tweet.text = "Hello @test_bot!"
        mock_tweet.created_at = datetime(2023, 1, 1, 12, 0, 0)

        mock_extract_reply_data = mocker.patch.object(
            instance, "_extract_reply_mention_data"
        )
        mock_extract_reply_data.return_value = ("", "")

        user_map = {"user123": "suggester_user"}  # unknown_user not in map
        result = instance.extract_mention_data(mock_tweet, user_map)

        assert result["suggester"] == ""
        assert result["contributor"] == ""  # Falls back to empty suggester

    def test_trackers_twittertracker_extract_mention_data_no_text(
        self, mocker, twitterapiio_config
    ):
        mocker.patch("tweepy.Client")
        instance = TwitterapiioTracker(lambda x: None, twitterapiio_config)

        mock_tweet = mocker.MagicMock()
        mock_tweet.author_id = "user123"
        mock_tweet.id = "tweet123"
        mock_tweet.text = None  # No text attribute
        mock_tweet.created_at = None  # No created_at

        mock_extract_reply_data = mocker.patch.object(
            instance, "_extract_reply_mention_data"
        )
        mock_extract_reply_data.return_value = ("", "")

        user_map = {"user123": "suggester_user"}
        result = instance.extract_mention_data(mock_tweet, user_map)

        assert result["content_preview"] == ""
        assert "timestamp" in result  # Should use current timestamp
        assert result["suggester"] == "suggester_user"

    # # run
    def test_trackers_twittertracker_run_wrapper_calls_base_run(
        self, mocker, twitterapiio_config
    ):
        mock_client = mocker.patch("tweepy.Client")
        mock_user = mocker.MagicMock()
        mock_user_data = mocker.MagicMock()
        mock_user_data.id = "12345"
        mock_user.data = mock_user_data
        mock_client.return_value.get_me.return_value = mock_user

        # Patch BaseMentionTracker.run so no real loop runs
        mocked_base_run = mocker.patch("trackers.twitter.BaseMentionTracker.run")

        # Create instance (MessageParser.parse mocked out)
        tracker = TwitterapiioTracker(
            parse_message_callback=lambda x: x, config=twitterapiio_config
        )

        # Call the wrapper
        tracker.run(poll_interval_minutes=10, max_iterations=5)

        # Ensure BaseMentionTracker.run was called once with correct args
        mocked_base_run.assert_called_once_with(
            poll_interval_minutes=10,
            max_iterations=5,
        )

    # check_mentions
    def test_trackers_twittertracker_check_mentions_found(self, mocker, twitterapiio_config):
        mock_client = mocker.patch("tweepy.Client")
        mock_user = mocker.MagicMock()
        mock_user_data = mocker.MagicMock()
        mock_user_data.id = "12345"
        mock_user.data = mock_user_data
        mock_client.return_value.get_me.return_value = mock_user

        instance = TwitterapiioTracker(lambda x: None, twitterapiio_config)

        mock_tweet = mocker.MagicMock()
        mock_tweet.id = "tweet123"
        mock_user_obj = mocker.MagicMock()
        mock_user_obj.id = "user123"
        mock_user_obj.username = "test_user"

        mock_response = mocker.MagicMock()
        mock_response.data = [mock_tweet]
        mock_response.includes = {"users": [mock_user_obj]}
        instance.client.get_users_mentions.return_value = mock_response

        mock_process_mention = mocker.patch.object(instance, "process_mention")
        mock_process_mention.return_value = True
        mock_is_processed = mocker.patch.object(instance, "is_processed")
        mock_is_processed.return_value = False

        result = instance.check_mentions()

        assert result == 1
        instance.client.get_users_mentions.assert_called_once_with(
            "12345",
            tweet_fields=[
                "created_at",
                "conversation_id",
                "author_id",
                "text",
                "referenced_tweets",
            ],
            expansions=["author_id"],
            max_results=20,
        )
        mock_process_mention.assert_called_once()

    def test_trackers_twittertracker_check_mentions_no_data(
        self, mocker, twitterapiio_config
    ):
        mock_client = mocker.patch("tweepy.Client")
        mock_user = mocker.MagicMock()
        mock_user_data = mocker.MagicMock()
        mock_user_data.id = "12345"
        mock_user.data = mock_user_data
        mock_client.return_value.get_me.return_value = mock_user

        instance = TwitterapiioTracker(lambda x: None, twitterapiio_config)

        mock_response = mocker.MagicMock()
        mock_response.data = None
        instance.client.get_users_mentions.return_value = mock_response

        result = instance.check_mentions()

        assert result == 0

    def test_trackers_twittertracker_check_mentions_no_users_in_includes(
        self, mocker, twitterapiio_config
    ):
        mock_client = mocker.patch("tweepy.Client")
        mock_user = mocker.MagicMock()
        mock_user_data = mocker.MagicMock()
        mock_user_data.id = "12345"
        mock_user.data = mock_user_data
        mock_client.return_value.get_me.return_value = mock_user

        instance = TwitterapiioTracker(lambda x: None, twitterapiio_config)

        mock_tweet = mocker.MagicMock()
        mock_tweet.id = "tweet123"

        mock_response = mocker.MagicMock()
        mock_response.data = [mock_tweet]
        mock_response.includes = {}  # No users in includes
        instance.client.get_users_mentions.return_value = mock_response

        mock_is_processed = mocker.patch.object(instance, "is_processed")
        mock_is_processed.return_value = False
        mock_process_mention = mocker.patch.object(instance, "process_mention")
        mock_process_mention.return_value = True

        result = instance.check_mentions()

        assert result == 1
        # Should still process even without user map

    def test_trackers_twittertracker_check_mentions_exception(
        self, mocker, twitterapiio_config
    ):
        mock_client = mocker.patch("tweepy.Client")
        mock_user = mocker.MagicMock()
        mock_user_data = mocker.MagicMock()
        mock_user_data.id = "12345"
        mock_user.data = mock_user_data
        mock_client.return_value.get_me.return_value = mock_user

        instance = TwitterapiioTracker(lambda x: None, twitterapiio_config)

        instance.client.get_users_mentions.side_effect = Exception("API error")
        mock_log_action = mocker.patch.object(instance, "log_action")

        mock_logger_error = mocker.patch.object(instance.logger, "error")

        result = instance.check_mentions()

        assert result == 0
        mock_logger_error.assert_called_with(
            "Error checking Twitter mentions: API error"
        )
        mock_log_action.assert_called_with("twitter_check_error", "Error: API error")

    def test_trackers_twittertracker_check_mentions_already_processed(
        self, mocker, twitterapiio_config
    ):
        mock_client = mocker.patch("tweepy.Client")
        mock_user = mocker.MagicMock()
        mock_user_data = mocker.MagicMock()
        mock_user_data.id = "12345"
        mock_user.data = mock_user_data
        mock_client.return_value.get_me.return_value = mock_user

        instance = TwitterapiioTracker(lambda x: None, twitterapiio_config)

        mock_tweet = mocker.MagicMock()
        mock_tweet.id = "tweet123"
        mock_response = mocker.MagicMock()
        mock_response.data = [mock_tweet]
        mock_response.includes = {"users": []}
        instance.client.get_users_mentions.return_value = mock_response

        mock_is_processed = mocker.patch.object(instance, "is_processed")
        mock_is_processed.return_value = True

        mock_process_mention = mocker.patch.object(instance, "process_mention")

        result = instance.check_mentions()

        assert result == 0
        mock_is_processed.assert_called_with("tweet123")
        mock_process_mention.assert_not_called()

    def test_trackers_twittertracker_check_mentions_process_mention_false(
        self, mocker, twitterapiio_config
    ):
        mock_client = mocker.patch("tweepy.Client")
        mock_user = mocker.MagicMock()
        mock_user_data = mocker.MagicMock()
        mock_user_data.id = "12345"
        mock_user.data = mock_user_data
        mock_client.return_value.get_me.return_value = mock_user

        instance = TwitterapiioTracker(lambda x: None, twitterapiio_config)

        mock_tweet = mocker.MagicMock()
        mock_tweet.id = "tweet123"
        mock_response = mocker.MagicMock()
        mock_response.data = [mock_tweet]
        mock_response.includes = {"users": []}
        instance.client.get_users_mentions.return_value = mock_response

        mock_is_processed = mocker.patch.object(instance, "is_processed")
        mock_is_processed.return_value = False

        mock_process_mention = mocker.patch.object(instance, "process_mention")
        mock_process_mention.return_value = False

        result = instance.check_mentions()

        assert result == 0
        mock_process_mention.assert_called_once()

    def test_trackers_twittertracker_run_mentions_found_logging(
        self, mocker, twitterapiio_config
    ):
        mock_client = mocker.patch("tweepy.Client")
        mock_user = mocker.MagicMock()
        mock_user_data = mocker.MagicMock()
        mock_user_data.id = "12345"
        mock_user.data = mock_user_data
        mock_client.return_value.get_me.return_value = mock_user

        instance = TwitterapiioTracker(lambda x: None, twitterapiio_config)

        mock_check_mentions = mocker.patch.object(instance, "check_mentions")
        mock_check_mentions.return_value = 5

        mocker.patch("time.sleep", side_effect=StopIteration)
        mock_logger_info = mocker.patch.object(instance.logger, "info")

        try:
            instance.run(poll_interval_minutes=0.1, max_iterations=1)
        except StopIteration:
            pass

        mock_logger_info.assert_any_call("Found 5 new mentions")
