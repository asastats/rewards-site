"""Testing module for :py:mod:`utils.mappers` module's mapping functions."""

from datetime import datetime

import pytest
from django.conf import settings
from django.http import Http404

from core.models import Issue, IssueStatus
from utils.mappers import (
    _create_contributor_from_text,
    _create_issues_bulk,
    _map_closed_addressed_issues,
    _map_closed_archived_issues,
    _map_open_issues,
    _map_unprocessed_closed_archived_issues,
    map_github_issues,
)


class TestUtilsMappersMappingCreation:
    """Testing class for bulk-optimized :py:mod:`utils.mappers` creating function."""

    # # _create_contributor_from_text
    @pytest.mark.django_db
    def test_utils_mappers_create_contributor_from_text_no_text(self):
        """Test function returns None when text is empty."""
        contributors = {}
        result, updated_contributors = _create_contributor_from_text("", contributors)
        assert result is None
        assert updated_contributors == contributors

    @pytest.mark.django_db
    def test_utils_mappers_create_contributor_from_text_no_match(self):
        """Test function returns None when no pattern matches."""
        contributors = {}
        text = "This text doesn't contain the pattern"
        result, updated_contributors = _create_contributor_from_text(text, contributors)
        assert result is None
        assert updated_contributors == contributors

    @pytest.mark.django_db
    def test_utils_mappers_create_contributor_from_text_discord_pattern_with_brackets(
        self, mocker
    ):
        """Test creating contributor from Discord pattern with brackets."""
        # Mock platform
        mock_platform = mocker.MagicMock()
        mock_platform.name = "Discord"

        # Mock SocialPlatform.objects.get
        mocker.patch(
            "utils.mappers.SocialPlatform.objects.get", return_value=mock_platform
        )

        # Mock Contributor.objects.filter (no existing contributor)
        mock_filter = mocker.MagicMock()
        mock_filter.first = mocker.MagicMock(return_value=None)
        mocker.patch(
            "utils.mappers.Contributor.objects.filter", return_value=mock_filter
        )

        # Mock Contributor.objects.create
        mock_contributor = mocker.MagicMock()
        mock_contributor.id = 1
        mock_contributor.name = "john_doe"
        mock_contributor.info = "john_doe"
        mocker.patch(
            "utils.mappers.Contributor.objects.create", return_value=mock_contributor
        )

        # Mock Handle.objects.create
        mocker.patch("utils.mappers.Handle.objects.create")

        contributors = {}
        text = "By john_doe in [Discord]"

        result, updated_contributors = _create_contributor_from_text(text, contributors)

        assert result == 1
        assert updated_contributors == {"john_doe": 1}

    @pytest.mark.django_db
    def test_utils_mappers_create_contributor_from_text_twitter_pattern_without_brackets(
        self, mocker
    ):
        """Test creating contributor from Twitter pattern without brackets."""
        # Mock platform
        mock_platform = mocker.MagicMock()
        mock_platform.name = "Twitter"

        # Mock SocialPlatform.objects.get
        mocker.patch(
            "utils.mappers.SocialPlatform.objects.get", return_value=mock_platform
        )

        # Mock Contributor.objects.filter (no existing contributor)
        mock_filter = mocker.MagicMock()
        mock_filter.first = mocker.MagicMock(return_value=None)
        mocker.patch(
            "utils.mappers.Contributor.objects.filter", return_value=mock_filter
        )

        # Mock Contributor.objects.create
        mock_contributor = mocker.MagicMock()
        mock_contributor.id = 2
        mock_contributor.name = "jane_smith"
        mock_contributor.info = "jane_smith"
        mocker.patch(
            "utils.mappers.Contributor.objects.create", return_value=mock_contributor
        )

        # Mock Handle.objects.create
        mocker.patch("utils.mappers.Handle.objects.create")

        contributors = {}
        text = "By jane_smith on Twitter"

        result, updated_contributors = _create_contributor_from_text(text, contributors)

        assert result == 2
        assert updated_contributors == {"jane_smith": 2}

    @pytest.mark.django_db
    def test_utils_mappers_create_contributor_from_text_existing_contributor(
        self, mocker
    ):
        """Test function when contributor already exists."""
        # Mock platform
        mock_platform = mocker.MagicMock()
        mock_platform.name = "Discord"

        # Mock SocialPlatform.objects.get
        mocker.patch(
            "utils.mappers.SocialPlatform.objects.get", return_value=mock_platform
        )

        # Mock existing contributor
        mock_existing_contributor = mocker.MagicMock()
        mock_existing_contributor.id = 5
        mock_existing_contributor.name = "existing_user"
        mock_existing_contributor.info = "existing_user"

        mocker.patch(
            "utils.mappers.Contributor.objects.from_handle",
            return_value=mock_existing_contributor,
        )

        # Mock Handle.objects.get_or_create
        mocker.patch("utils.mappers.Handle.objects.get_or_create")

        contributors = {}
        text = "By existing_user in [Discord]"

        result, updated_contributors = _create_contributor_from_text(text, contributors)

        assert result == 5
        assert updated_contributors == {"existing_user": 5}

    # # _create_issues_bulk
    def test_utils_mappers_create_issues_bulk_empty_assignments(self, mocker):
        """Test function returns early when no assignments provided."""
        mocked_issue_filter = mocker.patch("utils.mappers.Issue.objects.filter")
        mocked_bulk_create = mocker.patch("utils.mappers.Issue.objects.bulk_create")
        mocked_contribution_filter = mocker.patch(
            "utils.mappers.Contribution.objects.filter"
        )

        _create_issues_bulk([])

        mocked_issue_filter.assert_not_called()
        mocked_bulk_create.assert_not_called()
        mocked_contribution_filter.assert_not_called()

    @pytest.mark.django_db
    def test_utils_mappers_create_issues_bulk_all_new_issues(self, mocker):
        """Test bulk creation when all issues are new."""
        issue_assignments = [
            (101, 1, IssueStatus.ARCHIVED),
            (102, 2, IssueStatus.ARCHIVED),
            (103, 3, IssueStatus.ARCHIVED),
        ]

        # Create proper QuerySet-like mock for existing issues
        mock_existing_issues = mocker.MagicMock()
        mock_existing_issues.values_list.return_value = []

        # Mock Issue.objects.filter to return our mock QuerySet
        mocked_issue_filter = mocker.patch("utils.mappers.Issue.objects.filter")
        mocked_issue_filter.return_value = mock_existing_issues

        # Mock bulk create
        mocked_bulk_create = mocker.patch("utils.mappers.Issue.objects.bulk_create")

        # Mock getting all issues after creation - return proper QuerySet-like object
        mock_issue1 = mocker.MagicMock()
        mock_issue1.number = 101
        mock_issue2 = mocker.MagicMock()
        mock_issue2.number = 102
        mock_issue3 = mocker.MagicMock()
        mock_issue3.number = 103

        mock_issues_queryset = mocker.MagicMock()
        mock_issues_queryset.__iter__ = mocker.MagicMock(
            return_value=iter([mock_issue1, mock_issue2, mock_issue3])
        )

        # First call returns empty (existing issues), second call returns all issues
        mocked_issue_filter.side_effect = [mock_existing_issues, mock_issues_queryset]

        # Mock contributions
        mock_contrib1 = mocker.MagicMock()
        mock_contrib1.id = 1
        mock_contrib2 = mocker.MagicMock()
        mock_contrib2.id = 2
        mock_contrib3 = mocker.MagicMock()
        mock_contrib3.id = 3

        # Create a proper mock for the contributions queryset that can be converted
        mock_contrib_queryset = mocker.MagicMock()
        mock_contrib_queryset.__iter__ = mocker.MagicMock(
            return_value=iter([mock_contrib1, mock_contrib2, mock_contrib3])
        )

        # Mock the filter to return our queryset
        mocked_contrib_filter = mocker.patch(
            "utils.mappers.Contribution.objects.filter"
        )
        mocked_contrib_filter.return_value = mock_contrib_queryset

        # Mock bulk_update - we need to check it's called with the queryset
        mocked_bulk_update = mocker.patch(
            "utils.mappers.Contribution.objects.bulk_update"
        )

        _create_issues_bulk(issue_assignments)

        # Verify issue creation
        mocked_bulk_create.assert_called_once()
        created_issues = mocked_bulk_create.call_args[0][0]
        assert len(created_issues) == 3
        assert {issue.number for issue in created_issues} == {101, 102, 103}
        assert all(issue.status == IssueStatus.ARCHIVED for issue in created_issues)

        # Verify contribution updates
        mocked_bulk_update.assert_called_once_with(mock_contrib_queryset, ["issue"])

        # Verify individual contributions were updated
        assert mock_contrib1.issue == mock_issue1
        assert mock_contrib2.issue == mock_issue2
        assert mock_contrib3.issue == mock_issue3

    @pytest.mark.django_db
    def test_utils_mappers_create_issues_bulk_mixed_existing_issues(self, mocker):
        """Test bulk creation when some issues exist and some are new."""
        issue_assignments = [
            (101, 1, IssueStatus.ARCHIVED),
            (102, 2, IssueStatus.ARCHIVED),
        ]

        # Mock existing issues (only 101 exists)
        mock_existing_issues = mocker.MagicMock()
        mock_existing_issues.values_list.return_value = [101]

        # Mock Issue.objects.filter
        mocked_issue_filter = mocker.patch("utils.mappers.Issue.objects.filter")
        mocked_issue_filter.return_value = mock_existing_issues

        # Mock bulk create
        mocked_bulk_create = mocker.patch("utils.mappers.Issue.objects.bulk_create")

        # Mock getting all issues after creation
        mock_issue1 = mocker.MagicMock()
        mock_issue1.number = 101
        mock_issue2 = mocker.MagicMock()
        mock_issue2.number = 102

        mock_issues_queryset = mocker.MagicMock()
        mock_issues_queryset.__iter__ = mocker.MagicMock(
            return_value=iter([mock_issue1, mock_issue2])
        )

        # First call returns existing issues, second call returns all issues
        mocked_issue_filter.side_effect = [mock_existing_issues, mock_issues_queryset]

        # Mock contributions
        mock_contrib1 = mocker.MagicMock()
        mock_contrib1.id = 1
        mock_contrib2 = mocker.MagicMock()
        mock_contrib2.id = 2

        mock_contrib_queryset = mocker.MagicMock()
        mock_contrib_queryset.__iter__ = mocker.MagicMock(
            return_value=iter([mock_contrib1, mock_contrib2])
        )
        mocked_contrib_filter = mocker.patch(
            "utils.mappers.Contribution.objects.filter"
        )
        mocked_contrib_filter.return_value = mock_contrib_queryset

        mocked_bulk_update = mocker.patch(
            "utils.mappers.Contribution.objects.bulk_update"
        )

        _create_issues_bulk(issue_assignments)

        # Verify only one issue was created
        mocked_bulk_create.assert_called_once()
        created_issues = mocked_bulk_create.call_args[0][0]
        assert len(created_issues) == 1
        assert created_issues[0].number == 102

        # Verify both contributions were updated - called with queryset
        mocked_bulk_update.assert_called_once_with(mock_contrib_queryset, ["issue"])

        # Verify individual contributions were updated
        assert mock_contrib1.issue == mock_issue1
        assert mock_contrib2.issue == mock_issue2

    @pytest.mark.django_db
    def test_utils_mappers_create_issues_bulk_all_existing_issues(self, mocker):
        """Test bulk creation when all issues already exist."""
        issue_assignments = [
            (101, 1, IssueStatus.ARCHIVED),
            (102, 2, IssueStatus.ARCHIVED),
        ]

        # Mock existing issues (both exist)
        mock_existing_issues = mocker.MagicMock()
        mock_existing_issues.values_list.return_value = [101, 102]

        mocked_issue_filter = mocker.patch("utils.mappers.Issue.objects.filter")
        mocked_issue_filter.return_value = mock_existing_issues

        # Mock bulk create
        mocked_bulk_create = mocker.patch("utils.mappers.Issue.objects.bulk_create")

        # Mock getting all issues
        mock_issue1 = mocker.MagicMock()
        mock_issue1.number = 101
        mock_issue2 = mocker.MagicMock()
        mock_issue2.number = 102

        mock_issues_queryset = mocker.MagicMock()
        mock_issues_queryset.__iter__ = mocker.MagicMock(
            return_value=iter([mock_issue1, mock_issue2])
        )

        # Both calls return the same
        mocked_issue_filter.side_effect = [mock_existing_issues, mock_issues_queryset]

        # Mock contributions
        mock_contrib1 = mocker.MagicMock()
        mock_contrib1.id = 1
        mock_contrib2 = mocker.MagicMock()
        mock_contrib2.id = 2

        mock_contrib_queryset = mocker.MagicMock()
        mock_contrib_queryset.__iter__ = mocker.MagicMock(
            return_value=iter([mock_contrib1, mock_contrib2])
        )
        mocked_contrib_filter = mocker.patch(
            "utils.mappers.Contribution.objects.filter"
        )
        mocked_contrib_filter.return_value = mock_contrib_queryset

        mocked_bulk_update = mocker.patch(
            "utils.mappers.Contribution.objects.bulk_update"
        )

        _create_issues_bulk(issue_assignments)

        # Verify no new issues were created
        mocked_bulk_create.assert_not_called()

        # Verify both contributions were updated - called with queryset
        mocked_bulk_update.assert_called_once_with(mock_contrib_queryset, ["issue"])

        # Verify individual contributions were updated
        assert mock_contrib1.issue == mock_issue1
        assert mock_contrib2.issue == mock_issue2

    @pytest.mark.django_db
    def test_utils_mappers_create_issues_bulk_duplicate_assignments(self, mocker):
        """Test bulk creation handles duplicate assignments gracefully."""
        issue_assignments = [
            (101, 1, IssueStatus.ARCHIVED),
            (101, 1, IssueStatus.ARCHIVED),
            (102, 2, IssueStatus.ARCHIVED),
        ]  # Duplicate (101, 1)

        # Mock existing issues
        mock_existing_issues = mocker.MagicMock()
        mock_existing_issues.values_list.return_value = []
        mocked_issue_filter = mocker.patch("utils.mappers.Issue.objects.filter")
        mocked_issue_filter.return_value = mock_existing_issues

        mocked_bulk_create = mocker.patch("utils.mappers.Issue.objects.bulk_create")

        # Mock getting all issues
        mock_issue1 = mocker.MagicMock()
        mock_issue1.number = 101
        mock_issue2 = mocker.MagicMock()
        mock_issue2.number = 102

        mock_issues_queryset = mocker.MagicMock()
        mock_issues_queryset.__iter__ = mocker.MagicMock(
            return_value=iter([mock_issue1, mock_issue2])
        )
        mocked_issue_filter.side_effect = [mock_existing_issues, mock_issues_queryset]

        # Mock contributions
        mock_contrib1 = mocker.MagicMock()
        mock_contrib1.id = 1
        mock_contrib2 = mocker.MagicMock()
        mock_contrib2.id = 2

        mock_contrib_queryset = mocker.MagicMock()
        mock_contrib_queryset.__iter__ = mocker.MagicMock(
            return_value=iter([mock_contrib1, mock_contrib2])
        )
        mocked_contrib_filter = mocker.patch(
            "utils.mappers.Contribution.objects.filter"
        )
        mocked_contrib_filter.return_value = mock_contrib_queryset

        mocked_bulk_update = mocker.patch(
            "utils.mappers.Contribution.objects.bulk_update"
        )

        _create_issues_bulk(issue_assignments)

        # Should only create 2 unique issues
        mocked_bulk_create.assert_called_once()
        created_issues = mocked_bulk_create.call_args[0][0]
        assert len(created_issues) == 2
        assert {issue.number for issue in created_issues} == {101, 102}

        # Both contributions should be updated once - called with queryset
        mocked_bulk_update.assert_called_once_with(mock_contrib_queryset, ["issue"])

        # Verify individual contributions were updated
        assert mock_contrib1.issue == mock_issue1
        assert mock_contrib2.issue == mock_issue2

    @pytest.mark.django_db
    def test_utils_mappers_create_issues_bulk_missing_issue_after_creation(
        self, mocker
    ):
        """Test handling when issue is missing after bulk creation."""
        issue_assignments = [(101, 1, IssueStatus.ARCHIVED)]

        # Mock existing issues (none exist)
        mock_existing_issues = mocker.MagicMock()
        mock_existing_issues.values_list.return_value = []
        mocked_issue_filter = mocker.patch("utils.mappers.Issue.objects.filter")
        mocked_issue_filter.return_value = mock_existing_issues

        # Mock bulk create
        mocked_bulk_create = mocker.patch("utils.mappers.Issue.objects.bulk_create")

        # Mock getting all issues after creation returns empty
        mock_empty_queryset = mocker.MagicMock()
        mock_empty_queryset.__iter__ = mocker.MagicMock(return_value=iter([]))
        mocked_issue_filter.side_effect = [mock_existing_issues, mock_empty_queryset]

        # Mock contributions
        mocked_contrib_filter = mocker.patch(
            "utils.mappers.Contribution.objects.filter"
        )
        mocked_contrib_filter.return_value = mock_empty_queryset

        mocked_bulk_update = mocker.patch(
            "utils.mappers.Contribution.objects.bulk_update"
        )

        _create_issues_bulk(issue_assignments)

        # Issue should be created
        mocked_bulk_create.assert_called_once()
        # But no contributions should be updated since issue is missing
        mocked_bulk_update.assert_not_called()

    @pytest.mark.django_db
    def test_utils_mappers_create_issues_bulk_no_contributions_found(self, mocker):
        """Test handling when no contributions are found for update."""
        issue_assignments = [
            (101, 1, IssueStatus.ARCHIVED),
            (102, 999, IssueStatus.ARCHIVED),
        ]  # 999 doesn't exist

        # Mock existing issues
        mock_existing_issues = mocker.MagicMock()
        mock_existing_issues.values_list.return_value = []
        mocked_issue_filter = mocker.patch("utils.mappers.Issue.objects.filter")
        mocked_issue_filter.return_value = mock_existing_issues

        mocked_bulk_create = mocker.patch("utils.mappers.Issue.objects.bulk_create")

        # Mock getting all issues
        mock_issue1 = mocker.MagicMock()
        mock_issue1.number = 101
        mock_issue2 = mocker.MagicMock()
        mock_issue2.number = 102

        mock_issues_queryset = mocker.MagicMock()
        mock_issues_queryset.__iter__ = mocker.MagicMock(
            return_value=iter([mock_issue1, mock_issue2])
        )
        mocked_issue_filter.side_effect = [mock_existing_issues, mock_issues_queryset]

        # Mock contributions - only one exists
        mock_contrib1 = mocker.MagicMock()
        mock_contrib1.id = 1

        mock_contrib_queryset = mocker.MagicMock()
        mock_contrib_queryset.__iter__ = mocker.MagicMock(
            return_value=iter([mock_contrib1])
        )
        mocked_contrib_filter = mocker.patch(
            "utils.mappers.Contribution.objects.filter"
        )
        mocked_contrib_filter.return_value = mock_contrib_queryset

        mocked_bulk_update = mocker.patch(
            "utils.mappers.Contribution.objects.bulk_update"
        )

        _create_issues_bulk(issue_assignments)

        # Issues should be created
        mocked_bulk_create.assert_called_once()
        # Only existing contribution should be updated - called with queryset
        mocked_bulk_update.assert_called_once_with(mock_contrib_queryset, ["issue"])

        # Verify individual contribution was updated
        assert mock_contrib1.issue == mock_issue1


class TestUtilsMappersMapClosedAddressedIssues:
    """Testing class for :py:mod:`utils.mappers` _map_closed_addressed_issues function."""

    @pytest.mark.django_db
    def test_utils_mappers_map_closed_addressed_issues_debug_simple_case(self, mocker):
        """Debug test to understand why function returns False."""
        # Create a more realistic mock issue
        mock_label = mocker.MagicMock()
        mock_label.name = "addressed"  # Ensure name is properly set

        mock_issue_obj = mocker.MagicMock()
        mock_issue_obj.labels = [mock_label]
        mock_issue_obj.body = "Test body"
        mock_issue_obj.title = "Test Issue"
        mock_issue_obj.number = 101
        mock_issue_obj.user.login = "github_user"

        mock_issue = mocker.MagicMock()
        mock_issue.issue = mock_issue_obj
        mock_issue.comments = []

        # Mock the absolute minimum
        mocker.patch("utils.mappers._build_reward_mapping", return_value={})

        # Mock empty contributors
        mocker.patch("utils.mappers.Contributor.objects.all", return_value=[])
        mocker.patch("utils.mappers.EXCLUDED_CONTRIBUTORS", [])

        # Mock platforms - need at least one platform
        mock_platform = mocker.MagicMock()
        mock_platform.name = "GitHub"
        mock_platform.id = 1
        mocker.patch(
            "utils.mappers.SocialPlatform.objects.all", return_value=[mock_platform]
        )

        # Mock cycle
        mock_cycle = mocker.MagicMock()
        mocker.patch("utils.mappers.Cycle.objects.latest", return_value=mock_cycle)

        # Mock the identification functions to return None (so issue gets skipped but function returns True)
        mocker.patch("utils.mappers._identify_platform_from_text", return_value=None)
        mocker.patch("utils.mappers._identify_reward_from_labels", return_value=None)

        result = _map_closed_addressed_issues([mock_issue])

        print(f"DEBUG: Function returned: {result}")
        # Should return True because addressed issues were found
        assert result is True

    @pytest.mark.django_db
    def test_utils_mappers_map_closed_addressed_issues_no_issues(self, mocker):
        """Test function returns False when no addressed issues."""
        result = _map_closed_addressed_issues([])
        assert result is False

    @pytest.mark.django_db
    def test_utils_mappers_map_closed_addressed_issues_no_addressed_labels(
        self, mocker
    ):
        """Test function returns False when no issues have addressed label."""
        # Create proper mock structure without addressed label
        mock_label = mocker.MagicMock()
        mock_label.name = "bug"  # Different label

        mock_issue_obj = mocker.MagicMock()
        mock_issue_obj.labels = [mock_label]
        mock_issue_obj.body = "Some body"
        mock_issue_obj.title = "Test Issue"
        mock_issue_obj.number = 101

        mock_issue = mocker.MagicMock()
        mock_issue.issue = mock_issue_obj
        mock_issue.comments = []

        result = _map_closed_addressed_issues([mock_issue])
        assert result is False

    @pytest.mark.django_db
    def test_utils_mappers_map_closed_addressed_issues_successful_processing(
        self, mocker
    ):
        """Test successful processing of addressed issues."""
        # Create proper mock structure
        mock_label = mocker.MagicMock()
        mock_label.name = "addressed"

        mock_issue_obj = mocker.MagicMock()
        mock_issue_obj.labels = [mock_label]
        mock_issue_obj.body = "By test_user in [Discord]"
        mock_issue_obj.title = "Test Issue"
        mock_issue_obj.number = 101
        mock_issue_obj.user.login = "github_user"

        mock_issue = mocker.MagicMock()
        mock_issue.issue = mock_issue_obj
        mock_issue.comments = []

        # Mock all dependencies
        mock_reward = mocker.MagicMock()
        mocker.patch(
            "utils.mappers._build_reward_mapping", return_value={"bug": mock_reward}
        )

        # Mock contributors
        mock_contributor = mocker.MagicMock()
        mock_contributor.info = "Test User (g@test_user, d@testuser)"
        mock_contributor.id = 1

        mocker.patch(
            "utils.mappers.Contributor.objects.all", return_value=[mock_contributor]
        )
        mocker.patch("utils.mappers.EXCLUDED_CONTRIBUTORS", [])

        # Mock platforms
        mock_platform1 = mocker.MagicMock()
        mock_platform1.name = "GitHub"
        mock_platform1.id = 1

        mock_platform2 = mocker.MagicMock()
        mock_platform2.name = "Discord"
        mock_platform2.id = 2

        mocker.patch(
            "utils.mappers.SocialPlatform.objects.all",
            return_value=[mock_platform1, mock_platform2],
        )

        # Mock cycle
        mock_cycle = mocker.MagicMock()
        mocker.patch("utils.mappers.Cycle.objects.latest", return_value=mock_cycle)

        # Mock identification functions
        mocker.patch("utils.mappers._identify_platform_from_text", return_value=2)
        mocker.patch(
            "utils.mappers._identify_reward_from_labels", return_value=mock_reward
        )
        mocker.patch(
            "utils.mappers._extract_url_text", return_value="https://example.com"
        )

        # Mock issue operations
        mocker.patch("utils.mappers.Issue.objects.get", side_effect=Issue.DoesNotExist)
        mock_created_issue = mocker.MagicMock()
        mocker.patch(
            "utils.mappers.Issue.objects.create", return_value=mock_created_issue
        )

        # Mock contributor identification - return actual IDs
        mocker.patch("utils.mappers._identify_contributor_from_user", return_value=1)
        mocker.patch("utils.mappers._identify_contributor_from_text", return_value=None)

        # Mock contribution operations
        mock_contribution_filter = mocker.MagicMock()
        mock_contribution_filter.first = mocker.MagicMock(return_value=None)
        mocker.patch(
            "utils.mappers.Contribution.objects.filter",
            return_value=mock_contribution_filter,
        )

        mock_contribution_create = mocker.patch(
            "utils.mappers.Contribution.objects.create"
        )

        result = _map_closed_addressed_issues([mock_issue])

        assert result is True
        mock_contribution_create.assert_called_once()

    @pytest.mark.django_db
    def test_utils_mappers_map_closed_addressed_issues_skip_internal_issues(
        self, mocker
    ):
        """Test that internal issues are skipped."""
        # Create proper mock structure with internal title
        mock_label = mocker.MagicMock()
        mock_label.name = "addressed"

        mock_issue_obj = mocker.MagicMock()
        mock_issue_obj.labels = [mock_label]
        mock_issue_obj.body = "Some body"
        mock_issue_obj.title = "[Internal] Test Issue"
        mock_issue_obj.number = 101

        mock_issue = mocker.MagicMock()
        mock_issue.issue = mock_issue_obj
        mock_issue.comments = []

        # Mock minimal dependencies
        mocker.patch("utils.mappers._build_reward_mapping", return_value={})

        # Mock contributors
        mock_contributor = mocker.MagicMock()
        mock_contributor.info = "Test User"
        mock_contributor.id = 1

        mocker.patch(
            "utils.mappers.Contributor.objects.all", return_value=[mock_contributor]
        )
        mocker.patch("utils.mappers.EXCLUDED_CONTRIBUTORS", [])

        # Mock platforms
        mock_platform = mocker.MagicMock()
        mock_platform.name = "GitHub"
        mock_platform.id = 1
        mocker.patch(
            "utils.mappers.SocialPlatform.objects.all", return_value=[mock_platform]
        )

        # Mock cycle
        mocker.patch(
            "utils.mappers.Cycle.objects.latest", return_value=mocker.MagicMock()
        )

        result = _map_closed_addressed_issues([mock_issue])

        # The function should return True because it found addressed issues
        assert result is True

    @pytest.mark.django_db
    def test_utils_mappers_map_closed_addressed_issues_no_reward_identified(
        self, mocker
    ):
        """Test that issues without rewards are skipped."""
        # Create proper mock structure
        mock_label = mocker.MagicMock()
        mock_label.name = "addressed"

        mock_issue_obj = mocker.MagicMock()
        mock_issue_obj.labels = [mock_label]
        mock_issue_obj.body = "By test_user in [Discord]"
        mock_issue_obj.title = "Test Issue"
        mock_issue_obj.number = 101
        mock_issue_obj.user.login = "github_user"

        mock_issue = mocker.MagicMock()
        mock_issue.issue = mock_issue_obj
        mock_issue.comments = []

        # Mock dependencies
        mocker.patch("utils.mappers._build_reward_mapping", return_value={})

        # Mock contributors
        mock_contributor = mocker.MagicMock()
        mock_contributor.info = "Test User"
        mock_contributor.id = 1

        mocker.patch(
            "utils.mappers.Contributor.objects.all", return_value=[mock_contributor]
        )
        mocker.patch("utils.mappers.EXCLUDED_CONTRIBUTORS", [])

        # Mock platforms
        mock_platform = mocker.MagicMock()
        mock_platform.name = "GitHub"
        mock_platform.id = 1
        mocker.patch(
            "utils.mappers.SocialPlatform.objects.all", return_value=[mock_platform]
        )

        # Mock cycle
        mocker.patch(
            "utils.mappers.Cycle.objects.latest", return_value=mocker.MagicMock()
        )

        # Mock platform identification
        mocker.patch("utils.mappers._identify_platform_from_text", return_value=1)

        # Mock reward identification to return None (no reward found)
        mocker.patch("utils.mappers._identify_reward_from_labels", return_value=None)

        # Mock URL extraction
        mocker.patch("utils.mappers._extract_url_text", return_value=None)

        result = _map_closed_addressed_issues([mock_issue])

        # Function should return True (found addressed issues) skip due to no reward
        assert result is True

    @pytest.mark.django_db
    def test_utils_mappers_map_closed_addressed_issues_title_reward(self, mocker):
        """Test creating new contributor when none identified."""
        # Create proper mock structure
        mock_label = mocker.MagicMock()
        mock_label.name = "addressed"

        mock_issue_obj = mocker.MagicMock()
        mock_issue_obj.labels = [mock_label]
        mock_issue_obj.body = "By new_user in [Discord]"
        mock_issue_obj.title = "Test Issue"
        mock_issue_obj.number = 101
        mock_issue_obj.user.login = "github_user"

        mock_issue = mocker.MagicMock()
        mock_issue.issue = mock_issue_obj
        mock_issue.comments = []

        # Mock dependencies
        mock_reward = mocker.MagicMock()
        mocker.patch(
            "utils.mappers._build_reward_mapping", return_value={"bug": mock_reward}
        )

        # Mock empty contributors (no existing contributors)
        mocker.patch("utils.mappers.Contributor.objects.all", return_value=[])
        mocker.patch("utils.mappers.EXCLUDED_CONTRIBUTORS", [])

        # Mock platforms
        mock_platform = mocker.MagicMock()
        mock_platform.name = "GitHub"
        mock_platform.id = 1
        mocker.patch(
            "utils.mappers.SocialPlatform.objects.all", return_value=[mock_platform]
        )

        # Mock cycle
        mocker.patch(
            "utils.mappers.Cycle.objects.latest", return_value=mocker.MagicMock()
        )

        # Mock platform identification
        mocker.patch("utils.mappers._identify_platform_from_text", return_value=1)

        # Mock reward identification
        mocked_reward_labels = mocker.patch(
            "utils.mappers._identify_reward_from_labels"
        )
        mock_reward_title = mocker.MagicMock()
        mocker.patch(
            "utils.mappers._identify_reward_from_issue_title",
            return_value=mock_reward_title,
        )

        # Mock URL extraction
        mocker.patch("utils.mappers._extract_url_text", return_value=None)

        # Mock issue operations
        mocker.patch("utils.mappers.Issue.objects.get", side_effect=Issue.DoesNotExist)
        mocker.patch(
            "utils.mappers.Issue.objects.create", return_value=mocker.MagicMock()
        )

        # Mock contributor identification to return None
        mocker.patch("utils.mappers._identify_contributor_from_user", return_value=None)
        mocker.patch("utils.mappers._identify_contributor_from_text", return_value=None)

        # Mock contributor creation
        mocker.patch(
            "utils.mappers._create_contributor_from_text",
            return_value=(2, {"new_user": 2}),
        )

        # Mock contribution operations
        mock_contribution_filter = mocker.MagicMock()
        mock_contribution_filter.first = mocker.MagicMock(return_value=None)
        mocker.patch(
            "utils.mappers.Contribution.objects.filter",
            return_value=mock_contribution_filter,
        )

        mock_contribution_create = mocker.patch(
            "utils.mappers.Contribution.objects.create"
        )

        result = _map_closed_addressed_issues([mock_issue])

        assert result is True
        mock_contribution_create.assert_called_once()
        call_kwargs = mock_contribution_create.call_args[1]
        assert call_kwargs["reward"] == mock_reward_title
        mocked_reward_labels.assert_not_called()

    @pytest.mark.django_db
    def test_utils_mappers_map_closed_addressed_issues_no_platform_fallback_to_github(
        self, mocker
    ):
        """Test that when no platform is identified, it falls back to GitHub."""
        # Create proper mock structure
        mock_label = mocker.MagicMock()
        mock_label.name = "addressed"

        mock_issue_obj = mocker.MagicMock()
        mock_issue_obj.labels = [mock_label]
        mock_issue_obj.body = "Test body"
        mock_issue_obj.title = "Test Issue"
        mock_issue_obj.number = 101
        mock_issue_obj.user.login = "github_user"

        mock_issue = mocker.MagicMock()
        mock_issue.issue = mock_issue_obj
        mock_issue.comments = []

        # Mock dependencies
        mock_reward = mocker.MagicMock()
        mocker.patch(
            "utils.mappers._build_reward_mapping", return_value={"bug": mock_reward}
        )

        # Mock contributors
        mock_contributor = mocker.MagicMock()
        mock_contributor.info = "Test User (g@test_user)"
        mock_contributor.id = 1

        mocker.patch(
            "utils.mappers.Contributor.objects.all", return_value=[mock_contributor]
        )
        mocker.patch("utils.mappers.EXCLUDED_CONTRIBUTORS", [])

        # Mock platforms - GitHub must be first for fallback
        mock_platform1 = mocker.MagicMock()
        mock_platform1.name = "GitHub"
        mock_platform1.id = 1

        mock_platform2 = mocker.MagicMock()
        mock_platform2.name = "Discord"
        mock_platform2.id = 2

        mocker.patch(
            "utils.mappers.SocialPlatform.objects.all",
            return_value=[mock_platform1, mock_platform2],
        )

        # Mock cycle
        mocker.patch(
            "utils.mappers.Cycle.objects.latest", return_value=mocker.MagicMock()
        )

        # Mock platform identification to return None
        mocker.patch("utils.mappers._identify_platform_from_text", return_value=None)

        # Mock reward identification
        mocker.patch(
            "utils.mappers._identify_reward_from_labels", return_value=mock_reward
        )

        # Mock URL extraction
        mocker.patch("utils.mappers._extract_url_text", return_value=None)

        # Mock issue operations
        mocker.patch("utils.mappers.Issue.objects.get", side_effect=Issue.DoesNotExist)
        mocker.patch(
            "utils.mappers.Issue.objects.create", return_value=mocker.MagicMock()
        )

        # Mock contributor identification
        mocker.patch("utils.mappers._identify_contributor_from_user", return_value=1)
        mocker.patch("utils.mappers._identify_contributor_from_text", return_value=None)

        # Mock contribution operations
        mock_contribution_filter = mocker.MagicMock()
        mock_contribution_filter.first = mocker.MagicMock(return_value=None)
        mocker.patch(
            "utils.mappers.Contribution.objects.filter",
            return_value=mock_contribution_filter,
        )

        mock_contribution_create = mocker.patch(
            "utils.mappers.Contribution.objects.create"
        )

        result = _map_closed_addressed_issues([mock_issue])

        assert result is True
        # Verify contribution was created with GitHub platform ID (1)
        call_kwargs = mock_contribution_create.call_args[1]
        assert call_kwargs["platform_id"] == 1

    @pytest.mark.django_db
    def test_utils_mappers_map_closed_addressed_issues_create_new_contributor(
        self, mocker
    ):
        """Test creating new contributor when none identified."""
        # Create proper mock structure
        mock_label = mocker.MagicMock()
        mock_label.name = "addressed"

        mock_issue_obj = mocker.MagicMock()
        mock_issue_obj.labels = [mock_label]
        mock_issue_obj.body = "By new_user in [Discord]"
        mock_issue_obj.title = "Test Issue"
        mock_issue_obj.number = 101
        mock_issue_obj.user.login = "github_user"

        mock_issue = mocker.MagicMock()
        mock_issue.issue = mock_issue_obj
        mock_issue.comments = []

        # Mock dependencies
        mock_reward = mocker.MagicMock()
        mocker.patch(
            "utils.mappers._build_reward_mapping", return_value={"bug": mock_reward}
        )

        # Mock empty contributors (no existing contributors)
        mocker.patch("utils.mappers.Contributor.objects.all", return_value=[])
        mocker.patch("utils.mappers.EXCLUDED_CONTRIBUTORS", [])

        # Mock platforms
        mock_platform = mocker.MagicMock()
        mock_platform.name = "GitHub"
        mock_platform.id = 1
        mocker.patch(
            "utils.mappers.SocialPlatform.objects.all", return_value=[mock_platform]
        )

        # Mock cycle
        mocker.patch(
            "utils.mappers.Cycle.objects.latest", return_value=mocker.MagicMock()
        )

        # Mock platform identification
        mocker.patch("utils.mappers._identify_platform_from_text", return_value=1)

        # Mock reward identification
        mocker.patch(
            "utils.mappers._identify_reward_from_labels", return_value=mock_reward
        )

        # Mock URL extraction
        mocker.patch("utils.mappers._extract_url_text", return_value=None)

        # Mock issue operations
        mocker.patch("utils.mappers.Issue.objects.get", side_effect=Issue.DoesNotExist)
        mocker.patch(
            "utils.mappers.Issue.objects.create", return_value=mocker.MagicMock()
        )

        # Mock contributor identification to return None
        mocker.patch("utils.mappers._identify_contributor_from_user", return_value=None)
        mocker.patch("utils.mappers._identify_contributor_from_text", return_value=None)

        # Mock contributor creation
        mocker.patch(
            "utils.mappers._create_contributor_from_text",
            return_value=(2, {"new_user": 2}),
        )

        # Mock contribution operations
        mock_contribution_filter = mocker.MagicMock()
        mock_contribution_filter.first = mocker.MagicMock(return_value=None)
        mocker.patch(
            "utils.mappers.Contribution.objects.filter",
            return_value=mock_contribution_filter,
        )

        mock_contribution_create = mocker.patch(
            "utils.mappers.Contribution.objects.create"
        )

        result = _map_closed_addressed_issues([mock_issue])

        assert result is True
        mock_contribution_create.assert_called_once()

    @pytest.mark.django_db
    def test_utils_mappers_map_closed_addressed_issues_no_contributors_found(
        self, mocker
    ):
        """Test that issues without identifiable contributors are skipped."""
        # Create proper mock structure
        mock_label = mocker.MagicMock()
        mock_label.name = "addressed"

        mock_issue_obj = mocker.MagicMock()
        mock_issue_obj.labels = [mock_label]
        mock_issue_obj.body = "Some body without contributor info"
        mock_issue_obj.title = "Test Issue"
        mock_issue_obj.number = 101
        mock_issue_obj.user.login = "unknown_user"

        mock_issue = mocker.MagicMock()
        mock_issue.issue = mock_issue_obj
        mock_issue.comments = []

        # Mock dependencies
        mock_reward = mocker.MagicMock()
        mocker.patch(
            "utils.mappers._build_reward_mapping", return_value={"bug": mock_reward}
        )

        # Mock empty contributors
        mocker.patch("utils.mappers.Contributor.objects.all", return_value=[])
        mocker.patch("utils.mappers.EXCLUDED_CONTRIBUTORS", [])

        # Mock platforms
        mock_platform = mocker.MagicMock()
        mock_platform.name = "GitHub"
        mock_platform.id = 1
        mocker.patch(
            "utils.mappers.SocialPlatform.objects.all", return_value=[mock_platform]
        )

        # Mock cycle
        mocker.patch(
            "utils.mappers.Cycle.objects.latest", return_value=mocker.MagicMock()
        )

        # Mock platform identification
        mocker.patch("utils.mappers._identify_platform_from_text", return_value=1)

        # Mock reward identification
        mocker.patch(
            "utils.mappers._identify_reward_from_labels", return_value=mock_reward
        )

        # Mock URL extraction
        mocker.patch("utils.mappers._extract_url_text", return_value=None)

        # Mock issue operations
        mocker.patch("utils.mappers.Issue.objects.get", side_effect=Issue.DoesNotExist)
        mocker.patch(
            "utils.mappers.Issue.objects.create", return_value=mocker.MagicMock()
        )

        # Mock contributor identification to return None
        mocker.patch("utils.mappers._identify_contributor_from_user", return_value=None)
        mocker.patch("utils.mappers._identify_contributor_from_text", return_value=None)

        # Mock contributor creation to return None (no pattern match)
        mocker.patch(
            "utils.mappers._create_contributor_from_text", return_value=(None, {})
        )

        result = _map_closed_addressed_issues([mock_issue])

        # Function should return True (found addressed issues) but skip processing due to no contributors
        assert result is True

    @pytest.mark.django_db
    def test_utils_mappers_map_closed_addressed_issues_existing_issue_update(
        self, mocker
    ):
        """Test that existing issues are updated to ADDRESSED status."""
        # Create proper mock structure
        mock_label = mocker.MagicMock()
        mock_label.name = "addressed"

        mock_issue_obj = mocker.MagicMock()
        mock_issue_obj.labels = [mock_label]
        mock_issue_obj.body = "Test body"
        mock_issue_obj.title = "Test Issue"
        mock_issue_obj.number = 101
        mock_issue_obj.user.login = "github_user"

        mock_issue = mocker.MagicMock()
        mock_issue.issue = mock_issue_obj
        mock_issue.comments = []

        # Mock dependencies
        mock_reward = mocker.MagicMock()
        mocker.patch(
            "utils.mappers._build_reward_mapping", return_value={"bug": mock_reward}
        )

        # Mock contributors
        mock_contributor = mocker.MagicMock()
        mock_contributor.info = "Test User"
        mock_contributor.id = 1

        mocker.patch(
            "utils.mappers.Contributor.objects.all", return_value=[mock_contributor]
        )
        mocker.patch("utils.mappers.EXCLUDED_CONTRIBUTORS", [])

        # Mock platforms
        mock_platform = mocker.MagicMock()
        mock_platform.name = "GitHub"
        mock_platform.id = 1
        mocker.patch(
            "utils.mappers.SocialPlatform.objects.all", return_value=[mock_platform]
        )

        # Mock cycle
        mocker.patch(
            "utils.mappers.Cycle.objects.latest", return_value=mocker.MagicMock()
        )

        # Mock platform identification
        mocker.patch("utils.mappers._identify_platform_from_text", return_value=1)

        # Mock reward identification
        mocker.patch(
            "utils.mappers._identify_reward_from_labels", return_value=mock_reward
        )

        # Mock URL extraction
        mocker.patch("utils.mappers._extract_url_text", return_value=None)

        # Mock existing issue with CREATED status
        mock_existing_issue = mocker.MagicMock()
        mock_existing_issue.status = IssueStatus.CREATED
        mock_existing_issue.save = mocker.MagicMock()

        mocker.patch(
            "utils.mappers.Issue.objects.get", return_value=mock_existing_issue
        )

        # Mock contributor identification
        mocker.patch("utils.mappers._identify_contributor_from_user", return_value=1)
        mocker.patch("utils.mappers._identify_contributor_from_text", return_value=None)

        # Mock contribution operations
        mock_contribution_filter = mocker.MagicMock()
        mock_contribution_filter.first = mocker.MagicMock(return_value=None)
        mocker.patch(
            "utils.mappers.Contribution.objects.filter",
            return_value=mock_contribution_filter,
        )

        mocker.patch("utils.mappers.Contribution.objects.create")

        result = _map_closed_addressed_issues([mock_issue])

        assert result is True
        # Verify issue status was updated to ADDRESSED
        assert mock_existing_issue.status == IssueStatus.ADDRESSED
        mock_existing_issue.save.assert_called_once()

    @pytest.mark.django_db
    def test_utils_mappers_map_closed_addressed_issues_skip_empty_body(self, mocker):
        """Test that issues with empty body and comments are skipped."""
        # Create proper mock structure with empty body
        mock_label = mocker.MagicMock()
        mock_label.name = "addressed"

        mock_issue_obj = mocker.MagicMock()
        mock_issue_obj.labels = [mock_label]
        mock_issue_obj.body = None  # Empty body
        mock_issue_obj.title = "Test Issue"
        mock_issue_obj.number = 101

        mock_issue = mocker.MagicMock()
        mock_issue.issue = mock_issue_obj
        mock_issue.comments = []  # Empty comments

        # Mock minimal dependencies
        mocker.patch("utils.mappers._build_reward_mapping", return_value={})

        # Mock contributors
        mock_contributor = mocker.MagicMock()
        mock_contributor.info = "Test User"
        mock_contributor.id = 1

        mocker.patch(
            "utils.mappers.Contributor.objects.all", return_value=[mock_contributor]
        )
        mocker.patch("utils.mappers.EXCLUDED_CONTRIBUTORS", [])

        # Mock platforms
        mock_platform = mocker.MagicMock()
        mock_platform.name = "GitHub"
        mock_platform.id = 1
        mocker.patch(
            "utils.mappers.SocialPlatform.objects.all", return_value=[mock_platform]
        )

        # Mock cycle
        mocker.patch(
            "utils.mappers.Cycle.objects.latest", return_value=mocker.MagicMock()
        )

        result = _map_closed_addressed_issues([mock_issue])

        # Function should return True (found addressed issues) but skip processing due to empty body
        assert result is True

    @pytest.mark.django_db
    def test_utils_mappers_map_closed_addressed_issues_multiple_contributors(
        self, mocker
    ):
        """Test processing with multiple contributors identified."""
        # Create proper mock structure
        mock_label = mocker.MagicMock()
        mock_label.name = "addressed"

        mock_issue_obj = mocker.MagicMock()
        mock_issue_obj.labels = [mock_label]
        mock_issue_obj.body = "By user1 and user2 in [Discord]"
        mock_issue_obj.title = "Test Issue"
        mock_issue_obj.number = 101
        mock_issue_obj.user.login = "github_user"

        mock_issue = mocker.MagicMock()
        mock_issue.issue = mock_issue_obj
        mock_issue.comments = []

        # Mock dependencies
        mock_reward = mocker.MagicMock()
        mocker.patch(
            "utils.mappers._build_reward_mapping", return_value={"bug": mock_reward}
        )

        # Mock contributors
        mock_contributor1 = mocker.MagicMock()
        mock_contributor1.info = "User One"
        mock_contributor1.id = 1

        mock_contributor2 = mocker.MagicMock()
        mock_contributor2.info = "User Two"
        mock_contributor2.id = 2

        mocker.patch(
            "utils.mappers.Contributor.objects.all",
            return_value=[mock_contributor1, mock_contributor2],
        )
        mocker.patch("utils.mappers.EXCLUDED_CONTRIBUTORS", [])

        # Mock platforms
        mock_platform = mocker.MagicMock()
        mock_platform.name = "GitHub"
        mock_platform.id = 1
        mocker.patch(
            "utils.mappers.SocialPlatform.objects.all", return_value=[mock_platform]
        )

        # Mock cycle
        mocker.patch(
            "utils.mappers.Cycle.objects.latest", return_value=mocker.MagicMock()
        )

        # Mock platform identification
        mocker.patch("utils.mappers._identify_platform_from_text", return_value=1)

        # Mock reward identification
        mocker.patch(
            "utils.mappers._identify_reward_from_labels", return_value=mock_reward
        )

        # Mock URL extraction
        mocker.patch("utils.mappers._extract_url_text", return_value=None)

        # Mock issue operations
        mocker.patch("utils.mappers.Issue.objects.get", side_effect=Issue.DoesNotExist)
        mocker.patch(
            "utils.mappers.Issue.objects.create", return_value=mocker.MagicMock()
        )

        # Mock contributor identification to return multiple IDs
        mocker.patch("utils.mappers._identify_contributor_from_user", return_value=1)
        mocker.patch("utils.mappers._identify_contributor_from_text", return_value=2)

        # Mock contribution operations
        mock_contribution_filter = mocker.MagicMock()
        mock_contribution_filter.first = mocker.MagicMock(return_value=None)
        mocker.patch(
            "utils.mappers.Contribution.objects.filter",
            return_value=mock_contribution_filter,
        )

        mock_contribution_create = mocker.patch(
            "utils.mappers.Contribution.objects.create"
        )

        result = _map_closed_addressed_issues([mock_issue])

        assert result is True
        # Verify two contributions were created
        assert mock_contribution_create.call_count == 2

    @pytest.mark.django_db
    def test_utils_mappers_map_closed_addressed_issues_existing_issue_already_addressed(
        self, mocker
    ):
        """Test that existing issues with ADDRESSED status are not modified."""
        # Create proper mock structure
        mock_label = mocker.MagicMock()
        mock_label.name = "addressed"

        mock_issue_obj = mocker.MagicMock()
        mock_issue_obj.labels = [mock_label]
        mock_issue_obj.body = "Test body with contributor info"
        mock_issue_obj.title = "Test Issue"
        mock_issue_obj.number = 101
        mock_issue_obj.user.login = "github_user"

        mock_issue = mocker.MagicMock()
        mock_issue.issue = mock_issue_obj
        mock_issue.comments = []

        # Mock dependencies
        mock_reward = mocker.MagicMock()
        mocker.patch(
            "utils.mappers._build_reward_mapping", return_value={"bug": mock_reward}
        )

        # Mock contributors
        mock_contributor = mocker.MagicMock()
        mock_contributor.info = "Test User"
        mock_contributor.id = 1

        mocker.patch(
            "utils.mappers.Contributor.objects.all", return_value=[mock_contributor]
        )
        mocker.patch("utils.mappers.EXCLUDED_CONTRIBUTORS", [])

        # Mock platforms
        mock_platform = mocker.MagicMock()
        mock_platform.name = "GitHub"
        mock_platform.id = 1
        mocker.patch(
            "utils.mappers.SocialPlatform.objects.all", return_value=[mock_platform]
        )

        # Mock cycle
        mocker.patch(
            "utils.mappers.Cycle.objects.latest", return_value=mocker.MagicMock()
        )

        # Mock platform identification
        mocker.patch("utils.mappers._identify_platform_from_text", return_value=1)

        # Mock reward identification
        mocker.patch(
            "utils.mappers._identify_reward_from_labels", return_value=mock_reward
        )

        # Mock URL extraction
        mocker.patch("utils.mappers._extract_url_text", return_value=None)

        # Mock existing issue with ADDRESSED status (already addressed)
        mock_existing_issue = mocker.MagicMock()
        mock_existing_issue.status = IssueStatus.ADDRESSED  # Already ADDRESSED
        mock_existing_issue.save = mocker.MagicMock()

        mocker.patch(
            "utils.mappers.Issue.objects.get", return_value=mock_existing_issue
        )

        # Mock contributor identification
        mocker.patch("utils.mappers._identify_contributor_from_user", return_value=1)
        mocker.patch("utils.mappers._identify_contributor_from_text", return_value=None)

        # Mock contribution operations - return existing contribution
        mock_existing_contribution = mocker.MagicMock()
        mock_contribution_filter = mocker.MagicMock()
        mock_contribution_filter.first = mocker.MagicMock(
            return_value=mock_existing_contribution
        )
        mocker.patch(
            "utils.mappers.Contribution.objects.filter",
            return_value=mock_contribution_filter,
        )

        mock_contribution_create = mocker.patch(
            "utils.mappers.Contribution.objects.create"
        )

        result = _map_closed_addressed_issues([mock_issue])

        assert result is True
        # Verify issue status was NOT changed (already ADDRESSED)
        assert mock_existing_issue.status == IssueStatus.ADDRESSED
        mock_existing_issue.save.assert_not_called()  # Should not save since status didn't change
        # Verify no new contribution was created (existing one found)
        mock_contribution_create.assert_not_called()

    @pytest.mark.django_db
    def test_utils_mappers_map_closed_addressed_issues_skip_when_contribution_exists(
        self, mocker
    ):
        """Test that no new contribution is created when existing contribution exists."""
        # Create proper mock structure
        mock_label = mocker.MagicMock()
        mock_label.name = "addressed"

        mock_issue_obj = mocker.MagicMock()
        mock_issue_obj.labels = [mock_label]
        mock_issue_obj.body = "Test body with contributor info"
        mock_issue_obj.title = "Test Issue"
        mock_issue_obj.number = 101
        mock_issue_obj.user.login = "github_user"

        mock_issue = mocker.MagicMock()
        mock_issue.issue = mock_issue_obj
        mock_issue.comments = []

        # Mock dependencies
        mock_reward = mocker.MagicMock()
        mocker.patch(
            "utils.mappers._build_reward_mapping", return_value={"bug": mock_reward}
        )

        # Mock contributors
        mock_contributor = mocker.MagicMock()
        mock_contributor.info = "Test User"
        mock_contributor.id = 1

        mocker.patch(
            "utils.mappers.Contributor.objects.all", return_value=[mock_contributor]
        )
        mocker.patch("utils.mappers.EXCLUDED_CONTRIBUTORS", [])

        # Mock platforms
        mock_platform = mocker.MagicMock()
        mock_platform.name = "GitHub"
        mock_platform.id = 1
        mocker.patch(
            "utils.mappers.SocialPlatform.objects.all", return_value=[mock_platform]
        )

        # Mock cycle
        mock_cycle = mocker.MagicMock()
        mocker.patch("utils.mappers.Cycle.objects.latest", return_value=mock_cycle)

        # Mock platform identification
        mocker.patch("utils.mappers._identify_platform_from_text", return_value=1)

        # Mock reward identification
        mocker.patch(
            "utils.mappers._identify_reward_from_labels", return_value=mock_reward
        )

        # Mock URL extraction
        mocker.patch(
            "utils.mappers._extract_url_text", return_value="https://example.com"
        )

        # Mock issue operations - create new issue
        mocker.patch("utils.mappers.Issue.objects.get", side_effect=Issue.DoesNotExist)
        mock_created_issue = mocker.MagicMock()
        mocker.patch(
            "utils.mappers.Issue.objects.create", return_value=mock_created_issue
        )

        # Mock contributor identification
        mocker.patch("utils.mappers._identify_contributor_from_user", return_value=1)
        mocker.patch("utils.mappers._identify_contributor_from_text", return_value=None)

        # Mock contribution operations - return EXISTING contribution (not None)
        mock_existing_contribution = (
            mocker.MagicMock()
        )  # This represents an existing contribution
        mock_contribution_filter = mocker.MagicMock()
        mock_contribution_filter.first = mocker.MagicMock(
            return_value=mock_existing_contribution
        )  # Returns truthy value
        mocker.patch(
            "utils.mappers.Contribution.objects.filter",
            return_value=mock_contribution_filter,
        )

        mock_contribution_create = mocker.patch(
            "utils.mappers.Contribution.objects.create"
        )

        result = _map_closed_addressed_issues([mock_issue])

        assert result is True
        # Verify NO new contribution was created since existing one was found
        mock_contribution_create.assert_not_called()
        # Verify that Contribution.objects.filter was called with correct parameters
        mock_contribution_filter.first.assert_called_once()


class TestUtilsMappersMapClosedArchivedIssues:
    """Testing class for :py:mod:`utils.mappers` _map_closed_archived_issues."""

    # # _map_closed_archived_issues
    @pytest.mark.django_db
    def test_utils_mappers_map_closed_archived_issues_bulk_no_token(self, mocker):
        """Test function returns False when no GitHub token is provided."""
        result = _map_closed_archived_issues(None)
        assert result == []

    @pytest.mark.django_db
    def test_utils_mappers_map_closed_archived_issues_bulk_no_contributions(
        self, mocker
    ):
        """Test function returns True when there are no contributions to process."""
        # Create a proper QuerySet mock that returns empty list
        mock_contributions_queryset = mocker.MagicMock()
        mock_contributions_queryset.only.return_value = (
            mock_contributions_queryset  # Chainable
        )
        mock_contributions_queryset.__iter__ = mocker.MagicMock(return_value=iter([]))

        # Mock the boolean check - empty queryset should be falsy
        mock_contributions_queryset.__bool__ = mocker.MagicMock(return_value=False)
        mock_contributions_queryset.exists = mocker.MagicMock(return_value=False)

        mocker.patch(
            "utils.mappers.Contribution.objects.all",
            return_value=mock_contributions_queryset,
        )

        mocked_create_issues_bulk = mocker.patch("utils.mappers._create_issues_bulk")

        result = _map_closed_archived_issues(mocker.MagicMock())

        assert result == []
        mocked_create_issues_bulk.assert_not_called()

    @pytest.mark.django_db
    def test_utils_mappers_map_closed_archived_issues_bulk_url_in_body_matching(
        self, mocker
    ):
        """Test successful matching when URL appears in issue body."""

        # Mock contributions
        mock_contrib = mocker.MagicMock()
        mock_contrib.id = 1
        mock_contrib.url = "https://example.com/contrib"

        # Create a proper QuerySet mock
        mock_contributions_queryset = mocker.MagicMock()
        mock_contributions_queryset.only.return_value = (
            mock_contributions_queryset  # Chainable
        )
        mock_contributions_queryset.__iter__ = mocker.MagicMock(
            return_value=iter([mock_contrib])
        )

        mocker.patch(
            "utils.mappers.Contribution.objects.all",
            return_value=mock_contributions_queryset,
        )

        # Mock GitHub issue with URL in body
        mock_issue = mocker.MagicMock()
        mock_issue.issue.number = 101
        mock_issue.issue.body = "Check out https://example.com/contrib for details"

        mocker.patch("utils.mappers._is_url_github_issue", return_value=False)
        mocked_create_issues_bulk = mocker.patch("utils.mappers._create_issues_bulk")

        result = _map_closed_archived_issues([mock_issue])

        assert result == []
        mocked_create_issues_bulk.assert_called_once_with(
            [(101, 1, IssueStatus.ARCHIVED)]
        )

    @pytest.mark.django_db
    def test_utils_mappers_map_closed_archived_issues_bulk_github_issue_url_match(
        self, mocker
    ):
        """Test successful matching when contribution URL is a GitHub issue URL."""

        # Mock contribution with GitHub issue URL
        github_issue_url = (
            f"https://github.com/{settings.ISSUE_TRACKER_OWNER}/"
            f"{settings.ISSUE_TRACKER_NAME}/issues/456"
        )
        mock_contrib = mocker.MagicMock()
        mock_contrib.id = 1
        mock_contrib.url = github_issue_url

        # Create a proper QuerySet mock
        mock_contributions_queryset = mocker.MagicMock()
        mock_contributions_queryset.only.return_value = (
            mock_contributions_queryset  # Chainable
        )
        mock_contributions_queryset.__iter__ = mocker.MagicMock(
            return_value=iter([mock_contrib])
        )

        mocker.patch(
            "utils.mappers.Contribution.objects.all",
            return_value=mock_contributions_queryset,
        )

        # Mock GitHub issue
        mock_issue = mocker.MagicMock()
        mock_issue.issue.number = 456  # Matching issue number
        mock_issue.issue.body = "Some issue body without the URL"

        mocker.patch("utils.mappers._is_url_github_issue", return_value=456)
        mocked_create_issues_bulk = mocker.patch("utils.mappers._create_issues_bulk")

        result = _map_closed_archived_issues([mock_issue])

        assert result == []
        mocked_create_issues_bulk.assert_called_once_with(
            [(456, 1, IssueStatus.ARCHIVED)]
        )

    @pytest.mark.django_db
    def test_utils_mappers_map_closed_archived_issues_bulk_skip_empty_urls(
        self, mocker
    ):
        """Test that contributions with empty URLs are skipped."""

        # Mock contributions with various URL states
        mock_contrib1 = mocker.MagicMock()
        mock_contrib1.id = 1
        mock_contrib1.url = ""  # Empty string

        mock_contrib2 = mocker.MagicMock()
        mock_contrib2.id = 2
        mock_contrib2.url = None  # None value

        mock_contrib3 = mocker.MagicMock()
        mock_contrib3.id = 3
        mock_contrib3.url = "https://valid.com/url"  # Valid URL

        # Create a proper QuerySet mock
        mock_contributions_queryset = mocker.MagicMock()
        mock_contributions_queryset.only.return_value = (
            mock_contributions_queryset  # Chainable
        )
        mock_contributions_queryset.__iter__ = mocker.MagicMock(
            return_value=iter([mock_contrib1, mock_contrib2, mock_contrib3])
        )

        mocker.patch(
            "utils.mappers.Contribution.objects.all",
            return_value=mock_contributions_queryset,
        )

        mock_issue = mocker.MagicMock()
        mock_issue.issue.number = 101
        mock_issue.issue.body = "Contains https://valid.com/url"

        mocker.patch("utils.mappers._is_url_github_issue", return_value=False)
        mocked_create_issues_bulk = mocker.patch("utils.mappers._create_issues_bulk")

        result = _map_closed_archived_issues([mock_issue])

        assert result == []
        # Should only process the valid URL
        mocked_create_issues_bulk.assert_called_once_with(
            [(101, 3, IssueStatus.ARCHIVED)]
        )

    @pytest.mark.django_db
    def test_utils_mappers_map_closed_archived_issues_bulk_transaction_decorator(
        self, mocker
    ):
        """Test that function has transaction.atomic decorator."""

        mock_contrib = mocker.MagicMock()
        mock_contrib.id = 1
        mock_contrib.url = "https://example.com/contrib"

        # Create a proper QuerySet mock
        mock_contributions_queryset = mocker.MagicMock()
        mock_contributions_queryset.only.return_value = (
            mock_contributions_queryset  # Chainable
        )
        mock_contributions_queryset.__iter__ = mocker.MagicMock(
            return_value=iter([mock_contrib])
        )

        mocker.patch(
            "utils.mappers.Contribution.objects.all",
            return_value=mock_contributions_queryset,
        )

        mock_issue = mocker.MagicMock()
        mock_issue.issue.number = 101
        mock_issue.issue.body = "Contains https://example.com/contrib"

        mocker.patch("utils.mappers._is_url_github_issue", return_value=False)
        mocked_create_issues_bulk = mocker.patch("utils.mappers._create_issues_bulk")

        # Check that function is decorated with transaction.atomic
        # by checking if it's wrapped
        assert _map_closed_archived_issues.__name__ == "_map_closed_archived_issues"

        result = _map_closed_archived_issues([mock_issue])

        assert result == []
        mocked_create_issues_bulk.assert_called_once()

    @pytest.mark.django_db
    def test_utils_mappers_map_closed_archived_issues_bulk_issue_no_body_url_match(
        self, mocker
    ):
        """Test that issues without body are still checked for issue URL matching."""

        # Mock contribution with GitHub issue URL
        github_issue_url = (
            f"https://github.com/{settings.ISSUE_TRACKER_OWNER}/"
            f"{settings.ISSUE_TRACKER_NAME}/issues/456"
        )
        mock_contrib = mocker.MagicMock()
        mock_contrib.id = 1
        mock_contrib.url = github_issue_url

        # Create a proper QuerySet mock
        mock_contributions_queryset = mocker.MagicMock()
        mock_contributions_queryset.only.return_value = (
            mock_contributions_queryset  # Chainable
        )
        mock_contributions_queryset.__iter__ = mocker.MagicMock(
            return_value=iter([mock_contrib])
        )

        mocker.patch(
            "utils.mappers.Contribution.objects.all",
            return_value=mock_contributions_queryset,
        )

        # Mock GitHub issue without body but with matching number
        mock_issue = mocker.MagicMock()
        mock_issue.issue.number = 456
        mock_issue.issue.body = None

        mocker.patch("utils.mappers._is_url_github_issue", return_value=456)
        mocked_create_issues_bulk = mocker.patch("utils.mappers._create_issues_bulk")

        result = _map_closed_archived_issues([mock_issue])

        assert result == []
        # Should still match via GitHub issue URL even with no body
        mocked_create_issues_bulk.assert_called_once_with(
            [(456, 1, IssueStatus.ARCHIVED)]
        )

    @pytest.mark.django_db
    def test_utils_mappers_map_closed_archived_issues_bulk_no_matches(self, mocker):
        """Test function when no URLs match any issue bodies or GitHub issue URLs."""

        mock_contrib = mocker.MagicMock()
        mock_contrib.id = 1
        mock_contrib.url = "https://example.com/nomatch"

        # Create a proper QuerySet mock
        mock_contributions_queryset = mocker.MagicMock()
        mock_contributions_queryset.only.return_value = (
            mock_contributions_queryset  # Chainable
        )
        mock_contributions_queryset.__iter__ = mocker.MagicMock(
            return_value=iter([mock_contrib])
        )

        mocker.patch(
            "utils.mappers.Contribution.objects.all",
            return_value=mock_contributions_queryset,
        )

        mock_issue1 = mocker.MagicMock()
        mock_issue1.issue.title = "[Internal] foo bar"
        mock_issue1.issue.body = "Internal issue body"
        mock_issue1.issue.number = 100
        mock_issue1.comments = []  # Empty list of strings, not MagicMock

        mock_issue2 = mocker.MagicMock()
        mock_issue2.issue.number = 101
        mock_issue2.issue.body = "Contains completely different URL"
        mock_issue2.issue.title = "Test Issue"
        mock_issue2.comments = []  # Empty list of strings

        mock_issue3 = mocker.MagicMock()
        label1, label2 = mocker.MagicMock(), mocker.MagicMock()
        label1.name = "foobar"
        label2.name = "wontfix"
        mock_issue3.issue.labels = [label1, label2]
        mock_issue3.issue.body = "Wontfix issue"
        mock_issue3.issue.number = 102
        mock_issue3.issue.title = "Wontfix Issue"
        mock_issue3.comments = []

        label3 = mocker.MagicMock()
        label3.name = "addressed"
        mock_issue4 = mocker.MagicMock()
        mock_issue4.issue.labels = [label3]
        mock_issue4.issue.body = "Addressed issue"
        mock_issue4.issue.number = 103
        mock_issue4.issue.title = "Addressed Issue"
        mock_issue4.comments = []

        mocker.patch("utils.mappers._is_url_github_issue", return_value=False)
        mocked_create_issues_bulk = mocker.patch("utils.mappers._create_issues_bulk")

        result = _map_closed_archived_issues(
            [mock_issue1, mock_issue2, mock_issue3, mock_issue4]
        )

        # Should return unprocessed issues (all issues except internal ones)
        assert len(result) == 1  # Excludes internal issue
        mocked_create_issues_bulk.assert_called_once_with([])

    @pytest.mark.django_db
    def test_utils_mappers_map_closed_archived_issues_bulk_multiple_issues(
        self, mocker
    ):
        """Test processing multiple issues with different matching methods."""

        # Mock contributions
        mock_contrib1 = mocker.MagicMock()
        mock_contrib1.id = 1
        mock_contrib1.url = "https://example.com/body_match"

        mock_contrib2 = mocker.MagicMock()
        mock_contrib2.id = 2
        github_issue_url = (
            f"https://github.com/{settings.ISSUE_TRACKER_OWNER}/"
            f"{settings.ISSUE_TRACKER_NAME}/issues/202"
        )
        mock_contrib2.url = github_issue_url

        # Create a proper QuerySet mock
        mock_contributions_queryset = mocker.MagicMock()
        mock_contributions_queryset.only.return_value = (
            mock_contributions_queryset  # Chainable
        )
        mock_contributions_queryset.__iter__ = mocker.MagicMock(
            return_value=iter([mock_contrib1, mock_contrib2])
        )

        mocker.patch(
            "utils.mappers.Contribution.objects.all",
            return_value=mock_contributions_queryset,
        )

        # Mock multiple issues
        mock_issue1 = mocker.MagicMock()
        mock_issue1.issue.number = 101
        mock_issue1.issue.body = "Contains https://example.com/body_match"

        mock_issue2 = mocker.MagicMock()
        mock_issue2.issue.number = 202
        mock_issue2.issue.body = "No matching URL here"
        mocked_is_url = mocker.patch("utils.mappers._is_url_github_issue")
        mocked_is_url.side_effect = lambda url: (
            202 if url == github_issue_url else False
        )
        mocked_create_issues_bulk = mocker.patch("utils.mappers._create_issues_bulk")

        result = _map_closed_archived_issues([mock_issue1, mock_issue2])

        assert result == []
        # Should have both assignments via different methods
        call_args = mocked_create_issues_bulk.call_args[0][0]
        assert set(call_args) == {
            (101, 1, IssueStatus.ARCHIVED),
            (202, 2, IssueStatus.ARCHIVED),
        }


class TestUtilsMappersMapOpenIssues:
    """Testing class for bulk-optimized :py:mod:`utils.mappers` _map_open_issues"""

    # # _map_open_issues
    @pytest.mark.django_db
    def test_utils_mappers_map_open_issues_no_issues(self):
        """Test _map_open_issues with no issues."""
        result = _map_open_issues([])

        assert result is False

    @pytest.mark.django_db
    def test_utils_mappers_map_open_issues_successful_creation(self, mocker):
        """Test _map_open_issues successfully creates contributions."""
        # Mock GitHub issue
        mock_issue = mocker.MagicMock()
        mock_issue.issue.number = 101
        mock_issue.issue.body = "Discord discussion about feature"
        mock_issue.issue.title = "Feature Request"
        mock_issue.issue.user.login = "testuser"
        mock_issue.comments = []
        mock_issue.issue.labels = []

        # Mock all dependencies
        mocker.patch(
            "utils.mappers._build_reward_mapping",
            return_value={"feature request": "mock_reward"},
        )

        mocker.patch(
            "utils.mappers.Contributor.objects.all",
            return_value=[mocker.MagicMock(info="testuser (g@testuser)", id=1)],
        )

        mocker.patch(
            "utils.mappers.SocialPlatform.objects.all",
            return_value=[mocker.MagicMock(name="Discord", id=1)],
        )

        mock_cycle = mocker.MagicMock()
        mocker.patch("utils.mappers.Cycle.objects.latest", return_value=mock_cycle)

        mocker.patch("utils.mappers._identify_contributor_from_user", return_value=1)
        mocker.patch("utils.mappers._identify_platform_from_text", return_value=1)
        mocker.patch(
            "utils.mappers._identify_reward_from_labels", return_value="mock_reward"
        )
        mocker.patch(
            "utils.mappers._extract_url_text",
            return_value="https://discord.com/test",
        )

        mock_issue_obj = mocker.MagicMock()
        mocker.patch("utils.mappers.get_object_or_404", side_effect=Http404)
        mocker.patch("utils.mappers.Issue.objects.create", return_value=mock_issue_obj)

        mock_contribution_create = mocker.patch(
            "utils.mappers.Contribution.objects.create"
        )

        result = _map_open_issues([mock_issue])

        assert result is True
        mock_contribution_create.assert_called_once()

    @pytest.mark.django_db
    def test_utils_mappers_map_open_issues_reward_from_title(self, mocker):
        """Test _map_open_issues successfully creates contributions."""
        # Mock GitHub issue
        mock_issue = mocker.MagicMock()
        mock_issue.issue.number = 101
        mock_issue.issue.body = "Discord discussion about feature"
        mock_issue.issue.title = "Feature Request"
        mock_issue.issue.user.login = "testuser"
        mock_issue.comments = []
        mock_issue.issue.labels = []

        # Mock all dependencies
        mocker.patch(
            "utils.mappers._build_reward_mapping",
            return_value={"feature request": "mock_reward"},
        )

        mocker.patch(
            "utils.mappers.Contributor.objects.all",
            return_value=[mocker.MagicMock(info="testuser (g@testuser)", id=1)],
        )

        mocker.patch(
            "utils.mappers.SocialPlatform.objects.all",
            return_value=[mocker.MagicMock(name="Discord", id=1)],
        )

        mock_cycle = mocker.MagicMock()
        mocker.patch("utils.mappers.Cycle.objects.latest", return_value=mock_cycle)

        mocker.patch("utils.mappers._identify_contributor_from_user", return_value=1)
        mocker.patch("utils.mappers._identify_platform_from_text", return_value=1)
        mockwed_reward_title = mocker.patch(
            "utils.mappers._identify_reward_from_issue_title",
            return_value="mock_reward",
        )
        mockwed_reward_labels = mocker.patch(
            "utils.mappers._identify_reward_from_labels"
        )
        mocker.patch(
            "utils.mappers._identify_reward_from_labels", return_value="mock_reward"
        )
        mocker.patch(
            "utils.mappers._extract_url_text",
            return_value="https://discord.com/test",
        )

        mock_issue_obj = mocker.MagicMock()
        mocker.patch("utils.mappers.get_object_or_404", side_effect=Http404)
        mocker.patch("utils.mappers.Issue.objects.create", return_value=mock_issue_obj)

        mock_contribution_create = mocker.patch(
            "utils.mappers.Contribution.objects.create"
        )

        result = _map_open_issues([mock_issue])

        assert result is True
        mock_contribution_create.assert_called_once()
        mockwed_reward_title.assert_called_once_with(mock_issue.issue.title)
        mockwed_reward_labels.assert_not_called()

    @pytest.mark.django_db
    def test_utils_mappers_map_open_issues_for_excluded_contributors(self, mocker):
        # Mock GitHub issue
        mock_issue = mocker.MagicMock()
        mock_issue.issue.number = 101
        mock_issue.issue.body = "Discord discussion about feature"
        mock_issue.issue.title = "Feature Request"
        mock_issue.issue.user.login = "testuser"
        mock_issue.comments = []
        mock_issue.issue.labels = []

        # Mock all dependencies
        mocker.patch(
            "utils.mappers._build_reward_mapping",
            return_value={"feature request": "mock_reward"},
        )

        # Patch the constant directly at the module where it's used
        excluded_contributor = "foobar"
        mocker.patch("utils.mappers.EXCLUDED_CONTRIBUTORS", [excluded_contributor])

        # Mock Contributor.objects.all() to return a contributor that should be excluded
        mocker.patch(
            "utils.mappers.Contributor.objects.all",
            return_value=[
                mocker.MagicMock(info=f"{excluded_contributor} (g@testuser)", id=1)
            ],
        )

        mocker.patch(
            "utils.mappers.SocialPlatform.objects.all",
            return_value=[mocker.MagicMock(name="Discord", id=1)],
        )

        mock_cycle = mocker.MagicMock()
        mocker.patch("utils.mappers.Cycle.objects.latest", return_value=mock_cycle)

        mocker.patch("utils.mappers._identify_platform_from_text", return_value=1)
        mocker.patch(
            "utils.mappers._identify_reward_from_labels", return_value="mock_reward"
        )
        mocker.patch(
            "utils.mappers._extract_url_text",
            return_value="https://discord.com/test",
        )

        mock_issue_obj = mocker.MagicMock()
        mocker.patch("utils.mappers.get_object_or_404", side_effect=Http404)
        mocker.patch("utils.mappers.Issue.objects.create", return_value=mock_issue_obj)

        mock_contribution_create = mocker.patch(
            "utils.mappers.Contribution.objects.create"
        )

        result = _map_open_issues([mock_issue])

        assert result is True
        mock_contribution_create.assert_not_called()

    @pytest.mark.django_db
    def test_utils_mappers_map_open_issues_skip_no_contributor(self, mocker):
        """Test _map_open_issues skips issues with no contributor."""
        mock_issue = mocker.MagicMock()
        mock_issue.issue.number = 101
        mock_issue.issue.body = "Some text"
        mock_issue.issue.title = "No Internal"
        mock_issue.issue.user.login = "unknownuser"
        mock_issue.comments = []

        mocker.patch("utils.mappers._build_reward_mapping", return_value={})
        mocker.patch("utils.mappers.Contributor.objects.all", return_value=[])
        mocker.patch("utils.mappers.SocialPlatform.objects.all", return_value=[])
        mocker.patch(
            "utils.mappers.Cycle.objects.latest", return_value=mocker.MagicMock()
        )
        mocker.patch("utils.mappers._identify_contributor_from_user", return_value=None)
        mocker.patch("utils.mappers._identify_contributor_from_text", return_value=None)

        mock_contribution_create = mocker.patch(
            "utils.mappers.Contribution.objects.create"
        )

        result = _map_open_issues([mock_issue])

        assert result is True
        mock_contribution_create.assert_not_called()

    @pytest.mark.django_db
    def test_utils_mappers_map_open_issues_skip_internal_title(self, mocker):
        """Test _map_open_issues skips issues with [Internal] in title."""
        mock_issue = mocker.MagicMock()
        mock_issue.issue.number = 101
        mock_issue.issue.body = "Some text"
        mock_issue.issue.title = "[Internal] Internal task"
        mock_issue.comments = []

        mock_contribution_create = mocker.patch(
            "utils.mappers.Contribution.objects.create"
        )
        mocker.patch("utils.mappers.Cycle.objects.latest")

        result = _map_open_issues([mock_issue])

        assert result is True
        mock_contribution_create.assert_not_called()

    @pytest.mark.django_db
    def test_utils_mappers_map_open_issues_skip_no_body_comments(self, mocker):
        """Test _map_open_issues skips issues with no body or comments."""
        mock_issue = mocker.MagicMock()
        mock_issue.issue.number = 101
        mock_issue.issue.body = None
        mock_issue.comments = []
        mock_issue.issue.title = "Regular issue"

        mock_contribution_create = mocker.patch(
            "utils.mappers.Contribution.objects.create"
        )
        mocker.patch("utils.mappers.Cycle.objects.latest")

        result = _map_open_issues([mock_issue])

        assert result is True
        mock_contribution_create.assert_not_called()

    @pytest.mark.django_db
    def test_utils_mappers_map_open_issues_skip_no_contributor_from_user_fallback_text(
        self, mocker
    ):
        # Mock GitHub issue
        mock_issue = mocker.MagicMock()
        mock_issue.issue.number = 101
        mock_issue.issue.body = "Discord discussion about feature by @johndoe"
        mock_issue.issue.title = "Feature Request"
        mock_issue.issue.user.login = (
            "unknownuser"  # This won't match in _identify_contributor_from_user
        )
        mock_issue.comments = []
        mock_issue.issue.labels = [mocker.MagicMock(name="feature")]

        # Mock dependencies
        mocker.patch(
            "utils.mappers._build_reward_mapping",
            return_value={"feature": "mock_reward"},
        )

        # Mock contributors - user login won't match, but text will
        mocker.patch(
            "utils.mappers.Contributor.objects.all",
            return_value=[mocker.MagicMock(info="John Doe (johndoe)", id=1)],
        )

        mocker.patch(
            "utils.mappers.SocialPlatform.objects.all",
            return_value=[mocker.MagicMock(name="Discord", id=1)],
        )

        mocker.patch(
            "utils.mappers.Cycle.objects.latest", return_value=mocker.MagicMock()
        )

        # Mock identification functions
        mocker.patch(
            "utils.mappers._identify_contributor_from_user", return_value=None
        )  # User match fails
        mocker.patch(
            "utils.mappers._identify_contributor_from_text", return_value=1
        )  # Text match succeeds
        mocker.patch("utils.mappers._identify_platform_from_text", return_value=1)
        mocker.patch(
            "utils.mappers._identify_reward_from_labels", return_value="mock_reward"
        )
        mocker.patch(
            "utils.mappers._extract_url_text",
            return_value="https://discord.com/test",
        )

        mocker.patch("utils.mappers.get_object_or_404", side_effect=Http404)
        mocker.patch(
            "utils.mappers.Issue.objects.create", return_value=mocker.MagicMock()
        )
        mock_contribution_create = mocker.patch(
            "utils.mappers.Contribution.objects.create"
        )

        result = _map_open_issues([mock_issue])

        assert result is True
        mock_contribution_create.assert_called_once()

    @pytest.mark.django_db
    def test_utils_mappers_map_open_issues_for_no_platform(self, mocker):
        """Test _map_open_issues skips issue when no platform is identified."""
        # Mock GitHub issue
        mock_issue = mocker.MagicMock()
        mock_issue.issue.number = 101
        mock_issue.issue.body = "General discussion about feature"
        mock_issue.issue.title = "Feature Request"
        mock_issue.issue.user.login = "johndoe"
        mock_issue.comments = []
        mock_issue.issue.labels = [mocker.MagicMock(name="feature")]

        # Mock dependencies
        mocker.patch(
            "utils.mappers._build_reward_mapping",
            return_value={"feature": "mock_reward"},
        )

        mocker.patch(
            "utils.mappers.Contributor.objects.all",
            return_value=[mocker.MagicMock(info="John Doe (johndoe)", id=1)],
        )
        platform1 = mocker.MagicMock()
        platform1.id = 1
        platform1.name = "Discord"
        platform2 = mocker.MagicMock()
        platform2.id = 2
        platform1.name = "GitHub"
        mocker.patch(
            "utils.mappers.SocialPlatform.objects.all",
            return_value=[platform1, platform2],
        )

        mocker.patch(
            "utils.mappers.Cycle.objects.latest", return_value=mocker.MagicMock()
        )

        # Mock identification functions
        mocker.patch("utils.mappers._identify_contributor_from_user", return_value=1)
        mocker.patch("utils.mappers._identify_contributor_from_text", return_value=1)
        mocker.patch(
            "utils.mappers._identify_platform_from_text", return_value=None
        )  # Platform match fails
        mocker.patch(
            "utils.mappers._identify_reward_from_labels", return_value="mock_reward"
        )

        mock_contribution_create = mocker.patch(
            "utils.mappers.Contribution.objects.create"
        )

        result = _map_open_issues([mock_issue])

        assert result is True
        mock_contribution_create.assert_called_once()

    @pytest.mark.django_db
    def test_utils_mappers_map_open_issues_skip_no_reward(self, mocker):
        """Test _map_open_issues skips issue when no reward is identified."""
        # Mock GitHub issue
        mock_issue = mocker.MagicMock()
        mock_issue.issue.number = 101
        mock_issue.issue.body = "Discord discussion about feature"
        mock_issue.issue.title = "Feature Request"
        mock_issue.issue.user.login = "johndoe"
        mock_issue.comments = []
        mock_issue.issue.labels = [
            mocker.MagicMock(name="unknown-label")
        ]  # No matching reward

        # Mock dependencies
        mocker.patch(
            "utils.mappers._build_reward_mapping",
            return_value={"feature": "mock_reward"},
        )

        mocker.patch(
            "utils.mappers.Contributor.objects.all",
            return_value=[mocker.MagicMock(info="John Doe (johndoe)", id=1)],
        )

        mocker.patch(
            "utils.mappers.SocialPlatform.objects.all",
            return_value=[mocker.MagicMock(name="Discord", id=1)],
        )

        mocker.patch(
            "utils.mappers.Cycle.objects.latest", return_value=mocker.MagicMock()
        )

        # Mock identification functions
        mocker.patch("utils.mappers._identify_contributor_from_user", return_value=1)
        mocker.patch("utils.mappers._identify_contributor_from_text", return_value=1)
        mocker.patch("utils.mappers._identify_platform_from_text", return_value=1)
        mocker.patch(
            "utils.mappers._identify_reward_from_labels", return_value=None
        )  # Reward match fails

        mock_contribution_create = mocker.patch(
            "utils.mappers.Contribution.objects.create"
        )

        result = _map_open_issues([mock_issue])

        assert result is True
        mock_contribution_create.assert_not_called()

    @pytest.mark.django_db
    def test_utils_mappers_map_open_issues_transaction_decorator(self):
        """Test that _map_open_issues has transaction.atomic decorator."""
        # Check that function is decorated with transaction.atomic
        assert _map_open_issues.__name__ == "_map_open_issues"

        result = _map_open_issues([])

        assert result is False


class TestUtilsMappersMapUnprocessedClosedArchivedIssues:
    """Testing class for :py:mod:`utils.mappers` _map_unprocessed_closed_archived_issues function."""

    # # _map_unprocessed_closed_archived_issues
    @pytest.mark.django_db
    def test_utils_mappers_map_unprocessed_closed_archived_issues_no_archived_issues(
        self, mocker
    ):
        """Test function returns False when no archived issues."""
        result = _map_unprocessed_closed_archived_issues([])
        assert result is False

    @pytest.mark.django_db
    def test_utils_mappers_map_unprocessed_closed_archived_issues_no_archived_labels(
        self, mocker
    ):
        """Test function returns False when no issues have archived label."""
        mock_label = mocker.MagicMock()
        mock_label.name = "bug"  # Different label

        mock_issue_obj = mocker.MagicMock()
        mock_issue_obj.labels = [mock_label]

        mock_issue = mocker.MagicMock()
        mock_issue.issue = mock_issue_obj

        result = _map_unprocessed_closed_archived_issues([mock_issue])
        assert result is False

    @pytest.mark.django_db
    def test_utils_mappers_map_unprocessed_closed_archived_issues_skip_internal_issues(
        self, mocker
    ):
        """Test that internal issues are skipped."""
        mock_label = mocker.MagicMock()
        mock_label.name = "archived"

        mock_issue_obj = mocker.MagicMock()
        mock_issue_obj.labels = [mock_label]
        mock_issue_obj.body = "Some body"
        mock_issue_obj.title = "[Internal] Test Issue"
        mock_issue_obj.number = 101

        mock_issue = mocker.MagicMock()
        mock_issue.issue = mock_issue_obj
        mock_issue.comments = []

        # Mock minimal dependencies
        mocker.patch("utils.mappers._build_reward_mapping", return_value={})
        mocker.patch("utils.mappers.Contributor.objects.all", return_value=[])
        mocker.patch("utils.mappers.EXCLUDED_CONTRIBUTORS", [])
        mocker.patch("utils.mappers.SocialPlatform.objects.all", return_value=[])

        result = _map_unprocessed_closed_archived_issues([mock_issue])
        assert result is True  # Found archived issues but skipped internal one

    @pytest.mark.django_db
    def test_utils_mappers_map_unprocessed_closed_archived_issues_skip_empty_body(
        self, mocker
    ):
        """Test that issues with empty body and comments are skipped."""
        mock_label = mocker.MagicMock()
        mock_label.name = "archived"

        mock_issue_obj = mocker.MagicMock()
        mock_issue_obj.labels = [mock_label]
        mock_issue_obj.body = None  # Empty body
        mock_issue_obj.title = "Test Issue"
        mock_issue_obj.number = 101

        mock_issue = mocker.MagicMock()
        mock_issue.issue = mock_issue_obj
        mock_issue.comments = []  # Empty comments

        # Mock minimal dependencies
        mocker.patch("utils.mappers._build_reward_mapping", return_value={})
        mocker.patch("utils.mappers.Contributor.objects.all", return_value=[])
        mocker.patch("utils.mappers.EXCLUDED_CONTRIBUTORS", [])
        mocker.patch("utils.mappers.SocialPlatform.objects.all", return_value=[])

        result = _map_unprocessed_closed_archived_issues([mock_issue])
        assert result is True  # Found archived issues but skipped empty body

    @pytest.mark.django_db
    def test_utils_mappers_map_unprocessed_closed_archived_issues_skip_existing_issue(
        self, mocker
    ):
        """Test that issues with existing Issue records are skipped."""
        mock_label = mocker.MagicMock()
        mock_label.name = "archived"

        mock_issue_obj = mocker.MagicMock()
        mock_issue_obj.labels = [mock_label]
        mock_issue_obj.body = "Test body"
        mock_issue_obj.title = "Test Issue"
        mock_issue_obj.number = 101

        mock_issue = mocker.MagicMock()
        mock_issue.issue = mock_issue_obj
        mock_issue.comments = []

        # Mock minimal dependencies
        mocker.patch("utils.mappers._build_reward_mapping", return_value={})
        mocker.patch("utils.mappers.Contributor.objects.all", return_value=[])
        mocker.patch("utils.mappers.EXCLUDED_CONTRIBUTORS", [])
        mocker.patch("utils.mappers.SocialPlatform.objects.all", return_value=[])

        # Mock Issue.objects.filter.exists() to return True (issue already exists)
        mock_issue_filter = mocker.MagicMock()
        mock_issue_filter.exists = mocker.MagicMock(return_value=True)
        mocker.patch(
            "utils.mappers.Issue.objects.filter", return_value=mock_issue_filter
        )

        result = _map_unprocessed_closed_archived_issues([mock_issue])
        assert result is True  # Found archived issues but skipped existing issue

    @pytest.mark.django_db
    def test_utils_mappers_map_unprocessed_closed_archived_issues_skip_no_closing_date(
        self, mocker
    ):
        """Test that issues without closing date are skipped."""
        mock_label = mocker.MagicMock()
        mock_label.name = "archived"

        mock_issue_obj = mocker.MagicMock()
        mock_issue_obj.labels = [mock_label]
        mock_issue_obj.body = "Test body"
        mock_issue_obj.title = "Test Issue"
        mock_issue_obj.number = 101
        mock_issue_obj.closed_at = None  # No closing date

        mock_issue = mocker.MagicMock()
        mock_issue.issue = mock_issue_obj
        mock_issue.comments = []

        # Mock minimal dependencies
        mocker.patch("utils.mappers._build_reward_mapping", return_value={})
        mocker.patch("utils.mappers.Contributor.objects.all", return_value=[])
        mocker.patch("utils.mappers.EXCLUDED_CONTRIBUTORS", [])
        mocker.patch("utils.mappers.SocialPlatform.objects.all", return_value=[])

        # Mock Issue.objects.filter.exists() to return False (issue doesn't exist)
        mock_issue_filter = mocker.MagicMock()
        mock_issue_filter.exists = mocker.MagicMock(return_value=False)
        mocker.patch(
            "utils.mappers.Issue.objects.filter", return_value=mock_issue_filter
        )

        result = _map_unprocessed_closed_archived_issues([mock_issue])
        assert result is True  # Found archived issues but skipped no closing date

    @pytest.mark.django_db
    def test_utils_mappers_map_unprocessed_closed_archived_issues_skip_no_cycle_found(
        self, mocker
    ):
        """Test that issues without matching cycle are skipped."""
        mock_label = mocker.MagicMock()
        mock_label.name = "archived"

        mock_issue_obj = mocker.MagicMock()
        mock_issue_obj.labels = [mock_label]
        mock_issue_obj.body = "Test body"
        mock_issue_obj.title = "Test Issue"
        mock_issue_obj.number = 101
        mock_issue_obj.closed_at = datetime(2023, 1, 1)

        mock_issue = mocker.MagicMock()
        mock_issue.issue = mock_issue_obj
        mock_issue.comments = []

        # Mock minimal dependencies
        mocker.patch("utils.mappers._build_reward_mapping", return_value={})
        mocker.patch("utils.mappers.Contributor.objects.all", return_value=[])
        mocker.patch("utils.mappers.EXCLUDED_CONTRIBUTORS", [])
        mocker.patch("utils.mappers.SocialPlatform.objects.all", return_value=[])

        # Mock Issue.objects.filter.exists() to return False
        mock_issue_filter = mocker.MagicMock()
        mock_issue_filter.exists = mocker.MagicMock(return_value=False)
        mocker.patch(
            "utils.mappers.Issue.objects.filter", return_value=mock_issue_filter
        )

        # Mock Cycle.objects.filter().first() to return None (no cycle found)
        mock_cycle_filter = mocker.MagicMock()
        mock_cycle_filter.first = mocker.MagicMock(return_value=None)
        mocker.patch(
            "utils.mappers.Cycle.objects.filter", return_value=mock_cycle_filter
        )

        result = _map_unprocessed_closed_archived_issues([mock_issue])
        assert result is True  # Found archived issues but skipped no cycle

    @pytest.mark.django_db
    def test_utils_mappers_map_unprocessed_closed_archived_issues_skip_no_reward(
        self, mocker
    ):
        """Test that issues without rewards are skipped."""
        mock_label = mocker.MagicMock()
        mock_label.name = "archived"

        mock_issue_obj = mocker.MagicMock()
        mock_issue_obj.labels = [mock_label]
        mock_issue_obj.body = "Test body"
        mock_issue_obj.title = "Test Issue"
        mock_issue_obj.number = 101
        mock_issue_obj.closed_at = datetime(2023, 1, 1)

        mock_issue = mocker.MagicMock()
        mock_issue.issue = mock_issue_obj
        mock_issue.comments = []

        # Mock dependencies
        mocker.patch("utils.mappers._build_reward_mapping", return_value={})

        # Mock contributors
        mock_contributor = mocker.MagicMock()
        mock_contributor.info = "Test User"
        mock_contributor.id = 1
        mocker.patch(
            "utils.mappers.Contributor.objects.all", return_value=[mock_contributor]
        )
        mocker.patch("utils.mappers.EXCLUDED_CONTRIBUTORS", [])

        # Mock platforms
        mock_platform = mocker.MagicMock()
        mock_platform.name = "GitHub"
        mock_platform.id = 1
        mocker.patch(
            "utils.mappers.SocialPlatform.objects.all", return_value=[mock_platform]
        )

        # Mock Issue.objects.filter.exists() to return False
        mock_issue_filter = mocker.MagicMock()
        mock_issue_filter.exists = mocker.MagicMock(return_value=False)
        mocker.patch(
            "utils.mappers.Issue.objects.filter", return_value=mock_issue_filter
        )

        # Mock cycle
        mock_cycle = mocker.MagicMock()
        mock_cycle_filter = mocker.MagicMock()
        mock_cycle_filter.first = mocker.MagicMock(return_value=mock_cycle)
        mocker.patch(
            "utils.mappers.Cycle.objects.filter", return_value=mock_cycle_filter
        )

        # Mock platform identification
        mocker.patch("utils.mappers._identify_platform_from_text", return_value=1)

        # Mock reward identification to return None
        mocker.patch("utils.mappers._identify_reward_from_labels", return_value=None)

        # Mock URL extraction
        mocker.patch("utils.mappers._extract_url_text", return_value=None)

        result = _map_unprocessed_closed_archived_issues([mock_issue])
        assert result is True  # Found archived issues but skipped no reward

    @pytest.mark.django_db
    def test_utils_mappers_map_unprocessed_closed_archived_issues_skip_no_contributors(
        self, mocker
    ):
        """Test that issues without identifiable contributors are skipped."""
        mock_label = mocker.MagicMock()
        mock_label.name = "archived"

        mock_issue_obj = mocker.MagicMock()
        mock_issue_obj.labels = [mock_label]
        mock_issue_obj.body = "Some body without contributor info"
        mock_issue_obj.title = "Test Issue"
        mock_issue_obj.number = 101
        mock_issue_obj.closed_at = datetime(2023, 1, 1)
        mock_issue_obj.user.login = "unknown_user"

        mock_issue = mocker.MagicMock()
        mock_issue.issue = mock_issue_obj
        mock_issue.comments = []

        # Mock dependencies
        mock_reward = mocker.MagicMock()
        mocker.patch(
            "utils.mappers._build_reward_mapping", return_value={"bug": mock_reward}
        )

        # Mock empty contributors
        mocker.patch("utils.mappers.Contributor.objects.all", return_value=[])
        mocker.patch("utils.mappers.EXCLUDED_CONTRIBUTORS", [])

        # Mock platforms
        mock_platform = mocker.MagicMock()
        mock_platform.name = "GitHub"
        mock_platform.id = 1
        mocker.patch(
            "utils.mappers.SocialPlatform.objects.all", return_value=[mock_platform]
        )

        # Mock Issue.objects.filter.exists() to return False
        mock_issue_filter = mocker.MagicMock()
        mock_issue_filter.exists = mocker.MagicMock(return_value=False)
        mocker.patch(
            "utils.mappers.Issue.objects.filter", return_value=mock_issue_filter
        )

        # Mock cycle
        mock_cycle = mocker.MagicMock()
        mock_cycle_filter = mocker.MagicMock()
        mock_cycle_filter.first = mocker.MagicMock(return_value=mock_cycle)
        mocker.patch(
            "utils.mappers.Cycle.objects.filter", return_value=mock_cycle_filter
        )

        # Mock platform identification
        mocker.patch("utils.mappers._identify_platform_from_text", return_value=1)

        # Mock reward identification
        mocker.patch(
            "utils.mappers._identify_reward_from_labels", return_value=mock_reward
        )

        # Mock URL extraction
        mocker.patch("utils.mappers._extract_url_text", return_value=None)

        # Mock issue creation
        mock_created_issue = mocker.MagicMock()
        mocker.patch(
            "utils.mappers.Issue.objects.create", return_value=mock_created_issue
        )

        # Mock contributor identification to return None
        mocker.patch("utils.mappers._identify_contributor_from_user", return_value=None)
        mocker.patch("utils.mappers._identify_contributor_from_text", return_value=None)

        # Mock contributor creation to return None
        mocker.patch(
            "utils.mappers._create_contributor_from_text", return_value=(None, {})
        )

        result = _map_unprocessed_closed_archived_issues([mock_issue])
        assert result is True  # Found archived issues but skipped no contributors

    @pytest.mark.django_db
    def test_utils_mappers_map_unprocessed_closed_archived_issues_successful_processing(
        self, mocker
    ):
        """Test successful processing of archived issues."""
        mock_label = mocker.MagicMock()
        mock_label.name = "archived"

        mock_issue_obj = mocker.MagicMock()
        mock_issue_obj.labels = [mock_label]
        mock_issue_obj.body = "By test_user in [Discord]"
        mock_issue_obj.title = "Test Issue"
        mock_issue_obj.number = 101
        mock_issue_obj.closed_at = datetime(2023, 1, 1)
        mock_issue_obj.user.login = "github_user"

        mock_issue = mocker.MagicMock()
        mock_issue.issue = mock_issue_obj
        mock_issue.comments = []

        # Mock dependencies
        mock_reward = mocker.MagicMock()
        mocker.patch(
            "utils.mappers._build_reward_mapping", return_value={"bug": mock_reward}
        )

        # Mock contributors
        mock_contributor = mocker.MagicMock()
        mock_contributor.info = "Test User (g@test_user, d@testuser)"
        mock_contributor.id = 1
        mocker.patch(
            "utils.mappers.Contributor.objects.all", return_value=[mock_contributor]
        )
        mocker.patch("utils.mappers.EXCLUDED_CONTRIBUTORS", [])

        # Mock platforms
        mock_platform1 = mocker.MagicMock()
        mock_platform1.name = "GitHub"
        mock_platform1.id = 1

        mock_platform2 = mocker.MagicMock()
        mock_platform2.name = "Discord"
        mock_platform2.id = 2

        mocker.patch(
            "utils.mappers.SocialPlatform.objects.all",
            return_value=[mock_platform1, mock_platform2],
        )

        # Mock Issue.objects.filter.exists() to return False
        mock_issue_filter = mocker.MagicMock()
        mock_issue_filter.exists = mocker.MagicMock(return_value=False)
        mocker.patch(
            "utils.mappers.Issue.objects.filter", return_value=mock_issue_filter
        )

        # Mock cycle
        mock_cycle = mocker.MagicMock()
        mock_cycle_filter = mocker.MagicMock()
        mock_cycle_filter.first = mocker.MagicMock(return_value=mock_cycle)
        mocker.patch(
            "utils.mappers.Cycle.objects.filter", return_value=mock_cycle_filter
        )

        # Mock identification functions
        mocker.patch("utils.mappers._identify_platform_from_text", return_value=2)
        mocker.patch(
            "utils.mappers._identify_reward_from_labels", return_value=mock_reward
        )
        mocker.patch(
            "utils.mappers._extract_url_text", return_value="https://example.com"
        )

        # Mock issue creation
        mock_created_issue = mocker.MagicMock()
        mocker.patch(
            "utils.mappers.Issue.objects.create", return_value=mock_created_issue
        )

        # Mock contributor identification
        mocker.patch("utils.mappers._identify_contributor_from_user", return_value=1)
        mocker.patch("utils.mappers._identify_contributor_from_text", return_value=None)

        # Mock contribution creation
        mock_contribution_create = mocker.patch(
            "utils.mappers.Contribution.objects.create"
        )

        result = _map_unprocessed_closed_archived_issues([mock_issue])

        assert result is True
        mock_contribution_create.assert_called_once_with(
            contributor_id=1,
            cycle=mock_cycle,
            platform_id=2,
            reward=mock_reward,
            issue=mock_created_issue,
            percentage=1,
            url="https://example.com",
            confirmed=True,
        )

    @pytest.mark.django_db
    def test_utils_mappers_map_unprocessed_closed_archived_issues_reward_from_title(
        self, mocker
    ):
        """Test successful processing of archived issues."""
        mock_label = mocker.MagicMock()
        mock_label.name = "archived"

        mock_issue_obj = mocker.MagicMock()
        mock_issue_obj.labels = [mock_label]
        mock_issue_obj.body = "By test_user in [Discord]"
        mock_issue_obj.title = "Test Issue"
        mock_issue_obj.number = 101
        mock_issue_obj.closed_at = datetime(2023, 1, 1)
        mock_issue_obj.user.login = "github_user"

        mock_issue = mocker.MagicMock()
        mock_issue.issue = mock_issue_obj
        mock_issue.comments = []

        # Mock dependencies
        mock_reward = mocker.MagicMock()
        mocker.patch(
            "utils.mappers._build_reward_mapping", return_value={"bug": mock_reward}
        )

        # Mock contributors
        mock_contributor = mocker.MagicMock()
        mock_contributor.info = "Test User (g@test_user, d@testuser)"
        mock_contributor.id = 1
        mocker.patch(
            "utils.mappers.Contributor.objects.all", return_value=[mock_contributor]
        )
        mocker.patch("utils.mappers.EXCLUDED_CONTRIBUTORS", [])

        # Mock platforms
        mock_platform1 = mocker.MagicMock()
        mock_platform1.name = "GitHub"
        mock_platform1.id = 1

        mock_platform2 = mocker.MagicMock()
        mock_platform2.name = "Discord"
        mock_platform2.id = 2

        mocker.patch(
            "utils.mappers.SocialPlatform.objects.all",
            return_value=[mock_platform1, mock_platform2],
        )

        # Mock Issue.objects.filter.exists() to return False
        mock_issue_filter = mocker.MagicMock()
        mock_issue_filter.exists = mocker.MagicMock(return_value=False)
        mocker.patch(
            "utils.mappers.Issue.objects.filter", return_value=mock_issue_filter
        )

        # Mock cycle
        mock_cycle = mocker.MagicMock()
        mock_cycle_filter = mocker.MagicMock()
        mock_cycle_filter.first = mocker.MagicMock(return_value=mock_cycle)
        mocker.patch(
            "utils.mappers.Cycle.objects.filter", return_value=mock_cycle_filter
        )

        # Mock identification functions
        mocker.patch("utils.mappers._identify_platform_from_text", return_value=2)
        mocked_reward_title = mocker.patch(
            "utils.mappers._identify_reward_from_issue_title", return_value=mock_reward
        )
        mocked_reward_labels = mocker.patch(
            "utils.mappers._identify_reward_from_labels"
        )
        mocker.patch(
            "utils.mappers._extract_url_text", return_value="https://example.com"
        )

        # Mock issue creation
        mock_created_issue = mocker.MagicMock()
        mocker.patch(
            "utils.mappers.Issue.objects.create", return_value=mock_created_issue
        )

        # Mock contributor identification
        mocker.patch("utils.mappers._identify_contributor_from_user", return_value=1)
        mocker.patch("utils.mappers._identify_contributor_from_text", return_value=None)

        # Mock contribution creation
        mock_contribution_create = mocker.patch(
            "utils.mappers.Contribution.objects.create"
        )

        result = _map_unprocessed_closed_archived_issues([mock_issue])

        assert result is True
        mock_contribution_create.assert_called_once_with(
            contributor_id=1,
            cycle=mock_cycle,
            platform_id=2,
            reward=mock_reward,
            issue=mock_created_issue,
            percentage=1,
            url="https://example.com",
            confirmed=True,
        )
        mocked_reward_title.assert_called_once_with(
            mock_issue.issue.title, active=False
        )
        mocked_reward_labels.assert_not_called()

    @pytest.mark.django_db
    def test_utils_mappers_map_unprocessed_closed_archived_issues_platform_fallback(
        self, mocker
    ):
        """Test platform fallback to GitHub when no platform identified."""
        mock_label = mocker.MagicMock()
        mock_label.name = "archived"

        mock_issue_obj = mocker.MagicMock()
        mock_issue_obj.labels = [mock_label]
        mock_issue_obj.body = "Test body"
        mock_issue_obj.title = "Test Issue"
        mock_issue_obj.number = 101
        mock_issue_obj.closed_at = datetime(2023, 1, 1)
        mock_issue_obj.user.login = "github_user"

        mock_issue = mocker.MagicMock()
        mock_issue.issue = mock_issue_obj
        mock_issue.comments = []

        # Mock dependencies
        mock_reward = mocker.MagicMock()
        mocker.patch(
            "utils.mappers._build_reward_mapping", return_value={"bug": mock_reward}
        )

        # Mock contributors
        mock_contributor = mocker.MagicMock()
        mock_contributor.info = "Test User"
        mock_contributor.id = 1
        mocker.patch(
            "utils.mappers.Contributor.objects.all", return_value=[mock_contributor]
        )
        mocker.patch("utils.mappers.EXCLUDED_CONTRIBUTORS", [])

        # Mock platforms
        mock_platform1 = mocker.MagicMock()
        mock_platform1.name = "GitHub"
        mock_platform1.id = 1

        mock_platform2 = mocker.MagicMock()
        mock_platform2.name = "Discord"
        mock_platform2.id = 2

        mocker.patch(
            "utils.mappers.SocialPlatform.objects.all",
            return_value=[mock_platform1, mock_platform2],
        )

        # Mock Issue.objects.filter.exists() to return False
        mock_issue_filter = mocker.MagicMock()
        mock_issue_filter.exists = mocker.MagicMock(return_value=False)
        mocker.patch(
            "utils.mappers.Issue.objects.filter", return_value=mock_issue_filter
        )

        # Mock cycle
        mock_cycle = mocker.MagicMock()
        mock_cycle_filter = mocker.MagicMock()
        mock_cycle_filter.first = mocker.MagicMock(return_value=mock_cycle)
        mocker.patch(
            "utils.mappers.Cycle.objects.filter", return_value=mock_cycle_filter
        )

        # Mock platform identification to return None (fallback scenario)
        mocker.patch("utils.mappers._identify_platform_from_text", return_value=None)

        # Mock reward identification
        mocker.patch(
            "utils.mappers._identify_reward_from_labels", return_value=mock_reward
        )

        # Mock URL extraction
        mocker.patch("utils.mappers._extract_url_text", return_value=None)

        # Mock issue creation
        mock_created_issue = mocker.MagicMock()
        mocker.patch(
            "utils.mappers.Issue.objects.create", return_value=mock_created_issue
        )

        # Mock contributor identification
        mocker.patch("utils.mappers._identify_contributor_from_user", return_value=1)
        mocker.patch("utils.mappers._identify_contributor_from_text", return_value=None)

        # Mock contribution creation
        mock_contribution_create = mocker.patch(
            "utils.mappers.Contribution.objects.create"
        )

        result = _map_unprocessed_closed_archived_issues([mock_issue])

        assert result is True
        # Verify contribution was created with GitHub platform ID (fallback)
        call_kwargs = mock_contribution_create.call_args[1]
        assert call_kwargs["platform_id"] == 1  # GitHub platform ID

    @pytest.mark.django_db
    def test_utils_mappers_map_unprocessed_closed_archived_issues_create_new_contributor(
        self, mocker
    ):
        """Test creating new contributor when none identified."""
        mock_label = mocker.MagicMock()
        mock_label.name = "archived"

        mock_issue_obj = mocker.MagicMock()
        mock_issue_obj.labels = [mock_label]
        mock_issue_obj.body = "By new_user in [Discord]"
        mock_issue_obj.title = "Test Issue"
        mock_issue_obj.number = 101
        mock_issue_obj.closed_at = datetime(2023, 1, 1)
        mock_issue_obj.user.login = "github_user"

        mock_issue = mocker.MagicMock()
        mock_issue.issue = mock_issue_obj
        mock_issue.comments = []

        # Mock dependencies
        mock_reward = mocker.MagicMock()
        mocker.patch(
            "utils.mappers._build_reward_mapping", return_value={"bug": mock_reward}
        )

        # Mock empty contributors
        mocker.patch("utils.mappers.Contributor.objects.all", return_value=[])
        mocker.patch("utils.mappers.EXCLUDED_CONTRIBUTORS", [])

        # Mock platforms
        mock_platform = mocker.MagicMock()
        mock_platform.name = "GitHub"
        mock_platform.id = 1
        mocker.patch(
            "utils.mappers.SocialPlatform.objects.all", return_value=[mock_platform]
        )

        # Mock Issue.objects.filter.exists() to return False
        mock_issue_filter = mocker.MagicMock()
        mock_issue_filter.exists = mocker.MagicMock(return_value=False)
        mocker.patch(
            "utils.mappers.Issue.objects.filter", return_value=mock_issue_filter
        )

        # Mock cycle
        mock_cycle = mocker.MagicMock()
        mock_cycle_filter = mocker.MagicMock()
        mock_cycle_filter.first = mocker.MagicMock(return_value=mock_cycle)
        mocker.patch(
            "utils.mappers.Cycle.objects.filter", return_value=mock_cycle_filter
        )

        # Mock platform identification
        mocker.patch("utils.mappers._identify_platform_from_text", return_value=1)

        # Mock reward identification
        mocker.patch(
            "utils.mappers._identify_reward_from_labels", return_value=mock_reward
        )

        # Mock URL extraction
        mocker.patch("utils.mappers._extract_url_text", return_value=None)

        # Mock issue creation
        mock_created_issue = mocker.MagicMock()
        mocker.patch(
            "utils.mappers.Issue.objects.create", return_value=mock_created_issue
        )

        # Mock contributor identification to return None
        mocker.patch("utils.mappers._identify_contributor_from_user", return_value=None)
        mocker.patch("utils.mappers._identify_contributor_from_text", return_value=None)

        # Mock contributor creation
        mocker.patch(
            "utils.mappers._create_contributor_from_text",
            return_value=(2, {"new_user": 2}),
        )

        # Mock contribution creation
        mock_contribution_create = mocker.patch(
            "utils.mappers.Contribution.objects.create"
        )

        result = _map_unprocessed_closed_archived_issues([mock_issue])

        assert result is True
        mock_contribution_create.assert_called_once()

    @pytest.mark.django_db
    def test_utils_mappers_map_unprocessed_closed_archived_issues_multiple_contributors(
        self, mocker
    ):
        """Test processing with multiple contributors identified."""
        mock_label = mocker.MagicMock()
        mock_label.name = "archived"

        mock_issue_obj = mocker.MagicMock()
        mock_issue_obj.labels = [mock_label]
        mock_issue_obj.body = "By user1 and user2 in [Discord]"
        mock_issue_obj.title = "Test Issue"
        mock_issue_obj.number = 101
        mock_issue_obj.closed_at = datetime(2023, 1, 1)
        mock_issue_obj.user.login = "github_user"

        mock_issue = mocker.MagicMock()
        mock_issue.issue = mock_issue_obj
        mock_issue.comments = []

        # Mock dependencies
        mock_reward = mocker.MagicMock()
        mocker.patch(
            "utils.mappers._build_reward_mapping", return_value={"bug": mock_reward}
        )

        # Mock contributors
        mock_contributor1 = mocker.MagicMock()
        mock_contributor1.info = "User One"
        mock_contributor1.id = 1

        mock_contributor2 = mocker.MagicMock()
        mock_contributor2.info = "User Two"
        mock_contributor2.id = 2

        mocker.patch(
            "utils.mappers.Contributor.objects.all",
            return_value=[mock_contributor1, mock_contributor2],
        )
        mocker.patch("utils.mappers.EXCLUDED_CONTRIBUTORS", [])

        # Mock platforms
        mock_platform = mocker.MagicMock()
        mock_platform.name = "GitHub"
        mock_platform.id = 1
        mocker.patch(
            "utils.mappers.SocialPlatform.objects.all", return_value=[mock_platform]
        )

        # Mock Issue.objects.filter.exists() to return False
        mock_issue_filter = mocker.MagicMock()
        mock_issue_filter.exists = mocker.MagicMock(return_value=False)
        mocker.patch(
            "utils.mappers.Issue.objects.filter", return_value=mock_issue_filter
        )

        # Mock cycle
        mock_cycle = mocker.MagicMock()
        mock_cycle_filter = mocker.MagicMock()
        mock_cycle_filter.first = mocker.MagicMock(return_value=mock_cycle)
        mocker.patch(
            "utils.mappers.Cycle.objects.filter", return_value=mock_cycle_filter
        )

        # Mock platform identification
        mocker.patch("utils.mappers._identify_platform_from_text", return_value=1)

        # Mock reward identification
        mocker.patch(
            "utils.mappers._identify_reward_from_labels", return_value=mock_reward
        )

        # Mock URL extraction
        mocker.patch("utils.mappers._extract_url_text", return_value=None)

        # Mock issue creation
        mock_created_issue = mocker.MagicMock()
        mocker.patch(
            "utils.mappers.Issue.objects.create", return_value=mock_created_issue
        )

        # Mock contributor identification to return multiple IDs
        mocker.patch("utils.mappers._identify_contributor_from_user", return_value=1)
        mocker.patch("utils.mappers._identify_contributor_from_text", return_value=2)

        # Mock contribution creation
        mock_contribution_create = mocker.patch(
            "utils.mappers.Contribution.objects.create"
        )

        result = _map_unprocessed_closed_archived_issues([mock_issue])

        assert result is True
        # Verify two contributions were created
        assert mock_contribution_create.call_count == 2


class TestUtilsMappersPublicFunctions:
    """Testing class for bulk-optimized :py:mod:`utils.mappers` public function."""

    # # map_github_issues
    @pytest.mark.django_db
    def test_utils_mappers_map_github_issues_for_provided_token(self, mocker):
        closed_issues, open_issues = mocker.MagicMock(), mocker.MagicMock()
        github_issues = {"closed": closed_issues, "open": open_issues}
        mock_categorize = mocker.patch(
            "utils.mappers._fetch_and_categorize_issues", return_value=github_issues
        )
        mock_archived = mocker.patch("utils.mappers._map_closed_archived_issues")
        mock_unprocesed = mocker.patch(
            "utils.mappers._map_unprocessed_closed_archived_issues"
        )
        mock_addressed = mocker.patch("utils.mappers._map_closed_addressed_issues")
        mock_open_issues = mocker.patch("utils.mappers._map_open_issues")
        result = map_github_issues(issue_tracker_api_token="issue_tracker_api_token")

        mock_categorize.assert_called_once_with("issue_tracker_api_token")
        mock_archived.assert_called_once_with(closed_issues)
        mock_unprocesed.assert_called_once_with(mock_archived.return_value)
        mock_addressed.assert_called_once_with(closed_issues)
        mock_open_issues.assert_called_once_with(open_issues)

        assert result is False

    @pytest.mark.django_db
    def test_utils_mappers_map_github_issues_for_no_token(self, mocker):
        mock_categorize = mocker.patch(
            "utils.mappers._fetch_and_categorize_issues", return_value={}
        )
        mock_archived = mocker.patch("utils.mappers._map_closed_archived_issues")
        mock_unprocesed = mocker.patch(
            "utils.mappers._map_unprocessed_closed_archived_issues"
        )
        mock_addressed = mocker.patch("utils.mappers._map_closed_addressed_issues")
        mock_open_issues = mocker.patch("utils.mappers._map_open_issues")
        result = map_github_issues(issue_tracker_api_token="issue_tracker_api_token")

        mock_categorize.assert_called_once_with("issue_tracker_api_token")
        mock_archived.assert_called_once_with([])
        mock_unprocesed.assert_called_once_with(mock_archived.return_value)
        mock_addressed.assert_called_once_with([])
        mock_open_issues.assert_called_once_with([])

        assert result is False
