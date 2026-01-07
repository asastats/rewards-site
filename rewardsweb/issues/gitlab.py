"""Module containing functions for GitLab issues and webhooks management."""

import logging
import os

from django.conf import settings
from gitlab import Gitlab

from issues.base import BaseIssueProvider, BaseWebhookHandler
from issues.config import gitlab_config

logger = logging.getLogger(__name__)


class GitlabProvider(BaseIssueProvider):
    """GitLab provider implementation."""

    name = "gitlab"

    def _get_client(self, issue_tracker_api_token=None):
        """Get GitLab client.

        :var config: GitLab configuration data
        :type config: dict
        :param issue_tracker_api_token: if provided, token used for client instantiation
        :type issue_tracker_api_token: str
        :var pat: GitLab Personal Access Token.
        :type pat: str
        :var url: GitLab instance URL.
        :type url: str
        :return: GitLab client instance.
        :rtype: :class:`gitlab.Gitlab`
        """
        config = gitlab_config()
        url = config.get("url")
        if issue_tracker_api_token:
            return Gitlab(url=url, private_token=issue_tracker_api_token)

        pat = config.get("private_token")
        if pat:
            return Gitlab(url=url, private_token=pat)

        if not self.user or not self.user.profile.issue_tracker_api_token:
            return None

        return Gitlab(url=url, private_token=self.user.profile.issue_tracker_api_token)

    def _get_project(self):
        """Get GitLab project.

        TODO: implement usage of this

        :var project_id: The ID or path of the GitLab project.
        :type project_id: str
        :return: GitLab project instance.
        :rtype: :class:`gitlab.v4.objects.Project`
        """
        project_id = gitlab_config().get("project_id")
        if not project_id:
            return None

        return self.client.projects.get(project_id)

    def _get_repository(self):
        """Get GitLab project.

        :var project: GitLab project instance
        :type project: :class:`gitlab.v4.objects.Project`
        :return: GitLab project instance
        :rtype: :class:`gitlab.v4.objects.Project`
        """
        return (
            self.client.projects.get(
                f"{settings.ISSUE_TRACKER_OWNER}/{settings.ISSUE_TRACKER_NAME}"
            )
            if self.client
            else None
        )

    def _close_issue_with_labels_impl(self, issue_number, labels_to_set, comment):
        """Close GitLab issue with labels.

        :param issue_number: unique issue identifier
        :type issue_number: int
        :param labels_to_set: collection of labels to set
        :type labels_to_set: list
        :param comment: text to add as comment
        :type comment: str
        :var issue: GitLab issue instance
        :type issue: :class:`gitlab.v4.objects.ProjectIssue`
        :return: operation result
        :rtype: dict
        """
        issue = self.repo.issues.get(issue_number)
        if labels_to_set:
            issue.labels = labels_to_set

        if comment:
            issue.notes.create({"body": comment})

        issue.state_event = "close"
        issue.save()
        return {
            "message": f"Closed GitLab issue #{issue_number}",
            "issue_state": issue.state,
            "current_labels": issue.labels,
        }

    def _create_issue_impl(self, title, body, labels):
        """Create GitLab issue.

        :param title: issue title
        :type title: str
        :param body: issue body
        :type body: str
        :param labels: issue labels
        :type labels: list
        :var issue: created GitLab issue instance
        :type issue: :class:`gitlab.v4.objects.ProjectIssue`
        :return: operation result
        :rtype: dict
        """
        issue = self.repo.issues.create(
            {"title": title, "description": body, "labels": labels or []}
        )
        return {
            "issue_number": issue.iid,
            "issue_url": issue.web_url,
            "data": issue.attributes,
        }

    def _fetch_issues_impl(self, state, since):
        """Fetch GitLab issues.

        :param state: issue state filter
        :type state: str
        :param since: fetch issues updated after this date
        :type since: :class:`datetime.datetime`
        :return: collection of issue instances
        :rtype: list
        """
        return self.repo.issues.list(state=state, sort="updated_at", since=since)

    def _get_issue_by_number_impl(self, issue_number):
        """Get GitLab issue by number.

        :param issue_number: unique issue identifier
        :type issue_number: int
        :var issue: GitLab issue instance
        :type issue: :class:`gitlab.v4.objects.ProjectIssue`
        :var issue_data: formatted issue data
        :type issue_data: dict
        :return: operation result
        :rtype: dict
        """
        issue = self.repo.issues.get(issue_number)
        issue_data = {
            "number": issue.iid,
            "title": issue.title,
            "body": issue.description,
            "state": issue.state,
            "created_at": issue.created_at,
            "updated_at": issue.updated_at,
            "closed_at": issue.closed_at,
            "labels": issue.labels,
            "assignees": [assignee["username"] for assignee in issue.assignees],
            "user": issue.author["username"] if issue.author else None,
            "html_url": issue.web_url,
            "comments": len(issue.notes.list()),
        }
        return {
            "message": f"Retrieved GitLab issue #{issue_number}",
            "issue": issue_data,
        }

    def _issue_url_impl(self, issue_number):
        """Get URL of the GitLab issue defined by provided `issue_number`.

        :param issue_number: unique issue identifier
        :type issue_number: int
        :return: full URL to the issue
        :rtype: str
        """
        return (
            f"https://gitlab.com/{settings.ISSUE_TRACKER_OWNER}/"
            f"{settings.ISSUE_TRACKER_NAME}/-/issues/{issue_number}"
        )

    def _set_labels_to_issue_impl(self, issue_number, labels_to_set):
        """Set labels to GitLab issue.

        :param issue_number: unique issue identifier
        :type issue_number: int
        :param labels_to_set: collection of labels to set
        :type labels_to_set: list
        :var issue: GitLab issue instance
        :type issue: :class:`gitlab.v4.objects.ProjectIssue`
        :return: operation result
        :rtype: dict
        """
        issue = self.repo.issues.get(issue_number)
        issue.labels = labels_to_set
        issue.save()
        return {
            "message": f"Added labels {labels_to_set} to GitLab issue #{issue_number}",
            "current_labels": issue.labels,
        }


class GitLabWebhookHandler(BaseWebhookHandler):
    """GitLab webhook handler for issue creation events."""

    def validate(self):
        """Validate GitLab webhook token using X-Gitlab-Token header.

        :return: True if token matches or no token configured, False otherwise
        :rtype: bool
        """
        token = self.request.headers.get("X-Gitlab-Token")
        expected_token = os.getenv("ISSUES_WEBHOOK_SECRET", None)

        # Skip validation if no token configured
        if not expected_token:
            return True

        return token == expected_token

    def extract_issue_data(self):
        """Extract issue data from GitLab webhook payload.

        TODO: tests

        :var object_kind: GitLab object kind
        :type object_kind: str
        :var action: GitLab event type
        :type action: str
        :var issue: GitLab issue data
        :type issue: dict
        :var labels: collection of label names
        :type labels: list
        :return: issue data dict if object_kind is 'issue' and action is 'open'
        :rtype: dict or None
        """
        # Check if this is an issue creation event
        object_kind = self.payload.get("object_kind")
        action = self.payload.get("object_attributes", {}).get("action")

        if object_kind != "issue" or action != "open":
            return None

        issue = self.payload.get("object_attributes", {})
        labels = [label.get("title") for label in issue.get("labels", [])]

        return {
            "username": issue.get("author", {}).get("username", ""),
            "title": issue.get("title", ""),
            "type": self._parse_type_from_labels(labels),
            "body": issue.get("description", ""),
            "raw_content": issue.get("description", ""),
            "issue_url": issue.get("url", ""),
            "issue_number": issue.get("iid"),  # GitLab uses iid
            "project_id": self.payload.get("project", {}).get("id"),
            "project_name": self.payload.get("project", {}).get("name", ""),
            "created_at": issue.get("created_at", ""),
        }
