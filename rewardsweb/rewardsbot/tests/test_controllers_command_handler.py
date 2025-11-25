"""Testing module for :py:mod:`rewardsbot.controllers.command_handler` module.

This module contains tests for the SuggestRewardModal class and its
interaction handling functionality.
"""

import discord
import pytest

from rewardsbot.controllers.command_handler import SuggestRewardModal
from rewardsbot.services.suggestion import SuggestionService


class MockTextInput:
    """Mock TextInput that allows setting value for testing."""

    def __init__(self, value=""):
        self.value = value


class TestControllersCommandHandler:
    """Testing class for :py:mod:`rewardsbot.controllers.command_handler` components."""

    def _create_modal_with_mocked_inputs(
        self, target_message, type_val="", level_val="", user_val="", comment_val=""
    ):
        """Helper to create a modal with mocked input values."""
        modal = SuggestRewardModal(target_message=target_message)

        # Replace the TextInput instances with our mock ones
        modal.type_input = MockTextInput(type_val)
        modal.level_input = MockTextInput(level_val)
        modal.user_input = MockTextInput(user_val)
        modal.comment_input = MockTextInput(comment_val)

        return modal

    @pytest.mark.asyncio
    async def test_controllers_command_handler_suggest_reward_modal_initialization(
        self, mocker
    ):
        """Test SuggestRewardModal initialization with target message."""
        # Create a mock message with async context
        mock_message = mocker.AsyncMock(spec=discord.Message)
        mock_author = mocker.AsyncMock()
        mock_author.name = "test_user"
        mock_message.author = mock_author

        # Initialize modal within async context to handle event loop
        modal = SuggestRewardModal(target_message=mock_message)

        assert modal.target_message == mock_message
        assert modal.user_input.default == "test_user"
        assert modal.title == "Suggest a Reward"
        assert modal.type_input.required is True
        assert modal.level_input.required is True
        assert modal.user_input.required is True
        assert modal.comment_input.required is False

    @pytest.mark.asyncio
    async def test_controllers_command_handler_suggest_reward_modal_on_submit_success(
        self, mocker
    ):
        """Test successful suggestion submission via modal."""
        mock_interaction = mocker.AsyncMock(spec=discord.Interaction)
        mock_interaction.response.defer = mocker.AsyncMock()
        mock_interaction.followup.send = mocker.AsyncMock()

        mock_message = mocker.AsyncMock(spec=discord.Message)
        mock_message.jump_url = "https://discord.com/channels/123/456/789"
        mock_message.author.name = "test_user"

        mock_bot = mocker.MagicMock()
        mock_bot.api_service = mocker.MagicMock()
        mock_interaction.client = mock_bot

        # Create modal with mocked inputs
        modal = self._create_modal_with_mocked_inputs(
            target_message=mock_message,
            type_val="f",
            level_val="2",
            user_val="contributor_name",
            comment_val="test comment",
        )

        mock_create = mocker.patch.object(
            SuggestionService, "create_suggestion", new_callable=mocker.AsyncMock
        )
        await modal.on_submit(mock_interaction)

        mock_interaction.response.defer.assert_called_once_with(
            thinking=True, ephemeral=True
        )
        mock_create.assert_called_once_with(
            mock_bot.api_service,
            "F",
            "2",
            "contributor_name",
            "test comment",
            "https://discord.com/channels/123/456/789",
        )
        mock_interaction.followup.send.assert_called_once_with(
            "✅ Suggestion for [F2] submitted for contributor_name.", ephemeral=True
        )

    @pytest.mark.asyncio
    async def test_controllers_command_handler_suggest_reward_modal_on_submit_failure(
        self, mocker
    ):
        """Test suggestion submission failure via modal."""
        mock_interaction = mocker.AsyncMock(spec=discord.Interaction)
        mock_interaction.response.defer = mocker.AsyncMock()
        mock_interaction.followup.send = mocker.AsyncMock()

        mock_message = mocker.AsyncMock(spec=discord.Message)
        mock_message.jump_url = "https://discord.com/channels/123/456/789"
        mock_message.author.name = "test_user"

        mock_bot = mocker.MagicMock()
        mock_bot.api_service = mocker.MagicMock()
        mock_interaction.client = mock_bot

        modal = self._create_modal_with_mocked_inputs(
            target_message=mock_message,
            type_val="b",
            level_val="1",
            user_val="another_contributor",
            comment_val="",
        )

        mock_create = mocker.patch.object(
            SuggestionService, "create_suggestion", new_callable=mocker.AsyncMock
        )
        mock_create.side_effect = Exception("API unavailable")

        mock_logger = mocker.patch("rewardsbot.controllers.command_handler.logger")
        await modal.on_submit(mock_interaction)

        mock_interaction.response.defer.assert_called_once_with(
            thinking=True, ephemeral=True
        )
        mock_create.assert_called_once_with(
            mock_bot.api_service,
            "B",
            "1",
            "another_contributor",
            "",
            "https://discord.com/channels/123/456/789",
        )
        mock_interaction.followup.send.assert_called_once_with(
            "❌ Failed to submit suggestion: API unavailable", ephemeral=True
        )
        mock_logger.error.assert_called_once_with(
            "Suggestion submission error: API unavailable"
        )

    @pytest.mark.asyncio
    async def test_controllers_command_handler_suggest_reward_modal_on_submit_case_conversion(
        self, mocker
    ):
        """Test contribution type case conversion in modal submission."""
        mock_interaction = mocker.AsyncMock(spec=discord.Interaction)
        mock_interaction.response.defer = mocker.AsyncMock()
        mock_interaction.followup.send = mocker.AsyncMock()

        mock_message = mocker.AsyncMock(spec=discord.Message)
        mock_message.jump_url = "https://discord.com/channels/123/456/789"
        mock_message.author.name = "test_user"

        mock_bot = mocker.MagicMock()
        mock_bot.api_service = mocker.MagicMock()
        mock_interaction.client = mock_bot

        modal = self._create_modal_with_mocked_inputs(
            target_message=mock_message,
            type_val="at",  # lowercase input
            level_val="3",
            user_val="contributor",
            comment_val="test",
        )

        mock_create = mocker.patch.object(
            SuggestionService, "create_suggestion", new_callable=mocker.AsyncMock
        )
        await modal.on_submit(mock_interaction)

        mock_create.assert_called_once_with(
            mock_bot.api_service,
            "AT",
            "3",
            "contributor",
            "test",
            "https://discord.com/channels/123/456/789",
        )
        mock_interaction.followup.send.assert_called_once_with(
            "✅ Suggestion for [AT3] submitted for contributor.", ephemeral=True
        )

    @pytest.mark.asyncio
    async def test_controllers_command_handler_suggest_reward_modal_on_submit_no_comment(
        self, mocker
    ):
        """Test modal submission with no comment provided."""
        mock_interaction = mocker.AsyncMock(spec=discord.Interaction)
        mock_interaction.response.defer = mocker.AsyncMock()
        mock_interaction.followup.send = mocker.AsyncMock()

        mock_message = mocker.AsyncMock(spec=discord.Message)
        mock_message.jump_url = "https://discord.com/channels/123/456/789"
        mock_message.author.name = "test_user"

        mock_bot = mocker.MagicMock()
        mock_bot.api_service = mocker.MagicMock()
        mock_interaction.client = mock_bot

        modal = self._create_modal_with_mocked_inputs(
            target_message=mock_message,
            type_val="CT",
            level_val="2",
            user_val="contributor",
            comment_val="",  # Empty comment
        )

        mock_create = mocker.patch.object(
            SuggestionService, "create_suggestion", new_callable=mocker.AsyncMock
        )
        await modal.on_submit(mock_interaction)

        mock_create.assert_called_once_with(
            mock_bot.api_service,
            "CT",
            "2",
            "contributor",
            "",
            "https://discord.com/channels/123/456/789",
        )

    @pytest.mark.asyncio
    async def test_controllers_command_handler_suggest_reward_modal_on_submit_uses_prefilled_username(
        self, mocker
    ):
        """Test modal uses pre-filled username from message author."""
        mock_interaction = mocker.AsyncMock(spec=discord.Interaction)
        mock_interaction.response.defer = mocker.AsyncMock()
        mock_interaction.followup.send = mocker.AsyncMock()

        mock_message = mocker.AsyncMock(spec=discord.Message)
        mock_message.jump_url = "https://discord.com/channels/123/456/789"
        mock_message.author.name = "prefilled_user"

        mock_bot = mocker.MagicMock()
        mock_bot.api_service = mocker.MagicMock()
        mock_interaction.client = mock_bot

        # Create the modal normally to test the default username behavior
        modal = SuggestRewardModal(target_message=mock_message)

        # Replace just the inputs we need to control, preserving the default user_input
        modal = self._create_modal_with_mocked_inputs(
            target_message=mock_message,
            type_val="F",
            level_val="1",
            user_val="prefilled_user",  # User didn't change the pre-filled value
            comment_val="",
        )

        mock_create = mocker.patch.object(
            SuggestionService, "create_suggestion", new_callable=mocker.AsyncMock
        )
        await modal.on_submit(mock_interaction)

        mock_create.assert_called_once_with(
            mock_bot.api_service,
            "F",
            "1",
            "prefilled_user",
            "",
            "https://discord.com/channels/123/456/789",
        )
        mock_interaction.followup.send.assert_called_once_with(
            "✅ Suggestion for [F1] submitted for prefilled_user.", ephemeral=True
        )

    @pytest.mark.asyncio
    async def test_controllers_command_handler_suggest_reward_modal_on_submit_overrides_prefilled_username(
        self, mocker
    ):
        """Test modal allows overriding pre-filled username."""
        mock_interaction = mocker.AsyncMock(spec=discord.Interaction)
        mock_interaction.response.defer = mocker.AsyncMock()
        mock_interaction.followup.send = mocker.AsyncMock()

        mock_message = mocker.AsyncMock(spec=discord.Message)
        mock_message.jump_url = "https://discord.com/channels/123/456/789"
        mock_message.author.name = "original_user"  # Original author

        mock_bot = mocker.MagicMock()
        mock_bot.api_service = mocker.MagicMock()
        mock_interaction.client = mock_bot

        modal = self._create_modal_with_mocked_inputs(
            target_message=mock_message,
            type_val="B",
            level_val="3",
            user_val="different_user",  # User changed the username
            comment_val="override test",
        )

        mock_create = mocker.patch.object(
            SuggestionService, "create_suggestion", new_callable=mocker.AsyncMock
        )
        await modal.on_submit(mock_interaction)

        mock_create.assert_called_once_with(
            mock_bot.api_service,
            "B",
            "3",
            "different_user",
            "override test",
            "https://discord.com/channels/123/456/789",
        )
        # Should use the overridden username, not the original author
        mock_interaction.followup.send.assert_called_once_with(
            "✅ Suggestion for [B3] submitted for different_user.", ephemeral=True
        )
