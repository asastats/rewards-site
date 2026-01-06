"""Module containing base classes for issues and webhooks management."""

import logging
from abc import ABC, abstractmethod

from utils.constants.core import GITHUB_ISSUES_START_DATE
from utils.constants.ui import MISSING_API_TOKEN_TEXT

logger = logging.getLogger(__name__)


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

    def _issue_url_impl(self, issue_number):
        """Provider-specific implementation to full URL to the issue defined by number.

        :param issue_number: unique issue identifier
        :type issue_number: int
        :return: full URL to the issue
        :rtype: str
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

    def issue_url(self, issue_number):
        """Get full URL of the issue defined by provided `issue_number`.

        :param issue_number: unique issue identifier
        :type issue_number: int
        :return: full URL to the issue
        :rtype: str
        """
        return self._issue_url_impl(issue_number)

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
