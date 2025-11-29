"""Testing module for :py:mod:`updaters.twitter` module."""

import pytest

from updaters.twitter import TwitterUpdater


class TestUpdatersTwitterTwitterUpdater:
    """Testing class for :py:mod:`updaters.twitter.TwitterUpdater` class."""

    def test_updaters_twitter_twitterupdater_add_reaction_to_message_functionality(
        self,
    ):
        assert (
            TwitterUpdater().add_reaction_to_message("some_url", "some_reaction")
            is None
        )

    def test_updaters_twitter_twitterupdater_add_reply_to_message_functionality(
        self,
    ):
        assert TwitterUpdater().add_reply_to_message("some_url", "some_text") is None

    def test_updaters_twitter_twitterupdater_message_from_url_functionality(
        self, mocker
    ):
        url = mocker.MagicMock()
        message_data = mocker.MagicMock()
        mocked_mention = mocker.patch(
            "updaters.twitter.Mention.objects.message_from_url",
            return_value=message_data,
        )
        updater = TwitterUpdater()
        returned = updater.message_from_url(url)
        assert returned == message_data
        mocked_mention.assert_called_once_with(url)
