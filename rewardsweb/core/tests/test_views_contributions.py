"""Testing module for :py:mod:`core.views` views related to contributions."""

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.contrib.messages.storage.fallback import FallbackStorage
from django.urls import reverse
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from core.forms import ContributionEditForm, ContributionInvalidateForm
from core.models import (
    Contribution,
    Contributor,
    Cycle,
    Handle,
    Issue,
    IssueStatus,
    Reward,
    RewardType,
    SocialPlatform,
)
from core.views import (
    ContributionCreateView,
    ContributionDetailView,
    ContributionEditView,
    ContributionInvalidateView,
    ContributorDetailView,
    ContributorListView,
    CycleDetailView,
    CycleListView,
)
from utils.constants.core import DISCORD_EMOJIS
from utils.constants.ui import MISSING_API_TOKEN_TEXT

user_model = get_user_model()


class TestContributionDetailView:
    """Testing class for :class:`core.views.ContributionDetailView`."""

    def test_contributiondetailview_is_subclass_of_detailview(self):
        assert issubclass(ContributionDetailView, DetailView)

    def test_contributiondetailview_model(self):
        view = ContributionDetailView()
        assert view.model == Contribution


@pytest.mark.django_db
class TestDbContributionDetailView:
    """Testing class for :class:`core.views.ContributionDetailView` with database."""

    def test_contributiondetailview_get_object(self, rf, contribution):
        request = rf.get(f"/contributions/{contribution.id}/")

        view = ContributionDetailView()
        view.setup(request, pk=contribution.id)

        obj = view.get_object()

        assert obj == contribution
        assert obj.id == contribution.id


class TestContributionEditView:
    """Testing class for :class:`core.views.ContributionEditView`."""

    def test_contributioneditview_is_subclass_of_updateview(self):
        assert issubclass(ContributionEditView, UpdateView)

    def test_contributioneditview_model(self):
        view = ContributionEditView()
        assert view.model == Contribution

    def test_contributioneditview_form_class(self):
        view = ContributionEditView()
        assert view.form_class == ContributionEditForm

    def test_contributioneditview_template_name(self):
        view = ContributionEditView()
        assert view.template_name == "core/contribution_edit.html"


@pytest.mark.django_db
class TestDbContributionEditView:
    """Testing class for :class:`core.views.ContributionEditView` with database."""

    def _setup_messages(self, request):
        """Helper method to setup messages framework for request."""
        setattr(request, "session", "session")
        messages = FallbackStorage(request)
        setattr(request, "_messages", messages)
        return request

    def test_contributioneditview_get_success_url(
        self, rf, superuser, contribution, mocker
    ):
        request = rf.get(f"/contributions/{contribution.id}/edit/")
        request.user = superuser
        request = self._setup_messages(request)

        mocked_log_action = mocker.patch("core.models.Profile.log_action")

        view = ContributionEditView()
        view.setup(request, pk=contribution.id)
        view.object = contribution
        view.request = request

        success_url = view.get_success_url()

        expected_url = reverse("contribution_detail", kwargs={"pk": contribution.pk})
        assert success_url == expected_url
        mocked_log_action.assert_called_once()

    def test_contributioneditview_requires_superuser(
        self, rf, regular_user, contribution
    ):
        request = rf.get(f"/contribution/{contribution.id}/edit/")
        request.user = regular_user

        response = ContributionEditView.as_view()(request, pk=contribution.id)

        # Should redirect to login (302) for non-superusers
        assert response.status_code == 302

    def test_contributioneditview_superuser_access_granted(
        self, rf, superuser, contribution
    ):
        request = rf.get(f"/contribution/{contribution.id}/edit/")
        request.user = superuser

        response = ContributionEditView.as_view()(request, pk=contribution.id)

        # Should return 200 for superuser
        assert response.status_code == 200

    def test_contributioneditview_form_valid_with_existing_issue(
        self, rf, superuser, contribution, issue
    ):
        request = rf.post(
            f"/contribution/{contribution.id}/edit/",
            {
                "reward": contribution.reward.id,
                "percentage": "50.00",
                "comment": "Test comment",
                "issue_number": issue.number,
            },
        )
        request.user = superuser
        request = self._setup_messages(request)

        response = ContributionEditView.as_view()(request, pk=contribution.id)

        # Refresh contribution from database
        contribution.refresh_from_db()

        # Should redirect to success URL
        assert response.status_code == 302
        assert contribution.issue == issue

    def test_contributioneditview_form_valid_with_new_issue(
        self, rf, superuser, contribution, mocker
    ):
        provider = settings.ISSUE_TRACKER_PROVIDER.lower()
        name = provider.capitalize()
        mocker.patch(f"issues.{provider}.{name}Provider._get_client")
        mocker.patch(f"issues.{provider}.{name}Provider._get_repository")
        mock_issue_by_number = mocker.patch(
            f"issues.{provider}.BaseIssueProvider.issue_by_number",
            return_value={"success": True, "data": {"number": 123}},
        )
        mocked_log_action = mocker.patch("core.models.Profile.log_action")

        request = rf.post(
            f"/contribution/{contribution.id}/edit/",
            {
                "reward": contribution.reward.id,
                "percentage": "50.00",
                "comment": "Test comment",
                "issue_number": "123",
            },
        )
        request.user = superuser
        request = self._setup_messages(request)

        response = ContributionEditView.as_view()(request, pk=contribution.id)

        # Refresh contribution from database
        contribution.refresh_from_db()

        # Should redirect to success URL
        assert response.status_code == 302
        assert contribution.issue is not None
        assert contribution.issue.number == 123
        mock_issue_by_number.assert_called_once_with(123)

        calls = [
            mocker.call("issue_created", str(contribution.issue)),
            mocker.call("contribution_edited", contribution.info()),
        ]
        mocked_log_action.assert_has_calls(calls)

    def test_contributioneditview_form_invalid_with_nonexistent_tracker_issue(
        self, rf, superuser, contribution, mocker
    ):
        provider = settings.ISSUE_TRACKER_PROVIDER.lower()
        name = provider.capitalize()
        mocker.patch(f"issues.{provider}.{name}Provider._get_client")
        mocker.patch(f"issues.{provider}.{name}Provider._get_repository")
        mock_issue_by_number = mocker.patch(
            f"issues.{provider}.BaseIssueProvider.issue_by_number",
            return_value={
                "success": False,
                "error": "That tracker issue doesn't exist!",
            },
        )
        request = rf.post(
            f"/contribution/{contribution.id}/edit/",
            {
                "reward": contribution.reward.id,
                "percentage": "50.00",
                "comment": "Test comment",
                "issue_number": "999",
            },
        )
        request.user = superuser
        request = self._setup_messages(request)

        response = ContributionEditView.as_view()(request, pk=contribution.id)

        # Should return form with error (200 status)
        assert response.status_code == 200

        # Check that the form in the context has the expected error
        assert "form" in response.context_data
        form = response.context_data["form"]
        assert "issue_number" in form.errors
        assert "That tracker issue doesn't exist!" in form.errors["issue_number"]

        mock_issue_by_number.assert_called_once_with(999)

    def test_contributioneditview_form_invalid_with_tracker_api_error(
        self, rf, superuser, contribution, mocker
    ):
        provider = settings.ISSUE_TRACKER_PROVIDER.lower()
        name = provider.capitalize()
        mocker.patch(f"issues.{provider}.{name}Provider._get_client")
        mocker.patch(f"issues.{provider}.{name}Provider._get_repository")
        mock_issue_by_number = mocker.patch(
            f"issues.{provider}.BaseIssueProvider.issue_by_number",
            return_value={"success": False, "error": "API rate limit exceeded"},
        )

        request = rf.post(
            f"/contribution/{contribution.id}/edit/",
            {
                "reward": contribution.reward.id,
                "percentage": "50.00",
                "comment": "Test comment",
                "issue_number": "999",
            },
        )
        request.user = superuser
        request = self._setup_messages(request)

        response = ContributionEditView.as_view()(request, pk=contribution.id)

        # Should return form with error (200 status)
        assert response.status_code == 200

        # Check that the form in the context has the expected error
        assert "form" in response.context_data
        form = response.context_data["form"]
        assert "issue_number" in form.errors
        assert "API rate limit exceeded" in form.errors["issue_number"]

        mock_issue_by_number.assert_called_once_with(999)

    def test_contributioneditview_form_invalid_with_tracker_api_missing_token_error(
        self, rf, superuser, contribution, mocker
    ):
        provider = settings.ISSUE_TRACKER_PROVIDER.lower()
        name = provider.capitalize()
        mocker.patch(f"issues.{provider}.{name}Provider._get_client")
        mocker.patch(f"issues.{provider}.{name}Provider._get_repository")
        mock_issue_by_number = mocker.patch(
            f"issues.{provider}.BaseIssueProvider.issue_by_number",
            return_value={"success": False, "error": MISSING_API_TOKEN_TEXT},
        )

        request = rf.post(
            f"/contribution/{contribution.id}/edit/",
            {
                "reward": contribution.reward.id,
                "percentage": "50.00",
                "comment": "Test comment",
                "issue_number": "999",
            },
        )
        request.user = superuser
        request = self._setup_messages(request)

        response = ContributionEditView.as_view()(request, pk=contribution.id)

        # Should return form with error (200 status)
        assert response.status_code == 200

        # Check that the form in the context has the expected error
        assert "form" in response.context_data
        form = response.context_data["form"]
        assert "issue_number" in form.errors
        assert MISSING_API_TOKEN_TEXT in form.errors["issue_number"]

        mock_issue_by_number.assert_called_once_with(999)

    def test_contributioneditview_form_valid_without_issue_number(
        self, rf, superuser, contribution_with_issue
    ):
        """Test that empty issue_number removes existing issue association."""
        request = rf.post(
            f"/contribution/{contribution_with_issue.id}/edit/",
            {
                "reward": contribution_with_issue.reward.id,
                "percentage": "75.00",
                "comment": "Updated comment",
                "issue_number": "",  # Empty to remove issue
            },
        )
        request.user = superuser
        request = self._setup_messages(request)

        response = ContributionEditView.as_view()(
            request, pk=contribution_with_issue.id
        )

        # Refresh contribution from database
        contribution_with_issue.refresh_from_db()

        # Should redirect to success URL and remove issue
        assert response.status_code == 302
        assert contribution_with_issue.issue is None

    def test_contributioneditview_form_valid_with_none_issue_number(
        self, rf, superuser, contribution_with_issue
    ):
        """Test that missing issue_number removes existing issue association."""
        request = rf.post(
            f"/contribution/{contribution_with_issue.id}/edit/",
            {
                "reward": contribution_with_issue.reward.id,
                "percentage": "100.00",
                "comment": "Remove issue test",
                # issue_number not provided (defaults to None)
            },
        )
        request.user = superuser
        request = self._setup_messages(request)

        response = ContributionEditView.as_view()(
            request, pk=contribution_with_issue.id
        )

        # Refresh from database
        contribution_with_issue.refresh_from_db()

        # Should redirect and remove issue
        assert response.status_code == 302
        assert contribution_with_issue.issue is None

    def test_contributioneditview_form_valid_creates_new_issue_when_success_true(
        self, rf, superuser, contribution, mocker
    ):
        provider = settings.ISSUE_TRACKER_PROVIDER.lower()
        name = provider.capitalize()
        mocker.patch(f"issues.{provider}.{name}Provider._get_client")
        mocker.patch(f"issues.{provider}.{name}Provider._get_repository")
        mock_issue_by_number = mocker.patch(
            f"issues.{provider}.BaseIssueProvider.issue_by_number",
            return_value={"success": True, "data": {"number": 456}},
        )

        request = rf.post(
            f"/contribution/{contribution.id}/edit/",
            {
                "reward": contribution.reward.id,
                "percentage": "80.00",
                "comment": "Test with new issue",
                "issue_number": "456",
            },
        )
        request.user = superuser
        request = self._setup_messages(request)

        response = ContributionEditView.as_view()(request, pk=contribution.id)

        # Refresh contribution from database
        contribution.refresh_from_db()

        # Should redirect to success URL
        assert response.status_code == 302

        # Should create and attach a new issue
        assert contribution.issue is not None
        assert contribution.issue.number == 456
        assert contribution.issue.status == IssueStatus.CREATED

        # Verify the tracker API was called
        mock_issue_by_number.assert_called_once_with(456)

    def test_contributioneditview_form_valid_with_existing_issue_different_number(
        self, rf, superuser, contribution_with_issue
    ):
        """Test updating with a different existing issue number."""
        # Create a different issue
        different_issue = Issue.objects.create(number=789, status=IssueStatus.CREATED)

        request = rf.post(
            f"/contribution/{contribution_with_issue.id}/edit/",
            {
                "reward": contribution_with_issue.reward.id,
                "percentage": "90.00",
                "comment": "Updated with different issue",
                "issue_number": "789",  # Different existing issue
            },
        )
        request.user = superuser
        request = self._setup_messages(request)

        response = ContributionEditView.as_view()(
            request, pk=contribution_with_issue.id
        )

        # Refresh contribution from database
        contribution_with_issue.refresh_from_db()

        # Should redirect to success URL and update to different issue
        assert response.status_code == 302
        assert contribution_with_issue.issue == different_issue
        assert contribution_with_issue.issue.number == 789

    def test_contributioneditview_form_valid_with_new_issue_and_custom_status(
        self, rf, superuser, contribution, mocker
    ):
        """Test that new issue is created with custom status."""
        provider = settings.ISSUE_TRACKER_PROVIDER.lower()
        name = provider.capitalize()
        mocker.patch(f"issues.{provider}.{name}Provider._get_client")
        mocker.patch(f"issues.{provider}.{name}Provider._get_repository")
        mock_issue_by_number = mocker.patch(
            f"issues.{provider}.BaseIssueProvider.issue_by_number",
            return_value={"success": True, "data": {"number": 456}},
        )

        request = rf.post(
            f"/contribution/{contribution.id}/edit/",
            {
                "reward": contribution.reward.id,
                "percentage": "80.00",
                "comment": "Test with new issue and custom status",
                "issue_number": "456",
                "issue_status": IssueStatus.ADDRESSED,  # Custom status
            },
        )
        request.user = superuser
        request = self._setup_messages(request)

        response = ContributionEditView.as_view()(request, pk=contribution.id)

        # Refresh contribution from database
        contribution.refresh_from_db()

        # Should redirect to success URL
        assert response.status_code == 302

        # Should create and attach a new issue with custom status
        assert contribution.issue is not None
        assert contribution.issue.number == 456
        assert contribution.issue.status == IssueStatus.ADDRESSED  # Custom status

        # Verify the tracker API was called
        mock_issue_by_number.assert_called_once_with(456)

    def test_contributioneditview_form_valid_updates_existing_issue_status(
        self, rf, superuser, contribution_with_issue
    ):
        """Test updating existing issue status."""
        original_status = contribution_with_issue.issue.status
        new_status = IssueStatus.ADDRESSED

        request = rf.post(
            f"/contribution/{contribution_with_issue.id}/edit/",
            {
                "reward": contribution_with_issue.reward.id,
                "percentage": "90.00",
                "comment": "Update issue status",
                "issue_number": str(contribution_with_issue.issue.number),  # Same issue
                "issue_status": new_status,  # New status
            },
        )
        request.user = superuser
        request = self._setup_messages(request)

        response = ContributionEditView.as_view()(
            request, pk=contribution_with_issue.id
        )

        # Refresh contribution and issue from database
        contribution_with_issue.refresh_from_db()
        contribution_with_issue.issue.refresh_from_db()

        # Should redirect to success URL
        assert response.status_code == 302

        # Issue status should be updated
        assert contribution_with_issue.issue.status == new_status
        assert contribution_with_issue.issue.status != original_status

    def test_contributioneditview_form_valid_updates_existing_issue_status_logs_action(
        self, rf, superuser, contribution_with_issue, mocker
    ):
        """Test updating existing issue status logs the action."""
        new_status = IssueStatus.ADDRESSED
        mocked_log_action = mocker.patch("core.models.Profile.log_action")

        request = rf.post(
            f"/contribution/{contribution_with_issue.id}/edit/",
            {
                "reward": contribution_with_issue.reward.id,
                "percentage": "90.00",
                "comment": "Update issue status",
                "issue_number": str(contribution_with_issue.issue.number),
                "issue_status": new_status,
            },
        )
        request.user = superuser
        request = self._setup_messages(request)

        ContributionEditView.as_view()(request, pk=contribution_with_issue.id)

        contribution_with_issue.issue.refresh_from_db()
        calls = [
            mocker.call("issue_status_set", str(contribution_with_issue.issue)),
            mocker.call(
                "contribution_edited",
                contribution_with_issue.info() + " // Update issue status",
            ),
        ]
        mocked_log_action.assert_has_calls(calls)


class TestContributionInvalidateView:
    """Testing class for :class:`core.views.ContributionInvalidateView`."""

    def test_contributioninvalidateview_is_subclass_of_updateview(self):
        assert issubclass(ContributionInvalidateView, UpdateView)

    def test_contributioninvalidateview_model(self):
        view = ContributionInvalidateView()
        assert view.model == Contribution

    def test_contributioninvalidateview_form_class(self):
        view = ContributionInvalidateView()
        assert view.form_class == ContributionInvalidateForm

    def test_contributioninvalidateview_template_name(self):
        view = ContributionInvalidateView()
        assert view.template_name == "core/contribution_invalidate.html"


@pytest.mark.django_db
class TestContributionInvalidateViewDb:
    """Test suite for ContributionInvalidateView."""

    def test_contributioninvalidateview_superuser_required(
        self, client, regular_user, invalidate_url
    ):
        """Test that only superusers can access the view."""
        client.force_login(regular_user)
        response = client.get(invalidate_url)
        # The view uses @user_passes_test which redirects to login for non-superusers
        assert response.status_code == 302
        assert "/accounts/login/" in response.url

    def test_contributioninvalidateview_superuser_can_access(
        self, client, superuser, invalidate_url, mock_message_from_url
    ):
        """Test that superuser can access the view."""
        client.force_login(superuser)
        response = client.get(invalidate_url)
        assert response.status_code == 200

    def test_contributioninvalidateview_get_context_data(
        self, client, superuser, invalidate_url, mock_message_from_url
    ):
        """Test that context contains required data."""
        client.force_login(superuser)
        response = client.get(invalidate_url)

        assert response.status_code == 200
        assert "type" in response.context
        assert "original_comment" in response.context
        assert response.context["type"] == "duplicate"

    @pytest.mark.parametrize(
        "reply,expected_comment",
        [
            ("This is a test reply", "This is a test reply"),
            ("", ""),
        ],
    )
    def test_contributioninvalidateview_form_valid_all_operations_successful(
        self,
        client,
        superuser,
        contribution,
        invalidate_url,
        reply,
        expected_comment,
        mocker,
    ):
        """Test successful form submission with and without reply."""
        client.force_login(superuser)

        # Mock the UpdateProvider
        mock_updater_instance = mocker.MagicMock()
        mock_updater_instance.add_reply_to_message.return_value = True
        mock_updater_instance.add_reaction_to_message.return_value = True
        mock_update_provider = mocker.patch("core.views.UpdateProvider")
        mock_update_provider.return_value = mock_updater_instance
        mocked_log_action = mocker.patch("core.models.Profile.log_action")

        response = client.post(invalidate_url, {"reply": reply})

        # Check that operations were called appropriately
        mock_update_provider.assert_called_once_with(contribution.platform.name)
        if reply:
            mock_updater_instance.add_reply_to_message.assert_called_once_with(
                contribution.url, expected_comment
            )
        else:
            mock_updater_instance.add_reply_to_message.assert_not_called()

        mock_updater_instance.add_reaction_to_message.assert_called_once_with(
            contribution.url, "duplicate"
        )

        # Check that contribution was confirmed
        contribution.refresh_from_db()
        assert contribution.confirmed is True

        # Check success message
        messages = list(get_messages(response.wsgi_request))
        assert len(messages) == 1
        assert "successfully" in messages[0].message

        # Check redirect
        expected_url = reverse("contribution_detail", kwargs={"pk": contribution.pk})
        assert response.url == expected_url

        mocked_log_action.assert_called_once_with(
            "contribution_invalidated", contribution.info()
        )

    def test_contributioninvalidateview_form_valid_reply_fails(
        self, client, superuser, contribution, invalidate_url, mocker
    ):
        """Test form submission when reply operation fails."""
        client.force_login(superuser)

        # Mock the UpdateProvider
        mock_updater_instance = mocker.MagicMock()
        mock_updater_instance.add_reply_to_message.return_value = False
        mock_updater_instance.add_reaction_to_message.return_value = True
        mock_updater_instance.message_from_url.return_value = {
            "success": True,
            "author": "test_user",
            "timestamp": "2024-01-01T12:00:00.000000+00:00",
            "contribution": "Test message",
        }
        mock_update_provider = mocker.patch("core.views.UpdateProvider")
        mock_update_provider.return_value = mock_updater_instance

        response = client.post(invalidate_url, {"reply": "This is a test reply"})

        # Check that contribution was NOT confirmed
        contribution.refresh_from_db()
        assert contribution.confirmed is False

        # Check that form has error and was re-rendered
        assert response.status_code == 200
        content = response.content.decode()
        assert "Failed to add reply" in content or "All operations failed" in content

    def test_contributioninvalidateview_form_valid_reaction_fails(
        self, client, superuser, contribution, invalidate_url, mocker
    ):
        """Test form submission when reaction operation fails."""
        client.force_login(superuser)

        # Mock the UpdateProvider
        mock_updater_instance = mocker.MagicMock()
        mock_updater_instance.add_reaction_to_message.return_value = False
        mock_updater_instance.message_from_url.return_value = {
            "success": True,
            "author": "test_user",
            "timestamp": "2024-01-01T12:00:00.000000+00:00",
            "contribution": "Test message",
        }
        mock_update_provider = mocker.patch("core.views.UpdateProvider")
        mock_update_provider.return_value = mock_updater_instance

        response = client.post(invalidate_url, {"reply": ""})

        # Check that contribution was NOT confirmed
        contribution.refresh_from_db()
        assert contribution.confirmed is False

        # Check that form has error
        assert response.status_code == 200
        content = response.content.decode()
        # Check for either specific error or general error message
        assert any(
            msg in content
            for msg in ["Failed to add reaction", "All operations failed"]
        )

    def test_contributioninvalidateview_form_valid_both_operations_fail(
        self, client, superuser, contribution, invalidate_url, mocker
    ):
        """Test form submission when both operations fail."""
        client.force_login(superuser)

        # Mock the UpdateProvider
        mock_updater_instance = mocker.MagicMock()
        mock_updater_instance.add_reply_to_message.return_value = False
        mock_updater_instance.add_reaction_to_message.return_value = False
        mock_updater_instance.message_from_url.return_value = {
            "success": True,
            "author": "test_user",
            "timestamp": "2024-01-01T12:00:00.000000+00:00",
            "contribution": "Test message",
        }
        mock_update_provider = mocker.patch("core.views.UpdateProvider")
        mock_update_provider.return_value = mock_updater_instance

        response = client.post(invalidate_url, {"reply": "This is a test reply"})

        # Check that contribution was NOT confirmed
        contribution.refresh_from_db()
        assert contribution.confirmed is False

        # Check that form has error
        assert response.status_code == 200
        assert "All operations failed" in response.content.decode()

    def test_contributioninvalidateview_form_valid_reply_exception(
        self, client, superuser, contribution, invalidate_url, mocker
    ):
        """Test form submission when reply operation raises exception."""
        client.force_login(superuser)

        # Mock the UpdateProvider
        mock_updater_instance = mocker.MagicMock()
        mock_updater_instance.add_reply_to_message.side_effect = Exception(
            "Reply failed"
        )
        mock_updater_instance.add_reaction_to_message.return_value = True
        mock_updater_instance.message_from_url.return_value = {
            "success": True,
            "author": "test_user",
            "timestamp": "2024-01-01T12:00:00.000000+00:00",
            "contribution": "Test message",
        }
        mock_update_provider = mocker.patch("core.views.UpdateProvider")
        mock_update_provider.return_value = mock_updater_instance

        response = client.post(invalidate_url, {"reply": "This is a test reply"})

        # Check that contribution was NOT confirmed
        contribution.refresh_from_db()
        assert contribution.confirmed is False

        # Check that form has error
        assert response.status_code == 200
        content = response.content.decode()
        assert any(
            msg in content for msg in ["Failed to add reply", "All operations failed"]
        )

    def test_contributioninvalidateview_form_valid_reaction_exception(
        self, client, superuser, contribution, invalidate_url, mocker
    ):
        """Test form submission when reaction operation raises exception."""
        client.force_login(superuser)

        # Mock the UpdateProvider
        mock_updater_instance = mocker.MagicMock()
        mock_updater_instance.add_reaction_to_message.side_effect = Exception(
            "Reaction failed"
        )
        mock_updater_instance.message_from_url.return_value = {
            "success": True,
            "author": "test_user",
            "timestamp": "2024-01-01T12:00:00.000000+00:00",
            "contribution": "Test message",
        }
        mock_update_provider = mocker.patch("core.views.UpdateProvider")
        mock_update_provider.return_value = mock_updater_instance

        response = client.post(invalidate_url, {"reply": ""})

        # Check that contribution was NOT confirmed
        contribution.refresh_from_db()
        assert contribution.confirmed is False

        # Check that form has error
        assert response.status_code == 200
        content = response.content.decode()
        assert any(
            msg in content
            for msg in ["Failed to add reaction", "All operations failed"]
        )

    @pytest.mark.parametrize("reaction", ["duplicate", "wontfix"])
    def test_contributioninvalidateview_different_types(
        self, client, superuser, contribution, reaction, mocker
    ):
        """Test view works with different type parameters."""
        url = reverse(
            "contribution_invalidate",
            kwargs={"pk": contribution.pk, "reaction": reaction},
        )

        client.force_login(superuser)

        # Mock the UpdateProvider
        mock_updater_instance = mocker.MagicMock()
        mock_updater_instance.add_reaction_to_message.return_value = True
        mock_update_provider = mocker.patch("core.views.UpdateProvider")
        mock_update_provider.return_value = mock_updater_instance

        client.post(url, {"reply": ""})

        # Check that reaction was called with correct type
        mock_updater_instance.add_reaction_to_message.assert_called_once_with(
            contribution.url, reaction
        )

        # Check success
        contribution.refresh_from_db()
        assert contribution.confirmed is True

    def test_contributioninvalidateview_form_fields_present(
        self, client, superuser, invalidate_url, mock_message_from_url
    ):
        """Test that form contains expected fields."""
        client.force_login(superuser)
        response = client.get(invalidate_url)

        content = response.content.decode()
        assert 'name="reply"' in content
        assert "textarea" in content
        assert "Confirm as Duplicate" in content

    def test_contributioninvalidateview_original_comment_in_context_message_success(
        self, client, superuser, invalidate_url, mock_message_from_url_no_ms
    ):
        """Test that original comment is included when message_from_url returns success."""
        client.force_login(superuser)
        response = client.get(invalidate_url)

        assert "original_comment" in response.context
        assert "test_user" in response.context["original_comment"]
        assert "Test message content" in response.context["original_comment"]

    def test_contributioninvalidateview_original_comment_empty_when_message_fails(
        self, client, superuser, contribution, mocker
    ):
        """Test that original comment is empty when message_from_url fails."""
        url = reverse(
            "contribution_invalidate",
            kwargs={"pk": contribution.pk, "reaction": "duplicate"},
        )

        # Mock UpdateProvider to return failure
        mock_updater_instance = mocker.MagicMock()
        mock_updater_instance.message_from_url.return_value = {"success": False}
        mocker.patch("core.views.UpdateProvider", return_value=mock_updater_instance)

        client.force_login(superuser)
        response = client.get(url)

        # The view should still have original_comment in context, but empty
        assert "original_comment" in response.context
        assert response.context["original_comment"] == ""

    def test_contributioninvalidateview_success_message_content_with_comment(
        self, client, superuser, invalidate_url, mocker
    ):
        """Test success message includes reply information when comment is provided."""
        client.force_login(superuser)

        # Mock the UpdateProvider
        mock_updater_instance = mocker.MagicMock()
        mock_updater_instance.add_reply_to_message.return_value = True
        mock_updater_instance.add_reaction_to_message.return_value = True
        mocker.patch("core.views.UpdateProvider", return_value=mock_updater_instance)

        response = client.post(invalidate_url, {"reply": "Test reply"})

        messages = list(get_messages(response.wsgi_request))
        message_text = messages[0].message.lower()

        assert "reply" in message_text
        assert "reaction" in message_text
        assert "duplicate" in message_text

    def test_contributioninvalidateview_success_message_content_without_comment(
        self, client, superuser, invalidate_url, mocker
    ):
        """Test success message excludes reply information when no comment is provided."""
        client.force_login(superuser)

        # Mock the UpdateProvider
        mock_updater_instance = mocker.MagicMock()
        mock_updater_instance.add_reaction_to_message.return_value = True
        mocker.patch("core.views.UpdateProvider", return_value=mock_updater_instance)

        response = client.post(invalidate_url, {"reply": ""})

        messages = list(get_messages(response.wsgi_request))
        message_text = messages[0].message.lower()

        assert "reply" not in message_text
        assert "reaction" in message_text
        assert "duplicate" in message_text


class TestContributionCreateViewBasics:
    """Simple class-based view tests."""

    def test_contributioncreateview_is_subclass_of_createView(self):
        assert issubclass(ContributionCreateView, CreateView)

    def test_contributioncreateview_model_is_contribution(self):
        view = ContributionCreateView()
        assert view.model == Contribution

    def test_contributioncreateview_template_name(self):
        view = ContributionCreateView()
        assert view.template_name == "core/contribution_create.html"


@pytest.mark.django_db
class TestDbContributionCreateView:
    """Full DB tests for ContributionCreateView."""

    def _setup_messages(self, request):
        setattr(request, "session", "session")
        storage = FallbackStorage(request)
        setattr(request, "_messages", storage)
        return request

    def test_contributioncreateview_requires_superuser(self, rf, regular_user):
        request = rf.get("/contribution/add/")
        request.user = regular_user

        response = ContributionCreateView.as_view()(request)

        assert response.status_code == 302  # redirect to login

    def test_contributioncreateview_superuser_access(self, rf, superuser):
        request = rf.get("/contribution/add/")
        request.user = superuser

        response = ContributionCreateView.as_view()(request)

        assert response.status_code == 200

    def test_contributioncreateview_form_valid_creates_contribution_without_issue(
        self, rf, superuser, contributor, social_platform, reward, cycle
    ):
        request = rf.post(
            "/contribution/add/",
            {
                "contributor": contributor.id,
                "cycle": cycle.id,
                "platform": social_platform.id,
                "reward": reward.id,
                "percentage": "50.00",
                "comment": "Hello world",
            },
        )

        request.user = superuser
        request = self._setup_messages(request)

        response = ContributionCreateView.as_view()(request)

        # Should redirect
        assert response.status_code == 302

        new_obj = Contribution.objects.latest("id")
        assert new_obj.issue is None

    def test_contributioncreateview_form_valid_attaches_preselected_issue(
        self, rf, superuser, contributor, social_platform, reward, cycle, issue
    ):
        url = f"/contribution/add/issue/{issue.number}/"
        request = rf.post(
            url,
            {
                "contributor": contributor.id,
                "cycle": cycle.id,
                "platform": social_platform.id,
                "reward": reward.id,
                "percentage": "12.34",
                "comment": "Linked to issue",
            },
        )

        request.user = superuser
        request = self._setup_messages(request)

        response = ContributionCreateView.as_view()(request, issue_number=issue.number)

        assert response.status_code == 302

        contribution = Contribution.objects.latest("id")
        assert contribution.issue == issue

    def test_contributioncreateview_redirects_to_issue_detail_when_preselected_issue(
        self, rf, superuser, contributor, social_platform, reward, cycle, issue
    ):
        request = rf.post(
            f"/contribution/add/issue/{issue.number}/",
            {
                "contributor": contributor.id,
                "cycle": cycle.id,
                "platform": social_platform.id,
                "reward": reward.id,
                "percentage": "10",
                "comment": "",
            },
        )

        request.user = superuser
        request = self._setup_messages(request)

        response = ContributionCreateView.as_view()(request, issue_number=issue.number)

        expected_url = reverse("issue_detail", args=[issue.id])
        assert response.status_code == 302
        assert response.url == expected_url

    def test_contributioncreateview_redirects_to_contribution_detail_when_no_issue(
        self, rf, superuser, contributor, social_platform, reward, cycle
    ):
        request = rf.post(
            "/contribution/add/",
            {
                "contributor": contributor.id,
                "cycle": cycle.id,
                "platform": social_platform.id,
                "reward": reward.id,
                "percentage": "10",
                "comment": "",
            },
        )

        request.user = superuser
        request = self._setup_messages(request)

        response = ContributionCreateView.as_view()(request)

        new_contribution = Contribution.objects.latest("id")
        expected_url = reverse("contribution_detail", args=[new_contribution.pk])

        assert response.status_code == 302
        assert response.url == expected_url

    def test_contributioncreateview_preselected_issue_must_exist(self, rf, superuser):
        request = rf.post(
            "/contribution/add/issue/9999/",
            {
                "contributor": 1,
                "cycle": 1,
                "platform": 1,
                "reward": 1,
                "percentage": "10",
            },
        )
        request.user = superuser
        request = self._setup_messages(request)

        response = ContributionCreateView.as_view()(request, issue_number=9999)

        assert response.status_code == 200  # form invalid
        assert "form" in response.context_data
        assert response.context_data["form"].errors  # shows error

    def test_contributioncreateview_form_valid_with_nonexistent_issue_number(
        self, rf, superuser, contributor, social_platform, reward, cycle
    ):
        """
        If the user enters an issue_number manually, but no such Issue exists,
        ContributionCreateView should IGNORE IT and still create a normal contribution
        with issue=None (because issue creation/validation is disabled).
        """
        request = rf.post(
            "/contribution/add/9999",
            {
                "contributor": contributor.id,
                "cycle": cycle.id,
                "platform": social_platform.id,
                "reward": reward.id,
                "percentage": "33.33",
                "comment": "Trying an invalid issue number",
            },
        )

        request.user = superuser
        request = self._setup_messages(request)

        response = ContributionCreateView.as_view()(request)

        # Should redirect successfully
        assert response.status_code == 302

        # Retrieve created contribution
        new_contribution = Contribution.objects.latest("id")

        # No issue should be attached
        assert new_contribution.issue is None

    # # get form
    def _setup_messages(self, request):
        setattr(request, "session", "session")
        storage = FallbackStorage(request)
        setattr(request, "_messages", storage)
        return request

    @pytest.fixture
    def contributors_with_handles(self):
        """Creates contributors + handles for testing search."""
        platform = SocialPlatform.objects.create(name="GitHub")
        c1 = Contributor.objects.create(name="Alice Wonderland")
        c2 = Contributor.objects.create(name="Bob Builder")
        c3 = Contributor.objects.create(name="Charlie Alpha")

        Handle.objects.create(contributor=c1, platform=platform, handle="alice123")
        Handle.objects.create(contributor=c2, platform=platform, handle="bobdev")
        Handle.objects.create(contributor=c3, platform=platform, handle="alphacharlie")

        return c1, c2, c3

    def test_contributioncreateview_get_form_no_search_query_returns_all_contributors(
        self, rf, superuser, contributors_with_handles
    ):
        request = rf.get("/contribution/add/")  # no ?q parameter
        request.user = superuser

        view = ContributionCreateView()
        view.setup(request)
        view.request = request
        view.url_issue_number = None

        form = view.get_form()

        # Should contain ALL contributors
        qs = form.fields["contributor"].queryset
        assert qs.count() == len(contributors_with_handles)

    def test_contributioncreateview_get_form_with_search_query_filters_by_name(
        self, rf, superuser, contributors_with_handles
    ):
        request = rf.get("/contribution/add/?q=ali")  # matches Alice
        request.user = superuser

        view = ContributionCreateView()
        view.setup(request)
        view.request = request
        view.url_issue_number = None

        form = view.get_form()
        qs = form.fields["contributor"].queryset

        assert qs.count() == 1
        assert qs.first().name.startswith("Alice")

    def test_contributioncreateview_get_form_with_search_query_filters_by_handle(
        self, rf, superuser, contributors_with_handles
    ):
        request = rf.get("/contribution/add/?q=dev")  # matches bobdev
        request.user = superuser

        view = ContributionCreateView()
        view.setup(request)
        view.request = request
        view.url_issue_number = None

        form = view.get_form()
        qs = form.fields["contributor"].queryset

        assert qs.count() == 1
        assert qs.first().name == "Bob Builder"

    def test_contributioncreateview_get_form_reads_search_query_from_post(
        self, rf, superuser, contributors_with_handles
    ):
        request = rf.post("/contribution/add/", data={"q": "alpha"})
        request.user = superuser

        view = ContributionCreateView()
        view.setup(request)
        view.request = request
        view.url_issue_number = None

        form = view.get_form()
        qs = form.fields["contributor"].queryset

        assert qs.count() == 1
        assert qs.first().name == "Charlie Alpha"

    def test_contributioncreateview_get_form_search_is_case_insensitive(
        self, rf, superuser, contributors_with_handles
    ):
        request = rf.get("/contribution/add/?q=ALICE")
        request.user = superuser

        view = ContributionCreateView()
        view.setup(request)
        view.request = request
        view.url_issue_number = None

        form = view.get_form()
        qs = form.fields["contributor"].queryset

        assert qs.count() == 1
        assert qs.first().name == "Alice Wonderland"

    def test_contributioncreateview_get_form_distinct_removes_duplicates(
        self, rf, superuser, contributors_with_handles
    ):
        # Add second handle for same contributor → search should return only 1 result
        platform = SocialPlatform.objects.first()
        c1 = contributors_with_handles[0]
        Handle.objects.create(contributor=c1, platform=platform, handle="aliceXYZ")

        request = rf.get("/contribution/add/?q=alice")
        request.user = superuser

        view = ContributionCreateView()
        view.setup(request)
        view.request = request
        view.url_issue_number = None

        form = view.get_form()
        qs = form.fields["contributor"].queryset

        assert qs.count() == 1  # distinct removes duplicates


class TestContributorListView:
    """Testing class for :class:`core.views.ContributorListView`."""

    def test_contributorlistview_is_subclass_of_listview(self):
        assert issubclass(ContributorListView, ListView)

    def test_contributorlistview_model(self):
        view = ContributorListView()
        assert view.model == Contributor

    def test_contributorlistview_paginate_by(self):
        view = ContributorListView()
        assert view.paginate_by == 20


@pytest.mark.django_db
class TestDbContributorListView:
    """Testing class for :class:`core.views.ContributorListView` with database."""

    def test_contributorlistview_queryset(self, rf):
        request = rf.get("/contributors/")

        # Create test contributors
        Contributor.objects.create(name="contributor1", address="addr1")
        Contributor.objects.create(name="contributor2", address="addr2")

        view = ContributorListView()
        view.setup(request)

        queryset = view.get_queryset()

        assert queryset.count() == 2
        assert all(isinstance(obj, Contributor) for obj in queryset)


class TestContributorListViewSearch:
    """Testing class for :class:`core.views.ContributorListView` search functionality."""

    def test_contributorlistview_search_inheritance(self):
        assert issubclass(ContributorListView, ListView)

    def test_contributorlistview_model(self):
        view = ContributorListView()
        assert view.model == Contributor

    def test_contributorlistview_paginate_by(self):
        view = ContributorListView()
        assert view.paginate_by == 20

    def test_contributorlistview_template_name_suffix(self):
        view = ContributorListView()
        assert view.template_name_suffix == "_list"


@pytest.mark.django_db
class TestDbContributorListViewSearch:
    """Testing class for :class:`core.views.ContributorListView` search with database."""

    def test_contributorlistview_search_by_name(self, rf):
        # Create test contributors
        contributor1 = Contributor.objects.create(name="John Doe", address="addr1")
        contributor2 = Contributor.objects.create(name="Jane Smith", address="addr2")
        contributor3 = Contributor.objects.create(name="Bob Johnson", address="addr3")

        # Create request with search query
        request = rf.get("/contributors/", {"q": "john"})
        view = ContributorListView()
        view.setup(request)

        queryset = view.get_queryset()

        # Should find John Doe and Bob Johnson
        assert queryset.count() == 2
        assert contributor1 in queryset
        assert contributor3 in queryset
        assert contributor2 not in queryset

    def test_contributorlistview_search_by_handle(self, rf):
        # Create test contributors
        contributor1 = Contributor.objects.create(name="User1", address="addr1")
        contributor2 = Contributor.objects.create(name="User2", address="addr2")

        # Create social platforms
        github = SocialPlatform.objects.create(name="GitHub", prefix="g@")
        discord = SocialPlatform.objects.create(name="Discord", prefix="")

        # Create handles
        Handle.objects.create(
            contributor=contributor1, platform=github, handle="developer"
        )
        Handle.objects.create(
            contributor=contributor2, platform=discord, handle="tester"
        )

        # Create request with search query
        request = rf.get("/contributors/", {"q": "test"})
        view = ContributorListView()
        view.setup(request)

        queryset = view.get_queryset()

        # Should find contributor with "tester" handle
        assert queryset.count() == 1
        assert contributor2 in queryset
        assert contributor1 not in queryset

    def test_contributorlistview_search_by_name_and_handle(self, rf):
        # Create test contributors
        contributor1 = Contributor.objects.create(name="Alice", address="addr1")
        contributor2 = Contributor.objects.create(name="Bob", address="addr2")
        contributor3 = Contributor.objects.create(name="Charlie", address="addr3")

        # Create social platform
        github = SocialPlatform.objects.create(name="GitHub", prefix="g@")

        # Create handles
        Handle.objects.create(
            contributor=contributor1, platform=github, handle="alice_dev"
        )
        Handle.objects.create(
            contributor=contributor2, platform=github, handle="charlie_fan"
        )

        # Create request with search query
        request = rf.get("/contributors/", {"q": "charlie"})
        view = ContributorListView()
        view.setup(request)

        queryset = view.get_queryset()

        # Should find Charlie by name and Bob by handle
        assert queryset.count() == 2
        assert contributor2 in queryset  # Has handle "charlie_fan"
        assert contributor3 in queryset  # Name is "Charlie"
        assert contributor1 not in queryset

    def test_contributorlistview_search_case_insensitive(self, rf):
        # Create test contributors
        contributor1 = Contributor.objects.create(name="John Doe", address="addr1")
        contributor2 = Contributor.objects.create(name="Mary Jane", address="addr2")

        # Create social platform
        github = SocialPlatform.objects.create(name="GitHub", prefix="g@")
        Handle.objects.create(
            contributor=contributor2, platform=github, handle="SuperUser"
        )

        # Test different case variations
        test_cases = ["john", "JOHN", "John", "super", "SUPER", "Super"]

        for search_term in test_cases:
            request = rf.get("/contributors/", {"q": search_term})
            view = ContributorListView()
            view.setup(request)

            queryset = view.get_queryset()

            if search_term.lower() == "john":
                assert queryset.count() == 1
                assert contributor1 in queryset
            elif search_term.lower() == "super":
                assert queryset.count() == 1
                assert contributor2 in queryset

    def test_contributorlistview_search_partial_match(self, rf):
        # Create test contributors
        contributor1 = Contributor.objects.create(name="Alexander", address="addr1")
        contributor2 = Contributor.objects.create(name="Sandra", address="addr2")

        # Create social platform
        github = SocialPlatform.objects.create(name="GitHub", prefix="g@")
        Handle.objects.create(
            contributor=contributor2, platform=github, handle="pythonista"
        )

        # Test partial searches
        request = rf.get("/contributors/", {"q": "alex"})
        view = ContributorListView()
        view.setup(request)
        queryset = view.get_queryset()

        assert queryset.count() == 1
        assert contributor1 in queryset

        request = rf.get("/contributors/", {"q": "thon"})
        view = ContributorListView()
        view.setup(request)
        queryset = view.get_queryset()

        assert queryset.count() == 1
        assert contributor2 in queryset

    def test_contributorlistview_no_search_query(self, rf):
        # Create test contributors
        Contributor.objects.create(name="User1", address="addr1")
        Contributor.objects.create(name="User2", address="addr2")
        Contributor.objects.create(name="User3", address="addr3")

        # Create request without search query
        request = rf.get("/contributors/")
        view = ContributorListView()
        view.setup(request)

        queryset = view.get_queryset()

        # Should return all contributors
        assert queryset.count() == 3

    def test_contributorlistview_empty_search_query(self, rf):
        # Create test contributors
        Contributor.objects.create(name="User1", address="addr1")
        Contributor.objects.create(name="User2", address="addr2")

        # Create request with empty search query
        request = rf.get("/contributors/", {"q": ""})
        view = ContributorListView()
        view.setup(request)

        queryset = view.get_queryset()

        # Should return all contributors
        assert queryset.count() == 2

    def test_contributorlistview_search_no_results(self, rf):
        # Create test contributors
        Contributor.objects.create(name="Alice", address="addr1")
        Contributor.objects.create(name="Bob", address="addr2")

        # Create request with non-matching search query
        request = rf.get("/contributors/", {"q": "xyz123"})
        view = ContributorListView()
        view.setup(request)

        queryset = view.get_queryset()

        # Should return empty queryset
        assert queryset.count() == 0

    def test_contributorlistview_search_context_data(self, rf):
        # Create a contributor
        Contributor.objects.create(name="Test User", address="addr1")

        # Create request with search query
        request = rf.get("/contributors/", {"q": "test"})
        view = ContributorListView()
        view.setup(request)
        view.object_list = view.get_queryset()

        context = view.get_context_data()

        # Should include search query in context
        assert "search_query" in context
        assert context["search_query"] == "test"

    def test_contributorlistview_search_context_no_query(self, rf):
        # Create a contributor
        Contributor.objects.create(name="Test User", address="addr1")

        # Create request without search query
        request = rf.get("/contributors/")
        view = ContributorListView()
        view.setup(request)
        view.object_list = view.get_queryset()

        context = view.get_context_data()

        # Should include empty search query in context
        assert "search_query" in context
        assert context["search_query"] == ""

    def test_contributorlistview_search_duplicate_handles(self, rf):
        # Create test contributors
        contributor1 = Contributor.objects.create(name="User1", address="addr1")
        contributor2 = Contributor.objects.create(name="User2", address="addr2")

        # Create social platform
        platform = SocialPlatform.objects.create(name="Platformxs", prefix="xs")

        # Create handles with similar names
        Handle.objects.create(
            contributor=contributor1, platform=platform, handle="developer1"
        )
        Handle.objects.create(
            contributor=contributor2, platform=platform, handle="developer2"
        )

        # Create request with search query
        request = rf.get("/contributors/", {"q": "developer"})
        view = ContributorListView()
        view.setup(request)

        queryset = view.get_queryset()

        # Should find both contributors (distinct results)
        assert queryset.count() == 2
        assert contributor1 in queryset
        assert contributor2 in queryset

    def test_contributorlistview_search_multiple_handles_same_contributor(self, rf):
        # Create test contributor
        contributor = Contributor.objects.create(name="Test User", address="addr1")

        # Create social platforms
        github = SocialPlatform.objects.create(name="GitHub", prefix="g@")
        discord = SocialPlatform.objects.create(name="Discord", prefix="")

        # Create multiple handles for same contributor
        Handle.objects.create(
            contributor=contributor, platform=github, handle="python_dev"
        )
        Handle.objects.create(
            contributor=contributor, platform=discord, handle="python_lover"
        )

        # Create request with search query
        request = rf.get("/contributors/", {"q": "python"})
        view = ContributorListView()
        view.setup(request)

        queryset = view.get_queryset()

        # Should find contributor only once (distinct results)
        assert queryset.count() == 1
        assert contributor in queryset

    def test_contributorlistview_integration_search(self, client):
        # Create test data
        contributor1 = Contributor.objects.create(
            name="Alice Developer", address="addr1"
        )
        contributor2 = Contributor.objects.create(name="Bob Tester", address="addr2")

        github = SocialPlatform.objects.create(name="GitHub", prefix="g@")
        Handle.objects.create(
            contributor=contributor1, platform=github, handle="alice_codes"
        )

        # Test search by name
        response = client.get(reverse("contributors"), {"q": "alice"})

        assert response.status_code == 200
        assert "search_query" in response.context
        assert response.context["search_query"] == "alice"
        assert contributor1 in response.context["contributor_list"]
        assert contributor2 not in response.context["contributor_list"]

        # Test search by handle
        response = client.get(reverse("contributors"), {"q": "codes"})

        assert response.status_code == 200
        assert contributor1 in response.context["contributor_list"]
        assert contributor2 not in response.context["contributor_list"]

        # Test no results
        response = client.get(reverse("contributors"), {"q": "nonexistent"})

        assert response.status_code == 200
        assert len(response.context["contributor_list"]) == 0


@pytest.mark.django_db
class TestDbContributorListViewHtmx:
    """Testing class for :class:`core.views.ContributorListView` htmx requests."""

    @pytest.mark.django_db
    def test_contributorlistview_render_to_response_htmx_returns_partial(self, rf):
        """HTMX request → should render only the partial fragment."""

        Contributor.objects.create(name="Alice", address="addr1")

        # simulate request
        request = rf.get("/contributors/?q=alice")
        request.htmx = True  # <-- ✅ BEFORE dispatch

        # Call view via dispatch(), not .render_to_response()
        response = ContributorListView.as_view()(request)
        html = response.content.decode()

        # Assertions
        assert response.status_code == 200
        assert "Alice" in html

        # ✅ Must NOT contain full page (no navbar)
        assert "<html" not in html.lower()
        assert "<body" not in html.lower()

    @pytest.mark.django_db
    def test_contributorlistview_render_to_response_standard_request_renders_full_page(
        rself, rf
    ):
        Contributor.objects.create(name="Bob", address="addr2")

        request = rf.get("/contributors/")
        request.htmx = False  # simulate normal request

        response = ContributorListView.as_view()(request)
        response.render()
        html = response.content.decode()

        assert "<html" in html.lower()  # ✅ full HTML page
        assert f"{settings.PROJECT_OWNER} Contributors" in html
        assert "Bob" in html


class TestContributorDetailView:
    """Testing class for :class:`core.views.ContributorDetailView`."""

    def test_contributordetailview_is_subclass_of_detailview(self):
        assert issubclass(ContributorDetailView, DetailView)

    def test_contributordetailview_model(self):
        view = ContributorDetailView()
        assert view.model == Contributor


@pytest.mark.django_db
class TestDbContributorDetailView:
    """Testing class for :class:`core.views.ContributorDetailView` with database."""

    def test_contributordetailview_get_object(self, rf):
        contributor = Contributor.objects.create(
            name="test_contributor", address="test_address"
        )
        request = rf.get(f"/contributors/{contributor.id}/")

        view = ContributorDetailView()
        view.setup(request, pk=contributor.id)

        obj = view.get_object()

        assert obj == contributor
        assert obj.name == "test_contributor"


class TestCycleListView:
    """Testing class for :class:`core.views.CycleListView`."""

    def test_cyclelistview_is_subclass_of_listview(self):
        assert issubclass(CycleListView, ListView)

    def test_cyclelistview_model(self):
        view = CycleListView()
        assert view.model == Cycle

    def test_cyclelistview_paginate_by(self):
        view = CycleListView()
        assert view.paginate_by == 10


@pytest.mark.django_db
class TestDbCycleListView:
    """Testing class for :class:`core.views.CycleListView` with database."""

    def test_cyclelistview_get_context_data(self, rf):
        request = rf.get("/cycles/")

        # Create test cycles
        Cycle.objects.create(start="2023-01-01", end="2023-01-31")
        Cycle.objects.create(start="2023-02-01", end="2023-02-28")

        view = CycleListView()
        view.setup(request)

        view.object_list = view.get_queryset()
        context = view.get_context_data()

        assert context["total_cycles"] == 2

    def test_cyclelistview_get_queryset(self, rf):
        request = rf.get("/cycles/")

        # Create test cycles
        cycle1 = Cycle.objects.create(start="2023-01-02", end="2023-01-31")
        cycle2 = Cycle.objects.create(start="2023-02-02", end="2023-02-28")

        view = CycleListView()
        view.setup(request)

        queryset = view.get_queryset()

        # Should be in reverse order (most recent first)
        assert queryset.count() == 2
        assert queryset.first() == cycle2  # Most recent
        assert queryset.last() == cycle1  # Oldest


class TestCycleDetailView:
    """Testing class for :class:`core.views.CycleDetailView`."""

    def test_cycledetailview_is_subclass_of_detailview(self):
        assert issubclass(CycleDetailView, DetailView)

    def test_cycledetailview_model(self):
        view = CycleDetailView()
        assert view.model == Cycle

    # # get_queryset
    @pytest.mark.django_db
    def test_cycledetailview_get_queryset_integration(self):
        """Integration test to verify the actual queryset behavior."""
        # Create test data
        cycle = Cycle.objects.create(start="2025-01-01")
        contributor = Contributor.objects.create(name="test_contributor")
        platform = SocialPlatform.objects.create(name="GitHub")
        reward_type = RewardType.objects.create(label="BUG", name="Bug Fix")
        reward = Reward.objects.create(type=reward_type, level=1, amount=1000)

        # Create contributions
        Contribution.objects.create(
            cycle=cycle, contributor=contributor, platform=platform, reward=reward
        )

        view = CycleDetailView()
        queryset = view.get_queryset()

        # Verify annotations are present
        cycle_from_queryset = queryset.first()
        assert hasattr(cycle_from_queryset, "contributions_count")
        assert hasattr(cycle_from_queryset, "total_rewards_amount")

        # Verify prefetch is configured
        assert hasattr(queryset, "_prefetch_related_lookups")

    @pytest.mark.django_db
    def test_cycledetailview_get_queryset_integration2(self):
        """Integration test to verify the actual queryset behavior with reverse ordering."""
        # Create test data
        cycle = Cycle.objects.create(start="2025-09-08")
        contributor = Contributor.objects.create(name="test_contributor")
        platform = SocialPlatform.objects.create(name="GitHub")
        reward_type = RewardType.objects.create(label="BUG", name="Bug Fix")
        reward = Reward.objects.create(type=reward_type, level=1, amount=1000)

        # Create contributions with different IDs (created in order)
        contribution1 = Contribution.objects.create(
            cycle=cycle, contributor=contributor, platform=platform, reward=reward
        )
        contribution2 = Contribution.objects.create(
            cycle=cycle, contributor=contributor, platform=platform, reward=reward
        )
        contribution3 = Contribution.objects.create(
            cycle=cycle, contributor=contributor, platform=platform, reward=reward
        )

        view = CycleDetailView()
        queryset = view.get_queryset()

        # Get the cycle from the queryset
        cycle_from_queryset = queryset.first()

        # Verify prefetch_related is applied
        assert hasattr(queryset, "_prefetch_related_lookups")

        # Test 1: Prefetched data should be in reverse order
        assert hasattr(cycle_from_queryset, "prefetched_contributions")
        prefetched_contributions = cycle_from_queryset.prefetched_contributions
        assert prefetched_contributions == [contribution3, contribution2, contribution1]


@pytest.mark.django_db
class TestDbCycleDetailView:
    """Testing class for :class:`core.views.CycleDetailView` with database."""

    def test_cycledetailview_get_object(self, rf):
        cycle = Cycle.objects.create(start="2023-01-01", end="2023-01-31")
        request = rf.get(f"/cycles/{cycle.id}/")

        view = CycleDetailView()
        view.setup(request, pk=cycle.id)

        obj = view.get_object()

        assert obj == cycle
        assert obj.start.strftime("%Y-%m-%d") == "2023-01-01"
