"""Testing module for project's template tags and filters."""

import pytest

from core.templatetags.core_utils import messages_toast


class MockMessage:
    def __init__(self, message, level_tag="info"):
        self.message = message
        self.level_tag = level_tag

    def __str__(self):
        return self.message


@pytest.fixture
def mock_messages():
    return [
        MockMessage("Welcome back!", "success"),
        MockMessage("An error occurred.", "error"),
        MockMessage("Just some info.", "info"),
    ]


class TestCoreTemplateTags:

    # # messages_toast
    def test_core_templatetags_messages_toast_retrieves_and_returns_messages(
        self, mocker, mock_messages
    ):
        mock_request = mocker.MagicMock()
        mock_get_messages = mocker.patch(
            "core.templatetags.core_utils.messages.get_messages",
            return_value=mock_messages,
        )
        result_context = messages_toast(mock_request)
        mock_get_messages.assert_called_once_with(mock_request)
        expected_context = {"django_messages": mock_messages}
        assert result_context == expected_context

    def test_core_templatetags_messages_toast_handles_no_messages(self, mocker):
        mock_request = mocker.MagicMock()
        mock_empty_messages = []
        mock_get_messages = mocker.patch(
            "core.templatetags.core_utils.messages.get_messages",
            return_value=mock_empty_messages,
        )
        result_context = messages_toast(mock_request)
        mock_get_messages.assert_called_once_with(mock_request)
        assert result_context == {"django_messages": []}
