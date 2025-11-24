"""Module containing functions for providers' issues management."""

import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone

import jwt
import requests
from atlassian.bitbucket.cloud import Cloud
from django.conf import settings
from github import Auth, Github
from gitlab import Gitlab

from utils.constants.core import GITHUB_ISSUES_START_DATE
from utils.constants.ui import MISSING_API_TOKEN_TEXT
from utils.helpers import get_env_variable

logger = logging.getLogger(__name__)


class BitbucketApp:
    """Helper class for instantiating a Bitbucket client using a Bitbucket app."""

    def jwt_token(self):
        """Generate JWT token for a Bitbucket app.

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
        client_key = get_env_variable("BITBUCKET_CLIENT_KEY", "")
        shared_secret = get_env_variable("BITBUCKET_SHARED_SECRET", "")

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


class GitHubApp:
    """Helper class for instantiating GitHub client using GitHub bot."""

    def jwt_token(self):
        """Generate JWT token for GitHub bot.

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
        bot_private_key_filename = get_env_variable(
            "GITHUB_BOT_PRIVATE_KEY_FILENAME", ""
        )
        bot_client_id = get_env_variable("GITHUB_BOT_CLIENT_ID", "")
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
        installation_id = get_env_variable("GITHUB_BOT_INSTALLATION_ID", "")
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


class BaseIssueProvider(ABC):
    """Base provider that all providers must inherit from.

    :var BaseIssueProvider.name: name of the issue provider
    :type BaseIssueProvider.name: str
    :var BaseIssueProvider.user: Django user instance
    :type BaseIssueProvider.user: class:`django.contrib.auth.models.User`
    :var BaseIssueProvider.client: provider client instance
    :type BaseIssueProvider.client: object
    :var BaseIssueProvider.repo: repository/project instance
    :type BaseIssueProvider.repo: object
    """

    name = None
    user = None
    client = None
    repo = None

    def __init__(self, user, issue_tracker_api_token=None):
        """Initialize base provider.

        :param user: Django user instance
        :type user: class:`django.contrib.auth.models.User`
        :param issue_tracker_api_token: if provided, token used for client instantiation
        :type issue_tracker_api_token: str
        """
        self.user = user
        self.client = self._get_client(issue_tracker_api_token=issue_tracker_api_token)
        self.repo = self._get_repository()

    @abstractmethod
    def _get_client(self, issue_tracker_api_token=None):
        """Get authenticated client - must be implemented by subclasses.

        :param issue_tracker_api_token: if provided, token used for client instantiation
        :type issue_tracker_api_token: str
        :return: provider client instance
        """
        pass

    @abstractmethod
    def _get_repository(self):
        """Get repository/project - must be implemented by subclasses.

        :return: repository/project instance
        """
        pass

    @abstractmethod
    def _close_issue_with_labels_impl(self, issue_number, labels_to_set, comment):
        """Provider-specific implementation to close an issue with labels.

        :param issue_number: unique issue identifier
        :type issue_number: int
        :param labels_to_set: collection of labels to set
        :type labels_to_set: list
        :param comment: text to add as comment
        :type comment: str
        :return: operation result
        :rtype: dict
        """
        pass

    @abstractmethod
    def _create_issue_impl(self, title, body, labels):
        """Provider-specific implementation to create an issue.

        :param title: issue title
        :type title: str
        :param body: issue body
        :type body: str
        :param labels: issue labels
        :type labels: list
        :return: operation result
        :rtype: dict
        """
        pass

    @abstractmethod
    def _fetch_issues_impl(self, state, since):
        """Provider-specific implementation to fetch issues.

        :param state: issue state filter
        :type state: str
        :param since: fetch issues updated after this date
        :type since: :class:`datetime.datetime`
        :return: collection of issue instances
        :rtype: list
        """
        pass

    @abstractmethod
    def _get_issue_by_number_impl(self, issue_number):
        """Provider-specific implementation to get an issue by number.

        :param issue_number: unique issue identifier
        :type issue_number: int
        :return: formatted issue data
        :rtype: dict
        """
        pass

    @abstractmethod
    def _set_labels_to_issue_impl(self, issue_number, labels_to_set):
        """Provider-specific implementation to set labels to an issue.

        :param issue_number: unique issue identifier
        :type issue_number: int
        :param labels_to_set: collection of labels to set
        :type labels_to_set: list
        :return: operation result
        :rtype: dict
        """
        pass

    def close_issue_with_labels(self, issue_number, labels_to_set=None, comment=None):
        """Close issue with labels.

        :param issue_number: unique issue identifier
        :type issue_number: int
        :param labels_to_set: collection of labels to set
        :type labels_to_set: list
        :param comment: text to add as comment
        :type comment: str
        :var client: provider client instance
        :type client: object
        :var result: operation result from provider-specific implementation
        :type result: dict
        :return: operation result
        :rtype: dict
        """
        try:
            if not self.client:
                return {"success": False, "error": MISSING_API_TOKEN_TEXT}

            result = self._close_issue_with_labels_impl(
                issue_number, labels_to_set, comment
            )
            return {"success": True, **result}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def create_issue(self, title, body, labels=None):
        """Create issue.

        :param title: issue title
        :type title: str
        :param body: issue body
        :type body: str
        :param labels: issue labels
        :type labels: list
        :var client: provider client instance
        :type client: object
        :var result: operation result from provider-specific implementation
        :type result: dict
        :return: operation result
        :rtype: dict
        """
        try:
            if not self.client:
                return {"success": False, "error": MISSING_API_TOKEN_TEXT}

            result = self._create_issue_impl(title, body, labels)
            return {"success": True, **result}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def fetch_issues(self, state="all", since=GITHUB_ISSUES_START_DATE):
        """Fetch issues from provider.

        :param state: issue state filter
        :type state: str
        :param since: fetch issues updated after this date
        :type since: :class:`datetime.datetime`
        :var client: provider client instance
        :type client: object
        :return: collection of issue instances
        :rtype: list
        """
        try:
            if not self.client:
                return []

            return self._fetch_issues_impl(state, since)

        except Exception as e:
            logger.error(f"Error fetching issues: {e}")
            return []

    def issue_by_number(self, issue_number):
        """Get issue by number.

        :param issue_number: unique issue identifier
        :type issue_number: int
        :var client: provider client instance
        :type client: object
        :var result: formatted issue data from provider-specific implementation
        :type result: dict
        :return: operation result
        :rtype: dict
        """
        try:
            if not self.client:
                return {"success": False, "error": MISSING_API_TOKEN_TEXT}

            result = self._get_issue_by_number_impl(issue_number)
            return {"success": True, **result}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def set_labels_to_issue(self, issue_number, labels_to_set):
        """Set labels to issue.

        :param issue_number: unique issue identifier
        :type issue_number: int
        :param labels_to_set: collection of labels to set
        :type labels_to_set: list
        :var client: provider client instance
        :type client: object
        :var result: operation result from provider-specific implementation
        :type result: dict
        :return: operation result
        :rtype: dict
        """
        try:
            if not self.client:
                return {"success": False, "error": MISSING_API_TOKEN_TEXT}

            result = self._set_labels_to_issue_impl(issue_number, labels_to_set)
            return {"success": True, **result}

        except Exception as e:
            return {"success": False, "error": str(e)}


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


class GitlabProvider(BaseIssueProvider):
    """GitLab provider implementation."""

    name = "gitlab"

    def _get_client(self, issue_tracker_api_token=None):
        """Get GitLab client.

        :param issue_tracker_api_token: if provided, token used for client instantiation
        :type issue_tracker_api_token: str
        :var pat: GitLab Personal Access Token.
        :type pat: str
        :var url: GitLab instance URL.
        :type url: str
        :return: GitLab client instance.
        :rtype: :class:`gitlab.Gitlab`
        """
        url = get_env_variable("GITLAB_URL", "https://gitlab.com")
        if issue_tracker_api_token:
            return Gitlab(url=url, private_token=issue_tracker_api_token)

        pat = get_env_variable("GITLAB_PRIVATE_TOKEN", "")

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
        project_id = get_env_variable("GITLAB_PROJECT_ID", "")
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
