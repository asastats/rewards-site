"""Testing module for :py:mod:`updaters.reddit` module."""

import pytest

from updaters.reddit import RedditUpdater


class TestUpdatersRedditRedditUpdater:
    """Testing class for :py:mod:`updaters.reddit.RedditUpdater` class."""

    def setup_method(self):
        """Set up test method."""
        self.updater = RedditUpdater()

    def test_updaters_reddit_redditupdater_add_reaction_to_message_for_not_implemented(
        self,
    ):
        """Test add_reaction_to_message raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            self.updater.add_reaction_to_message("some_url", "some_reaction")

    def test_updaters_reddit_redditupdater_add_reply_to_message_for_not_implemented(
        self,
    ):
        """Test add_reply_to_message raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            self.updater.add_reply_to_message("some_url", "some_text")

    def test_updaters_reddit_redditupdater_message_from_url_for_no_message_found(
        self, mocker
    ):
        mock_db_instance = mocker.MagicMock()
        mocker.patch(
            "updaters.reddit.MentionDatabaseManager", return_value=mock_db_instance
        )
        mock_db_instance.get_mention_by_url.return_value = None
        self.updater.db_manager = mock_db_instance

        url = "https://reddit.com/r/subreddit/comments/123"
        expected = {
            "success": False,
            "error": f"Message not found for URL: {url}",
        }
        returned = self.updater.message_from_url(url)
        assert returned == expected
        mock_db_instance.get_mention_by_url.assert_called_once_with(url)

    def test_updaters_reddit_redditupdater_message_from_url_functionality(self, mocker):
        mock_db_instance = mocker.MagicMock()
        mocker.patch(
            "updaters.reddit.MentionDatabaseManager", return_value=mock_db_instance
        )
        url = "https://reddit.com/r/subreddit/comments/456"
        timestamp = 1678876400
        message_data = {
            "suggester": "userA",
            "suggestion_url": url,
            "contribution_url": "https://reddit.com/r/subreddit/comments/455",
            "contributor": "userB",
            "type": "comment",
            "content": "This is a comment",
            "timestamp": timestamp,
            "item_id": "456",
        }
        mock_db_instance.get_mention_by_url.return_value = message_data
        self.updater.db_manager = mock_db_instance

        expected = {
            "success": True,
            "content": "This is a comment",
            "author": "userB",
            "timestamp": "2023-03-15T10:33:20+00:00",
            "message_id": "456",
            "raw_data": message_data,
        }
        returned = self.updater.message_from_url(url)
        assert returned == expected
        mock_db_instance.get_mention_by_url.assert_called_once_with(url)
