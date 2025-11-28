"""Testing module for :py:mod:`updaters.telegram` module."""

import pytest

from updaters.telegram import TelegramUpdater


class TestUpdatersTelegramTelegramUpdater:
    """Testing class for :py:mod:`updaters.telegram.TelegramUpdater` class."""

    def setup_method(self):
        """Set up test method."""
        self.updater = TelegramUpdater()

    def test_updaters_telegram_telegramupdater_add_reaction_to_message_for_not_implemented(
        self,
    ):
        """Test add_reaction_to_message raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            self.updater.add_reaction_to_message("some_url", "some_reaction")

    def test_updaters_telegram_telegramupdater_add_reply_to_message_for_not_implemented(
        self,
    ):
        """Test add_reply_to_message raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            self.updater.add_reply_to_message("some_url", "some_text")
