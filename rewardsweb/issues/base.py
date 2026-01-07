"""Module containing base classes for issues and webhooks management."""

import json
import logging
from abc import ABC, abstractmethod

import requests
from django.http import JsonResponse

from trackers.config import REWARDS_API_BASE_URL
from utils.constants.core import GITHUB_ISSUES_START_DATE, REWARDS_COLLECTION
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


class BaseWebhookHandler(ABC):
    """Abstract base class for all webhook handlers.

    :var BaseWebhookHandler.request: Django HTTP request object
    :type BaseWebhookHandler.request: class:`django.http.HttpRequest`
    :var BaseWebhookHandler.payload: parsed JSON payload from request
    :type BaseWebhookHandler.payload: dict or None
    """

    def __init__(self, request):
        """Initialize webhook handler with request.

        :param request: Django HTTP request object
        :type request: class:`django.http.HttpRequest`
        """
        self.request = request
        self.payload = None
        self._parse_payload()

    def process_webhook(self):
        """Main entry point to process webhook.

        :return: HTTP response with webhook processing result
        :rtype: class:`django.http.JsonResponse`
        """
        # 1. Validate webhook
        if not self.validate():
            return self._error_response("Webhook validation failed")

        # 2. Extract and validate issue data
        issue_data = self.extract_issue_data()
        if not issue_data:
            return self._success_response("Not an issue creation event")

        # 3. Issue creation detected, proceed with processing
        return self._process_issue_creation(issue_data)

    def _parse_payload(self):
        """Parse JSON payload from request body.

        Sets self.payload to parsed JSON or None if parsing fails.
        """
        try:
            self.payload = json.loads(self.request.body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self.payload = None

    @abstractmethod
    def validate(self):
        """Validate webhook signature/token.

        :return: True if validation passes, False otherwise
        :rtype: bool
        """
        pass

    @abstractmethod
    def extract_issue_data(self):
        """Extract issue data from payload.

        :return: None if not an issue creation event, dict with issue data if it's an issue creation
        :rtype: dict or None
        """
        pass

    def _parse_type_from_labels(self, labels):
        """Return issue type from provided labels collection.

        TODO: tests

        :param labels: collection of label names
        :type labels: list
        :return: issue type
        :rtype: str
        """
        return next(
            (
                item[0]
                for label in [label.lower() for label in labels]
                for item in REWARDS_COLLECTION
                if label in item[0].lower()
            ),
            REWARDS_COLLECTION[0][0],
        )

    def _process_issue_creation(self, issue_data):
        """Process a new issue creation.

        TODO: implement, docstring, and tests

        :param issue_data: extracted issue data
        :type issue_data: dict
        :var base_url: Rewards API base endpoints URL
        :type base_url: str
        :var response: requests' response instance
        :type response: :class:`requests.Response`
        :return: response data from Rewards API
        :rtype: dict

        :return: success response with issue data
        :rtype: class:`django.http.JsonResponse`
        """

        try:
            response = requests.post(
                f"{REWARDS_API_BASE_URL}/addcontribution",
                json=issue_data,
                headers={"Content-Type": "application/json"},
                timeout=30,
            )
            response.raise_for_status()  # Raises an HTTPError for bad responses

            return self._success_response(
                f'Issue #{issue_data.get("issue_number")} processed', issue_data
            )
            # return response.json()

        except requests.exceptions.ConnectionError:
            raise Exception(
                "Cannot connect to the API server. Make sure it's running on localhost."
            )

        except requests.exceptions.HTTPError as e:
            raise Exception(
                f"API returned error: {e.response.status_code} - {e.response.text}"
            )

        except requests.exceptions.Timeout:
            raise Exception("API request timed out.")

        except requests.exceptions.RequestException as e:
            raise Exception(f"API request failed: {e}")

    def _success_response(self, message, issue_data=None):
        """Return success response.

        :param message: success message
        :type message: str
        :param issue_data: extracted issue data (optional)
        :type issue_data: dict or None
        :return: JSON success response
        :rtype: class:`django.http.JsonResponse`
        """
        response_data = {
            "status": "success",
            "message": message,
            "provider": self.__class__.__name__,
        }

        if issue_data:
            response_data.update(
                {
                    "issue_title": issue_data.get("title"),
                    "issue_number": issue_data.get("issue_number"),
                    "username": issue_data.get("username"),
                }
            )

        return JsonResponse(response_data, status=200)

    def _error_response(self, message, status=403):
        """Return error response.

        :param message: error message
        :type message: str
        :param status: HTTP status code (default: 403)
        :type status: int
        :return: JSON error response
        :rtype: class:`django.http.JsonResponse`
        """
        return JsonResponse(
            {
                "status": "error",
                "message": message,
                "provider": self.__class__.__name__,
            },
            status=status,
        )
