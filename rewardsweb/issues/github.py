"""Module containing functions for GitHub issues and webhooks management."""

import logging
from datetime import datetime, timedelta

import jwt
import requests
from django.conf import settings
from github import Auth, Github

from issues.base import BaseIssueProvider
from issues.config import github_config

logger = logging.getLogger(__name__)


class GitHubApp:
    """Helper class for instantiating GitHub client using GitHub bot."""

    def jwt_token(self):
        """Generate JWT token for GitHub bot.

        :var config: Github configuration data
        :type config: dict
        :var bot_private_key_filename: filename of the bot's private key
        :type bot_private_key_filename: str
        :var bot_client_id: client ID of the bot
        :type bot_client_id: str
        :var pem_path: path to the bot's private key
        :type pem_path: :class:`pathlib.Path`
        :var signing_key: bot's private key
        :type signing_key: bytes
        :var now: current time
        :type now: :class:`datetime.datetime`
        :var expiration: expiration time for the token
        :type expiration: :class:`datetime.datetime`
        :var payload: JWT payload
        :type payload: dict
        :return: JWT token
        :rtype: str
        """
        config = github_config()
        bot_private_key_filename = config.get("private_key_filename")
        bot_client_id = config.get("client_id")
        if not (bot_private_key_filename and bot_client_id):
            return None

        pem_path = settings.BASE_DIR.parent / "fixtures" / bot_private_key_filename
        with open(pem_path, "rb") as pem_file:
            signing_key = pem_file.read()

        now = datetime.now()
        expiration = now + timedelta(minutes=8)
        payload = {
            "iat": int(now.timestamp()),
            "exp": int(expiration.timestamp()),
            "iss": bot_client_id,
        }
        return jwt.encode(payload, signing_key, algorithm="RS256")

    def installation_token(self):
        """Retrieve installation access token for GitHub bot.

        :var installation_id: ID of the bot's installation
        :type installation_id: str
        :var jwt_token: JWT token for the bot
        :type jwt_token: str
        :var headers: headers for the request
        :type headers: dict
        :var url: URL for the request
        :type url: str
        :var response: response from the request
        :type response: :class:`requests.Response`
        :return: installation access token
        :rtype: str
        """
        installation_id = github_config().get("installation_id")
        if not installation_id:
            return None

        jwt_token = self.jwt_token()
        if not jwt_token:
            return None

        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Accept": "application/vnd.github.v3+json",
        }
        url = (
            f"https://api.github.com/app/installations/{installation_id}/access_tokens"
        )
        response = requests.post(url, headers=headers)
        return response.json().get("token") if response.status_code == 201 else None

    def client(self):
        """Get authenticated GitHub client using GitHub bot.

        :var token: installation access token
        :type token: str
        :return: authenticated GitHub client
        :rtype: :class:`github.Github`
        """
        token = self.installation_token()
        return Github(token) if token else None


class GithubProvider(BaseIssueProvider):
    """GitHub provider implementation."""

    name = "github"

    def _get_client(self, issue_tracker_api_token=None):
        """Get GitHub client.

        :param issue_tracker_api_token: if provided, token used for client instantiation
        :type issue_tracker_api_token: str
        :var client: GitHub bot client instance
        :type client: :class:`github.Github`
        :var auth: GitHub authentication token instance
        :type auth: :class:`github.Auth.Token`
        :return: GitHub client instance
        :rtype: :class:`github.Github`
        """
        if issue_tracker_api_token:
            auth = Auth.Token(issue_tracker_api_token)
            return Github(auth=auth)

        client = GitHubApp().client()
        if client:
            return client

        if not self.user.profile.issue_tracker_api_token:
            return False

        auth = Auth.Token(self.user.profile.issue_tracker_api_token)
        return Github(auth=auth)

    def _get_repository(self):
        """Get GitHub repository.

        :return: GitHub repository instance
        :rtype: :class:`github.Repository.Repository`
        """
        return (
            self.client.get_repo(
                f"{settings.ISSUE_TRACKER_OWNER}/{settings.ISSUE_TRACKER_NAME}"
            )
            if self.client
            else None
        )

    def _close_issue_with_labels_impl(self, issue_number, labels_to_set, comment):
        """Close GitHub issue with labels.

        :param issue_number: unique issue's number
        :type issue_number: int
        :param labels_to_set: collection of GitHub labels to set to the issue
        :type labels_to_set: list
        :param comment: text to add as a GitHub comment
        :type comment: str
        :var issue: GitHub issue instance
        :type issue: :class:`github.Issue.Issue`
        :return: operation result
        :rtype: dict
        """
        issue = self.repo.get_issue(issue_number)
        if labels_to_set:
            issue.set_labels(*labels_to_set)

        if comment:
            issue.create_comment(comment)

        issue.edit(state="closed")
        return {
            "message": f"Closed issue #{issue_number} with labels {labels_to_set}",
            "issue_state": issue.state,
            "current_labels": [label.name for label in issue.labels],
        }

    def _create_issue_impl(self, title, body, labels):
        """Create GitHub issue.

        :param title: issue's title
        :type title: str
        :param body: formatted issue's body text
        :type body: str
        :param labels: collection of GitHub labels to assign to the issue
        :type labels: list
        :var issue: GitHub issue instance
        :type issue: :class:`github.Issue.Issue`
        :return: operation result
        :rtype: dict
        """
        issue = self.repo.create_issue(title=title, body=body, labels=labels or [])
        return {
            "issue_number": issue.number,
            "issue_url": issue.html_url,
            "data": issue.raw_data,
        }

    def _fetch_issues_impl(self, state, since):
        """Fetch GitHub issues.

        :param state: fetch only issues with this state
        :type state: str
        :param since: fetch only issues that have been updated after this date
        :type since: :class:`datetime.datetime`
        :return: collection of GitHub issue instances
        :rtype: :class:`github.PaginatedList`
        """
        return self.repo.get_issues(
            state=state, sort="updated", direction="asc", since=since
        )

    def _get_issue_by_number_impl(self, issue_number):
        """Retrieve the GitHub issue defined by `issue_number`.

        :param issue_number: unique issue's number
        :type issue_number: int
        :var issue: GitHub issue instance
        :type issue: :class:`github.Issue.Issue`
        :var issue_data: dictionary with relevant issue information
        :type issue_data: dict
        :return: operation result
        :rtype: dict
        """
        issue = self.repo.get_issue(issue_number)
        issue_data = {
            "number": issue.number,
            "title": issue.title,
            "body": issue.body,
            "state": issue.state,
            "created_at": issue.created_at,
            "updated_at": issue.updated_at,
            "closed_at": issue.closed_at,
            "labels": [label.name for label in issue.labels],
            "assignees": [assignee.login for assignee in issue.assignees],
            "user": issue.user.login if issue.user else None,
            "html_url": issue.html_url,
            "comments": issue.comments,
        }
        return {
            "message": f"Retrieved issue #{issue_number}",
            "issue": issue_data,
        }

    def _issue_url_impl(self, issue_number):
        """Get URL of the GitHub issue defined by provided `issue_number`.

        :param issue_number: unique issue identifier
        :type issue_number: int
        :return: full URL to the issue
        :rtype: str
        """
        return (
            f"https://github.com/{settings.ISSUE_TRACKER_OWNER}/"
            f"{settings.ISSUE_TRACKER_NAME}/issues/{issue_number}"
        )

    def _set_labels_to_issue_impl(self, issue_number, labels_to_set):
        """Add provided `labels` to the GitHub issue defined by `issue_number`.

        :param issue_number: unique issue's number
        :type issue_number: int
        :param labels_to_set: collection of GitHub labels to add to the issue
        :type labels_to_set: list
        :var issue: GitHub issue instance
        :type issue: :class:`github.Issue.Issue`
        :return: operation result
        :rtype: dict
        """
        issue = self.repo.get_issue(issue_number)
        issue.set_labels(*labels_to_set)
        issue = self.repo.get_issue(issue_number)
        return {
            "message": f"Added labels {labels_to_set} to issue #{issue_number}",
            "current_labels": [label.name for label in issue.labels],
        }
