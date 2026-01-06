"""Testing module for :py:mod:`core.views` views related to issues Hhtmx requests."""

import pytest
from django.conf import settings
from django.urls import reverse


@pytest.mark.django_db
class TestIssueModalHTMX:
    """Tests loading modal fragments dynamically via HTMX."""

    def test_issuemodalview_htmx_modal_loads(self, client, superuser, issue):
        """Modal fragment loads correctly using HTMX."""
        client.force_login(superuser)

        url = reverse("issue_modal", kwargs={"pk": issue.pk}) + "?action=addressed"
        response = client.get(url, HTTP_HX_REQUEST="true")

        assert response.status_code == 200
        content = response.content.decode()

        assert "<dialog" in content
        assert "close-addressed-modal" in content

    def test_modal_raises_404_for_non_superuser(self, client, issue):
        """Anonymous or normal user should trigger Http404"""
        url = reverse("issue_modal", kwargs={"pk": issue.pk}) + "?action=addressed"
        response = client.get(url, HTTP_HX_REQUEST="true")
        assert response.status_code == 404

    def test_modal_raises_404_for_invalid_action(self, client, superuser, issue):
        """Invalid ?action should raise Http404"""
        client.force_login(superuser)

        url = reverse("issue_modal", kwargs={"pk": issue.pk}) + "?action=banana"
        response = client.get(url, HTTP_HX_REQUEST="true")
        assert response.status_code == 404

    def test_issue_detail_view_handle_labels_submission_htmx(
        self, client, superuser, issue, mocker
    ):
        """IssueDetailView._handle_labels_submission should return HTMX partial on success."""
        client.force_login(superuser)
        provider = settings.ISSUE_TRACKER_PROVIDER.lower()
        name = provider.capitalize()
        mocker.patch(f"issues.{provider}.{name}Provider._get_client")
        mocker.patch(f"issues.{provider}.{name}Provider._get_repository")
        mocker.patch(
            f"issues.{provider}.BaseIssueProvider.set_labels_to_issue",
            return_value={
                "success": True,
                "message": "some message",
                "current_labels": ["bug", "blocker"],
            },
        )
        url = reverse("issue_detail", kwargs={"pk": issue.pk})
        data = {
            "submit_labels": "",
            "labels": ["bug"],
            "priority": "blocker",
        }
        response = client.post(url, data, HTTP_HX_REQUEST="true")

        assert response.status_code == 200
        content = response.content.decode()

        assert "<form" in content
        assert "bug" in content
        assert "blocker" in content
        assert "Labels updated successfully" in content
