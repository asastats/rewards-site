"""Testing module for :py:mod:`updaters.base` module."""

import pytest

from updaters.base import BaseUpdater


class DummyBaseUpdater(BaseUpdater):

    def add_reaction_to_message(self, url, reaction_name):
        super().add_reaction_to_message(url, reaction_name)
        return f"url: {url} reaction_name: {reaction_name}"

    def add_reply_to_message(self, url, text):
        super().add_reply_to_message(url, text)
        return f"url: {url} text: {text}"

    def message_from_url(self, url):
        super().message_from_url(url)
        return f"{url}"


class TestBaseUpdater:
    """Testing class for :class:`issues.providers.BaseUpdater` interface."""

    def test_updaters_base_baseupdater_is_abstract(self):
        with pytest.raises(TypeError) as exc_info:
            BaseUpdater()

        assert "Can't instantiate abstract class" in str(exc_info.value)

    # # add_reaction_to_message
    def test_updaters_base_baseupdater_add_reaction_to_message(self):
        updater = DummyBaseUpdater()
        assert (
            updater.add_reaction_to_message("url", "reaction_name")
            == "url: url reaction_name: reaction_name"
        )

    # # add_reply_to_message
    def test_updaters_base_baseupdater_add_reply_to_message(self):
        updater = DummyBaseUpdater()
        assert updater.add_reply_to_message("url", "text") == "url: url text: text"

    # # message_from_url
    def test_updaters_base_baseupdater_message_from_url(self):
        updater = DummyBaseUpdater()
        assert updater.message_from_url("url") == "url"
