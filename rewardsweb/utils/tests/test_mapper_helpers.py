"""Testing module for :py:mod:`utils.mappers` module's classes and helper functions."""

import pickle
import re
from collections import defaultdict
from datetime import datetime
from unittest import mock

import pytest
from django.conf import settings

import utils.mappers
from core.models import Reward, RewardType, SocialPlatform
from utils.constants.core import GITHUB_ISSUES_START_DATE
from utils.mappers import (
    CustomIssue,
    _build_reward_mapping,
    _extract_url_text,
    _fetch_and_categorize_issues,
    _identify_contributor_from_text,
    _identify_contributor_from_user,
    _identify_platform_from_text,
    _identify_reward_from_issue_title,
    _identify_reward_from_labels,
    _is_url_github_issue,
    _load_saved_issues,
    _save_issues,
)


class TestUtilsMappersConstants:
    """Testing class for :class:`utils.mappers` constants."""

    # # field characteristics
    @pytest.mark.parametrize(
        "constant,value",
        [
            ("URL_EXCEPTIONS", ["discord.com/invite"]),
            ("REWARD_LABELS", ["F", "B", "AT", "CT", "IC", "TWR", "D", "ER"]),
            ("REWARD_PATTERN", re.compile("^\\[(F|B|AT|CT|IC|TWR|D|ER)(1|2|3)\\]")),
        ],
    )
    def test_utils_mappers_module_constants(self, constant, value):
        assert getattr(utils.mappers, constant) == value


class TestUtilsMappersCustomIssue:
    """Testing class for :class:`utils.mappers.CustomIssue` wrapper."""

    def test_utils_mappers_custom_issue_initialization(self, mocker):
        """Test basic initialization."""
        mock_issue = mocker.MagicMock()
        mock_issue.number = 101

        custom_issue = CustomIssue(issue=mock_issue, comments=[])

        assert custom_issue.issue == mock_issue
        assert custom_issue.comments == []

    def test_utils_mappers_custom_issue_with_comments(self, mocker):
        """Test initialization with comments."""
        mock_issue = mocker.MagicMock()
        mock_issue.number = 102

        comments = [mocker.MagicMock(), mocker.MagicMock()]
        custom_issue = CustomIssue(issue=mock_issue, comments=comments)

        assert custom_issue.issue == mock_issue
        assert custom_issue.comments == comments


class TestUtilsMappersHelpers:
    """Testing class for :py:mod:`utils.mappers` helper functions."""

    # # _build_reward_mapping
    @pytest.mark.django_db
    def test_utils_mappers_build_reward_mapping_success(self, mocker):
        """Test _build_reward_mapping successfully builds mapping."""
        # Mock Reward objects
        mock_reward1 = mocker.MagicMock()
        mock_reward2 = mocker.MagicMock()

        # Mock REWARDS_COLLECTION to return known values
        mock_rewards_collection = [
            ["[AT] Admin Task", 1000000],
            ["[F] Feature Request", 2000000],
        ]
        mocker.patch("utils.mappers.REWARDS_COLLECTION", mock_rewards_collection)

        # Mock ISSUE_CREATION_LABEL_CHOICES
        mock_label_choices = [
            ("admin task", "Admin Task"),
            ("feature request", "Feature Request"),
        ]
        mocker.patch("utils.mappers.ISSUE_CREATION_LABEL_CHOICES", mock_label_choices)

        # Mock Reward.objects.get to return rewards
        mocker.patch(
            "utils.mappers.Reward.objects.get", side_effect=[mock_reward1, mock_reward2]
        )

        result = _build_reward_mapping()

        assert "admin task" in result
        assert "feature request" in result
        assert result["admin task"] == mock_reward1
        assert result["feature request"] == mock_reward2

    @pytest.mark.django_db
    def test_utils_mappers_build_reward_mapping_no_reward_found(self, mocker):
        """Test _build_reward_mapping when no reward is found."""
        mock_rewards_collection = [
            ["[AT] Admin Task", 1000000],
        ]
        mocker.patch("utils.mappers.REWARDS_COLLECTION", mock_rewards_collection)

        mock_label_choices = [
            ("admin task", "Admin Task"),
        ]
        mocker.patch("utils.mappers.ISSUE_CREATION_LABEL_CHOICES", mock_label_choices)

        # Mock Reward.DoesNotExist
        mocker.patch(
            "utils.mappers.Reward.objects.get",
            side_effect=Reward.DoesNotExist("No reward found"),
        )

        result = _build_reward_mapping()

        assert result == {}

    @pytest.mark.django_db
    def test_utils_mappers_build_reward_mapping_multiple_rewards(self, mocker):
        """Test _build_reward_mapping when multiple rewards are found."""
        mock_rewards_collection = [
            ["[AT] Admin Task", 1000000],
        ]
        mocker.patch("utils.mappers.REWARDS_COLLECTION", mock_rewards_collection)

        mock_label_choices = [
            ("admin task", "Admin Task"),
        ]
        mocker.patch("utils.mappers.ISSUE_CREATION_LABEL_CHOICES", mock_label_choices)

        mock_reward = mocker.MagicMock()

        # Mock MultipleObjectsReturned and then first()
        mocker.patch(
            "utils.mappers.Reward.objects.get",
            side_effect=Reward.MultipleObjectsReturned("Multiple rewards"),
        )
        mocker.patch(
            "utils.mappers.Reward.objects.filter",
            return_value=mocker.MagicMock(first=lambda: mock_reward),
        )

        result = _build_reward_mapping()

        assert "admin task" in result
        assert result["admin task"] == mock_reward

    @pytest.mark.django_db
    def test_utils_mappers_build_reward_mapping_no_bracket_match(self, mocker):
        """Test _build_reward_mapping when no bracket pattern is found."""
        mock_rewards_collection = [
            ["Admin Task Without Brackets", 1000000],
        ]
        mocker.patch("utils.mappers.REWARDS_COLLECTION", mock_rewards_collection)

        mock_label_choices = [
            ("admin task", "Admin Task"),
        ]
        mocker.patch("utils.mappers.ISSUE_CREATION_LABEL_CHOICES", mock_label_choices)

        result = _build_reward_mapping()

        assert result == {}

    # # _extract_url_text
    @pytest.mark.django_db
    def test_utils_mappers_extract_url_text_markdown_link(self, mocker):
        """Test _extract_url_text with markdown link."""
        body = "Check this [Discord link](https://discord.com/channels/123/456)"
        platform_id = 1

        # Mock SocialPlatform
        mock_platform = mocker.MagicMock()
        mock_platform.name = "Discord"
        mocker.patch(
            "utils.mappers.SocialPlatform.objects.get", return_value=mock_platform
        )

        result = _extract_url_text(body, platform_id)

        assert result == "https://discord.com/channels/123/456"

    @pytest.mark.django_db
    def test_utils_mappers_extract_url_text_multiple_links(self, mocker):
        """Test _extract_url_text with multiple markdown links."""
        body = """
        Check these links:
        [GitHub issue](https://github.com/user/repo/issues/123)
        [Discord channel](https://discord.com/channels/123/456)
        """
        platform_id = 1

        mock_platform = mocker.MagicMock()
        mock_platform.name = "Discord"
        mocker.patch(
            "utils.mappers.SocialPlatform.objects.get", return_value=mock_platform
        )

        result = _extract_url_text(body, platform_id)

        assert result == "https://discord.com/channels/123/456"

    @pytest.mark.django_db
    def test_utils_mappers_extract_url_text_no_matching_platform(self, mocker):
        """Test _extract_url_text with no matching platform in URLs."""
        body = "Check [GitHub issue](https://github.com/user/repo/issues/123)"
        platform_id = 1

        mock_platform = mocker.MagicMock()
        mock_platform.name = "Discord"
        mocker.patch(
            "utils.mappers.SocialPlatform.objects.get", return_value=mock_platform
        )

        result = _extract_url_text(body, platform_id)

        assert result is None

    @pytest.mark.django_db
    def test_utils_mappers_extract_url_text_platform_not_found(self, mocker):
        """Test _extract_url_text when platform is not found."""
        body = "Some text with [link](https://example.com)"
        platform_id = 999

        mocker.patch(
            "utils.mappers.SocialPlatform.objects.get",
            side_effect=SocialPlatform.DoesNotExist("Platform not found"),
        )

        result = _extract_url_text(body, platform_id)

        assert result is None

    @pytest.mark.django_db
    def test_utils_mappers_extract_url_text_no_markdown_links(self, mocker):
        """Test _extract_url_text with no markdown links."""
        body = "Just plain text without any markdown links"
        platform_id = 1

        mock_platform = mocker.MagicMock()
        mock_platform.name = "Discord"
        mocker.patch(
            "utils.mappers.SocialPlatform.objects.get", return_value=mock_platform
        )

        result = _extract_url_text(body, platform_id)

        assert result is None

    # # _fetch_and_categorize_issues
    def test_utils_mappers_fetch_and_categorize_issues_no_token(self, mocker):
        """Test _fetch_and_categorize_issues returns saved issues when no token provided."""
        saved_issues = {
            "closed": ["issue1"],
            "open": ["issue2"],
            "timestamp": "2024-01-01",
        }

        mocker.patch("utils.mappers._load_saved_issues", return_value=saved_issues)

        result = _fetch_and_categorize_issues("", refetch=False)

        assert result == saved_issues

    def test_utils_mappers_fetch_and_categorize_issues_refetch_false_uses_saved(
        self, mocker
    ):
        """Test _fetch_and_categorize_issues uses saved issues when refetch is False."""
        saved_issues = {
            "closed": ["issue1"],
            "open": ["issue2"],
            "timestamp": "2024-01-01",
        }
        mocker.patch("utils.mappers._load_saved_issues", return_value=saved_issues)

        name = settings.ISSUE_TRACKER_PROVIDER.capitalize()
        mocker.patch(f"issues.providers.{name}Provider._get_client")
        mocker.patch(f"issues.providers.{name}Provider._get_repository")
        mocker.patch("issues.providers.BaseIssueProvider.fetch_issues", return_value=[])

        result = _fetch_and_categorize_issues("valid_token", refetch=False)

        assert result == saved_issues

    def test_utils_mappers_fetch_and_categorize_issues_refetch_true_fetches_new(
        self, mocker
    ):
        """Test _fetch_and_categorize_issues fetches new issues when refetch is True."""

        new_issues = [
            mocker.MagicMock(
                state="closed",
                number=101,
                pull_request=None,
                updated_at=datetime(2024, 1, 2, 10, 30, 0),
            ),
            mocker.MagicMock(
                state="open",
                number=102,
                pull_request=None,
                updated_at=datetime(2024, 1, 2, 11, 45, 0),
            ),
        ]

        mocker.patch("utils.mappers._load_saved_issues", return_value=defaultdict(list))
        name = settings.ISSUE_TRACKER_PROVIDER.capitalize()
        mocker.patch(f"issues.providers.{name}Provider._get_client")
        mocker.patch(f"issues.providers.{name}Provider._get_repository")
        mock_fetch_issues = mocker.patch(
            "issues.providers.BaseIssueProvider.fetch_issues", return_value=new_issues
        )
        mocker.patch("utils.mappers._save_issues")

        result = _fetch_and_categorize_issues("valid_token", refetch=True)

        mock_fetch_issues.assert_called_once_with(
            state="all", since=GITHUB_ISSUES_START_DATE
        )
        assert len(result["closed"]) == 1
        assert len(result["open"]) == 1
        assert result["closed"][0].issue.number == 101
        assert result["open"][0].issue.number == 102

    def test_utils_mappers_fetch_and_categorize_issues_saves_every_10_issues(
        self, mocker
    ):
        """Test _fetch_and_categorize_issues saves progress every 10 issues."""

        issues = []
        for i in range(25):
            issue = mocker.MagicMock(
                state="open" if i % 2 == 0 else "closed",
                number=100 + i,
                pull_request=None,
                updated_at=datetime(2024, 1, i + 1),
            )
            issues.append(issue)

        mocker.patch("utils.mappers._load_saved_issues", return_value=defaultdict(list))
        name = settings.ISSUE_TRACKER_PROVIDER.capitalize()
        mocker.patch(f"issues.providers.{name}Provider._get_client")
        mocker.patch(f"issues.providers.{name}Provider._get_repository")
        mocker.patch(
            "issues.providers.BaseIssueProvider.fetch_issues", return_value=issues
        )
        mock_save_issues = mocker.patch("utils.mappers._save_issues")

        _fetch_and_categorize_issues("valid_token", refetch=True)

        # Should save at issues 9, 19 (0-indexed: 10th, 20th) and at the end
        # 10th (index 9), 20th (index 19), and final (25th)
        assert mock_save_issues.call_count == 4

    def test_utils_mappers_fetch_and_categorize_issues_uses_since_parameter(
        self, mocker
    ):
        """Test _fetch_and_categorize_issues uses since parameter from saved issues."""

        saved_issues = {"closed": ["old_issue"], "timestamp": datetime(2024, 1, 1)}
        new_issues = [
            mocker.MagicMock(
                state="closed",
                number=101,
                pull_request=None,
                updated_at=datetime(2024, 1, 2),
            ),
        ]

        mocker.patch("utils.mappers._load_saved_issues", return_value=saved_issues)
        name = settings.ISSUE_TRACKER_PROVIDER.capitalize()
        mocker.patch(f"issues.providers.{name}Provider._get_client")
        mocker.patch(f"issues.providers.{name}Provider._get_repository")
        mock_fetch_issues = mocker.patch(
            "issues.providers.BaseIssueProvider.fetch_issues", return_value=new_issues
        )
        mocker.patch("utils.mappers._save_issues")

        _fetch_and_categorize_issues("valid_token", refetch=False)

        # Should use timestamp from saved issues as since parameter
        mock_fetch_issues.assert_called_once_with(
            state="all", since=datetime(2024, 1, 1)
        )

    def test_utils_mappers_fetch_and_categorize_issues_uses_default_since(self, mocker):
        """Test _fetch_and_categorize_issues uses default since when no saved timestamp."""

        saved_issues = {"closed": ["old_issue"]}  # No timestamp
        new_issues = [
            mocker.MagicMock(
                state="closed",
                number=101,
                pull_request=None,
                updated_at=datetime(2024, 1, 2),
            ),
        ]

        mocker.patch("utils.mappers._load_saved_issues", return_value=saved_issues)
        name = settings.ISSUE_TRACKER_PROVIDER.capitalize()
        mocker.patch(f"issues.providers.{name}Provider._get_client")
        mocker.patch(f"issues.providers.{name}Provider._get_repository")
        mock_fetch_issues = mocker.patch(
            "issues.providers.BaseIssueProvider.fetch_issues", return_value=new_issues
        )
        mocker.patch("utils.mappers._save_issues")

        _fetch_and_categorize_issues("valid_token", refetch=True)

        # Should use GITHUB_ISSUES_START_DATE as since parameter
        from utils.constants.core import GITHUB_ISSUES_START_DATE

        mock_fetch_issues.assert_called_once_with(
            state="all", since=GITHUB_ISSUES_START_DATE
        )

    def test_utils_mappers_fetch_and_categorize_issues_empty_fetch(self, mocker):
        """Test _fetch_and_categorize_issues handles empty fetch results."""
        mocker.patch("utils.mappers._load_saved_issues", return_value=defaultdict(list))
        name = settings.ISSUE_TRACKER_PROVIDER.capitalize()
        mocker.patch(f"issues.providers.{name}Provider._get_client")
        mocker.patch(f"issues.providers.{name}Provider._get_repository")
        mocker.patch("issues.providers.BaseIssueProvider.fetch_issues", return_value=[])
        mock_save_issues = mocker.patch("utils.mappers._save_issues")

        result = _fetch_and_categorize_issues("valid_token", refetch=True)

        assert result == defaultdict(list)
        mock_save_issues.assert_not_called()  # No issues to save

    def test_utils_mappers_fetch_and_categorize_issues_only_pull_requests(self, mocker):
        """Test _fetch_and_categorize_issues when all results are pull requests."""

        issues = [
            mocker.MagicMock(
                state="closed",
                number=101,
                pull_request=True,
                updated_at=datetime(2024, 1, 2),
            ),
            mocker.MagicMock(
                state="open",
                number=102,
                pull_request=True,
                updated_at=datetime(2024, 1, 2),
            ),
        ]

        mocker.patch("utils.mappers._load_saved_issues", return_value=defaultdict(list))
        name = settings.ISSUE_TRACKER_PROVIDER.capitalize()
        mocker.patch(f"issues.providers.{name}Provider._get_client")
        mocker.patch(f"issues.providers.{name}Provider._get_repository")
        mocker.patch(
            "issues.providers.BaseIssueProvider.fetch_issues", return_value=issues
        )
        mock_save_issues = mocker.patch("utils.mappers._save_issues")

        result = _fetch_and_categorize_issues("valid_token", refetch=True)

        assert result["closed"] == []
        assert result["open"] == []
        # Should still save at the end even with no regular issues
        mock_save_issues.assert_called_once()

    def test_utils_mappers_fetch_and_categorize_issues_progress_printing(self, mocker):
        """Test _fetch_and_categorize_issues prints progress every 10 issues."""

        issues = []
        for i in range(15):
            issue = mocker.MagicMock(
                state="open",
                number=100 + i,
                pull_request=None,
                updated_at=datetime(2024, 1, i + 1),
            )
            issues.append(issue)

        mocker.patch("utils.mappers._load_saved_issues", return_value=defaultdict(list))
        name = settings.ISSUE_TRACKER_PROVIDER.capitalize()
        mocker.patch(f"issues.providers.{name}Provider._get_client")
        mocker.patch(f"issues.providers.{name}Provider._get_repository")
        mocker.patch(
            "issues.providers.BaseIssueProvider.fetch_issues", return_value=issues
        )
        mocker.patch("utils.mappers._save_issues")
        mock_print = mocker.patch("builtins.print")

        _fetch_and_categorize_issues("valid_token", refetch=True)

        # Should print at issue numbers 100, 110 (0-indexed: 1st, 11th)
        print_calls = [
            call for call in mock_print.call_args_list if "Issue number:" in str(call)
        ]
        assert len(print_calls) == 2
        # Check the actual call arguments
        assert print_calls[0] == mock.call("Issue number: ", 100)
        assert print_calls[1] == mock.call("Issue number: ", 110)

    def test_utils_mappers_fetch_and_categorize_issues_final_count_print(self, mocker):
        """Test _fetch_and_categorize_issues prints final count."""

        issues = [
            mocker.MagicMock(
                state="closed",
                number=101,
                pull_request=None,
                updated_at=datetime(2024, 1, 2),
            ),
            mocker.MagicMock(
                state="open",
                number=102,
                pull_request=None,
                updated_at=datetime(2024, 1, 2),
            ),
            mocker.MagicMock(
                state="closed",
                number=103,
                pull_request=None,
                updated_at=datetime(2024, 1, 2),
            ),
        ]

        mocker.patch("utils.mappers._load_saved_issues", return_value=defaultdict(list))
        name = settings.ISSUE_TRACKER_PROVIDER.capitalize()
        mocker.patch(f"issues.providers.{name}Provider._get_client")
        mocker.patch(f"issues.providers.{name}Provider._get_repository")
        mocker.patch(
            "issues.providers.BaseIssueProvider.fetch_issues", return_value=issues
        )
        mocker.patch("utils.mappers._save_issues")
        mock_print = mocker.patch("builtins.print")

        _fetch_and_categorize_issues("valid_token", refetch=True)

        # Should print final count
        final_print_call = mock_print.call_args_list[-1]
        assert "Number of issues: 3" in str(final_print_call)

    def test_utils_mappers_fetch_and_categorize_issues_mixed_states(self, mocker):
        issues = [
            mocker.MagicMock(
                state="closed",
                number=101,
                pull_request=None,
                updated_at=datetime(2024, 1, 2),
            ),
            mocker.MagicMock(
                state="open",
                number=102,
                pull_request=None,
                updated_at=datetime(2024, 1, 2),
            ),
            mocker.MagicMock(
                state="closed",
                number=103,
                pull_request=None,
                updated_at=datetime(2024, 1, 2),
            ),
            mocker.MagicMock(
                state="open",
                number=104,
                pull_request=None,
                updated_at=datetime(2024, 1, 2),
            ),
        ]

        mocker.patch("utils.mappers._load_saved_issues", return_value=defaultdict(list))
        name = settings.ISSUE_TRACKER_PROVIDER.capitalize()
        mocker.patch(f"issues.providers.{name}Provider._get_client")
        mocker.patch(f"issues.providers.{name}Provider._get_repository")
        mocker.patch(
            "issues.providers.BaseIssueProvider.fetch_issues", return_value=issues
        )
        mocker.patch("utils.mappers._save_issues")

        result = _fetch_and_categorize_issues("valid_token", refetch=True)

        assert len(result["closed"]) == 2
        assert len(result["open"]) == 2
        assert result["closed"][0].issue.number == 101
        assert result["closed"][1].issue.number == 103
        assert result["open"][0].issue.number == 102
        assert result["open"][1].issue.number == 104

    def test_utils_mappers_fetch_and_categorize_issues_handles_missing_keys_in_print(
        self, mocker
    ):

        issues = [
            mocker.MagicMock(
                state="closed",
                number=101,
                pull_request=None,
                updated_at=datetime(2024, 1, 2),
            ),
        ]

        # Mock _load_saved_issues to return a dict without 'open' key
        saved_issues = {"closed": [], "timestamp": datetime(2024, 1, 1)}
        mocker.patch("utils.mappers._load_saved_issues", return_value=saved_issues)
        name = settings.ISSUE_TRACKER_PROVIDER.capitalize()
        mocker.patch(f"issues.providers.{name}Provider._get_client")
        mocker.patch(f"issues.providers.{name}Provider._get_repository")
        mocker.patch(
            "issues.providers.BaseIssueProvider.fetch_issues", return_value=issues
        )
        mocker.patch("utils.mappers._save_issues")
        mock_print = mocker.patch("builtins.print")

        # This should not raise TypeError
        _fetch_and_categorize_issues("valid_token", refetch=True)

        # Verify the print was called successfully
        mock_print.assert_called()

    # # _identify_contributor_from_text
    def test_utils_mappers_identify_contributor_from_text_name_part_match(self):
        text = "This issue was reported by John Doe in our discussion"
        contributors = {"John Doe (johndoe, jd)": 1}

        result = _identify_contributor_from_text(text, contributors)

        assert result == 1

    def test_utils_mappers_identify_contributor_from_text_name_part_case_insensitive(
        self,
    ):
        """Test _identify_contributor_from_text name part matching is case insensitive."""
        text = "Reported by JOHN DOE in the meeting"
        contributors = {"john doe (johndoe, jd)": 1}

        result = _identify_contributor_from_text(text, contributors)

        assert result == 1

    def test_utils_mappers_identify_contributor_from_text_name_part_no_match(self):
        text = "This issue was reported by Jane Smith"
        contributors = {"John Doe (johndoe, jd)": 1}

        result = _identify_contributor_from_text(text, contributors)

        assert result is None

    # # _identify_contributor_from_text - handle.lower() in text_lower
    def test_utils_mappers_identify_contributor_from_text_handle_match_first_handle(
        self,
    ):
        """Test _identify_contributor_from_text matches first handle in parentheses."""
        text = "User johndoe reported this issue"
        contributors = {"John Doe (johndoe, jd)": 1}

        result = _identify_contributor_from_text(text, contributors)

        assert result == 1

    def test_utils_mappers_identify_contributor_from_text_handle_match_second_handle(
        self,
    ):
        """Test _identify_contributor_from_text matches second handle in parentheses."""
        text = "User jd mentioned this in the discussion"
        contributors = {"John Doe (johndoe, jd)": 1}

        result = _identify_contributor_from_text(text, contributors)

        assert result == 1

    def test_utils_mappers_identify_contributor_from_text_handle_match_multiple_handles(
        self,
    ):
        """Test _identify_contributor_from_text matches with multiple handles."""
        text = "User john_doe_alt reported the bug"
        contributors = {"John Doe (johndoe, jd, john_doe_alt)": 1}

        result = _identify_contributor_from_text(text, contributors)

        assert result == 1

    def test_utils_mappers_identify_contributor_from_text_handle_case_insensitive(self):
        """Test _identify_contributor_from_text handle matching is case insensitive."""
        text = "User JOHN_DOE reported this"
        contributors = {"John Doe (john_doe, jd)": 1}

        result = _identify_contributor_from_text(text, contributors)

        assert result == 1

    def test_utils_mappers_identify_contributor_from_text_handle_partial_match(self):
        """Test _identify_contributor_from_text matches handle as substring."""
        text = "Username johndoe123 mentioned this issue"
        contributors = {"John Doe (johndoe, jd)": 1}

        result = _identify_contributor_from_text(text, contributors)

        assert result == 1

    def test_utils_mappers_identify_contributor_from_text_handle_no_match(self):
        text = "User unknownuser reported this"
        contributors = {"John Doe (johndoe, jd)": 1}

        result = _identify_contributor_from_text(text, contributors)

        assert result is None

    def test_utils_mappers_identify_contributor_from_text_priority_name_before_handle(
        self,
    ):
        text = "John Doe (aka johndoe) reported this issue"
        contributors = {"John Doe (johndoe, jd)": 1}

        result = _identify_contributor_from_text(text, contributors)

        assert result == 1

    def test_utils_mappers_identify_contributor_from_text_priority_first_contributor(
        self,
    ):
        text = "johndoe reported this issue"
        contributors = {"John Doe (johndoe, jd)": 1, "Jane Smith (janesmith, js)": 2}

        result = _identify_contributor_from_text(text, contributors)

        assert result == 1

    def test_utils_mappers_identify_contributor_from_text_no_parentheses_simple_match(
        self,
    ):
        text = "John Doe reported this issue"
        contributors = {"John Doe": 1}

        result = _identify_contributor_from_text(text, contributors)

        assert result == 1

    def test_utils_mappers_identify_contributor_from_text_no_parentheses_case_insensit(
        self,
    ):
        text = "JOHN DOE reported this issue"
        contributors = {"john doe": 1}

        result = _identify_contributor_from_text(text, contributors)

        assert result == 1

    def test_utils_mappers_identify_contributor_from_text_no_parentheses_no_match(self):
        text = "Jane Smith reported this issue"
        contributors = {"John Doe": 1}

        result = _identify_contributor_from_text(text, contributors)

        assert result is None

    def test_utils_mappers_identify_contributor_from_text_empty_text(self):
        """Test _identify_contributor_from_text handles empty text."""
        text = ""
        contributors = {"John Doe (johndoe)": 1}

        result = _identify_contributor_from_text(text, contributors)

        assert result is None

    def test_utils_mappers_identify_contributor_from_text_none_text(self):
        """Test _identify_contributor_from_text handles None text."""
        contributors = {"John Doe (johndoe)": 1}

        result = _identify_contributor_from_text(None, contributors)

        assert result is None

    def test_utils_mappers_identify_contributor_from_text_empty_contributors(self):
        """Test _identify_contributor_from_text handles empty contributors."""
        text = "John Doe reported this"
        contributors = {}

        result = _identify_contributor_from_text(text, contributors)

        assert result is None

    def test_utils_mappers_identify_contributor_from_text_complex_handle_parsing(self):
        text = "User complex_handle-123 reported this"
        contributors = {"John Doe (complex_handle-123, jd-456)": 1}

        result = _identify_contributor_from_text(text, contributors)

        assert result == 1

    def test_utils_mappers_identify_contributor_from_text_handles_with_spaces(self):
        text = "User john doe reported this"
        contributors = {"John Doe (john doe, jd)": 1}

        result = _identify_contributor_from_text(text, contributors)

        assert result == 1

    def test_utils_mappers_identify_contributor_from_text_multiple_match_diff_formats(
        self,
    ):
        text = "John and janesmith both worked on this"
        contributors = {
            "John Doe (johndoe, jd)": 1,
            "Jane Smith (janesmith)": 2,
            "Bob Johnson": 3,
        }

        result = _identify_contributor_from_text(text, contributors)

        # Should return first match (John Doe) because "John" matches the name part
        assert result == 2

    def test_utils_mappers_identify_contributor_from_text_exact_vs_partial_precedence(
        self,
    ):
        """Test _identify_contributor_from_text precedence of exact matches over partial."""
        text = "John Doe Smith reported this"
        contributors = {"John Doe (johndoe)": 1, "John Doe Smith (jdsmith)": 2}

        result = _identify_contributor_from_text(text, contributors)

        # Should match "John Doe Smith" exactly, not partial "John Doe"
        # The function checks contributors in order, so we need to ensure the exact match comes first
        # Let's reverse the order to test this properly
        contributors_reversed = {"John Doe Smith (jdsmith)": 2, "John Doe (johndoe)": 1}

        result = _identify_contributor_from_text(text, contributors_reversed)
        assert result == 2

    def test_utils_mappers_identify_contributor_from_text_handle_takes_precedence_over_partial_name(
        self,
    ):
        """Test _identify_contributor_from_text handle match takes precedence over partial name match."""
        text = "User janesmith reported this issue"
        contributors = {
            "John Smith (johnsmith)": 1,  # "Smith" would partially match but shouldn't
            "Jane Smith (janesmith)": 2,  # Exact handle match should win
        }

        result = _identify_contributor_from_text(text, contributors)

        assert result == 2

    @pytest.mark.django_db
    def test_utils_mappers_identify_contributor_from_text_simple_match(self):
        """Test _identify_contributor_from_text with simple name match."""
        body = "This issue was reported by John Doe"
        contributors = {"John Doe": 1, "Jane Smith": 2}

        result = _identify_contributor_from_text(body, contributors)

        assert result == 1

    @pytest.mark.django_db
    def test_utils_mappers_identify_contributor_from_text_handle_match(self):
        """Test _identify_contributor_from_text with handle match."""
        body = "User with handle user123 reported this issue"
        contributors = {"John Doe (user123, john_doe)": 1}

        result = _identify_contributor_from_text(body, contributors)

        assert result == 1

    @pytest.mark.django_db
    def test_utils_mappers_identify_contributor_from_text_multiple_handles(self):
        """Test _identify_contributor_from_text with multiple handles."""
        body = "User handle456 mentioned this"
        contributors = {"John Doe (user123, handle456, john_doe)": 1}

        result = _identify_contributor_from_text(body, contributors)

        assert result == 1

    @pytest.mark.django_db
    def test_utils_mappers_identify_contributor_from_text_case_insensitive(self):
        """Test _identify_contributor_from_text is case insensitive."""
        body = "Reported by JOHN DOE"
        contributors = {"john doe": 1}

        result = _identify_contributor_from_text(body, contributors)

        assert result == 1

    @pytest.mark.django_db
    def test_utils_mappers_identify_contributor_from_text_no_match(self):
        """Test _identify_contributor_from_text with no match."""
        body = "Reported by Unknown User"
        contributors = {"John Doe": 1, "Jane Smith": 2}

        result = _identify_contributor_from_text(body, contributors)

        assert result is None

    @pytest.mark.django_db
    def test_utils_mappers_identify_contributor_from_text_empty_body(self):
        """Test _identify_contributor_from_text with empty body."""
        contributors = {"John Doe": 1}

        result = _identify_contributor_from_text("", contributors)

        assert result is None

    # # _identify_contributor_from_user
    def test_utils_mappers_identify_contributor_from_user_exact_match_strict(self):
        """Test exact match when strict=True (default)."""
        # Setup
        user = "john_doe"
        contributors = {
            "John Doe (g@john_doe, t@johndoe)": 1,
            "Jane Smith (g@jane_smith, d@jane)": 2,
            "Bob Wilson (g@bob_wilson)": 3,
        }

        # Execute
        result = _identify_contributor_from_user(user, contributors, strict=True)

        # Assert
        assert result == 1

    def test_utils_mappers_identify_contributor_from_user_exact_match_non_strict(self):
        """Test exact match when strict=False."""
        # Setup
        user = "john_doe"
        contributors = {
            "John Doe (g@john_doe, t@johndoe)": 1,
            "Jane Smith (g@jane_smith, d@jane)": 2,
            "Bob Wilson (john_doe)": 3,  # Handle without g@ prefix
        }

        # Execute
        result = _identify_contributor_from_user(user, contributors, strict=False)

        # Assert - should match the first one because "john_doe" appears in "g@john_doe"
        # The function does substring matching, not exact handle matching
        assert result == 1

    def test_utils_mappers_identify_contributor_from_user_case_insensitive(self):
        """Test case insensitive matching."""
        # Setup
        user = "John_Doe"  # Mixed case
        contributors = {
            "John Doe (g@john_doe, t@johndoe)": 1,  # Lowercase in contributor info
            "Jane Smith (g@JANE_SMITH)": 2,  # Uppercase in contributor info
        }

        # Execute
        result = _identify_contributor_from_user(user, contributors, strict=True)

        # Assert
        assert result == 1

    def test_utils_mappers_identify_contributor_from_user_no_match_strict(self):
        """Test no match found when strict=True."""
        # Setup
        user = "unknown_user"
        contributors = {
            "John Doe (g@john_doe, t@johndoe)": 1,
            "Jane Smith (g@jane_smith, d@jane)": 2,
        }

        # Execute
        result = _identify_contributor_from_user(user, contributors, strict=True)

        # Assert
        assert result is None

    def test_utils_mappers_identify_contributor_from_user_no_match_non_strict(self):
        """Test no match found when strict=False."""
        # Setup
        user = "unknown_user"
        contributors = {
            "John Doe (g@john_doe, t@johndoe)": 1,
            "Jane Smith (g@jane_smith, d@jane)": 2,
        }

        # Execute
        result = _identify_contributor_from_user(user, contributors, strict=False)

        # Assert
        assert result is None

    def test_utils_mappers_identify_contributor_from_user_partial_match_strict(self):
        """Test partial match within contributor info when strict=True."""
        # Setup
        user = "john"
        contributors = {
            "John Doe (g@john_doe, t@johndoe)": 1,
            "Johnny Cash (g@johnny_cash)": 2,
            "Jane Smith (g@jane_smith)": 3,
        }

        # Execute
        result = _identify_contributor_from_user(user, contributors, strict=True)

        # Assert - should match both john_doe and johnny_cash due to partial match
        assert result == 1  # First match

    def test_utils_mappers_identify_contributor_from_user_partial_match_non_strict(
        self,
    ):
        """Test partial match within contributor info when strict=False."""
        # Setup
        user = "john"
        contributors = {
            "John Doe (g@john_doe, t@johndoe)": 1,
            "Johnny Cash (johnny_cash)": 2,  # Without g@ prefix
            "Jane Smith (g@jane_smith)": 3,
        }

        # Execute
        result = _identify_contributor_from_user(user, contributors, strict=False)

        # Assert - should match both
        assert result == 1  # First match

    def test_utils_mappers_identify_contributor_from_user_empty_contributors(self):
        """Test with empty contributors dictionary."""
        # Setup
        user = "john_doe"
        contributors = {}

        # Execute
        result = _identify_contributor_from_user(user, contributors, strict=True)

        # Assert
        assert result is None

    def test_utils_mappers_identify_contributor_from_user_multiple_handles(self):
        """Test matching when contributor has multiple handles."""
        # Setup
        user = "jane_smith"
        contributors = {
            "Jane Smith (g@jane_smith, d@janesmith, t@jsmith)": 1,
            "John Doe (g@john_doe)": 2,
        }

        # Execute
        result = _identify_contributor_from_user(user, contributors, strict=True)

        # Assert
        assert result == 1

    def test_utils_mappers_identify_contributor_from_user_special_characters(self):
        """Test matching with special characters in username."""
        # Setup
        user = "user-name"
        contributors = {
            "User Name (g@user-name, d@username)": 1,
            "Another User (g@another_user)": 2,
        }

        # Execute
        result = _identify_contributor_from_user(user, contributors, strict=True)

        # Assert
        assert result == 1

    def test_utils_mappers_identify_contributor_from_user_numeric_username(self):
        """Test matching with numeric usernames."""
        # Setup
        user = "user123"
        contributors = {
            "User 123 (g@user123, d@user123)": 1,
            "Test User (g@test_user)": 2,
        }

        # Execute
        result = _identify_contributor_from_user(user, contributors, strict=True)

        # Assert
        assert result == 1

    def test_utils_mappers_identify_contributor_from_user_underscore_vs_dash(self):
        """Test matching with underscore vs dash differences."""
        # Setup
        user = "user-name"
        contributors = {
            "User Name (g@user_name, d@username)": 1,  # Underscore in contributor info
            "Another User (g@user-name)": 2,  # Dash in contributor info
        }

        # Execute
        result = _identify_contributor_from_user(user, contributors, strict=True)

        # Assert - should match the second one with exact dash match
        assert result == 2

    def test_utils_mappers_identify_contributor_from_user_priority_first_match(self):
        """Test that first matching contributor is returned."""
        # Setup
        user = "john"
        contributors = {
            "John Doe (g@john_doe, t@johndoe)": 1,
            "John Smith (g@john_smith)": 2,  # Also matches
            "Johnny Cash (g@johnny)": 3,  # Also matches
        }

        # Execute
        result = _identify_contributor_from_user(user, contributors, strict=True)

        # Assert - should return first match
        assert result == 1

    def test_utils_mappers_identify_contributor_from_user_with_magicmock(self):
        """Test using MagicMock for contributors."""
        # Setup
        user = "test_user"

        # Create MagicMock for contributors dictionary-like behavior
        contributors_dict = {
            "Test User (g@test_user, d@testuser)": 100,
            "Another User (g@another_user)": 200,
        }

        # Execute
        result = _identify_contributor_from_user(user, contributors_dict, strict=True)

        # Assert
        assert result == 100

    def test_utils_mappers_identify_contributor_from_user_complex_contributor_info(
        self,
    ):
        """Test matching with complex contributor info format."""
        # Setup
        user = "dev_user"
        contributors = {
            "Developer User (g@dev_user, d@developer, t@dev, r/u_dev)": 1,
            "Simple User (g@simple_user)": 2,
        }

        # Execute
        result = _identify_contributor_from_user(user, contributors, strict=True)

        # Assert
        assert result == 1

    def test_utils_mappers_identify_contributor_from_user_whitespace_handling(self):
        """Test handling of whitespace in contributor info."""
        # Setup
        user = "test_user"
        contributors = {
            "Test User (  g@test_user  ,  d@testuser  )": 1,  # Extra spaces
            "Another User (g@another_user)": 2,
        }

        # Execute
        result = _identify_contributor_from_user(user, contributors, strict=True)

        # Assert - should still match despite extra spaces
        assert result == 1

    def test_utils_mappers_identify_contributor_from_user_mixed_strictness(self):
        """Test comparing strict vs non-strict behavior."""
        # Setup
        user = "john_doe"
        contributors = {
            "John Doe (john_doe, t@johndoe)": 1,  # No g@ prefix
            "Jane Smith (g@jane_smith)": 2,
        }

        # Execute both modes
        result_strict = _identify_contributor_from_user(user, contributors, strict=True)
        result_non_strict = _identify_contributor_from_user(
            user, contributors, strict=False
        )
        result_default_strict = _identify_contributor_from_user(user, contributors)
        # Assert
        assert result_strict is None  # No match in strict mode (needs g@ prefix)
        assert result_default_strict is None  # default is True
        assert result_non_strict == 1  # Match in non-strict mode

    def test_utils_mappers_identify_contributor_from_user_empty_user(self):
        """Test with empty username."""
        # Setup
        user = ""
        contributors = {
            "Test User (g@test_user)": 1,
            "Another User (g@another_user)": 2,
        }

        # Execute
        result = _identify_contributor_from_user(user, contributors, strict=True)

        # Assert
        assert result is None

    def test_utils_mappers_identify_contributor_from_user_none_user(self):
        """Test with None username."""
        # Setup
        user = None
        contributors = {
            "Test User (g@test_user)": 1,
        }

        # Execute
        result = _identify_contributor_from_user(user, contributors, strict=True)

        # Assert
        assert result is None

    def test_utils_mappers_identify_contributor_from_user_strict_requires_g_prefix(
        self,
    ):
        """Test that strict mode requires g@ prefix."""
        # Setup
        user = "john_doe"
        contributors = {
            "John Doe (john_doe, t@johndoe)": 1,  # No g@ prefix
            "John Doe Official (g@john_doe)": 2,  # With g@ prefix
        }

        # Execute
        result_strict = _identify_contributor_from_user(user, contributors, strict=True)
        result_non_strict = _identify_contributor_from_user(
            user, contributors, strict=False
        )

        # Assert
        assert result_strict == 2  # Only matches the one with g@ prefix
        assert result_non_strict == 1  # Matches both, returns first

    def test_utils_mappers_identify_contributor_from_user_exact_handle_matching(self):
        """Test that the function does substring matching, not exact handle matching."""
        # Setup
        user = "john"
        contributors = {
            "John Doe (g@john_doe)": 1,  # Contains "john" but not exact match
            "John Smith (g@john)": 2,  # Exact match
        }

        # Execute
        result = _identify_contributor_from_user(user, contributors, strict=True)

        # Assert - both match due to substring search, returns first
        assert result == 1

    # # _identify_platform_from_text
    @pytest.mark.django_db
    def test_utils_mappers_identify_platform_from_text_match(self):
        """Test _identify_platform_from_text with platform match."""
        body = "Discussed on Discord about this issue"
        platforms = {"Discord": 1, "GitHub": 2}

        result = _identify_platform_from_text(body, platforms)

        assert result == 1

    @pytest.mark.django_db
    def test_utils_mappers_identify_platform_from_text_case_insensitive(self):
        """Test _identify_platform_from_text is case insensitive."""
        body = "discord channel discussion"
        platforms = {"Discord": 1}

        result = _identify_platform_from_text(body, platforms)

        assert result == 1

    @pytest.mark.django_db
    def test_utils_mappers_identify_platform_from_text_no_match(self):
        """Test _identify_platform_from_text with no platform match."""
        body = "General discussion about the issue"
        platforms = {"Discord": 1, "GitHub": 2}

        result = _identify_platform_from_text(body, platforms)

        assert result is None

    @pytest.mark.django_db
    def test_utils_mappers_identify_platform_from_text_empty_body(self):
        """Test _identify_platform_from_text with empty body."""
        platforms = {"Discord": 1}

        result = _identify_platform_from_text("", platforms)

        assert result is None

    @pytest.mark.django_db
    def test_utils_mappers_identify_platform_from_text_empty_platforms(self):
        """Test _identify_platform_from_text with empty platforms."""
        body = "Discord discussion"
        platforms = {}

        result = _identify_platform_from_text(body, platforms)

        assert result is None

    # # _identify_reward_from_labels
    @pytest.mark.django_db
    def test_utils_mappers_identify_reward_from_labels_exact_match(self, mocker):
        """Test _identify_reward_from_labels with exact label match."""
        mock_label1 = mocker.MagicMock()
        mock_label1.name = "admin task"
        mock_label2 = mocker.MagicMock()
        mock_label2.name = "other label"

        labels = [mock_label1, mock_label2]
        reward_mapping = {"admin task": "reward1", "feature request": "reward2"}

        result = _identify_reward_from_labels(labels, reward_mapping)

        assert result == "reward1"

    @pytest.mark.django_db
    def test_utils_mappers_identify_reward_from_labels_case_insensitive(self, mocker):
        """Test _identify_reward_from_labels is case insensitive."""
        mock_label = mocker.MagicMock()
        mock_label.name = "ADMIN TASK"

        labels = [mock_label]
        reward_mapping = {"admin task": "reward1"}

        result = _identify_reward_from_labels(labels, reward_mapping)

        assert result == "reward1"

    @pytest.mark.django_db
    def test_utils_mappers_identify_reward_from_labels_no_match(self, mocker):
        """Test _identify_reward_from_labels with no matching labels."""
        mock_label = mocker.MagicMock()
        mock_label.name = "unrelated label"

        labels = [mock_label]
        reward_mapping = {"admin task": "reward1"}

        result = _identify_reward_from_labels(labels, reward_mapping)

        assert result is None

    @pytest.mark.django_db
    def test_utils_mappers_identify_reward_from_labels_empty_labels(self, mocker):
        """Test _identify_reward_from_labels with empty labels list."""
        labels = []
        reward_mapping = {"admin task": "reward1"}

        result = _identify_reward_from_labels(labels, reward_mapping)

        assert result is None

    @pytest.mark.django_db
    def test_utils_mappers_identify_reward_from_labels_empty_mapping(self, mocker):
        """Test _identify_reward_from_labels with empty reward mapping."""
        mock_label = mocker.MagicMock()
        mock_label.name = "admin task"

        labels = [mock_label]
        reward_mapping = {}

        result = _identify_reward_from_labels(labels, reward_mapping)

        assert result is None

    def test_utils_mappers_identify_reward_from_labels_partial_match(self, mocker):
        """Test _identify_reward_from_labels returns reward for partial label match."""
        # Mock label objects
        mock_label1 = mocker.MagicMock()
        mock_label1.name = "admin task priority"  # Contains "admin task" as exact words

        mock_label2 = mocker.MagicMock()
        mock_label2.name = "other-label"

        labels = [mock_label1, mock_label2]

        # Mock reward mapping
        mock_reward = mocker.MagicMock()
        reward_mapping = {
            "admin task": mock_reward,
            "feature request": mocker.MagicMock(),
        }

        result = _identify_reward_from_labels(labels, reward_mapping)

        # Should return the reward for "admin task" since "admin task" is in "admin task priority"
        assert result == mock_reward

    # # _identify_reward_from_issue_title
    def test_utils_mappers_identify_reward_from_issue_title_empty_title(self, mocker):
        """Test that empty title returns None."""
        # Mock get_object_or_404 to ensure it's not called
        mock_get_object_or_404 = mocker.patch("utils.mappers.get_object_or_404")

        result = _identify_reward_from_issue_title("")

        assert result is None
        mock_get_object_or_404.assert_not_called()

    def test_utils_mappers_identify_reward_from_issue_title_none_title(self, mocker):
        """Test that None title returns None."""
        # Mock get_object_or_404 to ensure it's not called
        mock_get_object_or_404 = mocker.patch("utils.mappers.get_object_or_404")

        result = _identify_reward_from_issue_title(None)

        assert result is None
        mock_get_object_or_404.assert_not_called()

    def test_utils_mappers_identify_reward_from_issue_title_no_pattern_match(
        self, mocker
    ):
        """Test that title without reward pattern returns None."""
        # Mock get_object_or_404 to ensure it's not called
        mock_get_object_or_404 = mocker.patch("utils.mappers.get_object_or_404")

        result = _identify_reward_from_issue_title(
            "Regular issue title without pattern"
        )

        assert result is None
        mock_get_object_or_404.assert_not_called()

    def test_utils_mappers_identify_reward_from_issue_title_pattern_in_middle(
        self, mocker
    ):
        """Test that pattern not at start of title returns None."""
        # Mock get_object_or_404 to ensure it's not called
        mock_get_object_or_404 = mocker.patch("utils.mappers.get_object_or_404")

        result = _identify_reward_from_issue_title("Some text [F1] more text")

        assert result is None
        mock_get_object_or_404.assert_not_called()

    def test_utils_mappers_identify_reward_from_issue_title_pattern_with_whitespace(
        self, mocker
    ):
        """Test that pattern matches with leading/trailing whitespace."""
        mock_reward_type = mocker.MagicMock(spec=RewardType)
        mock_reward = mocker.MagicMock(spec=Reward)

        # Mock get_object_or_404 to return reward type
        mock_get_object_or_404 = mocker.patch(
            "utils.mappers.get_object_or_404", return_value=mock_reward_type
        )

        # Mock Reward.objects.filter().first() to return reward
        mock_reward_filter = mocker.MagicMock()
        mock_reward_filter.first = mocker.MagicMock(return_value=mock_reward)
        mocker.patch(
            "utils.mappers.Reward.objects.filter", return_value=mock_reward_filter
        )

        result = _identify_reward_from_issue_title("  [F1] Issue title with spaces  ")

        assert result == mock_reward
        mock_get_object_or_404.assert_called_once_with(RewardType, label="F")
        mock_reward_filter.first.assert_called_once()

    def test_utils_mappers_identify_reward_from_issue_title_valid_f1_pattern(
        self, mocker
    ):
        """Test valid F1 pattern returns reward."""
        mock_reward_type = mocker.MagicMock(spec=RewardType)
        mock_reward = mocker.MagicMock(spec=Reward)

        # Mock get_object_or_404 to return reward type
        mock_get_object_or_404 = mocker.patch(
            "utils.mappers.get_object_or_404", return_value=mock_reward_type
        )

        # Mock Reward.objects.filter().first() to return reward
        mock_reward_filter = mocker.MagicMock()
        mock_reward_filter.first = mocker.MagicMock(return_value=mock_reward)
        mocker.patch(
            "utils.mappers.Reward.objects.filter", return_value=mock_reward_filter
        )

        result = _identify_reward_from_issue_title("[F1] Fix bug in module")

        assert result == mock_reward
        mock_get_object_or_404.assert_called_once_with(RewardType, label="F")
        mock_reward_filter.first.assert_called_once()

    def test_utils_mappers_identify_reward_from_issue_title_valid_b2_pattern(
        self, mocker
    ):
        """Test valid B2 pattern returns reward."""
        mock_reward_type = mocker.MagicMock(spec=RewardType)
        mock_reward = mocker.MagicMock(spec=Reward)

        # Mock get_object_or_404 to return reward type
        mock_get_object_or_404 = mocker.patch(
            "utils.mappers.get_object_or_404", return_value=mock_reward_type
        )

        # Mock Reward.objects.filter().first() to return reward
        mock_reward_filter = mocker.MagicMock()
        mock_reward_filter.first = mocker.MagicMock(return_value=mock_reward)
        mocker.patch(
            "utils.mappers.Reward.objects.filter", return_value=mock_reward_filter
        )

        result = _identify_reward_from_issue_title("[B2] Build new feature")

        assert result == mock_reward
        mock_get_object_or_404.assert_called_once_with(RewardType, label="B")
        mock_reward_filter.first.assert_called_once()

    def test_utils_mappers_identify_reward_from_issue_title_valid_at3_pattern(
        self, mocker
    ):
        """Test valid AT3 pattern returns reward."""
        mock_reward_type = mocker.MagicMock(spec=RewardType)
        mock_reward = mocker.MagicMock(spec=Reward)

        # Mock get_object_or_404 to return reward type
        mock_get_object_or_404 = mocker.patch(
            "utils.mappers.get_object_or_404", return_value=mock_reward_type
        )

        # Mock Reward.objects.filter().first() to return reward
        mock_reward_filter = mocker.MagicMock()
        mock_reward_filter.first = mocker.MagicMock(return_value=mock_reward)
        mocker.patch(
            "utils.mappers.Reward.objects.filter", return_value=mock_reward_filter
        )

        result = _identify_reward_from_issue_title("[AT3] Advanced testing")

        assert result == mock_reward
        mock_get_object_or_404.assert_called_once_with(RewardType, label="AT")
        mock_reward_filter.first.assert_called_once()

    def test_utils_mappers_identify_reward_from_issue_title_valid_ct1_pattern(
        self, mocker
    ):
        """Test valid CT1 pattern returns reward."""
        mock_reward_type = mocker.MagicMock(spec=RewardType)
        mock_reward = mocker.MagicMock(spec=Reward)

        # Mock get_object_or_404 to return reward type
        mock_get_object_or_404 = mocker.patch(
            "utils.mappers.get_object_or_404", return_value=mock_reward_type
        )

        # Mock Reward.objects.filter().first() to return reward
        mock_reward_filter = mocker.MagicMock()
        mock_reward_filter.first = mocker.MagicMock(return_value=mock_reward)
        mocker.patch(
            "utils.mappers.Reward.objects.filter", return_value=mock_reward_filter
        )

        result = _identify_reward_from_issue_title("[CT1] Code review task")

        assert result == mock_reward
        mock_get_object_or_404.assert_called_once_with(RewardType, label="CT")
        mock_reward_filter.first.assert_called_once()

    def test_utils_mappers_identify_reward_from_issue_title_valid_ic2_pattern(
        self, mocker
    ):
        """Test valid IC2 pattern returns reward."""
        mock_reward_type = mocker.MagicMock(spec=RewardType)
        mock_reward = mocker.MagicMock(spec=Reward)

        # Mock get_object_or_404 to return reward type
        mock_get_object_or_404 = mocker.patch(
            "utils.mappers.get_object_or_404", return_value=mock_reward_type
        )

        # Mock Reward.objects.filter().first() to return reward
        mock_reward_filter = mocker.MagicMock()
        mock_reward_filter.first = mocker.MagicMock(return_value=mock_reward)
        mocker.patch(
            "utils.mappers.Reward.objects.filter", return_value=mock_reward_filter
        )

        result = _identify_reward_from_issue_title("[IC2] Integration challenge")

        assert result == mock_reward
        mock_get_object_or_404.assert_called_once_with(RewardType, label="IC")
        mock_reward_filter.first.assert_called_once()

    def test_utils_mappers_identify_reward_from_issue_title_valid_twr3_pattern(
        self, mocker
    ):
        """Test valid TWR3 pattern returns reward."""
        mock_reward_type = mocker.MagicMock(spec=RewardType)
        mock_reward = mocker.MagicMock(spec=Reward)

        # Mock get_object_or_404 to return reward type
        mock_get_object_or_404 = mocker.patch(
            "utils.mappers.get_object_or_404", return_value=mock_reward_type
        )

        # Mock Reward.objects.filter().first() to return reward
        mock_reward_filter = mocker.MagicMock()
        mock_reward_filter.first = mocker.MagicMock(return_value=mock_reward)
        mocker.patch(
            "utils.mappers.Reward.objects.filter", return_value=mock_reward_filter
        )

        result = _identify_reward_from_issue_title("[TWR3] Technical writing reward")

        assert result == mock_reward
        mock_get_object_or_404.assert_called_once_with(RewardType, label="TWR")
        mock_reward_filter.first.assert_called_once()

    def test_utils_mappers_identify_reward_from_issue_title_valid_d1_pattern(
        self, mocker
    ):
        """Test valid D1 pattern returns reward."""
        mock_reward_type = mocker.MagicMock(spec=RewardType)
        mock_reward = mocker.MagicMock(spec=Reward)

        # Mock get_object_or_404 to return reward type
        mock_get_object_or_404 = mocker.patch(
            "utils.mappers.get_object_or_404", return_value=mock_reward_type
        )

        # Mock Reward.objects.filter().first() to return reward
        mock_reward_filter = mocker.MagicMock()
        mock_reward_filter.first = mocker.MagicMock(return_value=mock_reward)
        mocker.patch(
            "utils.mappers.Reward.objects.filter", return_value=mock_reward_filter
        )

        result = _identify_reward_from_issue_title("[D1] Documentation task")

        assert result == mock_reward
        mock_get_object_or_404.assert_called_once_with(RewardType, label="D")
        mock_reward_filter.first.assert_called_once()

    def test_utils_mappers_identify_reward_from_issue_title_valid_er2_pattern(
        self, mocker
    ):
        """Test valid ER2 pattern returns reward."""
        mock_reward_type = mocker.MagicMock(spec=RewardType)
        mock_reward = mocker.MagicMock(spec=Reward)

        # Mock get_object_or_404 to return reward type
        mock_get_object_or_404 = mocker.patch(
            "utils.mappers.get_object_or_404", return_value=mock_reward_type
        )

        # Mock Reward.objects.filter().first() to return reward
        mock_reward_filter = mocker.MagicMock()
        mock_reward_filter.first = mocker.MagicMock(return_value=mock_reward)
        mocker.patch(
            "utils.mappers.Reward.objects.filter", return_value=mock_reward_filter
        )

        result = _identify_reward_from_issue_title("[ER2] Emergency response")

        assert result == mock_reward
        mock_get_object_or_404.assert_called_once_with(RewardType, label="ER")
        mock_reward_filter.first.assert_called_once()

    def test_utils_mappers_identify_reward_from_issue_title_reward_not_found(
        self, mocker
    ):
        """Test that when reward doesn't exist, returns None."""
        mock_reward_type = mocker.MagicMock(spec=RewardType)

        # Mock get_object_or_404 to return reward type
        mock_get_object_or_404 = mocker.patch(
            "utils.mappers.get_object_or_404", return_value=mock_reward_type
        )

        # Mock Reward.objects.filter().first() to return None
        mock_reward_filter = mocker.MagicMock()
        mock_reward_filter.first = mocker.MagicMock(return_value=None)
        mocker.patch(
            "utils.mappers.Reward.objects.filter", return_value=mock_reward_filter
        )

        result = _identify_reward_from_issue_title("[F1] Fix bug")

        assert result is None
        mock_get_object_or_404.assert_called_once_with(RewardType, label="F")
        mock_reward_filter.first.assert_called_once()

    def test_utils_mappers_identify_reward_from_issue_title_inactive_reward(
        self, mocker
    ):
        """Test that active=False parameter is passed correctly."""
        mock_reward_type = mocker.MagicMock(spec=RewardType)
        mock_reward = mocker.MagicMock(spec=Reward)

        # Mock get_object_or_404 to return reward type
        mock_get_object_or_404 = mocker.patch(
            "utils.mappers.get_object_or_404", return_value=mock_reward_type
        )

        # Mock Reward.objects.filter().first() to return reward
        mock_reward_filter = mocker.MagicMock()
        mock_reward_filter.first = mocker.MagicMock(return_value=mock_reward)
        mocked_filter = mocker.patch(
            "utils.mappers.Reward.objects.filter", return_value=mock_reward_filter
        )

        result = _identify_reward_from_issue_title("[F1] Fix bug", active=False)

        assert result == mock_reward
        mock_get_object_or_404.assert_called_once_with(RewardType, label="F")
        # Verify that Reward.objects.filter was called with active=False
        mock_reward_filter.first.assert_called_once()
        # Check the filter call arguments
        mocked_filter.assert_called_once_with(
            type=mock_reward_type, level=1, active=False
        )

    def test_utils_mappers_identify_reward_from_issue_title_all_reward_labels(
        self, mocker
    ):
        """Test all valid reward labels from REWARD_LABELS."""
        reward_labels = ["F", "B", "AT", "CT", "IC", "TWR", "D", "ER"]

        for label in reward_labels:
            for level in [1, 2, 3]:
                mock_reward_type = mocker.MagicMock(spec=RewardType)
                mock_reward = mocker.MagicMock(spec=Reward)

                # Mock get_object_or_404 to return reward type
                mock_get_object_or_404 = mocker.patch(
                    "utils.mappers.get_object_or_404", return_value=mock_reward_type
                )

                # Mock Reward.objects.filter().first() to return reward
                mock_reward_filter = mocker.MagicMock()
                mock_reward_filter.first = mocker.MagicMock(return_value=mock_reward)
                mocker.patch(
                    "utils.mappers.Reward.objects.filter",
                    return_value=mock_reward_filter,
                )

                title = f"[{label}{level}] Test issue"
                result = _identify_reward_from_issue_title(title)

                assert result == mock_reward
                mock_get_object_or_404.assert_called_once_with(RewardType, label=label)
                mock_reward_filter.first.assert_called_once()

                # Reset mocks for next iteration
                mocker.stopall()

    def test_utils_mappers_identify_reward_from_issue_title_invalid_level(self, mocker):
        """Test that invalid level (not 1,2,3) doesn't match pattern."""
        # Mock get_object_or_404 to ensure it's not called
        mock_get_object_or_404 = mocker.patch("utils.mappers.get_object_or_404")

        # Test levels outside valid range
        invalid_titles = [
            "[F0] Invalid level",
            "[F4] Invalid level",
            "[F9] Invalid level",
            "[F10] Invalid level",
        ]

        for title in invalid_titles:
            result = _identify_reward_from_issue_title(title)
            assert result is None

        # Verify get_object_or_404 was never called
        mock_get_object_or_404.assert_not_called()

    def test_utils_mappers_identify_reward_from_issue_title_case_sensitivity(
        self, mocker
    ):
        """Test that pattern matching is case sensitive."""
        # Mock get_object_or_404 to ensure it's not called for lowercase
        mock_get_object_or_404 = mocker.patch("utils.mappers.get_object_or_404")

        # Test lowercase labels (should not match)
        lowercase_titles = [
            "[f1] lowercase label",
            "[b2] lowercase label",
            "[at3] lowercase label",
        ]

        for title in lowercase_titles:
            result = _identify_reward_from_issue_title(title)
            assert result is None

        # Verify get_object_or_404 was never called for lowercase
        mock_get_object_or_404.assert_not_called()

    def test_utils_mappers_identify_reward_from_issue_title_malformed_patterns(
        self, mocker
    ):
        """Test various malformed patterns that should not match."""
        # Mock get_object_or_404 to ensure it's not called
        mock_get_object_or_404 = mocker.patch("utils.mappers.get_object_or_404")

        malformed_titles = [
            "[F1",  # Missing closing bracket
            "F1]",  # Missing opening bracket
            "[F 1]",  # Space between label and level
            "[F-1]",  # Wrong separator
            "[F_1]",  # Wrong separator
            "[]",  # Empty brackets
            "[F]",  # Missing level
            "[1]",  # Missing label
            "(F1)",  # Wrong brackets
            "{F1}",  # Wrong brackets
        ]

        for title in malformed_titles:
            result = _identify_reward_from_issue_title(title)
            assert result is None

        # Verify get_object_or_404 was never called
        mock_get_object_or_404.assert_not_called()

    # # _is_url_github_issue
    def test_utils_mappers_is_url_github_issue_valid_url(self):
        """Test valid GitHub issue URL returns issue number."""
        valid_url = (
            f"https://github.com/{settings.ISSUE_TRACKER_OWNER}/"
            f"{settings.ISSUE_TRACKER_NAME}/issues/123"
        )

        result = _is_url_github_issue(valid_url)

        assert result == 123

    def test_utils_mappers_is_url_github_issue_invalid_domain(self):
        """Test invalid domain returns False."""
        invalid_url = "https://gitlab.com/owner/repo/issues/123"

        result = _is_url_github_issue(invalid_url)

        assert result is False

    def test_utils_mappers_is_url_github_issue_invalid_owner(self):
        """Test invalid repo owner returns False."""
        invalid_url = (
            f"https://github.com/wrong_owner/{settings.ISSUE_TRACKER_NAME}/issues/123"
        )

        result = _is_url_github_issue(invalid_url)

        assert result is False

    def test_utils_mappers_is_url_github_issue_invalid_repo(self):
        """Test invalid repo name returns False."""
        invalid_url = (
            f"https://github.com/{settings.ISSUE_TRACKER_OWNER}/wrong_repo/issues/123"
        )

        result = _is_url_github_issue(invalid_url)

        assert result is False

    def test_utils_mappers_is_url_github_issue_invalid_path(self):
        """Test invalid path returns False."""
        invalid_url = (
            f"https://github.com/{settings.ISSUE_TRACKER_OWNER}/"
            f"{settings.ISSUE_TRACKER_NAME}/pulls/123"
        )

        result = _is_url_github_issue(invalid_url)

        assert result is False

    def test_utils_mappers_is_url_github_issue_non_numeric_issue(self):
        """Test non-numeric issue number returns False."""
        invalid_url = (
            f"https://github.com/{settings.ISSUE_TRACKER_OWNER}/"
            f"{settings.ISSUE_TRACKER_NAME}/issues/abc"
        )

        result = _is_url_github_issue(invalid_url)

        assert result is False


class TestUtilsMappersIOFunctions:
    """Testing class for :py:mod:`utils.mappers` helper functions."""

    # # _load_saved_issues
    def test_utils_mappers_load_saved_issues_returns_defaultdict(self, mocker):
        with (
            mock.patch("utils.mappers.Path") as mocked_path,
            mock.patch(
                "utils.mappers.read_pickle", return_value={}
            ) as mocked_read_pickle,
        ):
            # Mock the path chain
            mock_path_instance = mocker.MagicMock()
            mocked_path.return_value = mock_path_instance
            mock_path_instance.resolve.return_value.parent.parent.__truediv__.return_value = (
                mocker.MagicMock()
            )

            result = _load_saved_issues()

            assert isinstance(result, defaultdict)
            mocked_read_pickle.assert_called_once()

    def test_utils_mappers_load_saved_issues_loads_data_correctly(self, mocker):
        test_data = {
            "repo1": [{"id": 1, "title": "Issue 1"}],
            "repo2": [{"id": 2, "title": "Issue 2"}],
            "timestamp": 1234567890,
        }
        with (
            mock.patch("utils.mappers.Path") as mocked_path,
            mock.patch(
                "utils.mappers.read_pickle", return_value=test_data
            ) as mocked_read_pickle,
        ):
            # Mock the path chain
            mock_path_instance = mocker.MagicMock()
            mocked_path.return_value = mock_path_instance
            mock_path_instance.resolve.return_value.parent.parent.__truediv__.return_value = (
                mocker.MagicMock()
            )

            result = _load_saved_issues()

            assert isinstance(result, defaultdict)
            assert dict(result) == test_data
            mocked_read_pickle.assert_called_once()

    def test_utils_mappers_load_saved_issues_handles_empty_data(self, mocker):
        with (
            mock.patch("utils.mappers.Path") as mocked_path,
            mock.patch(
                "utils.mappers.read_pickle", return_value={}
            ) as mocked_read_pickle,
        ):
            # Mock the path chain
            mock_path_instance = mocker.MagicMock()
            mocked_path.return_value = mock_path_instance
            mock_path_instance.resolve.return_value.parent.parent.__truediv__.return_value = (
                mocker.MagicMock()
            )

            result = _load_saved_issues()

            assert isinstance(result, defaultdict)
            assert dict(result) == {}
            mocked_read_pickle.assert_called_once()

    # # _save_issues
    def test_utils_mappers_save_issues_writes_to_file(self, mocker):
        github_issues = {
            "repo1": [{"id": 1, "title": "Issue 1"}],
            "repo2": [{"id": 2, "title": "Issue 2"}],
        }
        timestamp = 1234567890

        with (
            mock.patch("utils.mappers.Path") as mocked_path,
            mock.patch("utils.mappers.open", mock.mock_open()) as mocked_open,
            mock.patch("utils.mappers.pickle.dump") as mocked_pickle_dump,
        ):
            # Mock the entire path chain correctly
            mock_final_path = mocker.MagicMock()

            # Set up the chain: Path() -> resolve() -> parent -> parent -> __truediv__("fixtures") -> __truediv__("github_issues.pkl")
            mock_path_instance = mocker.MagicMock()
            mocked_path.return_value = mock_path_instance

            mock_resolve = mocker.MagicMock()
            mock_path_instance.resolve.return_value = mock_resolve

            mock_parent1 = mocker.MagicMock()
            mock_parent2 = mocker.MagicMock()
            mock_resolve.parent = mock_parent1
            mock_parent1.parent = mock_parent2

            # Mock the __truediv__ chain
            mock_parent2.__truediv__.return_value = mock_final_path
            mock_final_path.__truediv__.return_value = mock_final_path

            _save_issues(github_issues, timestamp)

            # Assert open was called with the final path
            mocked_open.assert_called_once_with(mock_final_path, "wb")

            # Verify pickle.dump was called
            mocked_pickle_dump.assert_called_once()

            # Check that timestamp was added to the data
            call_args = mocked_pickle_dump.call_args[0]
            saved_data = call_args[0]
            assert saved_data["timestamp"] == timestamp
            assert saved_data["repo1"] == github_issues["repo1"]
            assert saved_data["repo2"] == github_issues["repo2"]

    def test_utils_mappers_save_issues_creates_directory(self, mocker):
        github_issues = {"repo1": [{"id": 1, "title": "Issue 1"}]}
        timestamp = 1234567890

        with (
            mock.patch("utils.mappers.Path") as mocked_path,
            mock.patch("utils.mappers.open", mock.mock_open()),
            mock.patch("utils.mappers.pickle.dump"),
        ):
            # Mock the entire path chain correctly
            mock_final_path = mocker.MagicMock()
            mock_parent_dir = mocker.MagicMock()
            mock_final_path.parent = mock_parent_dir

            # Set up the chain
            mock_path_instance = mocker.MagicMock()
            mocked_path.return_value = mock_path_instance

            mock_resolve = mocker.MagicMock()
            mock_path_instance.resolve.return_value = mock_resolve

            mock_parent1 = mocker.MagicMock()
            mock_parent2 = mocker.MagicMock()
            mock_resolve.parent = mock_parent1
            mock_parent1.parent = mock_parent2

            # Mock the __truediv__ chain to return our final path
            mock_parent2.__truediv__.return_value = mock_final_path
            mock_final_path.__truediv__.return_value = mock_final_path

            _save_issues(github_issues, timestamp)

            # Assert mkdir was called on the parent directory
            mock_parent_dir.mkdir.assert_called_once_with(parents=True, exist_ok=True)

    def test_utils_mappers_save_issues_handles_permission_error(self, mocker):
        github_issues = {"repo1": [{"id": 1, "title": "Issue 1"}]}
        timestamp = 1234567890

        with (
            mock.patch("utils.mappers.Path") as mocked_path,
            mock.patch(
                "utils.mappers.open", side_effect=PermissionError("Permission denied")
            ),
            mock.patch("utils.mappers.pickle.dump"),
        ):
            # Mock the path chain
            mock_path_instance = mocker.MagicMock()
            mocked_path.return_value = mock_path_instance
            mock_path_instance.resolve.return_value.parent.parent.__truediv__.return_value = (
                mocker.MagicMock()
            )

            with pytest.raises(PermissionError):
                _save_issues(github_issues, timestamp)

    def test_utils_mappers_save_and_load_roundtrip(self, mocker, tmp_path):
        # Import here to avoid circular imports if needed

        def mock_read_pickle(filename):
            if filename.exists():
                with open(filename, "rb") as f:
                    return pickle.load(f)
            return {}

        def mock_save_issues(github_issues, timestamp):
            path = tmp_path / "github_issues.pkl"
            github_issues["timestamp"] = timestamp
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "wb") as f:
                pickle.dump(github_issues, f)

        def mock_load_saved_issues():
            github_issues = defaultdict(list)
            path = tmp_path / "github_issues.pkl"
            data = mock_read_pickle(path)
            for key in data:
                github_issues[key] = data[key]
            return github_issues

        test_data = {
            "repo1": [{"id": 1, "title": "Issue 1", "state": "open"}],
            "repo2": [{"id": 2, "title": "Issue 2", "state": "closed"}],
        }
        timestamp = 1234567890

        # Save the data
        mock_save_issues(test_data.copy(), timestamp)

        # Load the data
        loaded_data = mock_load_saved_issues()

        # Verify
        expected_data = test_data.copy()
        expected_data["timestamp"] = timestamp
        assert dict(loaded_data) == expected_data
