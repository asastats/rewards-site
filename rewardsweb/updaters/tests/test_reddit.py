"""Testing module for :py:mod:`updaters.reddit` module."""

import pytest

from updaters.reddit import RedditUpdater


class TestUpdatersRedditRedditUpdater:
    """Testing class for :py:mod:`updaters.reddit.RedditUpdater` class."""

    def test_updaters_reddit_redditupdater_add_reaction_to_message_for_not_implemented(
        self,
    ):
        with pytest.raises(NotImplementedError):
            RedditUpdater().add_reaction_to_message("some_url", "some_reaction")

    def test_updaters_reddit_redditupdater_add_reply_to_message_for_not_implemented(
        self,
    ):
        with pytest.raises(NotImplementedError):
            RedditUpdater().add_reply_to_message("some_url", "some_text")

    def test_updaters_reddit_redditupdater_message_from_url_for_no_message_found(
        self, mocker
    ):
        url = mocker.MagicMock()
        mocked_mention = mocker.patch(
            "updaters.reddit.Mention.objects.message_from_url", return_value=None
        )
        updater = RedditUpdater()
        returned = updater.message_from_url(url)
        assert returned is None
        mocked_mention.assert_called_once_with(url)

    def test_updaters_reddit_redditupdater_message_from_url_functionality(self, mocker):
        url = mocker.MagicMock()
        message_data = mocker.MagicMock()
        mocked_mention = mocker.patch(
            "updaters.reddit.Mention.objects.message_from_url",
            return_value=message_data,
        )
        updater = RedditUpdater()
        returned = updater.message_from_url(url)
        assert returned == message_data
        mocked_mention.assert_called_once_with(url)
