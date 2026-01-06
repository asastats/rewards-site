"""Testing module for :py:mod:`core.views` views related to issues."""

from datetime import datetime

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.db.models import QuerySet
from django.urls import reverse
from django.views.generic import DetailView, ListView

from core.forms import IssueLabelsForm
from core.models import (
    Contribution,
    Contributor,
    Cycle,
    Issue,
    IssueStatus,
    Reward,
    RewardType,
    SocialPlatform,
)
from core.views import (
    CreateIssueView,
    IssueDetailView,
    IssueListView,
    IssueModalView,
)

user_model = get_user_model()


class TestIssueListView:
    """Testing class for :class:`core.views.IssueListView`."""

    def test_issuelistview_is_subclass_of_listview(self):
        assert issubclass(IssueListView, ListView)

    def test_issuelistview_model(self):
        view = IssueListView()
        assert view.model == Issue

    def test_issuelistview_paginate_by(self):
        view = IssueListView()
        assert view.paginate_by == 20


@pytest.mark.django_db
class TestDbIssueListView:
    """Testing class for :class:`core.views.IssueListView` with database."""

    def test_issuelistview_get_context_data(self, rf):
        request = rf.get("/issues/")

        # Create test issues
        Issue.objects.create(number=5055)
        issue1 = Issue.objects.create(number=5050)
        issue2 = Issue.objects.create(number=5051)
        Issue.objects.create(number=5052, status=IssueStatus.CREATED)
        latest_issue = Issue.objects.create(number=5054, status=IssueStatus.CREATED)
        Issue.objects.create(number=5053, status=IssueStatus.ADDRESSED)

        cycle = Cycle.objects.create(start="2025-09-08")
        contributor = Contributor.objects.create(name="test_contributor")
        platform = SocialPlatform.objects.create(name="GitHub")
        reward_type = RewardType.objects.create(label="BUG", name="Bug Fix")
        reward = Reward.objects.create(type=reward_type, level=1, amount=1000)

        Contribution.objects.create(
            cycle=cycle,
            issue=issue1,
            contributor=contributor,
            platform=platform,
            reward=reward,
        )
        Contribution.objects.create(
            cycle=cycle,
            issue=issue2,
            contributor=contributor,
            platform=platform,
            reward=reward,
        )
        Contribution.objects.create(
            cycle=cycle,
            issue=latest_issue,
            contributor=contributor,
            platform=platform,
            reward=reward,
        )
        view = IssueListView()
        view.setup(request)
        view.object_list = view.get_queryset()

        context = view.get_context_data()

        assert context["total_contributions"] == 3
        assert context["latest_issue"] == latest_issue

    # # get_queryset
    def test_issuelistview_get_queryset(self, rf):
        request = rf.get("/issues/")

        # Create test issues
        issue1 = Issue.objects.create(number=5055)
        issue2 = Issue.objects.create(number=5050)
        Issue.objects.create(number=5051)
        Issue.objects.create(number=5052, status=IssueStatus.WONTFIX)
        Issue.objects.create(number=5053, status=IssueStatus.ADDRESSED)
        Issue.objects.create(number=5054, status=IssueStatus.ARCHIVED)

        view = IssueListView()
        view.setup(request)

        queryset = view.get_queryset()

        assert queryset.count() == 3
        assert queryset.first() == issue1
        assert queryset.last() == issue2

    @pytest.mark.django_db
    def test_issuelistview_get_queryset_filters_by_created_status_and_prefetches(
        self, mocker
    ):
        """Test that get_queryset filters by CREATED and prefetches contributions."""
        # Mock the Issue.objects.filter chain
        mocked_filter = mocker.patch("core.views.Issue.objects.filter")
        mocked_prefetch = mocker.patch("core.views.Prefetch")

        view = IssueListView()
        returned = view.get_queryset()

        # Verify the filter was called with CREATED status
        mocked_filter.assert_called_once_with(status=IssueStatus.CREATED)

        # Verify Prefetch was called with the correct parameters
        mocked_prefetch.assert_called_once_with(
            "contribution_set",
            queryset=mocker.ANY,  # We'll check the queryset separately
            to_attr="prefetched_contributions",
        )

        # Verify prefetch_related was called with our Prefetch object
        mocked_filter.return_value.prefetch_related.assert_called_once_with(
            mocked_prefetch.return_value
        )

        # Verify the final return value
        assert returned == mocked_filter.return_value.prefetch_related.return_value

    @pytest.mark.django_db
    def test_issuelistview_get_queryset_contribution_queryset(self, mocker):
        """Test that Contribution queryset uses select_related with correct fields."""
        mocker.patch("core.views.Issue.objects.filter")
        mocked_prefetch = mocker.patch("core.views.Prefetch")
        mocked_contrib = mocker.patch("core.views.Contribution.objects")

        view = IssueListView()
        view.get_queryset()

        # Get the queryset that was passed to Prefetch
        prefetch_call_args = mocked_prefetch.call_args
        contribution_queryset = prefetch_call_args[1]["queryset"]

        # Verify the Contribution queryset uses select_related with correct fields
        mocked_contrib.select_related.assert_called_once_with(
            "contributor", "platform", "reward__type"
        )

        # Verify the queryset is ordered by created_at
        mocked_contrib.select_related.return_value.order_by.assert_called_once_with(
            "created_at"
        )

        # Verify the queryset passed to Prefetch is the fully constructed one
        assert (
            contribution_queryset
            == mocked_contrib.select_related.return_value.order_by.return_value
        )

    @pytest.mark.django_db
    def test_issuelistview_get_queryset_integration(self):
        """Integration test to verify the actual queryset behavior."""
        # Create test data
        issue1 = Issue.objects.create(number=1, status=IssueStatus.CREATED)
        Issue.objects.create(number=2, status=IssueStatus.WONTFIX)  # Should be excluded
        issue3 = Issue.objects.create(number=3, status=IssueStatus.CREATED)

        cycle = Cycle.objects.create(start="2025-09-08")
        contributor = Contributor.objects.create(name="test_contributor")
        platform = SocialPlatform.objects.create(name="GitHub")
        reward_type = RewardType.objects.create(label="BUG", name="Bug Fix")
        reward = Reward.objects.create(type=reward_type, level=1, amount=1000)

        # Create contributions
        Contribution.objects.create(
            cycle=cycle,
            issue=issue1,
            contributor=contributor,
            platform=platform,
            reward=reward,
        )
        Contribution.objects.create(
            cycle=cycle,
            issue=issue3,
            contributor=contributor,
            platform=platform,
            reward=reward,
        )

        view = IssueListView()
        queryset = view.get_queryset()

        # Verify only CREATED issues are included
        assert list(queryset) == [issue3, issue1]  # Ordered by -number

        # Verify prefetch_related is applied
        assert hasattr(queryset, "_prefetch_related_lookups")

        # Get an issue from the queryset and verify it has the prefetch attribute
        issue_from_queryset = queryset.first()
        # Note: The actual prefetched data would be available after evaluation
        assert issue_from_queryset.status == IssueStatus.CREATED


class TestIssueDetailView:
    """Test case for IssueDetailView."""

    def test_issuedetailview_is_subclass_of_detailview(self):
        assert issubclass(IssueDetailView, DetailView)

    def test_issuedetailview_model(self):
        view = IssueDetailView()
        assert view.model == Issue


@pytest.mark.django_db
class TestDbIssueDetailView:
    """Testing class for :class:`core.views.IssueDetailView` with database."""

    def test_issuedetailview_get_object(self, rf, issue):
        request = rf.get(f"/issues/{issue.id}/")

        view = IssueDetailView()
        view.setup(request, pk=issue.id)

        obj = view.get_object()

        assert obj == issue
        # Use the correct field name from your Issue model
        assert obj.number == issue.number  # Changed from issue_number to number

    def test_issuedetailview_accessible_to_regular_user(
        self, client, regular_user, issue
    ):
        """Test that regular users can access the view."""
        client.force_login(regular_user)
        url = reverse("issue_detail", kwargs={"pk": issue.pk})
        response = client.get(url)
        assert response.status_code == 200

    def test_issuedetailview_accessible_to_superuser(self, client, superuser, issue):
        """Test that superusers can access the view."""
        client.force_login(superuser)
        url = reverse("issue_detail", kwargs={"pk": issue.pk})
        response = client.get(url)
        assert response.status_code == 200

    def test_issuedetailview_tracker_data_added_for_superuser(
        self, client, superuser, issue, mocker
    ):
        provider = settings.ISSUE_TRACKER_PROVIDER.lower()
        name = provider.capitalize()
        mocker.patch(f"issues.{provider}.{name}Provider._get_client")
        mocker.patch(f"issues.{provider}.{name}Provider._get_repository")
        mock_get_issue = mocker.patch(
            f"issues.{provider}.BaseIssueProvider.issue_by_number"
        )

        # Create datetime objects for testing
        created_at = datetime(2023, 1, 1, 0, 0, 0)
        updated_at = datetime(2023, 1, 2, 0, 0, 0)

        mock_tracker_data = {
            "success": True,
            "issue": {
                "number": 123,
                "title": "Test Issue",
                "body": "Test body",
                "state": "open",
                "labels": ["bug"],
                "assignees": ["user1"],
                "html_url": "https://github.com/owner/repo/issues/123",
                "created_at": created_at,  # Use datetime object
                "updated_at": updated_at,  # Use datetime object
            },
        }
        mock_get_issue.return_value = mock_tracker_data

        client.force_login(superuser)
        url = reverse("issue_detail", kwargs={"pk": issue.pk})
        response = client.get(url)

        assert response.status_code == 200
        assert "tracker_issue" in response.context
        assert response.context["issue_title"] == "Test Issue"
        assert response.context["issue_created_at"] == created_at
        assert response.context["issue_updated_at"] == updated_at
        mock_get_issue.assert_called_once_with(issue.number)

    def test_issuedetailview_no_tracker_data_for_regular_user(
        self, client, regular_user, issue, mocker
    ):
        provider = settings.ISSUE_TRACKER_PROVIDER.lower()
        name = provider.capitalize()
        mocker.patch(f"issues.{provider}.{name}Provider._get_client")
        mocker.patch(f"issues.{provider}.{name}Provider._get_repository")
        mock_get_issue = mocker.patch(
            f"issues.{provider}.BaseIssueProvider.issue_by_number"
        )

        client.force_login(regular_user)
        url = reverse("issue_detail", kwargs={"pk": issue.pk})
        response = client.get(url)

        assert response.status_code == 200
        assert "issue_html_url" in response.context
        assert "tracker_issue" not in response.context
        assert "issue_title" not in response.context
        mock_get_issue.assert_not_called()

    def test_issuedetailview_tracker_error_for_superuser(
        self, client, superuser, issue, mocker
    ):
        provider = settings.ISSUE_TRACKER_PROVIDER.lower()
        name = provider.capitalize()
        mocker.patch(f"issues.{provider}.{name}Provider._get_client")
        mocker.patch(f"issues.{provider}.{name}Provider._get_repository")
        mock_get_issue = mocker.patch(
            f"issues.{provider}.BaseIssueProvider.issue_by_number"
        )
        mock_tracker_data = {"success": False, "error": "Authentication failed"}
        mock_get_issue.return_value = mock_tracker_data

        client.force_login(superuser)
        url = reverse("issue_detail", kwargs={"pk": issue.pk})
        response = client.get(url)

        assert response.status_code == 200
        assert response.context["tracker_error"] == "Authentication failed"
        assert "tracker_issue" not in response.context

    def test_issuedetailview_same_template_used_for_all_users(
        self, client, regular_user, superuser, issue
    ):
        """Test that the same template is used for both user types."""
        client.force_login(regular_user)
        url = reverse("issue_detail", kwargs={"pk": issue.pk})
        response_regular = client.get(url)

        client.force_login(superuser)
        response_super = client.get(url)

        # Both should use the same template
        regular_templates = [t.name for t in response_regular.templates]
        super_templates = [t.name for t in response_super.templates]

        assert "core/issue_detail.html" in regular_templates
        assert "core/issue_detail.html" in super_templates

    def test_issuedetailview_tracker_api_called_with_correct_arguments(
        self, client, superuser, issue, mocker
    ):
        provider = settings.ISSUE_TRACKER_PROVIDER.lower()
        name = provider.capitalize()
        mocker.patch(f"issues.{provider}.{name}Provider._get_client")
        mocker.patch(f"issues.{provider}.{name}Provider._get_repository")
        mock_get_issue = mocker.patch(
            f"issues.{provider}.BaseIssueProvider.issue_by_number"
        )
        mock_tracker_data = {
            "success": True,
            "issue": {
                "number": 123,
                "title": "Test Issue",
                "body": "Test body",
                "state": "open",
                "labels": [],
                "assignees": [],
                "html_url": "",
                "created_at": "",
                "updated_at": "",
            },
        }
        mock_get_issue.return_value = mock_tracker_data

        client.force_login(superuser)
        url = reverse("issue_detail", kwargs={"pk": issue.pk})
        response = client.get(url)

        assert response.status_code == 200
        # Verify the function was called with correct arguments
        mock_get_issue.assert_called_once_with(issue.number)

    def test_issuedetailview_context_data_includes_all_tracker_fields(
        self, client, superuser, issue, mocker
    ):
        provider = settings.ISSUE_TRACKER_PROVIDER.lower()
        name = provider.capitalize()
        mocker.patch(f"issues.{provider}.{name}Provider._get_client")
        mocker.patch(f"issues.{provider}.{name}Provider._get_repository")
        mock_get_issue = mocker.patch(
            f"issues.{provider}.BaseIssueProvider.issue_by_number"
        )
        mock_tracker_data = {
            "success": True,
            "issue": {
                "number": 123,
                "title": "Complete Test Issue",
                "body": "Complete test body with **markdown**",
                "state": "closed",
                "labels": ["bug", "feature", "urgent"],
                "assignees": ["user1", "user2", "user3"],
                "created_at": "2023-01-01T10:00:00",
                "updated_at": "2023-01-15T15:30:00",
            },
        }
        mock_get_issue.return_value = mock_tracker_data

        mock_url = mocker.patch(f"issues.{provider}.BaseIssueProvider.issue_url")
        issue_url = "full_issue_url"
        mock_url.return_value = issue_url
        client.force_login(superuser)
        url = reverse("issue_detail", kwargs={"pk": issue.pk})
        response = client.get(url)
        assert response.status_code == 200
        context = response.context
        mock_url.assert_called_once_with(123)
        assert context["tracker_issue"] == mock_tracker_data["issue"]
        assert context["issue_title"] == "Complete Test Issue"
        assert context["issue_body"] == "Complete test body with **markdown**"
        assert context["issue_state"] == "closed"
        assert context["issue_labels"] == ["bug", "feature", "urgent"]
        assert context["issue_assignees"] == ["user1", "user2", "user3"]
        assert context["issue_html_url"] == issue_url
        assert context["issue_created_at"] == "2023-01-01T10:00:00"
        assert context["issue_updated_at"] == "2023-01-15T15:30:00"


@pytest.mark.django_db
class TestIssueDetailViewWithForm:
    """Test the IssueDetailView with the new form functionality."""

    def test_issuedetailview_labels_form_in_context_for_superuser_and_open_issue(
        self, client, superuser, issue, mocker
    ):
        provider = settings.ISSUE_TRACKER_PROVIDER.lower()
        name = provider.capitalize()
        mocker.patch(f"issues.{provider}.{name}Provider._get_client")
        mocker.patch(f"issues.{provider}.{name}Provider._get_repository")
        mock_get_issue = mocker.patch(
            f"issues.{provider}.BaseIssueProvider.issue_by_number"
        )
        mock_tracker_data = {
            "success": True,
            "issue": {
                "number": 123,
                "title": "Test Issue",
                "body": "Test body",
                "state": "open",  # Issue is open
                "labels": ["bug"],
                "assignees": [],
                "html_url": "https://github.com/owner/repo/issues/123",
                "created_at": "2023-01-01T10:00:00",
                "updated_at": "2023-01-15T15:30:00",
            },
        }
        mock_get_issue.return_value = mock_tracker_data

        client.force_login(superuser)
        url = reverse("issue_detail", kwargs={"pk": issue.pk})
        response = client.get(url)

        assert response.status_code == 200
        assert "labels_form" in response.context
        assert isinstance(response.context["labels_form"], IssueLabelsForm)

    def test_issuedetailview_labels_form_not_in_context_for_superuser_and_closed_issue(
        self, client, superuser, issue, mocker
    ):
        provider = settings.ISSUE_TRACKER_PROVIDER.lower()
        name = provider.capitalize()
        mocker.patch(f"issues.{provider}.{name}Provider._get_client")
        mocker.patch(f"issues.{provider}.{name}Provider._get_repository")
        mock_get_issue = mocker.patch(
            f"issues.{provider}.BaseIssueProvider.issue_by_number"
        )
        mock_tracker_data = {
            "success": True,
            "issue": {
                "number": 123,
                "title": "Test Issue",
                "body": "Test body",
                "state": "closed",  # Issue is closed
                "labels": ["bug"],
                "assignees": [],
                "html_url": "https://github.com/owner/repo/issues/123",
                "created_at": "2023-01-01T10:00:00",
                "updated_at": "2023-01-15T15:30:00",
            },
        }
        mock_get_issue.return_value = mock_tracker_data

        client.force_login(superuser)
        url = reverse("issue_detail", kwargs={"pk": issue.pk})
        response = client.get(url)

        assert response.status_code == 200
        assert "labels_form" not in response.context

    def test_issuedetailview_labels_form_not_in_context_for_regular_user(
        self, client, regular_user, issue, mocker
    ):
        """Test that labels form is NOT in context for regular users even if issue is open."""
        provider = settings.ISSUE_TRACKER_PROVIDER.lower()
        name = provider.capitalize()
        mocker.patch(f"issues.{provider}.{name}Provider._get_client")
        mocker.patch(f"issues.{provider}.{name}Provider._get_repository")
        mock_get_issue = mocker.patch(
            f"issues.{provider}.BaseIssueProvider.issue_by_number"
        )
        mock_tracker_data = {
            "success": True,
            "issue": {
                "number": 123,
                "title": "Test Issue",
                "body": "Test body",
                "state": "open",  # Issue is open
                "labels": ["bug"],
                "assignees": [],
                "html_url": "https://github.com/owner/repo/issues/123",
                "created_at": "2023-01-01T10:00:00",
                "updated_at": "2023-01-15T15:30:00",
            },
        }
        mock_get_issue.return_value = mock_tracker_data

        client.force_login(regular_user)
        url = reverse("issue_detail", kwargs={"pk": issue.pk})
        response = client.get(url)

        assert response.status_code == 200
        assert "labels_form" not in response.context

    def test_issuedetailview_labels_form_not_in_context_when_tracker_fails(
        self, client, superuser, issue, mocker
    ):
        provider = settings.ISSUE_TRACKER_PROVIDER.lower()
        name = provider.capitalize()
        mocker.patch(f"issues.{provider}.{name}Provider._get_client")
        mocker.patch(f"issues.{provider}.{name}Provider._get_repository")
        mock_get_issue = mocker.patch(
            f"issues.{provider}.BaseIssueProvider.issue_by_number"
        )
        mock_tracker_data = {"success": False, "error": "GitHub API error"}
        mock_get_issue.return_value = mock_tracker_data

        client.force_login(superuser)
        url = reverse("issue_detail", kwargs={"pk": issue.pk})
        response = client.get(url)

        assert response.status_code == 200
        assert "labels_form" not in response.context
        assert "tracker_error" in response.context

    def test_issuedetailview_form_prepopulated_with_existing_labels(
        self, client, superuser, issue, mocker
    ):
        """Test that form is prepopulated with existing GitHub labels."""
        provider = settings.ISSUE_TRACKER_PROVIDER.lower()
        name = provider.capitalize()
        mocker.patch(f"issues.{provider}.{name}Provider._get_client")
        mocker.patch(f"issues.{provider}.{name}Provider._get_repository")
        mock_get_issue = mocker.patch(
            f"issues.{provider}.BaseIssueProvider.issue_by_number"
        )

        # Mock GitHub issue with existing labels including priority
        # Use only labels that exist in ISSUE_CREATION_LABEL_CHOICES
        mock_tracker_data = {
            "success": True,
            "issue": {
                "number": 123,
                "title": "Test Issue",
                "body": "Test body",
                "state": "open",
                "labels": [
                    "bug",
                    "feature",
                    "high priority",
                    "question",
                ],  # Only valid choices
                "assignees": ["user1"],
                "html_url": "https://github.com/owner/repo/issues/123",
                "created_at": "2023-01-01T10:00:00",
                "updated_at": "2023-01-15T15:30:00",
            },
        }
        mock_get_issue.return_value = mock_tracker_data

        client.force_login(superuser)
        url = reverse("issue_detail", kwargs={"pk": issue.pk})
        response = client.get(url)

        assert response.status_code == 200
        form = response.context["labels_form"]

        # Check that form is prepopulated with correct values
        # Only labels that exist in ISSUE_CREATION_LABEL_CHOICES should be included
        assert set(form.initial["labels"]) == {"bug", "feature"}
        assert form.initial["priority"] == "high priority"

    def test_issuedetailview_form_prepopulated_with_default_priority_when_no_priority(
        self, client, superuser, issue, mocker
    ):
        """Test that form uses default priority when no priority label exists."""
        provider = settings.ISSUE_TRACKER_PROVIDER.lower()
        name = provider.capitalize()
        mocker.patch(f"issues.{provider}.{name}Provider._get_client")
        mocker.patch(f"issues.{provider}.{name}Provider._get_repository")
        mock_get_issue = mocker.patch(
            f"issues.{provider}.BaseIssueProvider.issue_by_number"
        )

        # Mock GitHub issue with labels but no priority
        mock_tracker_data = {
            "success": True,
            "issue": {
                "number": 123,
                "title": "Test Issue",
                "body": "Test body",
                "state": "open",
                "labels": ["bug", "feature"],  # No priority label, only valid choices
                "assignees": ["user1"],
                "html_url": "https://github.com/owner/repo/issues/123",
                "created_at": "2023-01-01T10:00:00",
                "updated_at": "2023-01-15T15:30:00",
            },
        }
        mock_get_issue.return_value = mock_tracker_data

        client.force_login(superuser)
        url = reverse("issue_detail", kwargs={"pk": issue.pk})
        response = client.get(url)

        assert response.status_code == 200
        form = response.context["labels_form"]

        # Check that form uses default priority
        assert set(form.initial["labels"]) == {"bug", "feature"}
        assert form.initial["priority"] == "medium priority"  # Default

    def test_issuedetailview_form_prepopulated_with_unknown_labels_filtered_out(
        self, client, superuser, issue, mocker
    ):
        """Test that unknown labels are filtered out during prepopulation."""
        provider = settings.ISSUE_TRACKER_PROVIDER.lower()
        name = provider.capitalize()
        mocker.patch(f"issues.{provider}.{name}Provider._get_client")
        mocker.patch(f"issues.{provider}.{name}Provider._get_repository")
        mock_get_issue = mocker.patch(
            f"issues.{provider}.BaseIssueProvider.issue_by_number"
        )

        # Mock GitHub issue with some unknown labels
        mock_tracker_data = {
            "success": True,
            "issue": {
                "number": 123,
                "title": "Test Issue",
                "body": "Test body",
                "state": "open",
                "labels": ["bug", "unknown_label", "high priority", "another_unknown"],
                "assignees": ["user1"],
                "html_url": "https://github.com/owner/repo/issues/123",
                "created_at": "2023-01-01T10:00:00",
                "updated_at": "2023-01-15T15:30:00",
            },
        }
        mock_get_issue.return_value = mock_tracker_data

        client.force_login(superuser)
        url = reverse("issue_detail", kwargs={"pk": issue.pk})
        response = client.get(url)

        assert response.status_code == 200
        form = response.context["labels_form"]

        # Check that only known labels are included
        assert form.initial["labels"] == ["bug"]  # Only known label
        assert form.initial["priority"] == "high priority"

    def test_issuedetailview_priority_detection_with_various_formats(
        self, client, superuser, issue, mocker
    ):
        """Test that priority detection works with various label formats."""
        provider = settings.ISSUE_TRACKER_PROVIDER.lower()
        name = provider.capitalize()
        mocker.patch(f"issues.{provider}.{name}Provider._get_client")
        mocker.patch(f"issues.{provider}.{name}Provider._get_repository")
        mock_get_issue = mocker.patch(
            f"issues.{provider}.BaseIssueProvider.issue_by_number"
        )

        # Mock GitHub issue with different priority label formats
        mock_tracker_data = {
            "success": True,
            "issue": {
                "number": 123,
                "title": "Test Issue",
                "body": "Test body",
                "state": "open",
                "labels": [
                    "bug",
                    "low priority",  # Use lowercase to match actual priority choices
                ],  # Only one priority to avoid ambiguity
                "assignees": ["user1"],
                "html_url": "https://github.com/owner/repo/issues/123",
                "created_at": "2023-01-01T10:00:00",
                "updated_at": "2023-01-15T15:30:00",
            },
        }
        mock_get_issue.return_value = mock_tracker_data

        client.force_login(superuser)
        url = reverse("issue_detail", kwargs={"pk": issue.pk})
        response = client.get(url)

        assert response.status_code == 200
        form = response.context["labels_form"]

        # Should detect the priority label correctly
        assert form.initial["labels"] == ["bug"]
        assert form.initial["priority"] == "low priority"

    def test_issuedetailview_post_request_sets_labels_successfully(
        self, client, superuser, issue, mocker
    ):
        """Test that POST request successfully sets labels on GitHub issue."""
        provider = settings.ISSUE_TRACKER_PROVIDER.lower()
        name = provider.capitalize()
        mocker.patch(f"issues.{provider}.{name}Provider._get_client")
        mocker.patch(f"issues.{provider}.{name}Provider._get_repository")
        mock_add_labels = mocker.patch(
            f"issues.{provider}.BaseIssueProvider.set_labels_to_issue"
        )
        mock_add_labels.return_value = {
            "success": True,
            "message": (
                "Added labels ['bug', 'feature', 'high priority'] "
                f"to issue #{issue.number}"
            ),
            "current_labels": ["bug", "feature", "high priority"],
        }

        client.force_login(superuser)
        url = reverse("issue_detail", kwargs={"pk": issue.pk})

        # Submit form with selected labels and priority
        response = client.post(
            url, {"labels": ["bug", "feature"], "priority": "high priority"}
        )

        assert response.status_code == 302  # Redirect after POST
        # Fix the URL assertion to match your actual URL pattern
        expected_url = reverse("issue_detail", kwargs={"pk": issue.pk})
        assert response.url == expected_url

    def test_issuedetailview_post_request_handles_tracker_error(
        self, client, superuser, issue, mocker
    ):
        """Test that GitHub errors are handled when setting labels."""
        provider = settings.ISSUE_TRACKER_PROVIDER.lower()
        name = provider.capitalize()
        mocker.patch(f"issues.{provider}.{name}Provider._get_client")
        mocker.patch(f"issues.{provider}.{name}Provider._get_repository")
        mock_add_labels = mocker.patch(
            f"issues.{provider}.BaseIssueProvider.set_labels_to_issue"
        )
        mock_add_labels.return_value = {
            "success": False,
            "error": "GitHub API rate limit exceeded",
        }

        client.force_login(superuser)
        url = reverse("issue_detail", kwargs={"pk": issue.pk})

        response = client.post(url, {"labels": ["bug"], "priority": "medium priority"})

        assert response.status_code == 302

    def test_issuedetailview_post_request_invalid_form(self, client, superuser, issue):
        """Test that invalid form submission shows error."""
        client.force_login(superuser)
        url = reverse("issue_detail", kwargs={"pk": issue.pk})

        # Submit empty form (invalid)
        response = client.post(url, {})

        assert response.status_code == 302

    def test_issuedetailview_post_request_denied_for_regular_user(
        self, client, regular_user, issue
    ):
        """Test that regular users cannot submit the form."""
        client.force_login(regular_user)
        url = reverse("issue_detail", kwargs={"pk": issue.pk})

        response = client.post(url, {"labels": ["bug"], "priority": "medium priority"})

        # Should redirect with error message
        assert response.status_code == 302

    def test_issuedetailview_context_variables_for_priority_and_labels(
        self, client, superuser, issue, mocker
    ):
        """Test that context variables for current priority and labels are set."""
        provider = settings.ISSUE_TRACKER_PROVIDER.lower()
        name = provider.capitalize()
        mocker.patch(f"issues.{provider}.{name}Provider._get_client")
        mocker.patch(f"issues.{provider}.{name}Provider._get_repository")
        mock_get_issue = mocker.patch(
            f"issues.{provider}.BaseIssueProvider.issue_by_number"
        )

        mock_tracker_data = {
            "success": True,
            "issue": {
                "number": 123,
                "title": "Test Issue",
                "body": "Test body",
                "state": "open",
                "labels": ["bug", "feature", "high priority"],  # Use valid choices
                "assignees": ["user1"],
                "html_url": "https://github.com/owner/repo/issues/123",
                "created_at": "2023-01-01T10:00:00",
                "updated_at": "2023-01-15T15:30:00",
            },
        }
        mock_get_issue.return_value = mock_tracker_data

        client.force_login(superuser)
        url = reverse("issue_detail", kwargs={"pk": issue.pk})
        response = client.get(url)

        assert response.status_code == 200
        context = response.context

        # Check that context variables are set
        assert context["current_priority"] == "high priority"
        assert set(context["current_custom_labels"]) == {"bug", "feature"}

    def test_issuedetailview_form_in_template_for_superuser(
        self, client, superuser, issue, mocker
    ):
        """Test that form appears in template for superusers."""
        provider = settings.ISSUE_TRACKER_PROVIDER.lower()
        name = provider.capitalize()
        mocker.patch(f"issues.{provider}.{name}Provider._get_client")
        mocker.patch(f"issues.{provider}.{name}Provider._get_repository")
        mock_get_issue = mocker.patch(
            f"issues.{provider}.BaseIssueProvider.issue_by_number"
        )
        mock_tracker_data = {
            "success": True,
            "issue": {
                "number": 123,
                "title": "Test Issue",
                "body": "Test body",
                "state": "open",
                "labels": ["bug", "high priority"],
                "assignees": ["user1"],
                "html_url": "https://github.com/owner/repo/issues/123",
                "created_at": "2023-01-01T10:00:00",
                "updated_at": "2023-01-15T15:30:00",
            },
        }
        mock_get_issue.return_value = mock_tracker_data

        client.force_login(superuser)
        url = reverse("issue_detail", kwargs={"pk": issue.pk})
        response = client.get(url)

        assert response.status_code == 200
        # Check that form elements are in the response
        content = response.content.decode()
        assert "Update Labels" in content  # Button text
        assert "bug" in content  # Label option
        assert "high priority" in content  # Priority option


@pytest.mark.django_db
class TestIssueDetailViewSubmissionHandlers:
    """Test the submission handler methods in IssueDetailView."""

    # # _handle_labels_submission
    def test_issuedetailview_handle_labels_submission_success(
        self, client, superuser, issue, mocker
    ):
        """Test successful labels form submission."""
        provider = settings.ISSUE_TRACKER_PROVIDER.lower()
        name = provider.capitalize()
        mocker.patch(f"issues.{provider}.{name}Provider._get_client")
        mocker.patch(f"issues.{provider}.{name}Provider._get_repository")
        mock_add_labels = mocker.patch(
            f"issues.{provider}.BaseIssueProvider.set_labels_to_issue"
        )
        mock_add_labels.return_value = {
            "success": True,
            "message": f"Added labels ['bug', 'feature', 'high priority'] to issue #{issue.number}",
            "current_labels": ["bug", "feature", "high priority"],
        }
        mocked_log_action = mocker.patch("core.models.Profile.log_action")

        client.force_login(superuser)
        url = reverse("issue_detail", kwargs={"pk": issue.pk})

        response = client.post(
            url,
            {
                "labels": ["bug", "feature"],
                "priority": "high priority",
                "submit_labels": "Set labels",
            },
        )

        assert response.status_code == 302
        assert response.url == reverse("issue_detail", kwargs={"pk": issue.pk})

        # Verify the function was called with correct arguments
        mock_add_labels.assert_called_once_with(
            issue.number, ["bug", "feature", "high priority"]
        )

        # Check success message
        messages = list(get_messages(response.wsgi_request))
        assert any(
            "Labels updated successfully" in str(message) for message in messages
        )
        mocked_log_action.assert_called_once()

    def test_issuedetailview_handle_labels_submission_tracker_failure(
        self, client, superuser, issue, mocker
    ):
        provider = settings.ISSUE_TRACKER_PROVIDER.lower()
        name = provider.capitalize()
        mocker.patch(f"issues.{provider}.{name}Provider._get_client")
        mocker.patch(f"issues.{provider}.{name}Provider._get_repository")
        mock_add_labels = mocker.patch(
            f"issues.{provider}.BaseIssueProvider.set_labels_to_issue"
        )
        mock_add_labels.return_value = {
            "success": False,
            "error": "GitHub API rate limit exceeded",
        }

        client.force_login(superuser)
        url = reverse("issue_detail", kwargs={"pk": issue.pk})

        response = client.post(
            url,
            {
                "labels": ["bug"],
                "priority": "medium priority",
                "submit_labels": "Set labels",
            },
        )

        assert response.status_code == 302
        assert response.url == reverse("issue_detail", kwargs={"pk": issue.pk})

        # Check error message
        messages = list(get_messages(response.wsgi_request))
        assert any("Failed to set labels" in str(message) for message in messages)
        assert any(
            "GitHub API rate limit exceeded" in str(message) for message in messages
        )

    def test_issuedetailview_handle_labels_submission_invalid_form(
        self, client, superuser, issue
    ):
        """Test labels form submission with invalid form data."""
        client.force_login(superuser)
        url = reverse("issue_detail", kwargs={"pk": issue.pk})

        # Submit empty form (invalid - required fields missing)
        response = client.post(
            url,
            {
                "submit_labels": "Set labels"
                # Missing 'labels' and 'priority' fields
            },
        )

        assert response.status_code == 302
        assert response.url == reverse("issue_detail", kwargs={"pk": issue.pk})

        # Check error message
        messages = list(get_messages(response.wsgi_request))
        assert any(
            "Please correct the errors in the form" in str(message)
            for message in messages
        )

    def test_issuedetailview_handle_labels_submission_empty_labels(
        self, client, superuser, issue
    ):
        """Test labels form submission with empty labels list."""
        client.force_login(superuser)
        url = reverse("issue_detail", kwargs={"pk": issue.pk})

        # Submit form with empty labels (invalid)
        response = client.post(
            url,
            {
                "labels": [],  # Empty labels
                "priority": "medium priority",
                "submit_labels": "Set labels",
            },
        )

        assert response.status_code == 302
        assert response.url == reverse("issue_detail", kwargs={"pk": issue.pk})

        # Check error message
        messages = list(get_messages(response.wsgi_request))
        assert any(
            "Please correct the errors in the form" in str(message)
            for message in messages
        )

    # # _handle_close_submission - addressed action
    def test_issuedetailview_handle_close_submission_addressed_success(
        self, client, superuser, issue, mocker
    ):
        provider = settings.ISSUE_TRACKER_PROVIDER.lower()
        name = provider.capitalize()
        mocker.patch(f"issues.{provider}.{name}Provider._get_client")
        mocker.patch(f"issues.{provider}.{name}Provider._get_repository")
        mock_get_issue = mocker.patch(
            f"issues.{provider}.BaseIssueProvider.issue_by_number"
        )
        mock_close_issue = mocker.patch(
            f"issues.{provider}.BaseIssueProvider.close_issue_with_labels"
        )
        mocked_log_action = mocker.patch("core.models.Profile.log_action")
        mocked_process = mocker.patch(
            "core.views.process_allocations_for_contributions",
            return_value=[(False, [])],
        )
        mock_tracker_data = {
            "success": True,
            "issue": {
                "number": 123,
                "title": "Test Issue",
                "body": "Test body",
                "state": "open",
                "labels": ["bug", "work in progress", "feature"],
                "assignees": [],
                "html_url": "https://github.com/owner/repo/issues/123",
                "created_at": "2023-01-01T10:00:00",
                "updated_at": "2023-01-15T15:30:00",
            },
        }
        mock_get_issue.return_value = mock_tracker_data
        mock_close_issue.return_value = {"success": True}

        client.force_login(superuser)
        url = reverse("issue_detail", kwargs={"pk": issue.pk})

        response = client.post(
            url,
            {
                "close_action": "addressed",
                "close_comment": "This issue has been addressed successfully.",
                "submit_close": "Confirm Close",
            },
        )

        assert response.status_code == 302
        assert response.url == reverse("issue_detail", kwargs={"pk": issue.pk})

        # Check that issue status was updated
        issue.refresh_from_db()
        assert issue.status == IssueStatus.ADDRESSED

        # Check that close_issue_with_labels was called with correct arguments
        mock_close_issue.assert_called_once()
        call_args = mock_close_issue.call_args[1]
        assert call_args["issue_number"] == issue.number
        assert call_args["comment"] == "This issue has been addressed successfully."
        assert "addressed" in call_args["labels_to_set"]
        assert "work in progress" not in call_args["labels_to_set"]
        assert "bug" in call_args["labels_to_set"]
        assert "feature" in call_args["labels_to_set"]

        # Check success message
        messages = list(get_messages(response.wsgi_request))
        assert any(
            f"✅ Issue #{issue.number} closed as addressed successfully" in str(message)
            for message in messages
        )

        calls = [
            mocker.call(
                "issue_closed",
                f"✅ Issue #{issue.number} closed as addressed successfully.",
            ),
            mocker.call("issue_status_set", str(issue)),
        ]
        mocked_log_action.assert_has_calls(calls)
        call_args = mocked_process.call_args[0]
        assert isinstance(call_args[0], QuerySet)
        assert (
            call_args[1]
            == Contribution.objects.addresses_and_amounts_from_contributions
        )

    def test_issuedetailview_handle_close_submission_addressed_success_no_comment(
        self, client, superuser, issue, contribution, mocker
    ):
        provider = settings.ISSUE_TRACKER_PROVIDER.lower()
        name = provider.capitalize()
        mocker.patch(f"issues.{provider}.{name}Provider._get_client")
        mocker.patch(f"issues.{provider}.{name}Provider._get_repository")
        mock_get_issue = mocker.patch(
            f"issues.{provider}.BaseIssueProvider.issue_by_number"
        )
        mock_close_issue = mocker.patch(
            f"issues.{provider}.BaseIssueProvider.close_issue_with_labels"
        )
        mock_add_reaction = mocker.patch(
            "updaters.discord.DiscordUpdater.add_reaction_to_message"
        )
        mocked_log_action = mocker.patch("core.models.Profile.log_action")
        mocked_process = mocker.patch(
            "core.views.process_allocations_for_contributions",
            return_value=[("txid", ["addr1"])],
        )
        mock_tracker_data = {
            "success": True,
            "issue": {
                "number": 123,
                "title": "Test Issue",
                "body": "Test body",
                "state": "open",
                "labels": ["bug"],
                "assignees": [],
                "html_url": "https://github.com/owner/repo/issues/123",
                "created_at": "2023-01-01T10:00:00",
                "updated_at": "2023-01-15T15:30:00",
            },
        }
        mock_get_issue.return_value = mock_tracker_data
        mock_close_issue.return_value = {"success": True}

        client.force_login(superuser)
        contribution.issue = issue
        contribution.save()
        url = reverse("issue_detail", kwargs={"pk": issue.pk})

        response = client.post(
            url,
            {
                "close_action": "addressed",
                "close_comment": "",  # Empty comment
                "submit_close": "Confirm Close",
            },
        )

        assert response.status_code == 302

        # Check that close_issue_with_labels was called with empty comment
        mock_close_issue.assert_called_once()
        mock_add_reaction.assert_called_once_with(contribution.url, "addressed")

        calls = [
            mocker.call(
                "issue_closed",
                f"✅ Issue #{issue.number} closed as addressed successfully.",
            ),
            mocker.call("issue_status_set", "123 [addressed]"),
            mocker.call("issue_status_set", "123 [claimable]"),
        ]
        mocked_log_action.assert_has_calls(calls)
        mocked_log_action.call_count == 4
        call_args = mocked_process.call_args[0]
        assert isinstance(call_args[0], QuerySet)
        assert (
            call_args[1]
            == Contribution.objects.addresses_and_amounts_from_contributions
        )

        call_args = mock_close_issue.call_args[1]
        assert call_args["comment"] == ""

    def test_issuedetailview_handle_close_submission_wontfix_success(
        self, client, superuser, issue, mocker
    ):
        provider = settings.ISSUE_TRACKER_PROVIDER.lower()
        name = provider.capitalize()
        mocker.patch(f"issues.{provider}.{name}Provider._get_client")
        mocker.patch(f"issues.{provider}.{name}Provider._get_repository")
        mock_get_issue = mocker.patch(
            f"issues.{provider}.BaseIssueProvider.issue_by_number"
        )
        mock_close_issue = mocker.patch(
            f"issues.{provider}.BaseIssueProvider.close_issue_with_labels"
        )
        mock_tracker_data = {
            "success": True,
            "issue": {
                "number": 123,
                "title": "Test Issue",
                "body": "Test body",
                "state": "open",
                "labels": ["bug", "work in progress"],
                "assignees": [],
                "html_url": "https://github.com/owner/repo/issues/123",
                "created_at": "2023-01-01T10:00:00",
                "updated_at": "2023-01-15T15:30:00",
            },
        }
        mock_get_issue.return_value = mock_tracker_data
        mock_close_issue.return_value = {"success": True}

        client.force_login(superuser)
        url = reverse("issue_detail", kwargs={"pk": issue.pk})

        response = client.post(
            url,
            {
                "close_action": "wontfix",
                "close_comment": "This issue will not be fixed.",
                "submit_close": "Confirm Close",
            },
        )

        assert response.status_code == 302
        assert response.url == reverse("issue_detail", kwargs={"pk": issue.pk})

        # Check that issue status was updated
        issue.refresh_from_db()
        assert issue.status == IssueStatus.WONTFIX

        # Check that close_issue_with_labels was called with correct arguments
        mock_close_issue.assert_called_once()
        call_args = mock_close_issue.call_args[1]
        assert call_args["issue_number"] == issue.number
        assert call_args["comment"] == "This issue will not be fixed."
        assert "wontfix" in call_args["labels_to_set"]
        assert "work in progress" not in call_args["labels_to_set"]

        # Check success message
        messages = list(get_messages(response.wsgi_request))
        assert any(
            f"Issue #{issue.number} closed as wontfix successfully" in str(message)
            for message in messages
        )

    def test_issuedetailview_handle_close_submission_invalid_action(
        self, client, superuser, issue
    ):
        """Test close submission with invalid action."""
        client.force_login(superuser)
        url = reverse("issue_detail", kwargs={"pk": issue.pk})

        response = client.post(
            url,
            {
                "close_action": "invalid_action",  # Invalid action
                "close_comment": "",
                "submit_close": "Confirm Close",
            },
        )

        assert response.status_code == 302
        assert response.url == reverse("issue_detail", kwargs={"pk": issue.pk})

        # Check error message
        messages = list(get_messages(response.wsgi_request))
        assert any("Invalid close action" in str(message) for message in messages)

    def test_issuedetailview_handle_close_submission_tracker_fetch_failure(
        self, client, superuser, issue, mocker
    ):
        provider = settings.ISSUE_TRACKER_PROVIDER.lower()
        name = provider.capitalize()
        mocker.patch(f"issues.{provider}.{name}Provider._get_client")
        mocker.patch(f"issues.{provider}.{name}Provider._get_repository")
        mock_get_issue = mocker.patch(
            f"issues.{provider}.BaseIssueProvider.issue_by_number"
        )

        mock_tracker_data = {"success": False, "error": "Authentication failed"}
        mock_get_issue.return_value = mock_tracker_data

        client.force_login(superuser)
        url = reverse("issue_detail", kwargs={"pk": issue.pk})

        response = client.post(
            url,
            {
                "close_action": "addressed",
                "close_comment": "",
                "submit_close": "Confirm Close",
            },
        )

        assert response.status_code == 302
        assert response.url == reverse("issue_detail", kwargs={"pk": issue.pk})

        # Check error message
        messages = list(get_messages(response.wsgi_request))
        assert any(
            "Failed to fetch tracker issue" in str(message) for message in messages
        )
        assert any("Authentication failed" in str(message) for message in messages)

    def test_issuedetailview_handle_close_submission_already_closed_issue(
        self, client, superuser, issue, mocker
    ):
        provider = settings.ISSUE_TRACKER_PROVIDER.lower()
        name = provider.capitalize()
        mocker.patch(f"issues.{provider}.{name}Provider._get_client")
        mocker.patch(f"issues.{provider}.{name}Provider._get_repository")
        mock_get_issue = mocker.patch(
            f"issues.{provider}.BaseIssueProvider.issue_by_number"
        )
        mock_tracker_data = {
            "success": True,
            "issue": {
                "number": 123,
                "title": "Test Issue",
                "body": "Test body",
                "state": "closed",  # Already closed
                "labels": ["bug"],
                "assignees": [],
                "html_url": "https://github.com/owner/repo/issues/123",
                "created_at": "2023-01-01T10:00:00",
                "updated_at": "2023-01-15T15:30:00",
            },
        }
        mock_get_issue.return_value = mock_tracker_data

        client.force_login(superuser)
        url = reverse("issue_detail", kwargs={"pk": issue.pk})

        response = client.post(
            url,
            {
                "close_action": "addressed",
                "close_comment": "",
                "submit_close": "Confirm Close",
            },
        )

        assert response.status_code == 302
        assert response.url == reverse("issue_detail", kwargs={"pk": issue.pk})

        # Check error message
        messages = list(get_messages(response.wsgi_request))
        assert any("already closed on tracker" in str(message) for message in messages)

    def test_issuedetailview_handle_close_submission_tracker_close_failure(
        self, client, superuser, issue, mocker
    ):
        provider = settings.ISSUE_TRACKER_PROVIDER.lower()
        name = provider.capitalize()
        mocker.patch(f"issues.{provider}.{name}Provider._get_client")
        mocker.patch(f"issues.{provider}.{name}Provider._get_repository")
        mock_get_issue = mocker.patch(
            f"issues.{provider}.BaseIssueProvider.issue_by_number"
        )
        mock_close_issue = mocker.patch(
            f"issues.{provider}.BaseIssueProvider.close_issue_with_labels"
        )
        mock_tracker_data = {
            "success": True,
            "issue": {
                "number": 123,
                "title": "Test Issue",
                "body": "Test body",
                "state": "open",
                "labels": ["bug"],
                "assignees": [],
                "html_url": "https://github.com/owner/repo/issues/123",
                "created_at": "2023-01-01T10:00:00",
                "updated_at": "2023-01-15T15:30:00",
            },
        }
        mock_get_issue.return_value = mock_tracker_data
        mock_close_issue.return_value = {
            "success": False,
            "error": "Failed to close issue on tracker",
        }

        client.force_login(superuser)
        url = reverse("issue_detail", kwargs={"pk": issue.pk})

        response = client.post(
            url,
            {
                "close_action": "addressed",
                "close_comment": "",
                "submit_close": "Confirm Close",
            },
        )

        assert response.status_code == 302
        assert response.url == reverse("issue_detail", kwargs={"pk": issue.pk})

        # Check that local status was reverted
        issue.refresh_from_db()
        assert issue.status == IssueStatus.CREATED  # Reverted to original

        # Check error message - the actual error message from the view
        messages = list(get_messages(response.wsgi_request))
        assert any(
            "Failed to close issue on tracker" in str(message) for message in messages
        )

    def test_issuedetailview_handle_close_submission_exception_handling(
        self, client, superuser, issue, mocker
    ):
        provider = settings.ISSUE_TRACKER_PROVIDER.lower()
        name = provider.capitalize()
        mocker.patch(f"issues.{provider}.{name}Provider._get_client")
        mocker.patch(f"issues.{provider}.{name}Provider._get_repository")
        mock_get_issue = mocker.patch(
            f"issues.{provider}.BaseIssueProvider.issue_by_number"
        )
        mock_get_issue.side_effect = Exception("Unexpected error")

        client.force_login(superuser)
        url = reverse("issue_detail", kwargs={"pk": issue.pk})

        response = client.post(
            url,
            {
                "close_action": "addressed",
                "close_comment": "",
                "submit_close": "Confirm Close",
            },
        )

        assert response.status_code == 302
        assert response.url == reverse("issue_detail", kwargs={"pk": issue.pk})

        # Check error message
        messages = list(get_messages(response.wsgi_request))
        assert any("Error closing issue" in str(message) for message in messages)
        assert any("Unexpected error" in str(message) for message in messages)

    def test_issuedetailview_handle_close_submission_labels_processing(
        self, client, superuser, issue, mocker
    ):
        provider = settings.ISSUE_TRACKER_PROVIDER.lower()
        name = provider.capitalize()
        mocker.patch(f"issues.{provider}.{name}Provider._get_client")
        mocker.patch(f"issues.{provider}.{name}Provider._get_repository")
        mock_get_issue = mocker.patch(
            f"issues.{provider}.BaseIssueProvider.issue_by_number"
        )
        mock_close_issue = mocker.patch(
            f"issues.{provider}.BaseIssueProvider.close_issue_with_labels"
        )
        mock_tracker_data = {
            "success": True,
            "issue": {
                "number": 123,
                "title": "Test Issue",
                "body": "Test body",
                "state": "open",
                "labels": [
                    "work in progress",
                    "bug",
                    "enhancement",
                    "WORK IN PROGRESS",
                ],  # Multiple cases
                "assignees": [],
                "html_url": "https://github.com/owner/repo/issues/123",
                "created_at": "2023-01-01T10:00:00",
                "updated_at": "2023-01-15T15:30:00",
            },
        }
        mock_get_issue.return_value = mock_tracker_data
        mock_close_issue.return_value = {"success": True}

        client.force_login(superuser)
        url = reverse("issue_detail", kwargs={"pk": issue.pk})

        response = client.post(
            url,
            {
                "close_action": "addressed",
                "close_comment": "",
                "submit_close": "Confirm Close",
            },
        )

        assert response.status_code == 302

        # Check that close_issue_with_labels was called with correct labels
        mock_close_issue.assert_called_once()
        call_args = mock_close_issue.call_args[1]
        labels_to_set = call_args["labels_to_set"]

        # Should contain addressed label and other labels except work in progress variants
        assert "addressed" in labels_to_set
        assert "bug" in labels_to_set
        assert "enhancement" in labels_to_set
        assert "work in progress" not in labels_to_set
        assert "WORK IN PROGRESS" not in labels_to_set

    def test_issuedetailview_handle_close_submission_existing_label_not_duplicated(
        self, client, superuser, issue, mocker
    ):
        provider = settings.ISSUE_TRACKER_PROVIDER.lower()
        name = provider.capitalize()
        mocker.patch(f"issues.{provider}.{name}Provider._get_client")
        mocker.patch(f"issues.{provider}.{name}Provider._get_repository")
        mock_get_issue = mocker.patch(
            f"issues.{provider}.BaseIssueProvider.issue_by_number"
        )
        mock_close_issue = mocker.patch(
            f"issues.{provider}.BaseIssueProvider.close_issue_with_labels"
        )
        mock_tracker_data = {
            "success": True,
            "issue": {
                "number": 123,
                "title": "Test Issue",
                "body": "Test body",
                "state": "open",
                "labels": ["bug", "addressed"],  # Already has addressed label
                "assignees": [],
                "html_url": "https://github.com/owner/repo/issues/123",
                "created_at": "2023-01-01T10:00:00",
                "updated_at": "2023-01-15T15:30:00",
            },
        }
        mock_get_issue.return_value = mock_tracker_data
        mock_close_issue.return_value = {"success": True}

        client.force_login(superuser)
        url = reverse("issue_detail", kwargs={"pk": issue.pk})

        response = client.post(
            url,
            {
                "close_action": "addressed",
                "close_comment": "",
                "submit_close": "Confirm Close",
            },
        )

        assert response.status_code == 302

        # Check that close_issue_with_labels was called with labels
        mock_close_issue.assert_called_once()
        call_args = mock_close_issue.call_args[1]
        labels_to_set = call_args["labels_to_set"]

        # Should contain only one 'addressed' label (not duplicated)
        assert labels_to_set.count("addressed") == 1


@pytest.mark.django_db
class TestIssueDetailViewCloseFunctionality:
    """Test the close issue functionality in IssueDetailView."""

    def test_issuedetailview_close_buttons_not_shown_for_regular_user(
        self, client, regular_user, issue, mocker
    ):
        provider = settings.ISSUE_TRACKER_PROVIDER.lower()
        name = provider.capitalize()
        mocker.patch(f"issues.{provider}.{name}Provider._get_client")
        mocker.patch(f"issues.{provider}.{name}Provider._get_repository")
        mock_get_issue = mocker.patch(
            f"issues.{provider}.BaseIssueProvider.issue_by_number"
        )
        mock_tracker_data = {
            "success": True,
            "issue": {
                "number": 123,
                "title": "Test Issue",
                "body": "Test body",
                "state": "open",
                "labels": ["bug"],
                "assignees": [],
                "html_url": "https://github.com/owner/repo/issues/123",
                "created_at": "2023-01-01T10:00:00",
                "updated_at": "2023-01-15T15:30:00",
            },
        }
        mock_get_issue.return_value = mock_tracker_data

        client.force_login(regular_user)
        url = reverse("issue_detail", kwargs={"pk": issue.pk})
        response = client.get(url)

        assert response.status_code == 200
        content = response.content.decode()
        assert "Close as addressed" not in content
        assert "Close as wontfix" not in content

    def test_issuedetailview_close_buttons_not_shown_for_closed_issue(
        self, client, superuser, issue, mocker
    ):
        provider = settings.ISSUE_TRACKER_PROVIDER.lower()
        name = provider.capitalize()
        mocker.patch(f"issues.{provider}.{name}Provider._get_client")
        mocker.patch(f"issues.{provider}.{name}Provider._get_repository")
        mock_get_issue = mocker.patch(
            f"issues.{provider}.BaseIssueProvider.issue_by_number"
        )
        mock_tracker_data = {
            "success": True,
            "issue": {
                "number": 123,
                "title": "Test Issue",
                "body": "Test body",
                "state": "closed",
                "labels": ["bug"],
                "assignees": [],
                "html_url": "https://github.com/owner/repo/issues/123",
                "created_at": "2023-01-01T10:00:00",
                "updated_at": "2023-01-15T15:30:00",
            },
        }
        mock_get_issue.return_value = mock_tracker_data

        client.force_login(superuser)
        url = reverse("issue_detail", kwargs={"pk": issue.pk})
        response = client.get(url)

        assert response.status_code == 200
        content = response.content.decode()
        assert "Close as addressed" not in content
        assert "Close as wontfix" not in content

    def test_issuedetailview_close_buttons_shown_for_open_issue_and_superuser(
        self, client, superuser, issue, mocker
    ):
        provider = settings.ISSUE_TRACKER_PROVIDER.lower()
        name = provider.capitalize()
        mocker.patch(f"issues.{provider}.{name}Provider._get_client")
        mocker.patch(f"issues.{provider}.{name}Provider._get_repository")
        mock_get_issue = mocker.patch(
            f"issues.{provider}.BaseIssueProvider.issue_by_number"
        )
        mocker.patch(
            "core.views.process_allocations_for_contributions", return_value=(False, [])
        )
        mock_tracker_data = {
            "success": True,
            "issue": {
                "number": 123,
                "title": "Test Issue",
                "body": "Test body",
                "state": "open",
                "labels": ["bug"],
                "assignees": [],
                "html_url": "https://github.com/owner/repo/issues/123",
                "created_at": "2023-01-01T10:00:00",
                "updated_at": "2023-01-15T15:30:00",
            },
        }
        mock_get_issue.return_value = mock_tracker_data

        client.force_login(superuser)
        url = reverse("issue_detail", kwargs={"pk": issue.pk})
        response = client.get(url)

        assert response.status_code == 200
        content = response.content.decode()
        assert "Close as addressed" in content
        assert "Close as wontfix" in content

    def test_issuedetailview_close_as_addressed_success(
        self, client, superuser, issue, mocker
    ):
        provider = settings.ISSUE_TRACKER_PROVIDER.lower()
        name = provider.capitalize()
        mocker.patch(f"issues.{provider}.{name}Provider._get_client")
        mocker.patch(f"issues.{provider}.{name}Provider._get_repository")
        mock_get_issue = mocker.patch(
            f"issues.{provider}.BaseIssueProvider.issue_by_number"
        )
        mock_close_issue = mocker.patch(
            f"issues.{provider}.BaseIssueProvider.close_issue_with_labels"
        )
        mock_process = mocker.patch(
            "core.views.process_allocations_for_contributions",
            return_value=[(False, [])],
        )
        mock_tracker_data = {
            "success": True,
            "issue": {
                "number": 123,
                "title": "Test Issue",
                "body": "Test body",
                "state": "open",
                "labels": ["bug", "work in progress"],
                "assignees": [],
                "html_url": "https://github.com/owner/repo/issues/123",
                "created_at": "2023-01-01T10:00:00",
                "updated_at": "2023-01-15T15:30:00",
            },
        }
        mock_get_issue.return_value = mock_tracker_data
        mock_close_issue.return_value = {"success": True}

        client.force_login(superuser)
        url = reverse("issue_detail", kwargs={"pk": issue.pk})

        response = client.post(
            url,
            {
                "close_action": "addressed",
                "close_comment": "Fixed the issue",
                "submit_close": "Confirm Close",
            },
        )

        assert response.status_code == 302
        assert response.url == reverse("issue_detail", kwargs={"pk": issue.pk})

        # Check that issue status was updated
        issue.refresh_from_db()
        assert issue.status == IssueStatus.ADDRESSED

        # Check that close_issue_with_labels was called with correct arguments
        mock_close_issue.assert_called_once()
        call_args = mock_close_issue.call_args[1]
        assert call_args["issue_number"] == issue.number
        assert call_args["comment"] == "Fixed the issue"
        assert "addressed" in call_args["labels_to_set"]
        assert "work in progress" not in call_args["labels_to_set"]
        mock_process.assert_called_once_with(
            mocker.ANY,
            Contribution.objects.addresses_and_amounts_from_contributions,
        )

    def test_issuedetailview_close_as_addressed_success_and_claimable(
        self, client, superuser, issue, mocker
    ):
        provider = settings.ISSUE_TRACKER_PROVIDER.lower()
        name = provider.capitalize()
        mocker.patch(f"issues.{provider}.{name}Provider._get_client")
        mocker.patch(f"issues.{provider}.{name}Provider._get_repository")
        mock_get_issue = mocker.patch(
            f"issues.{provider}.BaseIssueProvider.issue_by_number"
        )
        mock_close_issue = mocker.patch(
            f"issues.{provider}.BaseIssueProvider.close_issue_with_labels"
        )
        mock_process = mocker.patch(
            "core.views.process_allocations_for_contributions",
            return_value=[("txid1", ["addr1"]), ("txid2", ["addr2"])],
        )
        mock_tracker_data = {
            "success": True,
            "issue": {
                "number": 123,
                "title": "Test Issue",
                "body": "Test body",
                "state": "open",
                "labels": ["bug", "work in progress"],
                "assignees": [],
                "html_url": "https://github.com/owner/repo/issues/123",
                "created_at": "2023-01-01T10:00:00",
                "updated_at": "2023-01-15T15:30:00",
            },
        }
        mock_get_issue.return_value = mock_tracker_data
        mock_close_issue.return_value = {"success": True}

        client.force_login(superuser)
        url = reverse("issue_detail", kwargs={"pk": issue.pk})

        response = client.post(
            url,
            {
                "close_action": "addressed",
                "close_comment": "Fixed the issue",
                "submit_close": "Confirm Close",
            },
        )

        assert response.status_code == 302
        assert response.url == reverse("issue_detail", kwargs={"pk": issue.pk})

        # Check that issue status was updated
        issue.refresh_from_db()
        assert issue.status == IssueStatus.CLAIMABLE

        # Check that close_issue_with_labels was called with correct arguments
        mock_close_issue.assert_called_once()
        call_args = mock_close_issue.call_args[1]
        assert call_args["issue_number"] == issue.number
        assert call_args["comment"] == "Fixed the issue"
        assert "addressed" in call_args["labels_to_set"]
        assert "work in progress" not in call_args["labels_to_set"]
        mock_process.assert_called_once_with(
            mocker.ANY,
            Contribution.objects.addresses_and_amounts_from_contributions,
        )

    def test_issuedetailview_close_as_wontfix_success(
        self, client, superuser, issue, mocker
    ):
        provider = settings.ISSUE_TRACKER_PROVIDER.lower()
        name = provider.capitalize()
        mocker.patch(f"issues.{provider}.{name}Provider._get_client")
        mocker.patch(f"issues.{provider}.{name}Provider._get_repository")
        mock_get_issue = mocker.patch(
            f"issues.{provider}.BaseIssueProvider.issue_by_number"
        )
        mock_close_issue = mocker.patch(
            f"issues.{provider}.BaseIssueProvider.close_issue_with_labels"
        )

        mock_tracker_data = {
            "success": True,
            "issue": {
                "number": 123,
                "title": "Test Issue",
                "body": "Test body",
                "state": "open",
                "labels": ["bug", "work in progress"],
                "assignees": [],
                "html_url": "https://github.com/owner/repo/issues/123",
                "created_at": "2023-01-01T10:00:00",
                "updated_at": "2023-01-15T15:30:00",
            },
        }
        mock_get_issue.return_value = mock_tracker_data
        mock_close_issue.return_value = {"success": True}

        client.force_login(superuser)
        url = reverse("issue_detail", kwargs={"pk": issue.pk})

        response = client.post(
            url,
            {
                "close_action": "wontfix",
                "close_comment": "Will not fix",
                "submit_close": "Confirm Close",
            },
        )

        assert response.status_code == 302
        assert response.url == reverse("issue_detail", kwargs={"pk": issue.pk})

        # Check that issue status was updated
        issue.refresh_from_db()
        assert issue.status == IssueStatus.WONTFIX

        # Check that close_issue_with_labels was called with correct arguments
        mock_close_issue.assert_called_once()
        call_args = mock_close_issue.call_args[1]
        assert call_args["issue_number"] == issue.number
        assert call_args["comment"] == "Will not fix"
        assert "wontfix" in call_args["labels_to_set"]
        assert "work in progress" not in call_args["labels_to_set"]

    def test_issuedetailview_close_as_wontfix_success_existing_label(
        self, client, superuser, issue, mocker
    ):
        provider = settings.ISSUE_TRACKER_PROVIDER.lower()
        name = provider.capitalize()
        mocker.patch(f"issues.{provider}.{name}Provider._get_client")
        mocker.patch(f"issues.{provider}.{name}Provider._get_repository")
        mock_get_issue = mocker.patch(
            f"issues.{provider}.BaseIssueProvider.issue_by_number"
        )
        mock_close_issue = mocker.patch(
            f"issues.{provider}.BaseIssueProvider.close_issue_with_labels"
        )

        mock_tracker_data = {
            "success": True,
            "issue": {
                "number": 123,
                "title": "Test Issue",
                "body": "Test body",
                "state": "open",
                "labels": ["bug", "work in progress", "wontfix"],
                "assignees": [],
                "html_url": "https://github.com/owner/repo/issues/123",
                "created_at": "2023-01-01T10:00:00",
                "updated_at": "2023-01-15T15:30:00",
            },
        }
        mock_get_issue.return_value = mock_tracker_data
        mock_close_issue.return_value = {"success": True}

        client.force_login(superuser)
        url = reverse("issue_detail", kwargs={"pk": issue.pk})

        response = client.post(
            url,
            {
                "close_action": "wontfix",
                "close_comment": "Will not fix",
                "submit_close": "Confirm Close",
            },
        )

        assert response.status_code == 302
        assert response.url == reverse("issue_detail", kwargs={"pk": issue.pk})

        # Check that issue status was updated
        issue.refresh_from_db()
        assert issue.status == IssueStatus.WONTFIX

        # Check that close_issue_with_labels was called with correct arguments
        mock_close_issue.assert_called_once()
        call_args = mock_close_issue.call_args[1]
        assert call_args["issue_number"] == issue.number
        assert call_args["comment"] == "Will not fix"
        assert "wontfix" in call_args["labels_to_set"]
        assert "work in progress" not in call_args["labels_to_set"]

    def test_issuedetailview_close_issue_tracker_failure(
        self, client, superuser, issue, mocker
    ):
        provider = settings.ISSUE_TRACKER_PROVIDER.lower()
        name = provider.capitalize()
        mocker.patch(f"issues.{provider}.{name}Provider._get_client")
        mocker.patch(f"issues.{provider}.{name}Provider._get_repository")
        mock_get_issue = mocker.patch(
            f"issues.{provider}.BaseIssueProvider.issue_by_number"
        )
        mock_close_issue = mocker.patch(
            f"issues.{provider}.BaseIssueProvider.close_issue_with_labels"
        )

        mock_tracker_data = {
            "success": True,
            "issue": {
                "number": 123,
                "title": "Test Issue",
                "body": "Test body",
                "state": "open",
                "labels": ["bug"],
                "assignees": [],
                "html_url": "https://github.com/owner/repo/issues/123",
                "created_at": "2023-01-01T10:00:00",
                "updated_at": "2023-01-15T15:30:00",
            },
        }
        mock_get_issue.return_value = mock_tracker_data
        mock_close_issue.return_value = {"success": False, "error": "GitHub API error"}

        client.force_login(superuser)
        url = reverse("issue_detail", kwargs={"pk": issue.pk})

        response = client.post(
            url,
            {
                "close_action": "addressed",
                "close_comment": "",
                "submit_close": "Confirm Close",
            },
        )

        assert response.status_code == 302

        # Check that issue status was reverted to original
        issue.refresh_from_db()
        assert issue.status == IssueStatus.CREATED  # Original status

    def test_issuedetailview_close_already_closed_issue(
        self, client, superuser, issue, mocker
    ):
        provider = settings.ISSUE_TRACKER_PROVIDER.lower()
        name = provider.capitalize()
        mocker.patch(f"issues.{provider}.{name}Provider._get_client")
        mocker.patch(f"issues.{provider}.{name}Provider._get_repository")
        mock_get_issue = mocker.patch(
            f"issues.{provider}.BaseIssueProvider.issue_by_number"
        )
        mock_tracker_data = {
            "success": True,
            "issue": {
                "number": 123,
                "title": "Test Issue",
                "body": "Test body",
                "state": "closed",  # Already closed
                "labels": ["bug"],
                "assignees": [],
                "html_url": "https://github.com/owner/repo/issues/123",
                "created_at": "2023-01-01T10:00:00",
                "updated_at": "2023-01-15T15:30:00",
            },
        }
        mock_get_issue.return_value = mock_tracker_data

        client.force_login(superuser)
        url = reverse("issue_detail", kwargs={"pk": issue.pk})

        response = client.post(
            url,
            {
                "close_action": "addressed",
                "close_comment": "",
                "submit_close": "Confirm Close",
            },
        )

        assert response.status_code == 302

        # Check messages for error
        messages = list(get_messages(response.wsgi_request))
        assert any("already closed" in str(message) for message in messages)

    def test_issuedetailview_close_issue_invalid_action(self, client, superuser, issue):
        """Test closing with invalid action."""
        client.force_login(superuser)
        url = reverse("issue_detail", kwargs={"pk": issue.pk})

        response = client.post(
            url,
            {
                "close_action": "invalid_action",
                "close_comment": "",
                "submit_close": "Confirm Close",
            },
        )

        assert response.status_code == 302

        # Check messages for error
        messages = list(get_messages(response.wsgi_request))
        assert any("Invalid close action" in str(message) for message in messages)

    def test_issuedetailview_labels_form_not_shown_for_closed_issue(
        self, client, superuser, issue, mocker
    ):
        provider = settings.ISSUE_TRACKER_PROVIDER.lower()
        name = provider.capitalize()
        mocker.patch(f"issues.{provider}.{name}Provider._get_client")
        mocker.patch(f"issues.{provider}.{name}Provider._get_repository")
        mock_get_issue = mocker.patch(
            f"issues.{provider}.BaseIssueProvider.issue_by_number"
        )
        mock_tracker_data = {
            "success": True,
            "issue": {
                "number": 123,
                "title": "Test Issue",
                "body": "Test body",
                "state": "closed",
                "labels": ["bug"],
                "assignees": [],
                "html_url": "https://github.com/owner/repo/issues/123",
                "created_at": "2023-01-01T10:00:00",
                "updated_at": "2023-01-15T15:30:00",
            },
        }
        mock_get_issue.return_value = mock_tracker_data

        client.force_login(superuser)
        url = reverse("issue_detail", kwargs={"pk": issue.pk})
        response = client.get(url)

        assert response.status_code == 200
        assert "labels_form" not in response.context

    def test_issuedetailview_labels_form_shown_for_open_issue(
        self, client, superuser, issue, mocker
    ):
        provider = settings.ISSUE_TRACKER_PROVIDER.lower()
        name = provider.capitalize()
        mocker.patch(f"issues.{provider}.{name}Provider._get_client")
        mocker.patch(f"issues.{provider}.{name}Provider._get_repository")
        mock_get_issue = mocker.patch(
            f"issues.{provider}.BaseIssueProvider.issue_by_number"
        )
        mock_tracker_data = {
            "success": True,
            "issue": {
                "number": 123,
                "title": "Test Issue",
                "body": "Test body",
                "state": "open",
                "labels": ["bug"],
                "assignees": [],
                "html_url": "https://github.com/owner/repo/issues/123",
                "created_at": "2023-01-01T10:00:00",
                "updated_at": "2023-01-15T15:30:00",
            },
        }
        mock_get_issue.return_value = mock_tracker_data

        client.force_login(superuser)
        url = reverse("issue_detail", kwargs={"pk": issue.pk})
        response = client.get(url)

        assert response.status_code == 200
        assert "labels_form" in response.context
        assert isinstance(response.context["labels_form"], IssueLabelsForm)


class TestIssueModalView:
    """Test case for IssueDetailView."""

    def test_issuemodalview_is_subclass_of_detailview(self):
        assert issubclass(IssueModalView, DetailView)

    def test_issuemodalview_model(self):
        view = IssueModalView()
        assert view.model == Issue


@pytest.mark.django_db
class TestDbCreateIssueView:
    """Testing class for :class:`core.views.CreateIssueView` with database."""

    def test_createissueview_get_stores_contribution_id(
        self, rf, superuser, contribution
    ):
        request = rf.get(f"/create-issue/{contribution.id}/")
        request.user = superuser
        view = CreateIssueView()
        view.setup(request, contribution_id=contribution.id)

        response = view.get(request, contribution_id=contribution.id)

        assert view.contribution_id == contribution.id
        assert response.status_code == 200

    def test_createissueview_post_stores_contribution_id(
        self, rf, superuser, contribution
    ):
        request = rf.post(f"/create-issue/{contribution.id}/")
        request.user = superuser
        view = CreateIssueView()
        view.setup(request, contribution_id=contribution.id)

        response = view.post(request, contribution_id=contribution.id)

        assert view.contribution_id == contribution.id
        assert response.status_code == 200

    def test_createissueview_get_success_url(self, rf, superuser, contribution):
        request = rf.get(f"/create-issue/{contribution.id}/")
        request.user = superuser
        view = CreateIssueView()
        view.setup(request, contribution_id=contribution.id)
        view.contribution_id = contribution.id

        success_url = view.get_success_url()

        expected_url = reverse("contribution_detail", args=[contribution.id])
        assert success_url == expected_url

    def test_createissueview_get_initial_with_contribution_id(
        self, rf, superuser, contribution, mocker
    ):
        request = rf.get(f"/create-issue/{contribution.id}/")
        request.user = superuser
        view = CreateIssueView()
        view.setup(request, contribution_id=contribution.id)
        view.contribution_id = contribution.id

        mock_issue_data = mocker.patch("core.views.issue_data_for_contribution")
        mock_issue_data.return_value = {
            "priority": "high priority",
            "issue_body": "Test body",
            "issue_title": "Test title",
            "labels": ["bug"],
        }

        initial = view.get_initial()

        assert "priority" in initial
        assert "issue_body" in initial
        assert "issue_title" in initial
        assert "labels" in initial
        mock_issue_data.assert_called_once_with(contribution, superuser.profile)

    def test_createissueview_get_initial_without_contribution_id(self, rf, superuser):
        request = rf.get("/create-issue/")
        request.user = superuser
        view = CreateIssueView()
        view.setup(request)
        view.contribution_id = None

        initial = view.get_initial()

        expected_data = {
            "priority": "medium priority",
            "issue_body": "Please provide issue description here.",
            "issue_title": "Issue title",
        }
        assert initial == expected_data

    def test_createissueview_get_context_data(
        self, rf, superuser, contribution, mocker
    ):
        request = rf.get(f"/create-issue/{contribution.id}/")
        request.user = superuser
        view = CreateIssueView()
        view.setup(request, contribution_id=contribution.id)
        view.contribution_id = contribution.id
        view.object = None

        # Mock the info method
        mock_info = mocker.patch.object(Contribution, "info")
        mock_info.return_value = "Test Contribution Info"

        context = view.get_context_data()

        assert context["contribution_id"] == contribution.id
        assert context["contribution_info"] == "Test Contribution Info"
        assert "Create issue for Test Contribution Info" in context["page_title"]

    def test_createissueview_form_valid_success(
        self, rf, superuser, contribution, mocker
    ):
        request = rf.post(f"/create-issue/{contribution.id}/")
        request.user = superuser
        view = CreateIssueView()
        view.setup(request, contribution_id=contribution.id)
        view.contribution_id = contribution.id

        # Mock external dependencies
        provider = settings.ISSUE_TRACKER_PROVIDER.lower()
        name = provider.capitalize()
        mocker.patch(f"issues.{provider}.{name}Provider._get_client")
        mocker.patch(f"issues.{provider}.{name}Provider._get_repository")
        mock_create_issue = mocker.patch(
            f"issues.{provider}.BaseIssueProvider.create_issue"
        )
        mock_create_issue.return_value = {"success": True, "issue_number": 123}

        mock_confirm_contribution = mocker.patch(
            "core.views.Issue.objects.confirm_contribution_with_issue"
        )
        mock_add_reaction = mocker.patch(
            "updaters.discord.DiscordUpdater.add_reaction_to_message"
        )
        mocked_log_action = mocker.patch("core.models.Profile.log_action")

        # Create mock form with valid data
        mock_form = mocker.MagicMock()
        mock_form.cleaned_data = {
            "labels": ["bug", "feature"],
            "priority": "high priority",
            "issue_body": "Test issue body",
            "issue_title": "Test issue title",
        }

        response = view.form_valid(mock_form)

        mock_create_issue.assert_called_once_with(
            "Test issue title",
            "Test issue body",
            labels=["bug", "feature", "high priority"],
        )

        # Verify contribution was confirmed with issue
        mock_confirm_contribution.assert_called_once_with(123, contribution)

        # Verify Discord reaction was added
        mock_add_reaction.assert_called_once_with(contribution.url, mocker.ANY)

        # Verify response is successful
        assert response.status_code == 302

        mocked_log_action.assert_called_once_with(
            "contribution_created", contribution.info()
        )

    def test_createissueview_form_valid_failure(
        self, rf, superuser, contribution, mocker
    ):
        request = rf.post(f"/create-issue/{contribution.id}/")
        request.user = superuser
        view = CreateIssueView()
        view.setup(request, contribution_id=contribution.id)
        view.contribution_id = contribution.id

        provider = settings.ISSUE_TRACKER_PROVIDER.lower()
        name = provider.capitalize()
        mocker.patch(f"issues.{provider}.{name}Provider._get_client")
        mocker.patch(f"issues.{provider}.{name}Provider._get_repository")
        mock_create_issue = mocker.patch(
            f"issues.{provider}.BaseIssueProvider.create_issue"
        )
        mock_create_issue.return_value = {
            "success": False,
            "error": "GitHub API error",
        }

        # Create mock form with valid data
        mock_form = mocker.MagicMock()
        mock_form.cleaned_data = {
            "labels": ["bug"],
            "priority": "medium priority",
            "issue_body": "Test issue body",
            "issue_title": "Test issue title",
        }

        response = view.form_valid(mock_form)

        # Verify form error was added
        mock_form.add_error.assert_called_once_with(None, mocker.ANY)

        # Verify response indicates form is invalid
        assert response.status_code == 200

    def test_createissueview_requires_superuser(self, rf, regular_user, contribution):
        request = rf.get(f"/create-issue/{contribution.id}/")
        request.user = regular_user

        response = CreateIssueView.as_view()(request, contribution_id=contribution.id)

        # Should redirect to login or show permission denied
        assert response.status_code in [302, 403]

    def test_createissueview_superuser_access_granted(
        self, rf, superuser, contribution
    ):
        request = rf.get(f"/create-issue/{contribution.id}/")
        request.user = superuser

        response = CreateIssueView.as_view()(request, contribution_id=contribution.id)

        # Should return 200 for superuser
        assert response.status_code == 200
