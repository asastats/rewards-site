"""Testing module for :py:mod:`issues.issues` module."""

import pytest

from issues.issues import (
    IssueProvider,
    _contributor_link,
    _prepare_issue_body_from_contribution,
    _prepare_issue_labels_from_contribution,
    _prepare_issue_priority_from_contribution,
    _prepare_issue_title_from_contribution,
    issue_data_for_contribution,
)


class TestIssuesIssuesIssueProvider:
    """Testing class for :class:`issues.issues.IssueProvider`."""

    @pytest.mark.parametrize(
        "attr",
        ["name", "user", "_provider_instance"],
    )
    def test_issues_issues_issueprovider_inits_attribute_as_none(self, attr):
        assert getattr(IssueProvider, attr) is None

    # # __init__
    def test_issues_issues_issueprovider_init(self, mocker):
        user = mocker.MagicMock()
        mock_get_provider = mocker.patch.object(IssueProvider, "_get_provider_instance")
        provider = IssueProvider(user, name="github")
        assert provider.name == "github"
        assert provider.user == user
        mock_get_provider.assert_called_once_with(name="github")

    # # __getattr__
    def test_issues_issues_issueprovider_getattr(self, mocker):
        user = mocker.MagicMock()
        provider = IssueProvider(user, name="github")
        assert hasattr(provider, "create_issue")


class TestIssuesIssuesPrepareFunctions:
    """Testing class for :py:mod:`issues.issues` issue preparation functions."""

    # # contributor_link
    def test_issues_issues_contributor_link_for_contributor_not_found(self, mocker):
        handle = "handle"
        mocked_contributor = mocker.patch(
            "issues.issues.Contributor.objects.from_handle", return_value=None
        )
        returned = _contributor_link(handle)
        assert returned == handle
        mocked_contributor.assert_called_once_with(handle)

    def test_issues_issues_contributor_link_for_error(self, mocker):
        handle = "handle"
        mocked_contributor = mocker.patch(
            "issues.issues.Contributor.objects.from_handle",
            side_effect=ValueError("error"),
        )
        returned = _contributor_link(handle)
        assert returned == handle
        mocked_contributor.assert_called_once_with(handle)

    def test_issues_issues_contributor_link_functionality(self, mocker):
        handle = "handle"
        contributor = mocker.MagicMock()
        url = "http://example.com"
        contributor.get_absolute_url.return_value = url
        mocked_contributor = mocker.patch(
            "issues.issues.Contributor.objects.from_handle", return_value=contributor
        )
        returned = _contributor_link(handle)
        assert returned == f"[{handle}]({url})"
        mocked_contributor.assert_called_once_with(handle)

    # # _prepare_issue_body_from_contribution
    def test_issues_issues_prepare_issue_body_from_contribution_no_url(self, mocker):
        contribution, profile = mocker.MagicMock(), mocker.MagicMock()
        contribution.url = None
        mocked_link = mocker.patch("issues.issues._contributor_link")

        result = _prepare_issue_body_from_contribution(contribution, profile)

        assert result == "** Please provide the necessary information **"
        mocked_link.assert_not_called()

    def test_issues_issues_prepare_issue_body_from_contribution_url_no_success(
        self, mocker
    ):
        contribution, profile = mocker.MagicMock(), mocker.MagicMock()
        contribution.url = "https://discord.com/channels/test"
        mocked_link = mocker.patch("issues.issues._contributor_link")

        mocked_message_from_url = mocker.patch("issues.issues.message_from_url")
        mocked_message_from_url.return_value = {"success": False}

        result = _prepare_issue_body_from_contribution(contribution, profile)

        assert result == "** Please provide the necessary information **"
        mocked_message_from_url.assert_called_once_with(contribution.url)
        mocked_link.assert_not_called()

    def test_issues_issues_prepare_issue_body_from_contribution_successful_parsing(
        self, mocker
    ):
        contribution, profile = mocker.MagicMock(), "username"
        contribution.url = "https://discord.com/channels/test"
        link = "https://example.com"
        mocked_link = mocker.patch("issues.issues._contributor_link", return_value=link)

        test_message = {
            "success": True,
            "author": "testuser",
            "timestamp": "2023-10-15T14:30:00.000000+00:00",
            "content": "This is a test message\nwith multiple lines",
        }

        mocked_message_from_url = mocker.patch("issues.issues.message_from_url")
        mocked_message_from_url.return_value = test_message
        mocked_datetime = mocker.patch("issues.issues.datetime")
        mocked_datetime.strptime.return_value.strftime.return_value = "15 Oct 14:30"

        result = _prepare_issue_body_from_contribution(contribution, profile)

        expected_body = (
            f"By {link} on 15 Oct 14:30 in [Discord](https://discord.com/channels/test): "
            f"// su: {profile}\n> This is a test message\n> with multiple lines\n"
        )
        assert result == expected_body
        mocked_message_from_url.assert_called_once_with(contribution.url)
        mocked_datetime.strptime.assert_called_once_with(
            "2023-10-15T14:30:00.000000+00:00", "%Y-%m-%dT%H:%M:%S.%f%z"
        )
        mocked_link.assert_called_once_with(test_message.get("author"))

    # # _prepare_issue_labels_from_contribution
    def test_issues_issues_prepare_issue_labels_bug_type(self, mocker):
        contribution = mocker.MagicMock()
        reward_type = mocker.MagicMock()
        reward_type.name = "Bug Fix"
        contribution.reward.type = reward_type

        result = _prepare_issue_labels_from_contribution(contribution)

        assert result == ["bug"]

    def test_issues_issues_prepare_issue_labels_feature_type(self, mocker):
        contribution = mocker.MagicMock()
        reward_type = mocker.MagicMock()
        reward_type.name = "Feature Request"
        contribution.reward.type = reward_type

        result = _prepare_issue_labels_from_contribution(contribution)

        assert result == ["feature"]

    def test_issues_issues_prepare_issue_labels_task_type(self, mocker):
        contribution = mocker.MagicMock()
        reward_type = mocker.MagicMock()
        reward_type.name = "General Task"
        contribution.reward.type = reward_type

        result = _prepare_issue_labels_from_contribution(contribution)

        assert result == ["task"]

    def test_issues_issues_prepare_issue_labels_twitter_type(self, mocker):
        contribution = mocker.MagicMock()
        reward_type = mocker.MagicMock()
        reward_type.name = "Twitter Engagement"
        contribution.reward.type = reward_type

        result = _prepare_issue_labels_from_contribution(contribution)

        assert result == ["task"]

    def test_issues_issues_prepare_issue_labels_research_type(self, mocker):
        contribution = mocker.MagicMock()
        reward_type = mocker.MagicMock()
        reward_type.name = "Research Work"
        contribution.reward.type = reward_type

        result = _prepare_issue_labels_from_contribution(contribution)

        assert result == ["research"]

    def test_issues_issues_prepare_issue_labels_unknown_type(self, mocker):
        contribution = mocker.MagicMock()
        reward_type = mocker.MagicMock()
        reward_type.name = "Unknown Type"
        contribution.reward.type = reward_type

        result = _prepare_issue_labels_from_contribution(contribution)

        assert result == []

    # # _prepare_issue_priority_from_contribution
    def test_issues_issues_prepare_issue_priority_bug_type(self, mocker):
        contribution = mocker.MagicMock()
        reward_type = mocker.MagicMock()
        reward_type.name = "Critical Bug"
        contribution.reward.type = reward_type

        result = _prepare_issue_priority_from_contribution(contribution)

        assert result == "high priority"

    def test_issues_issues_prepare_issue_priority_non_bug_type(self, mocker):
        contribution = mocker.MagicMock()
        reward_type = mocker.MagicMock()
        reward_type.name = "Feature Implementation"
        contribution.reward.type = reward_type

        result = _prepare_issue_priority_from_contribution(contribution)

        assert result == "medium priority"

    # # _prepare_issue_title_from_contribution
    def test_issues_issues_prepare_issue_title_with_comment(self, mocker):
        contribution = mocker.MagicMock()
        reward_type = mocker.MagicMock()
        reward_type.label = "FEAT"
        contribution.reward.type = reward_type
        contribution.reward.level = "A"
        contribution.comment = "Implement new authentication system"

        result = _prepare_issue_title_from_contribution(contribution)

        expected_title = "[FEATA] Implement new authentication system"
        assert result == expected_title

    def test_issues_issues_prepare_issue_title_without_comment(self, mocker):
        contribution = mocker.MagicMock()
        reward_type = mocker.MagicMock()
        reward_type.label = "BUG"
        contribution.reward.type = reward_type
        contribution.reward.level = "B"
        contribution.comment = ""

        result = _prepare_issue_title_from_contribution(contribution)

        expected_title = "[BUGB] "
        assert result == expected_title

    # # issue_data_for_contribution
    def test_issues_issues_issue_data_for_contribution_complete_data(self, mocker):
        contribution, profile = mocker.MagicMock(), mocker.MagicMock()

        # Mock all the helper functions
        mocker.patch(
            "issues.issues._prepare_issue_title_from_contribution",
            return_value="Test Title",
        )
        mocker.patch(
            "issues.issues._prepare_issue_body_from_contribution",
            return_value="Test Body",
        )
        mocker.patch(
            "issues.issues._prepare_issue_labels_from_contribution",
            return_value=["bug"],
        )
        mocker.patch(
            "issues.issues._prepare_issue_priority_from_contribution",
            return_value="high priority",
        )

        result = issue_data_for_contribution(contribution, profile)

        expected_data = {
            "issue_title": "Test Title",
            "issue_body": "Test Body",
            "labels": ["bug"],
            "priority": "high priority",
        }
        assert result == expected_data

    def test_issues_issues_issue_data_for_contribution_calls_all_helpers(self, mocker):
        contribution, profile = mocker.MagicMock(), mocker.MagicMock()

        mocked_title = mocker.patch(
            "issues.issues._prepare_issue_title_from_contribution"
        )
        mocked_body = mocker.patch(
            "issues.issues._prepare_issue_body_from_contribution"
        )
        mocked_labels = mocker.patch(
            "issues.issues._prepare_issue_labels_from_contribution"
        )
        mocked_priority = mocker.patch(
            "issues.issues._prepare_issue_priority_from_contribution"
        )

        issue_data_for_contribution(contribution, profile)

        mocked_title.assert_called_once_with(contribution)
        mocked_body.assert_called_once_with(contribution, profile)
        mocked_labels.assert_called_once_with(contribution)
        mocked_priority.assert_called_once_with(contribution)
