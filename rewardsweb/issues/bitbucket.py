"""Module containing functions for Bitbucket issues and webhooks management."""

import logging
from datetime import datetime, timedelta, timezone

import jwt
import requests
from atlassian.bitbucket.cloud import Cloud
from django.conf import settings

from issues.base import BaseIssueProvider
from issues.config import bitbucket_config

logger = logging.getLogger(__name__)


class BitbucketApp:
    """Helper class for instantiating a Bitbucket client using a Bitbucket app."""

    def jwt_token(self):
        """Generate JWT token for a Bitbucket app.

        :var config: Bitbucket configuration data
        :type config: dict
        :var client_key: The clientKey from the app's descriptor.
        :type client_key: str
        :var shared_secret: The sharedSecret from the app's installation.
        :type shared_secret: str
        :var now: The current UTC time.
        :type now: :class:`datetime.datetime`
        :var expiration: The expiration time for the token (3 minutes).
        :type expiration: :class:`datetime.datetime`
        :var payload: The JWT payload.
        :type payload: dict
        :return: The JWT token.
        :rtype: str
        """
        config = bitbucket_config()
        client_key = config.get("client_key")
        shared_secret = config.get("shared_secret")

        if not (client_key and shared_secret):
            return None

        now = datetime.now(timezone.utc)
        expiration = now + timedelta(minutes=3)
        payload = {
            "iat": now,
            "exp": expiration,
            "iss": client_key,
        }
        return jwt.encode(payload, shared_secret, algorithm="HS256")

    def access_token(self):
        """Retrieve an access token for a Bitbucket app installation.

        :var jwt_token: The JWT token for the app.
        :type jwt_token: str
        :var url: The URL for the token exchange request.
        :type url: str
        :var headers: The headers for the request.
        :type headers: dict
        :var data: The data for the POST request.
        :type data: dict
        :var response: The response from the request.
        :type response: :class:`requests.Response`
        :return: The installation access token.
        :rtype: str
        """
        jwt_token = self.jwt_token()
        if not jwt_token:
            return None

        url = "https://bitbucket.org/site/oauth2/access_token"
        headers = {"Authorization": f"JWT {jwt_token}"}
        data = {"grant_type": "urn:bitbucket:oauth2:jwt"}

        response = requests.post(url, headers=headers, data=data)

        if response.status_code == 200:
            return response.json().get("access_token")

        return None


class BitbucketProvider(BaseIssueProvider):
    """Bitbucket provider implementation."""

    name = "bitbucket"

    def _get_client(self, issue_tracker_api_token=None):
        """Get Bitbucket client.

        :param issue_tracker_api_token: if provided, token used for client instantiation
        :type issue_tracker_api_token: str
        :var client: Bitbucket app client instance
        :type client: :class:`atlassian.bitbucket.cloud.Cloud`
        :var token: Bitbucket authentication token instance
        :type token: str
        :return: Bitbucket client instance
        :rtype: :class:`atlassian.bitbucket.cloud.Cloud`
        """
        if issue_tracker_api_token:
            return Cloud(token=issue_tracker_api_token)

        token = BitbucketApp().access_token()
        if token:
            return Cloud(token=token)

        if not self.user or not self.user.profile.issue_tracker_api_token:
            return None

        return Cloud(token=self.user.profile.issue_tracker_api_token)

    def _get_repository(self):
        """Get Bitbucket repository.

        :return: Bitbucket repository instance
        :rtype: object
        """
        return (
            self.client.repositories.get(
                settings.ISSUE_TRACKER_OWNER, settings.ISSUE_TRACKER_NAME
            )
            if self.client
            else None
        )

    def _close_issue_with_labels_impl(self, issue_number, labels_to_set, comment):
        """Close Bitbucket issue.

        :param issue_number: unique issue identifier
        :type issue_number: int
        :param labels_to_set: collection of components to set (Bitbucket uses components instead of labels)
        :type labels_to_set: list
        :param comment: text to add as comment
        :type comment: str
        :return: operation result
        :rtype: dict
        """
        workspace, repo_slug = self.repo
        if labels_to_set:
            self.client.update_issue(
                repo=repo_slug, issue_id=issue_number, components=labels_to_set
            )
        if comment:
            self.client.issue_comment(
                repo=repo_slug, issue_id=issue_number, content=comment
            )
        self.client.set_issue_status(
            repo=repo_slug, issue_id=issue_number, status="resolved"
        )
        return {
            "message": f"Closed Bitbucket issue #{issue_number}",
            "issue_state": "resolved",
            "current_labels": labels_to_set or [],
        }

    def _create_issue_impl(self, title, body, labels):
        """Create Bitbucket issue.

        :param title: issue title
        :type title: str
        :param body: issue body
        :type body: str
        :param labels: issue components (Bitbucket uses components instead of labels)
        :type labels: list
        :var issue: created Bitbucket issue instance
        :type issue: :class:`atlassian.bitbucket.issues.Issue`
        :return: operation result
        :rtype: dict
        """
        workspace, repo_slug = self.repo
        issue = self.client.create_issue(
            repo=repo_slug,
            title=title,
            content=body,
            kind="bug",
            priority="major",
        )
        return {
            "issue_number": issue.id,
            "issue_url": issue.links["html"]["href"],
            "data": issue.raw_data,
        }

    def _fetch_issues_impl(self, state, since):
        """Fetch Bitbucket issues from provider.

        Parameter `since` is not directly supported by Bitbucket API in the same way
        as GitHub/GitLab. Issues will be fetched without a 'since' filter.

        :param state: issue state filter (e.g., 'open', 'resolved')
        :type state: str
        :param since:  fetch only issues that have been updated after this date
        :type since: :class:`datetime.datetime`
        :return: collection of Bitbucket issue instances
        :rtype: list
        """
        workspace, repo_slug = self.repo
        return self.client.get_issues(repo=repo_slug, state=state)

    def _get_issue_by_number_impl(self, issue_number):
        """Get Bitbucket issue by number.

        :param issue_number: unique issue identifier
        :type issue_number: int
        :var issue: Bitbucket issue instance
        :type issue: :class:`atlassian.bitbucket.issues.Issue`
        :var issue_data: formatted issue data
        :type issue_data: dict
        :return: operation result
        :rtype: dict
        """
        workspace, repo_slug = self.repo
        issue = self.client.get_issue(repo=repo_slug, issue_id=issue_number)
        issue_data = {
            "number": issue.id,
            "title": issue.title,
            "body": issue.content,
            "state": issue.state,
            "created_at": issue.created_on,
            "updated_at": issue.updated_on,
            "closed_at": issue.edited_on if issue.state == "resolved" else None,
            "labels": issue.components if hasattr(issue, "components") else [],
            "assignees": [issue.assignee["display_name"]] if issue.assignee else [],
            "user": issue.reporter["display_name"] if issue.reporter else None,
            "html_url": issue.links["html"]["href"],
            "comments": len(issue.comments) if hasattr(issue, "comments") else 0,
        }
        return {
            "message": f"Retrieved Bitbucket issue #{issue_number}",
            "issue": issue_data,
        }

    def _issue_url_impl(self, issue_number):
        """Get URL of the Bitbucket issue defined by provided `issue_number`.

        :param issue_number: unique issue identifier
        :type issue_number: int
        :return: full URL to the issue
        :rtype: str
        """
        workspace, repo_slug = self.repo
        return f"https://bitbucket.org/{workspace}/{repo_slug}/issues/{issue_number}/"

    def _set_labels_to_issue_impl(self, issue_number, labels_to_set):
        """Set components to Bitbucket issue.

        :param issue_number: unique issue identifier
        :type issue_number: int
        :param labels_to_set: collection of components to set
        :type labels_to_set: list
        :var issue: Bitbucket issue instance
        :type issue: :class:`atlassian.bitbucket.issues.Issue`
        :return: operation result
        :rtype: dict
        """
        workspace, repo_slug = self.repo
        self.client.update_issue(
            repo=repo_slug, issue_id=issue_number, components=labels_to_set
        )
        issue = self.client.get_issue(repo=repo_slug, issue_id=issue_number)
        return {
            "message": f"Added components {labels_to_set} to Bitbucket issue #{issue_number}",
            "current_labels": (
                issue.components if hasattr(issue, "components") else []
            ),
        }
