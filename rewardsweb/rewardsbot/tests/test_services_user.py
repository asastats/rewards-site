"""Unit tests for :py:mod:`rewardsbot.services.user` module.

This module contains tests for the UserService class and its
user summary generation functionality.
"""

from unittest import mock

import pytest

from rewardsbot.models.contribution import Contribution
from rewardsbot.services.user import UserService


class TestServicesUser:
    """Testing class for :py:mod:`rewardsbot.services.user` components."""

    # # UserService.user_summary
    @pytest.mark.asyncio
    async def test_services_user_user_summary_success(self, mocker):
        """Test user_summary returns formatted summary on success."""
        mock_api_service = mocker.AsyncMock()

        # Mock contributions data
        mock_contributions = [
            {
                "id": 100,
                "cycle_id": 5,
                "contributor_name": "test_user",
                "type": "[F] Forum Post",
                "level": 2,
                "url": "https://example.com/1",
                "reward": 1000,
                "confirmed": True,
            },
            {
                "id": 99,
                "cycle_id": 5,
                "contributor_name": "test_user",
                "type": "[B] Blog Post",
                "level": 1,
                "url": "https://example.com/2",
                "reward": 1500,
                "confirmed": False,
            },
            {
                "id": 98,
                "cycle_id": 5,
                "contributor_name": "test_user",
                "type": "[AT] Article Translation",
                "level": 3,
                "url": "https://example.com/3",
                "reward": 2000,
                "confirmed": True,
            },
        ]
        mock_api_service.fetch_user_contributions.return_value = mock_contributions

        # Mock cycle data for first contribution
        mock_cycle_data = {
            "id": 5,
            "start": "2024-01-01T00:00:00",
            "end": "2024-01-31T23:59:59Z",
            "contributor_rewards": {},
            "total_rewards": 0,
        }
        mock_api_service.fetch_cycle_by_id_plain.return_value = mock_cycle_data

        # Mock formatted contributions
        formatted_contributions = [
            "[F2](https://example.com/1) 1,000 ✅",
            "[B1](https://example.com/2) 1,500 ⍻",
            "[AT3](https://example.com/3) 2,000 ✅",
        ]

        with mock.patch.object(Contribution, "formatted_contributions") as mock_format:
            mock_format.side_effect = formatted_contributions

            result = await UserService.user_summary(mock_api_service, "test_user")

            # Verify API calls
            mock_api_service.fetch_user_contributions.assert_called_once_with(
                "test_user"
            )
            mock_api_service.fetch_cycle_by_id_plain.assert_called_once_with(5)

            # Verify summary content
            assert "**test_user**" in result
            assert "First contribution cycle: 2024/01" in result
            assert "Total contributions: 3" in result
            assert "Total rewards: 4,500" in result
            assert "Last contributions:" in result
            # Check that all formatted contributions are included
            for formatted in formatted_contributions:
                assert formatted in result

    @pytest.mark.asyncio
    async def test_services_user_user_summary_no_contributions(self, mocker):
        """Test user_summary returns message for user with no contributions."""
        mock_api_service = mocker.AsyncMock()
        mock_api_service.fetch_user_contributions.return_value = []

        result = await UserService.user_summary(mock_api_service, "inactive_user")

        mock_api_service.fetch_user_contributions.assert_called_once_with(
            "inactive_user"
        )
        mock_api_service.fetch_cycle_by_id_plain.assert_not_called()
        assert result == "No contributions for inactive_user."

    @pytest.mark.asyncio
    async def test_services_user_user_summary_empty_contributions_list(self, mocker):
        """Test user_summary returns message for empty contributions list."""
        mock_api_service = mocker.AsyncMock()
        mock_api_service.fetch_user_contributions.return_value = []

        result = await UserService.user_summary(mock_api_service, "empty_user")

        mock_api_service.fetch_user_contributions.assert_called_once_with("empty_user")
        mock_api_service.fetch_cycle_by_id_plain.assert_not_called()
        assert result == "No contributions for empty_user."

    @pytest.mark.asyncio
    async def test_services_user_user_summary_cycle_date_parsing(self, mocker):
        """Test user_summary handles cycle date parsing correctly."""
        mock_api_service = mocker.AsyncMock()

        mock_contributions = [
            {
                "id": 100,
                "cycle_id": 3,
                "contributor_name": "date_test_user",
                "type": "[F] Forum Post",
                "level": 1,
                "url": "https://example.com/1",
                "reward": 500,
                "confirmed": True,
            }
        ]
        mock_api_service.fetch_user_contributions.return_value = mock_contributions

        # Test with different date formats
        test_cases = [
            ("2024-03-15T23:59:59Z", "2024/03"),  # UTC with Z
            ("2024-12-31T23:59:59Z", "2024/12"),  # December
            ("2023-01-01T00:00:00Z", "2023/01"),  # January
        ]

        for end_date, expected_format in test_cases:
            mock_cycle_data = {
                "id": 3,
                "start": "2024-01-01T00:00:00",
                "end": end_date,
                "contributor_rewards": {},
                "total_rewards": 0,
            }
            mock_api_service.fetch_cycle_by_id_plain.return_value = mock_cycle_data

            with mock.patch.object(
                Contribution,
                "formatted_contributions",
                return_value="[F1](https://example.com/1) 500 ✅",
            ):
                result = await UserService.user_summary(
                    mock_api_service, "date_test_user"
                )

                assert f"First contribution cycle: {expected_format}" in result

            # Reset mock for next iteration
            mock_api_service.fetch_cycle_by_id_plain.reset_mock()

    @pytest.mark.asyncio
    async def test_services_user_user_summary_unknown_cycle_date(self, mocker):
        """Test user_summary handles missing cycle date."""
        mock_api_service = mocker.AsyncMock()

        mock_contributions = [
            {
                "id": 100,
                "cycle_id": 1,
                "contributor_name": "unknown_date_user",
                "type": "[F] Forum Post",
                "level": 1,
                "url": "https://example.com/1",
                "reward": 500,
                "confirmed": True,
            }
        ]
        mock_api_service.fetch_user_contributions.return_value = mock_contributions

        # Cycle data without end date
        mock_cycle_data = {
            "id": 1,
            "start": "2024-01-01T00:00:00",
            "end": None,  # Missing end date
            "contributor_rewards": {},
            "total_rewards": 0,
        }
        mock_api_service.fetch_cycle_by_id_plain.return_value = mock_cycle_data

        with mock.patch.object(
            Contribution,
            "formatted_contributions",
            return_value="[F1](https://example.com/1) 500 ✅",
        ):
            result = await UserService.user_summary(
                mock_api_service, "unknown_date_user"
            )

            mock_api_service.fetch_cycle_by_id_plain.assert_called_once_with(1)
            assert "First contribution cycle: Unknown" in result

    @pytest.mark.asyncio
    async def test_services_user_user_summary_many_contributions(self, mocker):
        """Test user_summary shows only last 5 contributions for users with many."""
        mock_api_service = mocker.AsyncMock()

        # Create 8 contributions
        mock_contributions = [
            {
                "id": i,
                "cycle_id": 5,
                "contributor_name": "active_user",
                "type": "[F] Forum Post",
                "level": 1,
                "url": f"https://example.com/{i}",
                "reward": 100 * i,
                "confirmed": True,
            }
            for i in range(1, 9)  # IDs 1 through 8
        ]
        mock_api_service.fetch_user_contributions.return_value = mock_contributions

        mock_cycle_data = {
            "id": 5,
            "start": "2024-01-01T00:00:00",
            "end": "2024-01-31T23:59:59Z",
            "contributor_rewards": {},
            "total_rewards": 0,
        }
        mock_api_service.fetch_cycle_by_id_plain.return_value = mock_cycle_data

        # Mock formatted contributions - should only be called for last 5 (highest IDs)
        formatted_contributions = [
            f"[F1](https://example.com/{i}) {100 * i:,} ✅"
            for i in range(8, 3, -1)  # IDs 8, 7, 6, 5, 4
        ]

        with mock.patch.object(Contribution, "formatted_contributions") as mock_format:
            mock_format.side_effect = formatted_contributions

            result = await UserService.user_summary(mock_api_service, "active_user")

            # Verify only last 5 contributions are formatted (sorted by ID descending)
            assert mock_format.call_count == 5
            # Should show total of 8 contributions
            assert "Total contributions: 8" in result
            # Total rewards should be sum of all 8 contributions
            assert "Total rewards: 3,600" in result  # 100*(1+2+3+4+5+6+7+8) = 3600

    @pytest.mark.asyncio
    async def test_services_user_user_summary_reward_calculation(self, mocker):
        """Test user_summary correctly calculates total rewards."""
        mock_api_service = mocker.AsyncMock()

        mock_contributions = [
            {
                "id": 1,
                "cycle_id": 5,
                "contributor_name": "reward_test_user",
                "type": "[F] Forum Post",
                "level": 1,
                "url": "https://example.com/1",
                "reward": 1000,
                "confirmed": True,
            },
            {
                "id": 2,
                "cycle_id": 5,
                "contributor_name": "reward_test_user",
                "type": "[B] Blog Post",
                "level": 2,
                "url": "https://example.com/2",
                "reward": 2000,
                "confirmed": True,
            },
            {
                "id": 3,
                "cycle_id": 5,
                "contributor_name": "reward_test_user",
                "type": "[AT] Article Translation",
                "level": 3,
                "url": "https://example.com/3",
                "reward": 3000,  # No reward field
                "confirmed": True,
            },
            {
                "id": 4,
                "cycle_id": 5,
                "contributor_name": "reward_test_user",
                "type": "[CT] Code Translation",
                "level": 1,
                "url": "https://example.com/4",
                "reward": 0,  # Zero reward
                "confirmed": False,
            },
        ]
        mock_api_service.fetch_user_contributions.return_value = mock_contributions

        mock_cycle_data = {
            "id": 5,
            "start": "2024-01-01T00:00:00",
            "end": "2024-01-31T23:59:59Z",
            "contributor_rewards": {},
            "total_rewards": 0,
        }
        mock_api_service.fetch_cycle_by_id_plain.return_value = mock_cycle_data

        with mock.patch.object(
            Contribution,
            "formatted_contributions",
            return_value="[F1](https://example.com/1) 1,000 ✅",
        ):
            result = await UserService.user_summary(
                mock_api_service, "reward_test_user"
            )

            # Total rewards should be 1000 + 2000 + 3000 + 0 = 6000
            assert "Total rewards: 6,000" in result
            assert "Total contributions: 4" in result

    @pytest.mark.asyncio
    async def test_services_user_user_summary_api_error(self, mocker):
        """Test user_summary returns error message on API exception."""
        mock_api_service = mocker.AsyncMock()
        mock_api_service.fetch_user_contributions.side_effect = Exception(
            "API unavailable"
        )

        with mock.patch("rewardsbot.services.user.logger") as mock_logger:
            result = await UserService.user_summary(mock_api_service, "error_user")

            mock_api_service.fetch_user_contributions.assert_called_once_with(
                "error_user"
            )
            mock_logger.error.assert_called_once_with(
                "❌ User Summary Error: API unavailable", exc_info=True
            )
            assert result == "❌ Failed to generate user summary for error_user."

    @pytest.mark.asyncio
    async def test_services_user_user_summary_cycle_api_error(self, mocker):
        """Test user_summary returns error message on cycle API exception."""
        mock_api_service = mocker.AsyncMock()

        mock_contributions = [
            {
                "id": 100,
                "cycle_id": 5,
                "contributor_name": "cycle_error_user",
                "type": "[F] Forum Post",
                "level": 1,
                "url": "https://example.com/1",
                "reward": 500,
                "confirmed": True,
            }
        ]
        mock_api_service.fetch_user_contributions.return_value = mock_contributions
        mock_api_service.fetch_cycle_by_id_plain.side_effect = Exception(
            "Cycle API error"
        )

        with mock.patch("rewardsbot.services.user.logger") as mock_logger:
            result = await UserService.user_summary(
                mock_api_service, "cycle_error_user"
            )

            mock_api_service.fetch_user_contributions.assert_called_once_with(
                "cycle_error_user"
            )
            mock_api_service.fetch_cycle_by_id_plain.assert_called_once_with(5)
            mock_logger.error.assert_called_once_with(
                "❌ User Summary Error: Cycle API error", exc_info=True
            )
            assert result == "❌ Failed to generate user summary for cycle_error_user."

    @pytest.mark.asyncio
    async def test_services_user_user_summary_contribution_formatting_error(
        self, mocker
    ):
        """Test user_summary returns error message on contribution formatting error."""
        mock_api_service = mocker.AsyncMock()

        mock_contributions = [
            {
                "id": 100,
                "cycle_id": 5,
                "contributor_name": "format_error_user",
                "type": "[F] Forum Post",
                "level": 1,
                "url": "https://example.com/1",
                "reward": 500,
                "confirmed": True,
            }
        ]
        mock_api_service.fetch_user_contributions.return_value = mock_contributions

        mock_cycle_data = {
            "id": 5,
            "start": "2024-01-01T00:00:00",
            "end": "2024-01-31T23:59:59Z",
            "contributor_rewards": {},
            "total_rewards": 0,
        }
        mock_api_service.fetch_cycle_by_id_plain.return_value = mock_cycle_data

        with mock.patch.object(
            Contribution,
            "formatted_contributions",
            side_effect=Exception("Formatting error"),
        ), mock.patch("rewardsbot.services.user.logger") as mock_logger:

            result = await UserService.user_summary(
                mock_api_service, "format_error_user"
            )

            mock_api_service.fetch_user_contributions.assert_called_once_with(
                "format_error_user"
            )
            mock_api_service.fetch_cycle_by_id_plain.assert_called_once_with(5)
            mock_logger.error.assert_called_once_with(
                "❌ User Summary Error: Formatting error", exc_info=True
            )
            assert result == "❌ Failed to generate user summary for format_error_user."

    @pytest.mark.asyncio
    async def test_services_user_user_summary_special_characters_username(self, mocker):
        """Test user_summary handles special characters in username."""
        mock_api_service = mocker.AsyncMock()
        mock_api_service.fetch_user_contributions.return_value = []

        special_usernames = [
            "User-With-Dash",
            "User_With_Underscore",
            "User.With.Dots",
            "User With Spaces",
            "User123",
            "User@Special",
        ]

        for username in special_usernames:
            result = await UserService.user_summary(mock_api_service, username)

            mock_api_service.fetch_user_contributions.assert_called_with(username)
            assert f"No contributions for {username}." in result

            # Reset mock for next iteration
            mock_api_service.fetch_user_contributions.reset_mock()

    @pytest.mark.asyncio
    async def test_services_user_user_summary_contribution_ordering(self, mocker):
        """Test user_summary orders contributions by ID descending."""
        mock_api_service = mocker.AsyncMock()

        # Contributions with mixed ID order
        mock_contributions = [
            {
                "id": 50,
                "cycle_id": 5,
                "contributor_name": "ordering_user",
                "type": "[F] Forum Post",
                "level": 1,
                "url": "https://example.com/50",
                "reward": 500,
                "confirmed": True,
            },
            {
                "id": 100,
                "cycle_id": 5,
                "contributor_name": "ordering_user",
                "type": "[B] Blog Post",
                "level": 2,
                "url": "https://example.com/100",
                "reward": 1000,
                "confirmed": True,
            },
            {
                "id": 75,
                "cycle_id": 5,
                "contributor_name": "ordering_user",
                "type": "[AT] Article Translation",
                "level": 3,
                "url": "https://example.com/75",
                "reward": 1500,
                "confirmed": True,
            },
        ]
        mock_api_service.fetch_user_contributions.return_value = mock_contributions

        mock_cycle_data = {
            "id": 5,
            "start": "2024-01-01T00:00:00",
            "end": "2024-01-31T23:59:59Z",
            "contributor_rewards": {},
            "total_rewards": 0,
        }
        mock_api_service.fetch_cycle_by_id_plain.return_value = mock_cycle_data

        # Track the order in which contributions are processed
        processed_ids = []

        def mock_formatted_contributions(is_user_summary):
            # Get the Contribution instance from the call
            # We need to access the self parameter to get the contribution data
            # Since we can't easily access self from here, we'll use a different approach

            # Instead, we'll track the calls and extract the IDs from the call arguments
            # This is a bit hacky but works for testing purposes
            import inspect

            frame = inspect.currentframe()
            # Look back in the call stack to find the contribution data
            # This is fragile but works for this specific test
            for i in range(10):  # Look back up to 10 frames
                try:
                    frame = frame.f_back
                    local_vars = frame.f_locals
                    if "contribution" in local_vars:
                        contribution_data = local_vars["contribution"]
                        processed_ids.append(contribution_data["id"])
                        break
                except:
                    break

            return f"Formatted contribution"

        # Create a more sophisticated mock that can track the contribution data
        original_formatted_contributions = Contribution.formatted_contributions

        def tracking_formatted_contributions(self, is_user_summary):
            processed_ids.append(self.id)
            return f"Formatted {self.id}"

        with mock.patch.object(
            Contribution, "formatted_contributions", tracking_formatted_contributions
        ):
            await UserService.user_summary(mock_api_service, "ordering_user")

            # Verify contributions are processed in descending ID order: 100, 75, 50
            assert processed_ids == [100, 75, 50]

    @pytest.mark.asyncio
    async def test_services_user_user_summary_contribution_ordering_simple(
        self, mocker
    ):
        """Test user_summary orders contributions by ID descending - simpler approach."""
        mock_api_service = mocker.AsyncMock()

        # Contributions with mixed ID order
        mock_contributions = [
            {
                "id": 50,
                "cycle_id": 5,
                "contributor_name": "ordering_user",
                "type": "[F] Forum Post",
                "level": 1,
                "url": "https://example.com/50",
                "reward": 500,
                "confirmed": True,
            },
            {
                "id": 100,
                "cycle_id": 5,
                "contributor_name": "ordering_user",
                "type": "[B] Blog Post",
                "level": 2,
                "url": "https://example.com/100",
                "reward": 1000,
                "confirmed": True,
            },
            {
                "id": 75,
                "cycle_id": 5,
                "contributor_name": "ordering_user",
                "type": "[AT] Article Translation",
                "level": 3,
                "url": "https://example.com/75",
                "reward": 1500,
                "confirmed": True,
            },
        ]
        mock_api_service.fetch_user_contributions.return_value = mock_contributions

        mock_cycle_data = {
            "id": 5,
            "start": "2024-01-01T00:00:00",
            "end": "2024-01-31T23:59:59Z",
            "contributor_rewards": {},
            "total_rewards": 0,
        }
        mock_api_service.fetch_cycle_by_id_plain.return_value = mock_cycle_data

        # Track the creation of Contribution objects to see the order
        created_contributions = []
        original_init = Contribution.__init__

        def tracking_init(self, data):
            created_contributions.append(data["id"])
            original_init(self, data)

        with mock.patch.object(
            Contribution, "__init__", tracking_init
        ), mock.patch.object(
            Contribution,
            "formatted_contributions",
            return_value="Formatted contribution",
        ):

            await UserService.user_summary(mock_api_service, "ordering_user")

            # The contributions should be sorted by ID descending before being processed
            # So we should see them in order: 100, 75, 50
            assert created_contributions == [100, 75, 50]
