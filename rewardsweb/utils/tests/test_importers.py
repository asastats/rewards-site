"""Testing module for :py:mod:`utils.importers` module."""

from datetime import datetime, timedelta

import pandas as pd
import pytest
from django.core.exceptions import ObjectDoesNotExist
from django.db.utils import IntegrityError
from django.http import Http404

import utils.importers
from core.models import RewardType
from utils.importers import (
    CONTRIBUTION_CSV_COLUMNS,
    REWARDS_COLLECTION,
    _append_gaps_to_cycles_dataframe,
    _check_current_cycle,
    _create_active_rewards,
    _create_superusers,
    _dataframe_from_csv,
    _import_contributions,
    _import_rewards,
    _parse_addresses,
    _parse_label_and_name_from_reward_type,
    _parse_label_and_name_from_reward_type_legacy,
    _reward_amount,
    _reward_amount_legacy,
    import_from_csv,
)


class TestUtilsImportersConstants:
    """Testing class for :class:`utils.importers` constants."""

    @pytest.mark.parametrize(
        "constant,value",
        [
            ("ADDRESSES_CSV_COLUMNS", ["handle", "address"]),
            (
                "CONTRIBUTION_CSV_COLUMNS",
                [
                    "contributor",
                    "cycle_start",
                    "cycle_end",
                    "platform",
                    "url",
                    "type",
                    "level",
                    "percentage",
                    "reward",
                    "comment",
                ],
            ),
        ],
    )
    def test_utils_importers_module_constants(self, constant, value):
        assert getattr(utils.importers, constant) == value


class TestUtilsImportersHelperFunctions:
    """Testing class for :py:mod:`utils.importers` helper functions."""

    def test_utils_importers_append_gaps_to_cycles_dataframe_no_gaps(self):
        """Test when there are no gaps between cycles."""
        df = pd.DataFrame(
            {
                "cycle_start": ["2023-01-01", "2023-01-11", "2023-01-21"],
                "cycle_end": ["2023-01-10", "2023-01-20", "2023-01-30"],
            }
        )

        result = _append_gaps_to_cycles_dataframe(df)

        # Should return the same dataframe (no gaps added)
        expected = pd.DataFrame(
            {
                "cycle_start": ["2023-01-01", "2023-01-11", "2023-01-21"],
                "cycle_end": ["2023-01-10", "2023-01-20", "2023-01-30"],
            }
        )
        pd.testing.assert_frame_equal(result, expected)

    def test_utils_importers_append_gaps_to_cycles_dataframe_with_gaps(self):
        """Test when there are gaps between cycles."""
        df = pd.DataFrame(
            {
                "cycle_start": ["2023-01-01", "2023-01-15"],
                "cycle_end": ["2023-01-10", "2023-01-25"],
            }
        )

        result = _append_gaps_to_cycles_dataframe(df)

        # Should add one gap period between Jan 11-14
        expected = pd.DataFrame(
            {
                "cycle_start": ["2023-01-01", "2023-01-11", "2023-01-15"],
                "cycle_end": ["2023-01-10", "2023-01-14", "2023-01-25"],
            }
        )
        pd.testing.assert_frame_equal(result, expected)

    def test_utils_importers_append_gaps_to_cycles_dataframe_multiple_gaps(self):
        """Test when there are multiple gaps between cycles."""
        df = pd.DataFrame(
            {
                "cycle_start": ["2023-01-01", "2023-01-11", "2023-01-21"],
                "cycle_end": ["2023-01-05", "2023-01-15", "2023-01-25"],
            }
        )

        result = _append_gaps_to_cycles_dataframe(df)

        # Should add two gap periods: Jan 6-10 and Jan 16-20
        expected = pd.DataFrame(
            {
                "cycle_start": [
                    "2023-01-01",
                    "2023-01-06",
                    "2023-01-11",
                    "2023-01-16",
                    "2023-01-21",
                ],
                "cycle_end": [
                    "2023-01-05",
                    "2023-01-10",
                    "2023-01-15",
                    "2023-01-20",
                    "2023-01-25",
                ],
            }
        )
        pd.testing.assert_frame_equal(result, expected)

    def test_utils_importers_append_gaps_to_cycles_dataframe_single_row(self):
        """Test with single row dataframe (no gaps possible)."""
        df = pd.DataFrame({"cycle_start": ["2023-01-01"], "cycle_end": ["2023-01-10"]})

        result = _append_gaps_to_cycles_dataframe(df)

        # Should return the same single row
        expected = pd.DataFrame(
            {"cycle_start": ["2023-01-01"], "cycle_end": ["2023-01-10"]}
        )
        pd.testing.assert_frame_equal(result, expected)

    def test_utils_importers_append_gaps_to_cycles_dataframe_empty_dataframe(self):
        """Test with empty dataframe."""
        df = pd.DataFrame(columns=["cycle_start", "cycle_end"])

        result = _append_gaps_to_cycles_dataframe(df)

        # Should return empty dataframe
        expected = pd.DataFrame(columns=["cycle_start", "cycle_end"])
        pd.testing.assert_frame_equal(result, expected)

    def test_utils_importers_append_gaps_to_cycles_dataframe_overlapping_cycles(self):
        """Test with overlapping cycles (should not create gaps)."""
        df = pd.DataFrame(
            {
                "cycle_start": ["2023-01-01", "2023-01-05"],
                "cycle_end": ["2023-01-10", "2023-01-15"],
            }
        )

        result = _append_gaps_to_cycles_dataframe(df)

        # Should return original cycles (no gaps due to overlap)
        expected = pd.DataFrame(
            {
                "cycle_start": ["2023-01-01", "2023-01-05"],
                "cycle_end": ["2023-01-10", "2023-01-15"],
            }
        )
        pd.testing.assert_frame_equal(result, expected)

    def test_utils_importers_append_gaps_to_cycles_dataframe_consecutive_dates(self):
        """Test with cycles ending and starting on consecutive dates (no gap)."""
        df = pd.DataFrame(
            {
                "cycle_start": ["2023-01-01", "2023-01-11"],
                "cycle_end": ["2023-01-10", "2023-01-20"],
            }
        )

        result = _append_gaps_to_cycles_dataframe(df)

        # Should return original cycles (no gap since dates are consecutive)
        expected = pd.DataFrame(
            {
                "cycle_start": ["2023-01-01", "2023-01-11"],
                "cycle_end": ["2023-01-10", "2023-01-20"],
            }
        )
        pd.testing.assert_frame_equal(result, expected)

    def test_utils_importers_append_gaps_to_cycles_dataframe_unsorted_input(self):
        """Test that function sorts unsorted input correctly."""
        df = pd.DataFrame(
            {
                "cycle_start": ["2023-02-01", "2023-01-01", "2023-03-01"],
                "cycle_end": ["2023-02-10", "2023-01-10", "2023-03-10"],
            }
        )

        result = _append_gaps_to_cycles_dataframe(df)

        # Should sort by cycle_start and identify gaps
        expected = pd.DataFrame(
            {
                "cycle_start": [
                    "2023-01-01",
                    "2023-01-11",
                    "2023-02-01",
                    "2023-02-11",
                    "2023-03-01",
                ],
                "cycle_end": [
                    "2023-01-10",
                    "2023-01-31",
                    "2023-02-10",
                    "2023-02-28",
                    "2023-03-10",
                ],
            }
        )
        pd.testing.assert_frame_equal(result, expected)

    def test_utils_importers_append_gaps_to_cycles_dataframe_preserves_original_data(
        self,
    ):
        """Test that original cycle data is preserved in the result."""
        df = pd.DataFrame(
            {
                "cycle_start": ["2023-01-01", "2023-01-20"],
                "cycle_end": ["2023-01-10", "2023-01-30"],
            }
        )

        result = _append_gaps_to_cycles_dataframe(df)

        # Check that original cycles are present
        original_cycle_1 = result[
            (result["cycle_start"] == "2023-01-01")
            & (result["cycle_end"] == "2023-01-10")
        ]
        original_cycle_2 = result[
            (result["cycle_start"] == "2023-01-20")
            & (result["cycle_end"] == "2023-01-30")
        ]

        assert len(original_cycle_1) == 1
        assert len(original_cycle_2) == 1

        # Check that gap is present
        gap = result[
            (result["cycle_start"] == "2023-01-11")
            & (result["cycle_end"] == "2023-01-19")
        ]
        assert len(gap) == 1

    # # _check_current_cycle
    def test_utils_importers_check_current_cycle_creates_new_cycle(self, mocker):
        cycle_instance = mocker.MagicMock()
        cycle_instance.end = datetime.now().date() - timedelta(days=1)

        mocked_cycle_create = mocker.patch("utils.importers.Cycle.objects.create")
        mocked_datetime = mocker.patch("utils.importers.datetime")
        mocked_datetime.now.return_value.date.return_value = datetime.now().date()

        _check_current_cycle(cycle_instance)

        mocked_cycle_create.assert_called_once()

    def test_utils_importers_check_current_cycle_no_new_cycle(self, mocker):
        cycle_instance = mocker.MagicMock()
        cycle_instance.end = datetime.now().date() + timedelta(days=1)

        mocked_cycle_create = mocker.patch("utils.importers.Cycle.objects.create")
        mocked_datetime = mocker.patch("utils.importers.datetime")
        mocked_datetime.now.return_value.date.return_value = datetime.now().date()

        _check_current_cycle(cycle_instance)

        mocked_cycle_create.assert_not_called()

    def test_utils_importers_check_current_cycle_today_is_end_date(self, mocker):
        """Test _check_current_cycle when today is the end date."""
        cycle_instance = mocker.MagicMock()
        # Set end date to today
        cycle_instance.end = datetime.now().date()

        mocked_cycle_create = mocker.patch("utils.importers.Cycle.objects.create")
        mocked_datetime = mocker.patch("utils.importers.datetime")
        mocked_datetime.now.return_value.date.return_value = datetime.now().date()

        _check_current_cycle(cycle_instance)

        # Should not create new cycle since today is not after end date
        mocked_cycle_create.assert_not_called()

    # # _create_active_rewards
    def test_utils_importers_create_active_rewards(self, mocker):
        mocked_get_object_or_404 = mocker.patch("utils.importers.get_object_or_404")

        rewards = [mocker.MagicMock() for _ in range(len(REWARDS_COLLECTION) * 3)]
        rewards[1] = ObjectDoesNotExist("rwd1")
        rewards[7] = ObjectDoesNotExist("rwd5")
        mocked_reward_get = mocker.patch(
            "utils.importers.Reward.objects.get", side_effect=rewards
        )
        mocked_reward_create = mocker.patch("utils.importers.Reward.objects.create")
        reward_type = mocker.MagicMock()
        mocked_get_object_or_404.return_value = reward_type

        _create_active_rewards()

        assert mocked_get_object_or_404.call_count == len(REWARDS_COLLECTION) * 3
        assert mocked_reward_get.call_count == len(REWARDS_COLLECTION) * 3
        calls = [
            mocker.call(type=reward_type, level=2, amount=60000, active=True),
            mocker.call(type=reward_type, level=2, amount=70000, active=True),
        ]
        mocked_reward_create.assert_has_calls(calls, any_order=True)
        assert mocked_reward_create.call_count == 2

    def test_utils_importers_create_active_rewards_no_existing_rewards(self, mocker):
        """Test _create_active_rewards when no rewards exist."""
        mocked_get_object_or_404 = mocker.patch("utils.importers.get_object_or_404")
        reward_type = mocker.MagicMock()

        # All Reward.objects.get calls raise ObjectDoesNotExist (no existing rewards)
        mocker.patch(
            "utils.importers.Reward.objects.get",
            side_effect=ObjectDoesNotExist("No reward found"),
        )
        mocked_reward_create = mocker.patch("utils.importers.Reward.objects.create")
        mocked_get_object_or_404.return_value = reward_type

        _create_active_rewards()

        # Should create all rewards from REWARDS_COLLECTION
        total_expected_rewards = sum(len(reward) - 1 for reward in REWARDS_COLLECTION)
        assert mocked_reward_create.call_count == total_expected_rewards

    def test_utils_importers_create_active_rewards_all_exist(self, mocker):
        """Test _create_active_rewards when all rewards already exist."""
        mocked_get_object_or_404 = mocker.patch("utils.importers.get_object_or_404")
        reward_type = mocker.MagicMock()
        existing_reward = mocker.MagicMock()

        # All Reward.objects.get calls return existing rewards
        mocker.patch(
            "utils.importers.Reward.objects.get",
            return_value=existing_reward,
        )
        mocked_reward_create = mocker.patch("utils.importers.Reward.objects.create")
        mocked_reward_save = mocker.patch.object(existing_reward, "save")
        mocked_get_object_or_404.return_value = reward_type

        _create_active_rewards()

        # Should activate all existing rewards but not create new ones
        mocked_reward_create.assert_not_called()
        assert mocked_reward_save.call_count == sum(
            len(reward) - 1 for reward in REWARDS_COLLECTION
        )

    # # _create_superusers
    def test_utils_importers_create_superusers(self, mocker):
        """Test _create_superusers with all data provided."""
        mocked_get_env_variable = mocker.patch("utils.importers.get_env_variable")
        # Use valid Algorand addresses (58 characters)
        mocked_get_env_variable.side_effect = [
            "user1,user2",
            "pass1,pass2",
            "A" * 58 + "," + "B" * 58,  # Two valid addresses
        ]

        mocked_user_create = mocker.patch(
            "utils.importers.User.objects.create_superuser"
        )
        mocked_contributor_filter = mocker.patch(
            "utils.importers.Contributor.objects.filter"
        )
        mocked_contributor_create = mocker.patch(
            "utils.importers.Contributor.objects.from_full_handle"
        )

        # Mock user and profile
        mock_user1 = mocker.MagicMock()
        mock_user1.username = "user1"
        mock_user1.profile = mocker.MagicMock()
        mock_user2 = mocker.MagicMock()
        mock_user2.username = "user2"
        mock_user2.profile = mocker.MagicMock()
        mocked_user_create.side_effect = [mock_user1, mock_user2]

        # Mock contributor queries - no existing contributors
        mocked_contributor_filter.return_value.first.return_value = None

        _create_superusers()

        assert mocked_user_create.call_count == 2
        mocked_user_create.assert_any_call("user1", password="pass1")
        mocked_user_create.assert_any_call("user2", password="pass2")

        # Verify contributor creation was attempted for both users
        assert mocked_contributor_create.call_count == 2
        mocked_contributor_create.assert_any_call("user1", address="A" * 58)
        mocked_contributor_create.assert_any_call("user2", address="B" * 58)

        # Verify profiles were saved
        assert mock_user1.profile.save.call_count == 1
        assert mock_user2.profile.save.call_count == 1

    def test_utils_importers_create_superusers_empty_env_vars(self, mocker):
        """Test _create_superusers with empty environment variables."""
        # Mock get_env_variable to return empty strings
        mocker.patch("utils.importers.get_env_variable", return_value="")

        mocked_user_create = mocker.patch(
            "utils.importers.User.objects.create_superuser"
        )
        mocked_contributor_create = mocker.patch(
            "utils.importers.Contributor.objects.from_full_handle"
        )

        _create_superusers()

        # Should not create any users since empty strings are filtered out
        mocked_user_create.assert_not_called()
        mocked_contributor_create.assert_not_called()

    def test_utils_importers_create_superusers_single_user(self, mocker):
        """Test _create_superusers with single user."""
        mocker.patch(
            "utils.importers.get_env_variable",
            side_effect=["user1", "pass1", "A" * 58],  # Valid address
        )

        mocked_user_create = mocker.patch(
            "utils.importers.User.objects.create_superuser"
        )
        mocked_contributor_filter = mocker.patch(
            "utils.importers.Contributor.objects.filter"
        )
        mocked_contributor_create = mocker.patch(
            "utils.importers.Contributor.objects.from_full_handle"
        )

        # Mock user and profile
        mock_user = mocker.MagicMock()
        mock_user.username = "user1"
        mock_user.profile = mocker.MagicMock()
        mocked_user_create.return_value = mock_user

        # Mock contributor query - no existing contributor
        mocked_contributor_filter.return_value.first.return_value = None

        _create_superusers()

        # Should create one user
        mocked_user_create.assert_called_once_with("user1", password="pass1")
        mocked_contributor_create.assert_called_once_with("user1", address="A" * 58)
        mock_user.profile.save.assert_called_once()

    def test_utils_importers_create_superusers_mismatched_user_password_lengths(
        self, mocker
    ):
        """Test _create_superusers with mismatched user/password counts."""
        mocker.patch(
            "utils.importers.get_env_variable",
            side_effect=["user1,user2", "pass1", "A" * 58 + "," + "B" * 58],
        )

        with pytest.raises(AssertionError):
            _create_superusers()

    def test_utils_importers_create_superusers_with_existing_contributor(self, mocker):
        """Test _create_superusers when contributor already exists."""
        mocker.patch(
            "utils.importers.get_env_variable",
            side_effect=["user1", "pass1", "A" * 58],  # Valid address
        )

        mocked_user_create = mocker.patch(
            "utils.importers.User.objects.create_superuser"
        )
        mocked_contributor_filter = mocker.patch(
            "utils.importers.Contributor.objects.filter"
        )
        mocked_contributor_create = mocker.patch(
            "utils.importers.Contributor.objects.from_full_handle"
        )

        # Mock user and profile
        mock_user = mocker.MagicMock()
        mock_user.username = "user1"
        mock_user.profile = mocker.MagicMock()
        mocked_user_create.return_value = mock_user

        # Mock existing contributor
        mock_contributor = mocker.MagicMock()
        mocked_contributor_filter.return_value.first.return_value = mock_contributor

        _create_superusers()

        mocked_user_create.assert_called_once_with("user1", password="pass1")
        # Should not create new contributor since one exists
        mocked_contributor_create.assert_not_called()
        # Should link existing contributor to user profile
        assert mock_user.profile.contributor == mock_contributor
        mock_user.profile.save.assert_called_once()

    def test_utils_importers_create_superusers_no_addresses(self, mocker):
        """Test _create_superusers when no addresses are provided."""
        mocker.patch(
            "utils.importers.get_env_variable",
            side_effect=["user1,user2", "pass1,pass2", ""],  # Empty addresses
        )

        mocked_user_create = mocker.patch(
            "utils.importers.User.objects.create_superuser"
        )
        mocked_contributor_filter = mocker.patch(
            "utils.importers.Contributor.objects.filter"
        )
        mocked_contributor_create = mocker.patch(
            "utils.importers.Contributor.objects.from_full_handle"
        )

        # Mock users
        mock_user1 = mocker.MagicMock()
        mock_user1.username = "user1"
        mock_user1.profile = mocker.MagicMock()
        mock_user2 = mocker.MagicMock()
        mock_user2.username = "user2"
        mock_user2.profile = mocker.MagicMock()
        mocked_user_create.side_effect = [mock_user1, mock_user2]

        _create_superusers()

        assert mocked_user_create.call_count == 2
        mocked_user_create.assert_any_call("user1", password="pass1")
        mocked_user_create.assert_any_call("user2", password="pass2")

        # Should not create any contributors when no addresses provided
        mocked_contributor_filter.assert_not_called()
        mocked_contributor_create.assert_not_called()

        # Profiles should not be saved since no contributor linking occurred
        mock_user1.profile.save.assert_not_called()
        mock_user2.profile.save.assert_not_called()

    def test_utils_importers_create_superusers_different_address_count(self, mocker):
        """Test _create_superusers with different number of addresses than users."""
        mocker.patch(
            "utils.importers.get_env_variable",
            side_effect=[
                "user1,user2",
                "pass1,pass2",
                "A" * 58,  # Only one address for two users
            ],
        )

        with pytest.raises(AssertionError):
            _create_superusers()

    def test_utils_importers_create_superusers_empty_address_string(self, mocker):
        """Test _create_superusers with empty address string (not None)."""
        mocker.patch(
            "utils.importers.get_env_variable",
            side_effect=["user1", "pass1", ""],  # Empty address string
        )

        mocked_user_create = mocker.patch(
            "utils.importers.User.objects.create_superuser"
        )
        mocked_contributor_filter = mocker.patch(
            "utils.importers.Contributor.objects.filter"
        )
        mocked_contributor_create = mocker.patch(
            "utils.importers.Contributor.objects.from_full_handle"
        )

        # Mock user
        mock_user = mocker.MagicMock()
        mock_user.username = "user1"
        mock_user.profile = mocker.MagicMock()
        mocked_user_create.return_value = mock_user

        _create_superusers()

        mocked_user_create.assert_called_once_with("user1", password="pass1")
        # Should not attempt to create/link contributor when addresses list is empty
        mocked_contributor_filter.assert_not_called()
        mocked_contributor_create.assert_not_called()
        mock_user.profile.save.assert_not_called()

    def test_utils_importers_create_superusers_address_length_exactly_50(self, mocker):
        """Test _create_superusers with addresses exactly 50 characters long (should be filtered out)."""
        mocker.patch(
            "utils.importers.get_env_variable",
            side_effect=[
                "user1",
                "pass1",
                "A" * 50,  # Exactly 50 characters - should be filtered out
            ],
        )

        mocked_user_create = mocker.patch(
            "utils.importers.User.objects.create_superuser"
        )
        mocked_contributor_filter = mocker.patch(
            "utils.importers.Contributor.objects.filter"
        )
        mocked_contributor_create = mocker.patch(
            "utils.importers.Contributor.objects.from_full_handle"
        )

        # Mock user
        mock_user = mocker.MagicMock()
        mock_user.username = "user1"
        mock_user.profile = mocker.MagicMock()
        mocked_user_create.return_value = mock_user

        _create_superusers()

        mocked_user_create.assert_called_once_with("user1", password="pass1")
        # Should not create contributor since address is filtered out (length <= 50)
        mocked_contributor_filter.assert_not_called()
        mocked_contributor_create.assert_not_called()
        mock_user.profile.save.assert_not_called()

    def test_utils_importers_create_superusers_address_length_51(self, mocker):
        """Test _create_superusers with addresses 51 characters long (should be included)."""
        mocker.patch(
            "utils.importers.get_env_variable",
            side_effect=[
                "user1",
                "pass1",
                "A" * 51,  # 51 characters - should be included
            ],
        )

        mocked_user_create = mocker.patch(
            "utils.importers.User.objects.create_superuser"
        )
        mocked_contributor_filter = mocker.patch(
            "utils.importers.Contributor.objects.filter"
        )
        mocked_contributor_create = mocker.patch(
            "utils.importers.Contributor.objects.from_full_handle"
        )

        # Mock user and profile
        mock_user = mocker.MagicMock()
        mock_user.username = "user1"
        mock_user.profile = mocker.MagicMock()
        mocked_user_create.return_value = mock_user

        # Mock contributor query - no existing contributor
        mocked_contributor_filter.return_value.first.return_value = None

        _create_superusers()

        mocked_user_create.assert_called_once_with("user1", password="pass1")
        # Should create contributor since address length > 50
        mocked_contributor_create.assert_called_once_with("user1", address="A" * 51)
        mock_user.profile.save.assert_called_once()

    def test_utils_importers_create_superusers_whitespace_addresses_length_check(
        self, mocker
    ):
        """Test _create_superusers with whitespace addresses that might pass length check."""
        mocker.patch(
            "utils.importers.get_env_variable",
            side_effect=[
                "user1",
                "pass1",
                " "
                * 51,  # 51 whitespace characters - should be included by length check
            ],
        )

        mocked_user_create = mocker.patch(
            "utils.importers.User.objects.create_superuser"
        )
        mocked_contributor_filter = mocker.patch(
            "utils.importers.Contributor.objects.filter"
        )
        mocked_contributor_create = mocker.patch(
            "utils.importers.Contributor.objects.from_full_handle"
        )

        # Mock user and profile
        mock_user = mocker.MagicMock()
        mock_user.username = "user1"
        mock_user.profile = mocker.MagicMock()
        mocked_user_create.return_value = mock_user

        # Mock contributor query - no existing contributor
        mocked_contributor_filter.return_value.first.return_value = None

        _create_superusers()

        mocked_user_create.assert_called_once_with("user1", password="pass1")
        # Should create contributor since address length > 50 (even though it's whitespace)
        mocked_contributor_create.assert_called_once_with("user1", address=" " * 51)
        mock_user.profile.save.assert_called_once()

    # # _dataframe_from_csv
    def test_utils_importers_dataframe_from_csv_success(self, mocker):
        mock_dataframe = pd.DataFrame(
            {
                "contributor": ["user1", "user2"],
                "cycle_start": ["2023-01-01", "2023-01-01"],
                "cycle_end": ["2023-01-31", "2023-01-31"],
                "platform": ["GitHub", "Discord"],
                "url": ["https://example.com", None],
                "type": ["[F] Feature", "[B] Bug"],
                "level": [1, 2],
                "percentage": [100.0, 50.0],
                "reward": [1000, 500],
                "comment": ["Test comment", None],
            }
        )

        mocked_pd_read_csv = mocker.patch("utils.importers.pd.read_csv")
        mocked_pd_read_csv.return_value = mock_dataframe

        result = _dataframe_from_csv("test.csv")

        mocked_pd_read_csv.assert_called_once_with("test.csv", header=None, sep=",")
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2

    def test_utils_importers_dataframe_from_csv_file_not_found(self, mocker):
        mocked_pd_read_csv = mocker.patch("utils.importers.pd.read_csv")
        mocked_pd_read_csv.side_effect = FileNotFoundError

        result = _dataframe_from_csv("nonexistent.csv")

        assert result is None

    def test_utils_importers_dataframe_from_csv_empty_data(self, mocker):
        mocked_pd_read_csv = mocker.patch("utils.importers.pd.read_csv")
        mocked_pd_read_csv.side_effect = pd.errors.EmptyDataError

        result = _dataframe_from_csv("empty.csv")

        assert result is None

    # # _import_contributions
    def test_utils_importers_import_contributions(self, mocker):
        # Create real DataFrame
        mock_data = pd.DataFrame(
            [
                {
                    "contributor": "testuser",
                    "cycle_start": "2023-01-01",
                    "platform": "GitHub",
                    "type": "[F] Feature",
                    "level": 1,
                    "reward": 1000,
                    "percentage": 50.0,
                    "url": "https://example.com",
                    "comment": "Test comment",
                }
            ]
        )

        mocked_contributor = mocker.MagicMock()
        mocked_cycle = mocker.MagicMock()
        mocked_platform = mocker.MagicMock()
        mocked_reward_type = mocker.MagicMock()
        mocked_reward = mocker.MagicMock()

        mocked_contributor_from_handle = mocker.patch(
            "utils.importers.Contributor.objects.from_full_handle"
        )
        mocked_contributor_from_handle.return_value = mocked_contributor

        mocked_cycle_get = mocker.patch("utils.importers.Cycle.objects.get")
        mocked_cycle_get.return_value = mocked_cycle

        mocked_platform_get = mocker.patch("utils.importers.SocialPlatform.objects.get")
        mocked_platform_get.return_value = mocked_platform

        mocked_parse_callback = mocker.MagicMock(return_value=("F", "Feature"))
        mocked_get_object_or_404 = mocker.patch("utils.importers.get_object_or_404")
        mocked_get_object_or_404.return_value = mocked_reward_type

        mocked_reward_get = mocker.patch("utils.importers.Reward.objects.get")
        mocked_reward_get.return_value = mocked_reward

        mocked_amount_callback = mocker.MagicMock(return_value=1000000)
        mocked_contribution_create = mocker.patch(
            "utils.importers.Contribution.objects.create"
        )

        _import_contributions(mock_data, mocked_parse_callback, mocked_amount_callback)

        mocked_contributor_from_handle.assert_called_once_with("testuser")
        mocked_cycle_get.assert_called_once_with(start="2023-01-01")
        mocked_platform_get.assert_called_once_with(name__iexact="GitHub")
        mocked_parse_callback.assert_called_once_with("[F] Feature")
        mocked_get_object_or_404.assert_called_once_with(
            RewardType, label="F", name="Feature"
        )
        mocked_reward_get.assert_called_once_with(
            type=mocked_reward_type, level=1, amount=1000000
        )
        mocked_contribution_create.assert_called_once()

    def test_utils_importers_import_contributions_handles_missing_values(self, mocker):
        """Test _import_contributions handles missing values correctly."""
        # Create real DataFrame with missing values
        mock_data = pd.DataFrame(
            [
                {
                    "contributor": "testuser",
                    "cycle_start": "2023-01-01",
                    "platform": "GitHub",
                    "type": "[F] Feature",
                    "level": float("nan"),  # Missing level
                    "reward": 1000,
                    "percentage": float("nan"),  # Missing percentage
                    "url": float("nan"),  # Missing URL
                    "comment": float("nan"),  # Missing comment
                }
            ]
        )

        mocked_contributor = mocker.MagicMock()
        mocked_cycle = mocker.MagicMock()
        mocked_platform = mocker.MagicMock()
        mocked_reward_type = mocker.MagicMock()
        mocked_reward = mocker.MagicMock()

        mocker.patch(
            "utils.importers.Contributor.objects.from_full_handle",
            return_value=mocked_contributor,
        )
        mocker.patch("utils.importers.Cycle.objects.get", return_value=mocked_cycle)
        mocker.patch(
            "utils.importers.SocialPlatform.objects.get", return_value=mocked_platform
        )
        mocker.patch(
            "utils.importers._parse_label_and_name_from_reward_type",
            return_value=("F", "Feature"),
        )
        mocker.patch(
            "utils.importers.get_object_or_404", return_value=mocked_reward_type
        )
        mocker.patch("utils.importers.Reward.objects.get", return_value=mocked_reward)
        mocker.patch("utils.importers._reward_amount", return_value=1000000)
        mocked_contribution_create = mocker.patch(
            "utils.importers.Contribution.objects.create"
        )

        _import_contributions(
            mock_data,
            _parse_label_and_name_from_reward_type,
            _reward_amount,
        )

        # Verify default values are used for missing data
        mocked_contribution_create.assert_called_once()
        call_kwargs = mocked_contribution_create.call_args[1]
        assert call_kwargs["percentage"] == 1  # Default for missing percentage
        assert call_kwargs["url"] is None  # Default for missing URL
        assert call_kwargs["comment"] is None  # Default for missing comment

    def test_utils_importers_import_contributions_multiple_rows(self, mocker):
        """Test _import_contributions processes multiple rows correctly."""
        # Create real DataFrame with multiple rows
        mock_data = pd.DataFrame(
            [
                {
                    "contributor": "user1",
                    "cycle_start": "2023-01-01",
                    "platform": "GitHub",
                    "type": "[F] Feature",
                    "level": 1,
                    "reward": 1000,
                    "percentage": 100.0,
                    "url": "https://example.com/1",
                    "comment": "Comment 1",
                },
                {
                    "contributor": "user2",
                    "cycle_start": "2023-02-01",
                    "platform": "Discord",
                    "type": "[B] Bug",
                    "level": 2,
                    "reward": 500,
                    "percentage": 50.0,
                    "url": None,
                    "comment": "Comment 2",
                },
            ]
        )

        mocked_contributor = mocker.MagicMock()
        mocked_cycle = mocker.MagicMock()
        mocked_platform = mocker.MagicMock()
        mocked_reward_type = mocker.MagicMock()
        mocked_reward = mocker.MagicMock()

        mocker.patch(
            "utils.importers.Contributor.objects.from_full_handle",
            return_value=mocked_contributor,
        )
        mocker.patch("utils.importers.Cycle.objects.get", return_value=mocked_cycle)
        mocker.patch(
            "utils.importers.SocialPlatform.objects.get", return_value=mocked_platform
        )
        mocker.patch(
            "utils.importers._parse_label_and_name_from_reward_type",
            return_value=("F", "Feature"),
        )
        mocker.patch(
            "utils.importers.get_object_or_404", return_value=mocked_reward_type
        )
        mocker.patch("utils.importers.Reward.objects.get", return_value=mocked_reward)
        mocker.patch("utils.importers._reward_amount", return_value=1000000)
        mocked_contribution_create = mocker.patch(
            "utils.importers.Contribution.objects.create"
        )

        _import_contributions(
            mock_data,
            _parse_label_and_name_from_reward_type,
            _reward_amount,
        )

        # Verify create was called twice (once for each row)
        assert mocked_contribution_create.call_count == 2

    # _import_rewards
    def test_utils_importers_import_rewards_new_type(self, mocker):
        # Create real DataFrame
        mock_data = pd.DataFrame(
            {"type": ["[F] Feature"], "level": [1], "reward": [1000]}
        )

        mocked_parse_callback = mocker.MagicMock(return_value=("F", "Feature"))
        mocked_amount_callback = mocker.MagicMock(return_value=1000000)
        mocked_get_object_or_404 = mocker.patch("utils.importers.get_object_or_404")
        mocked_get_object_or_404.side_effect = Http404

        mocked_reward_type_create = mocker.patch(
            "utils.importers.RewardType.objects.create"
        )
        mocked_reward_create = mocker.patch("utils.importers.Reward.objects.create")

        _import_rewards(mock_data, mocked_parse_callback, mocked_amount_callback)

        mocked_reward_type_create.assert_called_once_with(label="F", name="Feature")
        mocked_reward_create.assert_called_once()

    def test_utils_importers_import_rewards_existing_type(self, mocker):
        # Create real DataFrame
        mock_data = pd.DataFrame(
            {"type": ["[F] Feature"], "level": [1], "reward": [1000]}
        )

        mocked_parse_callback = mocker.MagicMock(return_value=("F", "Feature"))
        mocked_amount_callback = mocker.MagicMock(return_value=1000000)
        mocked_reward_type = mocker.MagicMock()

        mocked_get_object_or_404 = mocker.patch("utils.importers.get_object_or_404")
        mocked_get_object_or_404.return_value = mocked_reward_type

        mocked_reward_create = mocker.patch("utils.importers.Reward.objects.create")

        _import_rewards(mock_data, mocked_parse_callback, mocked_amount_callback)

        mocked_get_object_or_404.assert_called_once_with(
            RewardType, label="F", name="Feature"
        )
        mocked_reward_create.assert_called_once()

    def test_utils_importers_import_rewards_for_integrity_error(self, mocker):
        # Create real DataFrame
        mock_data = pd.DataFrame(
            {"type": ["[F] Feature"], "level": [1], "reward": [1000]}
        )

        mocked_parse_callback = mocker.MagicMock(return_value=("F", "Feature"))
        mocked_amount_callback = mocker.MagicMock(return_value=1000000)
        mocked_reward_type = mocker.MagicMock()

        mocked_get_object_or_404 = mocker.patch("utils.importers.get_object_or_404")
        mocked_get_object_or_404.return_value = mocked_reward_type

        mocker.patch(
            "utils.importers.Reward.objects.create",
            side_effect=IntegrityError("error"),
        )

        _import_rewards(mock_data, mocked_parse_callback, mocked_amount_callback)

    def test_utils_importers_import_rewards_handles_missing_level(self, mocker):
        """Test _import_rewards handles missing level values."""
        # Create real DataFrame with missing level
        mock_data = pd.DataFrame(
            {"type": ["[F] Feature"], "level": [float("nan")], "reward": [1000]}
        )

        mocked_parse_callback = mocker.MagicMock(return_value=("F", "Feature"))
        mocked_amount_callback = mocker.MagicMock(return_value=1000000)
        mocked_reward_type = mocker.MagicMock()

        mocker.patch(
            "utils.importers.get_object_or_404", return_value=mocked_reward_type
        )
        mocked_reward_create = mocker.patch("utils.importers.Reward.objects.create")

        _import_rewards(mock_data, mocked_parse_callback, mocked_amount_callback)

        # Verify default level (1) is used
        mocked_reward_create.assert_called_once()
        call_kwargs = mocked_reward_create.call_args[1]
        assert call_kwargs["level"] == 1

    def test_utils_importers_import_rewards_multiple_rows(self, mocker):
        """Test _import_rewards processes multiple rows correctly."""
        # Create real DataFrame with multiple rows
        mock_data = pd.DataFrame(
            {
                "type": ["[F] Feature", "[B] Bug", "[S] Suggestion"],
                "level": [1, 2, 3],
                "reward": [1000, 500, 200],
            }
        )

        mocked_parse_callback = mocker.MagicMock(
            side_effect=[("F", "Feature"), ("B", "Bug"), ("S", "Suggestion")]
        )
        mocked_amount_callback = mocker.MagicMock(side_effect=[1000000, 500000, 200000])
        mocked_reward_type = mocker.MagicMock()

        mocker.patch(
            "utils.importers.get_object_or_404", return_value=mocked_reward_type
        )
        mocked_reward_create = mocker.patch("utils.importers.Reward.objects.create")

        _import_rewards(mock_data, mocked_parse_callback, mocked_amount_callback)

        # Verify create was called three times
        assert mocked_reward_create.call_count == 3

    def test_utils_importers_import_rewards_creates_new_reward_types(self, mocker):
        """Test _import_rewards creates new reward types when needed."""
        # Create real DataFrame
        mock_data = pd.DataFrame(
            {"type": ["[NEW] New Type"], "level": [1], "reward": [1000]}
        )

        mocked_parse_callback = mocker.MagicMock(return_value=("NEW", "New Type"))
        mocked_amount_callback = mocker.MagicMock(return_value=1000000)

        # Mock get_object_or_404 to raise Http404 (reward type doesn't exist)
        mocker.patch(
            "utils.importers.get_object_or_404", side_effect=Http404("Not found")
        )
        mocked_reward_type_create = mocker.patch(
            "utils.importers.RewardType.objects.create"
        )
        mocked_reward_create = mocker.patch("utils.importers.Reward.objects.create")

        _import_rewards(mock_data, mocked_parse_callback, mocked_amount_callback)

        # Verify new reward type was created
        mocked_reward_type_create.assert_called_once_with(label="NEW", name="New Type")
        mocked_reward_create.assert_called_once()

    # # _parse_addresses
    def test_utils_importers_parse_addresses_file_not_found(self, mocker):
        mocked_dataframe_from_csv = mocker.patch("utils.importers._dataframe_from_csv")
        # Mock both calls to return None to simulate file not found
        mocked_dataframe_from_csv.return_value = None

        result = _parse_addresses()

        assert result == []

    def test_utils_importers_parse_addresses_success_with_both_files(self, mocker):
        # Create test data for addresses
        addresses_data = pd.DataFrame(
            {
                "handle": ["handle1", "handle2", "handle3", "handle1"],
                "address": ["addr1", "addr1", "addr2", "addr1"],
            }
        )

        # Create test data for users
        users_data = pd.DataFrame(
            {
                "handle": ["handle4", "handle5"],
                "address": ["addr1", "addr3"],
            }
        )

        mocked_dataframe_from_csv = mocker.patch("utils.importers._dataframe_from_csv")
        # Mock the first call to return addresses data, second call to return users data
        mocked_dataframe_from_csv.side_effect = [addresses_data, users_data]

        result = _parse_addresses()

        # Expected result after combining both dataframes and grouping
        # Note: handles are reversed within each address group
        expected = [
            ["addr1", ["handle4", "handle2", "handle1"]],
            ["addr2", ["handle3"]],
            ["addr3", ["handle5"]],
        ]
        assert result == expected

    def test_utils_importers_parse_addresses_success_users_file_not_found(self, mocker):
        # Create test data for addresses
        addresses_data = pd.DataFrame(
            {
                "handle": ["handle1", "handle2", "handle3", "handle1"],
                "address": ["addr1", "addr1", "addr2", "addr1"],
            }
        )

        mocked_dataframe_from_csv = mocker.patch("utils.importers._dataframe_from_csv")
        # Mock first call to return addresses data, second call to return None (users file not found)
        mocked_dataframe_from_csv.side_effect = [addresses_data, None]

        result = _parse_addresses()

        # Expected result using only addresses data (same as original test)
        expected = [["addr1", ["handle2", "handle1"]], ["addr2", ["handle3"]]]
        assert result == expected

    def test_utils_importers_parse_addresses_both_files_empty(self, mocker):
        # Create empty dataframes
        empty_addresses = pd.DataFrame(columns=["handle", "address"])
        empty_users = pd.DataFrame(columns=["handle", "address"])

        mocked_dataframe_from_csv = mocker.patch("utils.importers._dataframe_from_csv")
        mocked_dataframe_from_csv.side_effect = [empty_addresses, empty_users]

        result = _parse_addresses()

        # Expected empty result
        expected = []
        assert result == expected

    def test_utils_importers_parse_addresses_handles_duplicates(self, mocker):
        """Test _parse_addresses handles duplicate handle-address pairs."""
        # Create test data with duplicates
        addresses_data = pd.DataFrame(
            {
                "handle": ["handle1", "handle1", "handle2", "handle2"],
                "address": ["addr1", "addr1", "addr2", "addr2"],
            }
        )

        mocker.patch(
            "utils.importers._dataframe_from_csv",
            side_effect=[addresses_data, None],  # No users file
        )

        result = _parse_addresses()

        # Should remove duplicates and reverse handles
        expected = [["addr1", ["handle1"]], ["addr2", ["handle2"]]]
        assert result == expected

    def test_utils_importers_parse_addresses_empty_dataframes(self, mocker):
        """Test _parse_addresses with empty dataframes."""
        empty_df = pd.DataFrame(columns=["handle", "address"])

        mocker.patch(
            "utils.importers._dataframe_from_csv",
            side_effect=[empty_df, empty_df],
        )

        result = _parse_addresses()

        assert result == []

    def test_utils_importers_parse_addresses_only_users_file(self, mocker):
        """Test _parse_addresses when only users file exists."""
        users_data = pd.DataFrame(
            {
                "handle": ["user1", "user2"],
                "address": ["addr1", "addr2"],
            }
        )

        mocked_dataframe_from_csv = mocker.patch("utils.importers._dataframe_from_csv")
        # Mock the first call (addresses) to return None, second call (users) to return data
        mocked_dataframe_from_csv.side_effect = [None, users_data]

        result = _parse_addresses()

        # When addresses file is None but users file exists, should use users data
        expected = [["addr1", ["user1"]], ["addr2", ["user2"]]]
        assert result == expected

    # # _parse_label_and_name_from_reward_type
    def test_utils_importers_parse_label_and_name_from_reward_type_standard(
        self,
    ):
        result = _parse_label_and_name_from_reward_type("[F] Feature Request")

        assert result == ("F", "Feature Request")

    def test_utils_importers_parse_label_and_name_from_reward_type_custom(self):
        result = _parse_label_and_name_from_reward_type("Custom Type")

        assert result == ("CST", "Custom")

    def test_utils_importers_parse_label_and_name_from_reward_type_nan(self):
        result = _parse_label_and_name_from_reward_type(float("nan"))

        assert result == ("CST", "Custom")

    def test_utils_importers_parse_label_and_name_from_reward_type_empty_string(self):
        """Test _parse_label_and_name_from_reward_type with empty string."""
        result = _parse_label_and_name_from_reward_type("")

        assert result == ("CST", "Custom")

    def test_utils_importers_parse_label_and_name_from_reward_type_none(self):
        """Test _parse_label_and_name_from_reward_type with None."""
        result = _parse_label_and_name_from_reward_type(None)

        assert result == ("CST", "Custom")

    def test_utils_importers_parse_label_and_name_from_reward_type_no_brackets(self):
        """Test _parse_label_and_name_from_reward_type without brackets."""
        result = _parse_label_and_name_from_reward_type("Feature Request")

        assert result == ("CST", "Custom")

    def test_utils_importers_parse_label_and_name_from_reward_type_malformed(self):
        """Test _parse_label_and_name_from_reward_type with malformed input."""
        result = _parse_label_and_name_from_reward_type("[F Feature")

        assert result == ("CST", "Custom")

    # # _parse_label_and_name_from_reward_type_legacy
    def test_utils_importers_parse_label_and_name_from_reward_type_legacy_f(
        self,
    ):
        result = _parse_label_and_name_from_reward_type_legacy("feature request custom")

        assert result == ("F", "Feature Request")

    def test_utils_importers_parse_label_and_name_from_reward_type_legacy_bug(
        self,
    ):
        result = _parse_label_and_name_from_reward_type_legacy("bug report custom")

        assert result == ("B", "Bug Report")

    def test_utils_importers_parse_label_and_name_from_reward_type_legacy_r(
        self,
    ):
        result = _parse_label_and_name_from_reward_type_legacy(
            "ecosystem research custom"
        )

        assert result == ("ER", "Ecosystem Research")

    def test_utils_importers_parse_label_and_name_from_reward_type_legacy_s(
        self,
    ):
        result = _parse_label_and_name_from_reward_type_legacy("something custom")

        assert result == ("S", "Suggestion")

    def test_utils_importers_parse_label_and_name_from_reward_type_legacy(
        self,
    ):
        result = _parse_label_and_name_from_reward_type_legacy("[F] Feature Request")

        assert result == ("F", "Feature Request")

    def test_utils_importers_parse_label_and_name_from_reward_type_legacy_empty(self):
        """Test _parse_label_and_name_from_reward_type_legacy with empty string."""
        result = _parse_label_and_name_from_reward_type_legacy("")

        # Empty string should fall through to "Suggestion" in legacy parser
        assert result == ("S", "Suggestion")

    def test_utils_importers_parse_label_and_name_from_reward_type_legacy_none(self):
        """Test _parse_label_and_name_from_reward_type_legacy with None."""
        # None should be handled by the base function and return ("CST", "Custom")
        # but then legacy logic converts "Custom" to "Suggestion"
        result = _parse_label_and_name_from_reward_type_legacy(None)

        assert result == ("S", "Suggestion")

    def test_utils_importers_parse_label_and_name_from_reward_type_legacy_case_insensitive(
        self,
    ):
        """Test _parse_label_and_name_from_reward_type_legacy is case insensitive."""
        # The legacy function converts to lowercase for comparison
        result1 = _parse_label_and_name_from_reward_type_legacy("Feature Request")
        result2 = _parse_label_and_name_from_reward_type_legacy("FEATURE REQUEST")
        result3 = _parse_label_and_name_from_reward_type_legacy("feature request")

        # All should match "feature request" pattern
        assert result1 == ("F", "Feature Request")
        assert result2 == ("F", "Feature Request")
        assert result3 == ("F", "Feature Request")

    def test_utils_importers_parse_label_and_name_from_reward_type_legacy_priority(
        self,
    ):
        """Test _parse_label_and_name_from_reward_type_legacy priority of patterns."""
        # Should match "feature request" first
        result = _parse_label_and_name_from_reward_type_legacy(
            "feature request and bug report"
        )

        assert result == ("F", "Feature Request")

    # # _reward_amount
    def test_utils_importers_reward_amount_normal(self):
        result = _reward_amount(1.5)

        assert result == 1500000

    def test_utils_importers_reward_amount_nan(self):
        result = _reward_amount(float("nan"))

        assert result == 0

    def test_utils_importers_reward_amount_zero(self):
        """Test _reward_amount with zero value."""
        result = _reward_amount(0)

        assert result == 0

    def test_utils_importers_reward_amount_negative(self):
        """Test _reward_amount with negative value."""
        result = _reward_amount(-1.5)

        assert result == -1500000

    def test_utils_importers_reward_amount_decimal_precision(self):
        """Test _reward_amount with decimal precision."""
        result = _reward_amount(1.234567)

        assert result == 1234567  # Should round to nearest integer

    def test_utils_importers_reward_amount_none(self):
        """Test _reward_amount with None."""
        result = _reward_amount(None)

        assert result == 0

    # # _reward_amount_legacy
    def test_utils_importers_reward_amount_legacy_normal(self):
        result = _reward_amount_legacy(1.5)

        assert result == 1500000

    def test_utils_importers_reward_amount_legacy_nan(self):
        result = _reward_amount_legacy(float("nan"))

        assert result == 0

    def test_utils_importers_reward_amount_legacy_zero(self):
        """Test _reward_amount_legacy with zero value."""
        result = _reward_amount_legacy(0)

        assert result == 0

    def test_utils_importers_reward_amount_legacy_negative(self):
        """Test _reward_amount_legacy with negative value."""
        result = _reward_amount_legacy(-1.5)

        assert result == -1500000

    def test_utils_importers_reward_amount_legacy_rounding(self):
        """Test _reward_amount_legacy rounding behavior."""
        result = _reward_amount_legacy(1.234567)

        # Should first round to 2 decimal places (1.23), then multiply
        assert result == 1230000

    def test_utils_importers_reward_amount_legacy_none(self):
        """Test _reward_amount_legacy with None."""
        result = _reward_amount_legacy(None)

        assert result == 0


class TestUtilsImportersPublicFunctions:
    """Testing class for :py:mod:`utils.importers` main functions."""

    # # import_from_csv
    @pytest.mark.django_db
    def test_utils_importers_import_from_csv_database_not_empty(self, mocker):
        # Mock the exact condition that triggers early return
        # The function checks: if len(SocialPlatform.objects.all()):
        mock_social_platforms = mocker.MagicMock()
        mock_social_platforms.__len__ = mocker.MagicMock(return_value=1)

        # Patch SocialPlatform.objects.all to return our mock with length 1
        mocker.patch(
            "utils.importers.SocialPlatform.objects.all",
            return_value=mock_social_platforms,
        )

        # Call the function - it should return early with error message
        result = import_from_csv("contributions.csv", "legacy.csv")

        # Verify the function returned early with error message
        assert result == "ERROR: Database is not empty!"

    @pytest.mark.django_db
    def test_utils_importers_import_from_csv_success(self, mocker):
        # Mock empty database check - return empty queryset
        mock_social_platforms = mocker.MagicMock()
        mock_social_platforms.__len__ = mocker.MagicMock(return_value=0)
        mocker.patch(
            "utils.importers.SocialPlatform.objects.all",
            return_value=mock_social_platforms,
        )

        # Mock all dependencies with proper return values
        mocker.patch(
            "utils.importers.social_platform_prefixes",
            return_value=[("Discord", ""), ("GitHub", "g@")],
        )
        mocker.patch("utils.importers.SocialPlatform.objects.bulk_create")

        # Mock addresses parsing
        mocker.patch(
            "utils.importers._parse_addresses",
            return_value=[("ADDRESS1", "handle1"), ("ADDRESS2", "handle2")],
        )

        # Mock Contributor creation
        mocker.patch("utils.importers.Contributor.objects.bulk_create")

        # Mock Handle creation completely to avoid database issues
        mocker.patch("utils.importers.Handle.objects.from_address_and_full_handle")

        # Mock DataFrame creation with real DataFrames
        mock_data = pd.DataFrame(
            {
                "contributor": ["user1"],
                "cycle_start": ["2023-01-01"],
                "cycle_end": ["2023-01-31"],
                "platform": ["GitHub"],
                "url": ["https://example.com"],
                "type": ["[F] Feature"],
                "level": [1],
                "percentage": [100.0],
                "reward": [1000],
                "comment": ["Test comment"],
            }
        )
        mock_legacy_data = pd.DataFrame(
            {
                "contributor": ["user2"],
                "cycle_start": ["2022-12-01"],
                "cycle_end": ["2022-12-31"],
                "platform": ["Discord"],
                "url": [None],
                "type": ["[B] Bug"],
                "level": [2],
                "percentage": [50.0],
                "reward": [500],
                "comment": [None],
            }
        )
        mocker.patch(
            "utils.importers._dataframe_from_csv",
            side_effect=[mock_data, mock_legacy_data],
        )

        mocker.patch("utils.importers.Cycle.objects.bulk_create")

        mock_latest_cycle = mocker.MagicMock()
        mock_latest_cycle.end = datetime.now().date() + timedelta(days=1)
        mocker.patch(
            "utils.importers.Cycle.objects.latest",
            return_value=mock_latest_cycle,
        )

        mocker.patch("utils.importers._check_current_cycle")
        mocker.patch("utils.importers._import_rewards")
        mocker.patch("utils.importers._create_active_rewards")
        mocker.patch("utils.importers._import_contributions")
        mocker.patch("utils.importers._create_superusers")

        result = import_from_csv("contributions.csv", "legacy.csv")

        assert result is False

    @pytest.mark.django_db
    def test_utils_importers_import_from_csv_saves_handles(self, mocker):
        # Mock empty database check - return empty queryset
        mock_social_platforms = mocker.MagicMock()
        mock_social_platforms.__len__ = mocker.MagicMock(return_value=0)
        mocker.patch(
            "utils.importers.SocialPlatform.objects.all",
            return_value=mock_social_platforms,
        )

        # Mock all dependencies with proper return values
        mocker.patch(
            "utils.importers.social_platform_prefixes",
            return_value=[("Discord", ""), ("GitHub", "g@")],
        )
        mocker.patch("utils.importers.SocialPlatform.objects.bulk_create")

        # Mock addresses parsing
        mocker.patch(
            "utils.importers._parse_addresses",
            return_value=[
                ("ADDRESS1", ["handle1", "handle1b"]),
                ("ADDRESS2", ["handle2"]),
            ],
        )

        # Mock Contributor creation
        mocker.patch("utils.importers.Contributor.objects.bulk_create")

        # Mock Handle creation completely to avoid database issues
        handle1, handle2, handle3 = (
            mocker.MagicMock(),
            mocker.MagicMock(),
            mocker.MagicMock(),
        )
        mocked_handle = mocker.patch(
            "utils.importers.Handle.objects.from_address_and_full_handle",
            side_effect=[handle1, handle2, handle3],
        )

        # Mock DataFrame creation with real DataFrames
        mock_data = pd.DataFrame(
            {
                "contributor": ["user1"],
                "cycle_start": ["2023-01-01"],
                "cycle_end": ["2023-01-31"],
                "platform": ["GitHub"],
                "url": ["https://example.com"],
                "type": ["[F] Feature"],
                "level": [1],
                "percentage": [100.0],
                "reward": [1000],
                "comment": ["Test comment"],
            }
        )
        mock_legacy_data = pd.DataFrame(
            {
                "contributor": ["user2"],
                "cycle_start": ["2022-12-01"],
                "cycle_end": ["2022-12-31"],
                "platform": ["Discord"],
                "url": [None],
                "type": ["[B] Bug"],
                "level": [2],
                "percentage": [50.0],
                "reward": [500],
                "comment": [None],
            }
        )
        mocker.patch(
            "utils.importers._dataframe_from_csv",
            side_effect=[mock_data, mock_legacy_data],
        )

        mocker.patch("utils.importers.Cycle.objects.bulk_create")

        mock_latest_cycle = mocker.MagicMock()
        mock_latest_cycle.end = datetime.now().date() + timedelta(days=1)
        mocker.patch(
            "utils.importers.Cycle.objects.latest",
            return_value=mock_latest_cycle,
        )

        mocker.patch("utils.importers._check_current_cycle")
        mocker.patch("utils.importers._import_rewards")
        mocker.patch("utils.importers._create_active_rewards")
        mocker.patch("utils.importers._import_contributions")
        mocker.patch("utils.importers._create_superusers")

        result = import_from_csv("contributions.csv", "legacy.csv")

        calls = [
            mocker.call("ADDRESS1", "handle1"),
            mocker.call("ADDRESS1", "handle1b"),
            mocker.call("ADDRESS2", "handle2"),
        ]
        mocked_handle.assert_has_calls(calls, any_order=True)
        assert mocked_handle.call_count == 3
        handle1.save.assert_called_once_with()
        handle2.save.assert_called_once_with()
        handle3.save.assert_called_once_with()

        assert result is False

    @pytest.mark.django_db
    def test_utils_importers_import_from_csv_creates_social_platforms(self, mocker):
        # Mock empty database check
        mock_social_platforms = mocker.MagicMock()
        mock_social_platforms.__len__ = mocker.MagicMock(return_value=0)
        mocker.patch(
            "utils.importers.SocialPlatform.objects.all",
            return_value=mock_social_platforms,
        )

        # Mock social platforms data
        mock_platforms_data = [("Discord", ""), ("GitHub", "g@"), ("Twitter", "t@")]
        mocker.patch(
            "utils.importers.social_platform_prefixes",
            return_value=mock_platforms_data,
        )

        # Mock bulk_create to capture what's being created
        mock_bulk_create = mocker.patch(
            "utils.importers.SocialPlatform.objects.bulk_create"
        )

        # Create proper mock DataFrames with all required columns
        mock_data = pd.DataFrame(
            {
                "cycle_start": ["2023-01-01"],
                "cycle_end": ["2023-01-31"],
                "type": ["[F] Feature"],
                "level": [1],
                "reward": [1000],
            }
        )
        mock_legacy_data = pd.DataFrame(
            {
                "cycle_start": ["2022-12-01"],
                "cycle_end": ["2022-12-31"],
                "type": ["[B] Bug"],
                "level": [2],
                "reward": [500],
            }
        )

        # Mock other dependencies minimally
        mocker.patch("utils.importers._parse_addresses", return_value=[])
        mocker.patch("utils.importers.Contributor.objects.bulk_create")
        mocker.patch("utils.importers.Handle.objects.from_address_and_full_handle")
        mocker.patch(
            "utils.importers._dataframe_from_csv",
            side_effect=[mock_data, mock_legacy_data],
        )
        mocker.patch("utils.importers.Cycle.objects.bulk_create")
        mocker.patch("utils.importers.Cycle.objects.latest")
        mocker.patch("utils.importers._check_current_cycle")
        mocker.patch("utils.importers._import_rewards")
        mocker.patch("utils.importers._create_active_rewards")
        mocker.patch("utils.importers._import_contributions")
        mocker.patch("utils.importers._create_superusers")

        result = import_from_csv("contributions.csv", "legacy.csv")

        # Verify SocialPlatform.objects.bulk_create was called with the correct generator
        mock_bulk_create.assert_called_once()
        call_args = mock_bulk_create.call_args[0][
            0
        ]  # Get the generator passed to bulk_create
        created_platforms = list(call_args)  # Convert generator to list to inspect

        assert len(created_platforms) == len(mock_platforms_data)
        for i, (name, prefix) in enumerate(mock_platforms_data):
            assert created_platforms[i].name == name
            assert created_platforms[i].prefix == prefix

        assert result is False

    @pytest.mark.django_db
    def test_utils_importers_import_from_csv_creates_contributors(self, mocker):
        # Mock empty database check
        mock_social_platforms = mocker.MagicMock()
        mock_social_platforms.__len__ = mocker.MagicMock(return_value=0)
        mocker.patch(
            "utils.importers.SocialPlatform.objects.all",
            return_value=mock_social_platforms,
        )

        # Mock platforms
        mocker.patch(
            "utils.importers.social_platform_prefixes",
            return_value=[("Discord", ""), ("GitHub", "g@")],
        )
        mocker.patch("utils.importers.SocialPlatform.objects.bulk_create")

        # Mock addresses parsing with multiple contributors
        mock_addresses = [
            ("0x1234567890abcdef", ["alice", "alice_gh"]),
            ("0xfedcba0987654321", ["bob"]),
            ("0xabcdef1234567890", ["charlie", "charlie_discord", "charlie_twitter"]),
        ]
        mocker.patch(
            "utils.importers._parse_addresses",
            return_value=mock_addresses,
        )

        # Mock Contributor bulk_create to capture what's being created
        mock_contributor_bulk_create = mocker.patch(
            "utils.importers.Contributor.objects.bulk_create"
        )

        # Mock Handle creation
        mocker.patch("utils.importers.Handle.objects.from_address_and_full_handle")

        # Create proper mock DataFrames with all required columns
        mock_data = pd.DataFrame(
            {
                "cycle_start": ["2023-01-01"],
                "cycle_end": ["2023-01-31"],
                "type": ["[F] Feature"],
                "level": [1],
                "reward": [1000],
            }
        )
        mock_legacy_data = pd.DataFrame(
            {
                "cycle_start": ["2022-12-01"],
                "cycle_end": ["2022-12-31"],
                "type": ["[B] Bug"],
                "level": [2],
                "reward": [500],
            }
        )
        mocker.patch(
            "utils.importers._dataframe_from_csv",
            side_effect=[mock_data, mock_legacy_data],
        )

        mocker.patch("utils.importers.Cycle.objects.bulk_create")
        mocker.patch("utils.importers.Cycle.objects.latest")
        mocker.patch("utils.importers._check_current_cycle")
        mocker.patch("utils.importers._import_rewards")
        mocker.patch("utils.importers._create_active_rewards")
        mocker.patch("utils.importers._import_contributions")
        mocker.patch("utils.importers._create_superusers")

        result = import_from_csv("contributions.csv", "legacy.csv")

        # Verify Contributor.objects.bulk_create was called with the correct generator
        mock_contributor_bulk_create.assert_called_once()
        call_args = mock_contributor_bulk_create.call_args[0][0]
        created_contributors = list(call_args)

        assert len(created_contributors) == len(mock_addresses)
        for i, (address, handles) in enumerate(mock_addresses):
            assert created_contributors[i].address == address
            assert (
                created_contributors[i].name == handles[0]
            )  # First handle is used as name

        assert result is False

    @pytest.mark.django_db
    def test_utils_importers_import_from_csv_creates_cycles(self, mocker):
        # Mock empty database check
        mock_social_platforms = mocker.MagicMock()
        mock_social_platforms.__len__ = mocker.MagicMock(return_value=0)
        mocker.patch(
            "utils.importers.SocialPlatform.objects.all",
            return_value=mock_social_platforms,
        )

        # Mock basic dependencies
        mocker.patch("utils.importers.social_platform_prefixes")
        mocker.patch("utils.importers.SocialPlatform.objects.bulk_create")
        mocker.patch("utils.importers._parse_addresses", return_value=[])
        mocker.patch("utils.importers.Contributor.objects.bulk_create")
        mocker.patch("utils.importers.Handle.objects.from_address_and_full_handle")

        # Mock DataFrame creation with cycle data - include all required columns
        mock_data = pd.DataFrame(
            {
                "cycle_start": ["2023-01-01", "2023-02-01"],
                "cycle_end": ["2023-01-31", "2023-02-28"],
                "type": ["[F] Feature", "[B] Bug"],
                "level": [1, 2],
                "reward": [1000, 500],
            }
        )
        mock_legacy_data = pd.DataFrame(
            {
                "cycle_start": ["2022-12-01"],
                "cycle_end": ["2022-12-31"],
                "type": ["[F] Feature"],
                "level": [1],
                "reward": [800],
            }
        )
        mocker.patch(
            "utils.importers._dataframe_from_csv",
            side_effect=[mock_data, mock_legacy_data],
        )

        # Mock Cycle bulk_create to capture what's being created
        mock_cycle_bulk_create = mocker.patch(
            "utils.importers.Cycle.objects.bulk_create"
        )

        # Mock latest cycle check
        mock_latest_cycle = mocker.MagicMock()
        mock_latest_cycle.end = datetime.now().date() + timedelta(days=1)
        mocker.patch(
            "utils.importers.Cycle.objects.latest",
            return_value=mock_latest_cycle,
        )
        mock_check_current_cycle = mocker.patch("utils.importers._check_current_cycle")

        # Mock remaining dependencies
        mocker.patch("utils.importers._import_rewards")
        mocker.patch("utils.importers._create_active_rewards")
        mocker.patch("utils.importers._import_contributions")
        mocker.patch("utils.importers._create_superusers")

        result = import_from_csv("contributions.csv", "legacy.csv")

        # Verify Cycle.objects.bulk_create was called with the correct cycles
        mock_cycle_bulk_create.assert_called_once()
        call_args = mock_cycle_bulk_create.call_args[0][0]
        created_cycles = list(call_args)

        # Should have 3 unique cycles (2 from mock_data, 1 from mock_legacy_data)
        expected_cycles = [
            ("2022-12-01", "2022-12-31"),
            ("2023-01-01", "2023-01-31"),
            ("2023-02-01", "2023-02-28"),
        ]

        assert len(created_cycles) == len(expected_cycles)
        for i, (start, end) in enumerate(expected_cycles):
            assert str(created_cycles[i].start) == start
            assert str(created_cycles[i].end) == end

        # Verify _check_current_cycle was called with the latest cycle
        mock_check_current_cycle.assert_called_once_with(mock_latest_cycle)

        assert result is False

    @pytest.mark.django_db
    def test_utils_importers_import_from_csv_calls_reward_functions(self, mocker):
        # Mock empty database check
        mock_social_platforms = mocker.MagicMock()
        mock_social_platforms.__len__ = mocker.MagicMock(return_value=0)
        mocker.patch(
            "utils.importers.SocialPlatform.objects.all",
            return_value=mock_social_platforms,
        )

        # Mock basic dependencies
        mocker.patch("utils.importers.social_platform_prefixes")
        mocker.patch("utils.importers.SocialPlatform.objects.bulk_create")
        mocker.patch("utils.importers._parse_addresses", return_value=[])
        mocker.patch("utils.importers.Contributor.objects.bulk_create")
        mocker.patch("utils.importers.Handle.objects.from_address_and_full_handle")

        # Mock DataFrame creation with all required columns
        mock_data = pd.DataFrame(
            {
                "type": ["[F] Feature"],
                "level": [1],
                "reward": [1000],
                "cycle_start": ["2023-01-01"],
                "cycle_end": ["2023-01-31"],
            }
        )
        mock_legacy_data = pd.DataFrame(
            {
                "type": ["[B] Bug"],
                "level": [2],
                "reward": [500],
                "cycle_start": ["2022-12-01"],
                "cycle_end": ["2022-12-31"],
            }
        )
        mocker.patch(
            "utils.importers._dataframe_from_csv",
            side_effect=[mock_data, mock_legacy_data],
        )

        mocker.patch("utils.importers.Cycle.objects.bulk_create")
        mocker.patch("utils.importers.Cycle.objects.latest")
        mocker.patch("utils.importers._check_current_cycle")

        # Mock reward functions to verify they're called correctly
        mock_import_rewards = mocker.patch("utils.importers._import_rewards")
        mock_create_active_rewards = mocker.patch(
            "utils.importers._create_active_rewards"
        )
        mocker.patch("utils.importers._import_contributions")
        mocker.patch("utils.importers._create_superusers")

        result = import_from_csv("contributions.csv", "legacy.csv")

        # Verify _import_rewards was called twice with correct parameters
        assert mock_import_rewards.call_count == 2

        # First call for current data
        first_call_args = mock_import_rewards.call_args_list[0]
        pd.testing.assert_frame_equal(
            first_call_args[0][0], mock_data[["type", "level", "reward"]]
        )
        assert first_call_args[0][1] == _parse_label_and_name_from_reward_type
        assert first_call_args[0][2] == _reward_amount

        # Second call for legacy data
        second_call_args = mock_import_rewards.call_args_list[1]
        pd.testing.assert_frame_equal(
            second_call_args[0][0], mock_legacy_data[["type", "level", "reward"]]
        )
        assert second_call_args[0][1] == _parse_label_and_name_from_reward_type_legacy
        assert second_call_args[0][2] == _reward_amount_legacy

        # Verify _create_active_rewards was called
        mock_create_active_rewards.assert_called_once_with()

        assert result is False

    @pytest.mark.django_db
    def test_utils_importers_import_from_csv_calls_contribution_functions(self, mocker):
        # Mock empty database check
        mock_social_platforms = mocker.MagicMock()
        mock_social_platforms.__len__ = mocker.MagicMock(return_value=0)
        mocker.patch(
            "utils.importers.SocialPlatform.objects.all",
            return_value=mock_social_platforms,
        )

        # Mock basic dependencies
        mocker.patch("utils.importers.social_platform_prefixes")
        mocker.patch("utils.importers.SocialPlatform.objects.bulk_create")
        mocker.patch("utils.importers._parse_addresses", return_value=[])
        mocker.patch("utils.importers.Contributor.objects.bulk_create")
        mocker.patch("utils.importers.Handle.objects.from_address_and_full_handle")

        # Mock DataFrame creation with all required columns
        mock_data = pd.DataFrame(
            {
                "contributor": ["user1"],
                "cycle_start": ["2023-01-01"],
                "cycle_end": ["2023-01-31"],
                "platform": ["GitHub"],
                "url": ["https://example.com"],
                "type": ["[F] Feature"],
                "level": [1],
                "percentage": [100.0],
                "reward": [1000],
                "comment": ["Test comment"],
            }
        )
        mock_legacy_data = pd.DataFrame(
            {
                "contributor": ["user2"],
                "cycle_start": ["2022-12-01"],
                "cycle_end": ["2022-12-31"],
                "platform": ["Discord"],
                "url": [None],
                "type": ["[B] Bug"],
                "level": [2],
                "percentage": [50.0],
                "reward": [500],
                "comment": [None],
            }
        )
        mocker.patch(
            "utils.importers._dataframe_from_csv",
            side_effect=[mock_data, mock_legacy_data],
        )

        mocker.patch("utils.importers.Cycle.objects.bulk_create")
        mocker.patch("utils.importers.Cycle.objects.latest")
        mocker.patch("utils.importers._check_current_cycle")
        mocker.patch("utils.importers._import_rewards")
        mocker.patch("utils.importers._create_active_rewards")

        # Mock contribution functions to verify they're called correctly
        mock_import_contributions = mocker.patch(
            "utils.importers._import_contributions"
        )
        mocker.patch("utils.importers._create_superusers")

        result = import_from_csv("contributions.csv", "legacy.csv")

        # Verify _import_contributions was called twice with correct parameters
        assert mock_import_contributions.call_count == 2

        # First call for legacy data (called first in the function)
        first_call_args = mock_import_contributions.call_args_list[0]
        pd.testing.assert_frame_equal(first_call_args[0][0], mock_legacy_data)
        assert first_call_args[0][1] == _parse_label_and_name_from_reward_type_legacy
        assert first_call_args[0][2] == _reward_amount_legacy

        # Second call for current data
        second_call_args = mock_import_contributions.call_args_list[1]
        pd.testing.assert_frame_equal(second_call_args[0][0], mock_data)
        assert second_call_args[0][1] == _parse_label_and_name_from_reward_type
        assert second_call_args[0][2] == _reward_amount

        assert result is False

    @pytest.mark.django_db
    def test_utils_importers_import_from_csv_calls_create_superusers(self, mocker):
        # Mock empty database check
        mock_social_platforms = mocker.MagicMock()
        mock_social_platforms.__len__ = mocker.MagicMock(return_value=0)
        mocker.patch(
            "utils.importers.SocialPlatform.objects.all",
            return_value=mock_social_platforms,
        )

        # Mock all dependencies minimally
        mocker.patch("utils.importers.social_platform_prefixes")
        mocker.patch("utils.importers.SocialPlatform.objects.bulk_create")
        mocker.patch("utils.importers._parse_addresses", return_value=[])
        mocker.patch("utils.importers.Contributor.objects.bulk_create")
        mocker.patch("utils.importers.Handle.objects.from_address_and_full_handle")

        # Create proper mock DataFrames with all required columns
        mock_data = pd.DataFrame(
            {
                "cycle_start": ["2023-01-01"],
                "cycle_end": ["2023-01-31"],
                "type": ["[F] Feature"],
                "level": [1],
                "reward": [1000],
            }
        )
        mock_legacy_data = pd.DataFrame(
            {
                "cycle_start": ["2022-12-01"],
                "cycle_end": ["2022-12-31"],
                "type": ["[B] Bug"],
                "level": [2],
                "reward": [500],
            }
        )
        mocker.patch(
            "utils.importers._dataframe_from_csv",
            side_effect=[mock_data, mock_legacy_data],
        )

        mocker.patch("utils.importers.Cycle.objects.bulk_create")
        mocker.patch("utils.importers.Cycle.objects.latest")
        mocker.patch("utils.importers._check_current_cycle")
        mocker.patch("utils.importers._import_rewards")
        mocker.patch("utils.importers._create_active_rewards")
        mocker.patch("utils.importers._import_contributions")

        # Mock _create_superusers to verify it's called
        mock_create_superusers = mocker.patch("utils.importers._create_superusers")

        result = import_from_csv("contributions.csv", "legacy.csv")

        # Verify _create_superusers was called
        mock_create_superusers.assert_called_once_with()

        assert result is False

    @pytest.mark.django_db
    def test_utils_importers_import_from_csv_empty_dataframes(self, mocker):
        """Test import_from_csv with empty DataFrames."""
        # Mock empty database check
        mock_social_platforms = mocker.MagicMock()
        mock_social_platforms.__len__ = mocker.MagicMock(return_value=0)
        mocker.patch(
            "utils.importers.SocialPlatform.objects.all",
            return_value=mock_social_platforms,
        )

        # Mock empty DataFrames with proper columns
        empty_df = pd.DataFrame(columns=CONTRIBUTION_CSV_COLUMNS)
        mocker.patch("utils.importers._dataframe_from_csv", return_value=empty_df)

        # Mock basic dependencies
        mocker.patch("utils.importers.social_platform_prefixes")
        mocker.patch("utils.importers.SocialPlatform.objects.bulk_create")
        mocker.patch("utils.importers._parse_addresses", return_value=[])
        mocker.patch("utils.importers.Contributor.objects.bulk_create")
        mocker.patch("utils.importers.Handle.objects.from_address_and_full_handle")

        # Mock cycle operations to handle empty data
        mocker.patch("utils.importers.Cycle.objects.bulk_create")
        mocker.patch("utils.importers.Cycle.objects.latest")
        mocker.patch("utils.importers._check_current_cycle")
        mocker.patch("utils.importers._import_rewards")
        mocker.patch("utils.importers._create_active_rewards")
        mocker.patch("utils.importers._import_contributions")
        mocker.patch("utils.importers._create_superusers")

        result = import_from_csv("empty.csv", "empty_legacy.csv")

        assert result is False

    @pytest.mark.django_db
    def test_utils_importers_import_from_csv_missing_files(self, mocker):
        """Test import_from_csv when CSV files are missing."""
        # Mock empty database check
        mock_social_platforms = mocker.MagicMock()
        mock_social_platforms.__len__ = mocker.MagicMock(return_value=0)
        mocker.patch(
            "utils.importers.SocialPlatform.objects.all",
            return_value=mock_social_platforms,
        )

        # Mock _dataframe_from_csv to return None (files not found)
        mocker.patch("utils.importers._dataframe_from_csv", return_value=None)

        # Mock basic dependencies
        mocker.patch("utils.importers.social_platform_prefixes")
        mocker.patch("utils.importers.SocialPlatform.objects.bulk_create")
        mocker.patch("utils.importers._parse_addresses", return_value=[])
        mocker.patch("utils.importers.Contributor.objects.bulk_create")
        mocker.patch("utils.importers.Handle.objects.from_address_and_full_handle")

        # Mock empty DataFrames for cycle operations
        empty_cycles_df = pd.DataFrame(columns=["cycle_start", "cycle_end"])
        mocker.patch("utils.importers.pd.concat", return_value=empty_cycles_df)

        mocker.patch("utils.importers.Cycle.objects.bulk_create")
        mocker.patch("utils.importers.Cycle.objects.latest")
        mocker.patch("utils.importers._check_current_cycle")
        mocker.patch("utils.importers._import_rewards")
        mocker.patch("utils.importers._create_active_rewards")
        mocker.patch("utils.importers._import_contributions")
        mocker.patch("utils.importers._create_superusers")

        result = import_from_csv("nonexistent.csv", "nonexistent_legacy.csv")

        assert result is False

    @pytest.mark.django_db
    def test_utils_importers_import_from_csv_no_addresses(self, mocker):
        """Test import_from_csv when no addresses are found."""
        # Mock empty database check
        mock_social_platforms = mocker.MagicMock()
        mock_social_platforms.__len__ = mocker.MagicMock(return_value=0)
        mocker.patch(
            "utils.importers.SocialPlatform.objects.all",
            return_value=mock_social_platforms,
        )

        # Mock no addresses
        mocker.patch("utils.importers._parse_addresses", return_value=[])

        # Mock basic dependencies
        mocker.patch("utils.importers.social_platform_prefixes")
        mocker.patch("utils.importers.SocialPlatform.objects.bulk_create")
        mocker.patch("utils.importers.Contributor.objects.bulk_create")
        mocker.patch("utils.importers.Handle.objects.from_address_and_full_handle")

        # Mock DataFrames
        mock_data = pd.DataFrame(
            {
                "cycle_start": ["2023-01-01"],
                "cycle_end": ["2023-01-31"],
                "type": ["[F] Feature"],
                "level": [1],
                "reward": [1000],
            }
        )
        mocker.patch("utils.importers._dataframe_from_csv", return_value=mock_data)

        mocker.patch("utils.importers.Cycle.objects.bulk_create")
        mocker.patch("utils.importers.Cycle.objects.latest")
        mocker.patch("utils.importers._check_current_cycle")
        mocker.patch("utils.importers._import_rewards")
        mocker.patch("utils.importers._create_active_rewards")
        mocker.patch("utils.importers._import_contributions")
        mocker.patch("utils.importers._create_superusers")

        result = import_from_csv("contributions.csv", "legacy.csv")

        # Should still complete successfully
        assert result is False
        # Contributor.objects.bulk_create should be called with empty generator
        # (though it won't create anything)
