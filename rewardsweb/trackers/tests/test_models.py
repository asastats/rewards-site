"""Testing module for :py:mod:`trackers.models` module."""

import pytest
from asgiref.sync import sync_to_async

from trackers.models import Mention, MentionLog


@pytest.mark.django_db
class TestTrackersModelsMentionManager:
    """Testing class for :class:`trackers.models.MentionManager` class."""

    def test_trackers_models_mentionmanager_is_processed_true(self):
        """Test is_processed method for a processed mention."""
        Mention.objects.create(
            item_id="test_item_id",
            platform="test_platform",
            raw_data={"key": "value"},
        )
        assert Mention.objects.is_processed("test_item_id", "test_platform") is True

    def test_trackers_models_mentionmanager_is_processed_false(self):
        """Test is_processed method for an unprocessed mention."""
        assert Mention.objects.is_processed("test_item_id", "test_platform") is False

    def test_trackers_models_mentionmanager_mark_processed(self):
        """Test mark_processed method."""
        test_data = {"suggester": "test_user"}
        Mention.objects.mark_processed("test_item_id", "test_platform", test_data)
        mention = Mention.objects.get(item_id="test_item_id")
        assert mention.platform == "test_platform"
        assert mention.suggester == "test_user"
        assert mention.raw_data == test_data

    def test_trackers_models_mentionmanager_last_processed_timestamp_found(self):
        """Test last_processed_timestamp method when a timestamp is found."""
        Mention.objects.create(
            item_id="1",
            platform="test_platform",
            raw_data={"timestamp": 1672531199},
        )
        Mention.objects.create(
            item_id="2",
            platform="test_platform",
            raw_data={"timestamp": 1672531200},
        )
        result = Mention.objects.last_processed_timestamp("test_platform")
        assert result == 1672531200

    def test_trackers_models_mentionmanager_last_processed_timestamp_not_found(self):
        """Test last_processed_timestamp method when no timestamp is found."""
        Mention.objects.create(
            item_id="1", platform="test_platform", raw_data={"key": "value"}
        )
        result = Mention.objects.last_processed_timestamp("test_platform")
        assert result is None

    def test_trackers_models_mentionmanager_last_processed_timestamp_no_mentions(self):
        """Test last_processed_timestamp method when there are no mentions."""
        result = Mention.objects.last_processed_timestamp("test_platform")
        assert result is None


@pytest.mark.django_db
class TestTrackersModelsMentionLogManager:
    """Testing class for :class:`trackers.models.MentionLogManager` class."""

    @pytest.mark.asyncio
    async def test_trackers_models_mentionlogmanager_log_action(self):
        """Test log_action method."""
        await MentionLog.objects.log_action(
            "test_platform", "test_action", "test_details"
        )
        log = await sync_to_async(
            MentionLog.objects.first
        )()  # Use sync_to_async for synchronous query
        assert log.platform == "test_platform"
        assert log.action == "test_action"
        assert log.details == "test_details"


@pytest.mark.django_db
class TestTrackersModelsMentionManagerMessageFromUrl:
    """Testing class for :py:meth:`trackers.models.MentionManager.message_from_url` method."""

    def setup_method(self):
        """Set up test method."""
        test_data_1 = {
            "item_id": "1",
            "platform": "twitter",
            "suggester": "user1",
            "suggestion_url": "https://twitter.com/status/1",
            "contribution_url": "https://twitter.com/contrib/1",
            "content": "Tweet content 1",
            "timestamp": 1678886400,
            "contributor": "userA",
        }
        test_data_2 = {
            "item_id": "2",
            "platform": "reddit",
            "suggester": "user2",
            "suggestion_url": "https://reddit.com/post/2",
            "contribution_url": "https://reddit.com/comment/2",
            "content": "Reddit content 2",
            "timestamp": 1678886500,
            "contributor": "userB",
        }
        Mention.objects.create(item_id="1", platform="twitter", raw_data=test_data_1)
        Mention.objects.create(item_id="2", platform="reddit", raw_data=test_data_2)

    def test_trackers_models_mentionmanager_message_from_url_suggestion_url(
        self,
    ):
        """Test retrieving a mention by its suggestion_url."""
        url = "https://twitter.com/status/1"
        message = Mention.objects.message_from_url(url)
        assert message["success"] is True
        assert message["content"] == "Tweet content 1"
        assert message["author"] == "userA"
        assert message["message_id"] == "1"

    def test_trackers_models_mentionmanager_message_from_url_contribution_url(
        self,
    ):
        """Test retrieving a mention by its contribution_url."""
        url = "https://reddit.com/comment/2"
        message = Mention.objects.message_from_url(url)
        assert message["success"] is True
        assert message["content"] == "Reddit content 2"
        assert message["author"] == "userB"
        assert message["message_id"] == "2"

    def test_trackers_models_mentionmanager_message_from_url_not_found(self):
        """Test retrieving a mention for a URL that does not exist."""
        url = "https://nonexistent.com/url"
        message = Mention.objects.message_from_url(url)
        assert message["success"] is False
        assert "not found" in message["error"]
