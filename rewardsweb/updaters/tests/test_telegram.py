"""Testing module for :py:mod:`updaters.telegram` module."""

from updaters.telegram import TelegramUpdater


class TestUpdatersTelegramTelegramUpdater:
    """Testing class for :py:mod:`updaters.telegram.TelegramUpdater` class."""

    def test_updaters_telegram_telegramupdater_add_reaction_to_message_functionality(
        self,
    ):
        assert (
            TelegramUpdater().add_reaction_to_message("some_url", "some_reaction")
            is True
        )

    def test_updaters_telegram_telegramupdater_add_reply_to_message_functionality(
        self,
    ):
        assert TelegramUpdater().add_reply_to_message("some_url", "some_text") is True

    def test_updaters_telegram_telegramupdater_message_from_url_for_no_message_found(
        self, mocker
    ):
        url = mocker.MagicMock()
        mocked_mention = mocker.patch(
            "updaters.telegram.Mention.objects.message_from_url", return_value=None
        )
        updater = TelegramUpdater()
        returned = updater.message_from_url(url)
        assert returned is None
        mocked_mention.assert_called_once_with(url)

    def test_updaters_telegram_telegramupdater_message_from_url_functionality(
        self, mocker
    ):
        url = mocker.MagicMock()
        message_data = mocker.MagicMock()
        mocked_mention = mocker.patch(
            "updaters.telegram.Mention.objects.message_from_url",
            return_value=message_data,
        )
        updater = TelegramUpdater()
        returned = updater.message_from_url(url)
        assert returned == message_data
        mocked_mention.assert_called_once_with(url)
