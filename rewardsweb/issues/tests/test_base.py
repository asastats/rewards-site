"""Testing module for :py:mod:`issues.base` module."""

import json

import pytest
from django.http import JsonResponse

from issues.base import BaseIssueProvider, BaseWebhookHandler


class DummyBaseIssueProvider(BaseIssueProvider):

    def _get_client(self, issue_tracker_api_token):
        super()._get_client(issue_tracker_api_token)
        return f"{issue_tracker_api_token}"

    def _get_repository(self):
        super()._get_repository()
        return "repo"

    def _close_issue_with_labels_impl(self, issue_number, labels_to_set, comment):
        super()._close_issue_with_labels_impl(issue_number, labels_to_set, comment)
        return f"{issue_number} {labels_to_set} {comment}"

    def _create_issue_impl(self, title, body, labels):
        super()._create_issue_impl(title, body, labels)
        return f"title: {title}, body: {body} labels:{labels}"

    def _fetch_issues_impl(self, state, since):
        super()._fetch_issues_impl(state, since)
        return f"state: {state} since: {since}"

    def _get_issue_by_number_impl(self, issue_number):
        super()._get_issue_by_number_impl(issue_number)
        return issue_number

    def _issue_url_impl(self, issue_number):
        super()._issue_url_impl(issue_number)
        return issue_number

    def _set_labels_to_issue_impl(self, issue_number, labels_to_set):
        super()._set_labels_to_issue_impl(issue_number, labels_to_set)
        return f"issue_number: {issue_number} labels_to_set: {labels_to_set}"


class TestBaseIssueProvider:
    """Testing class for :class:`issues.base.BaseIssueProvider` interface."""

    def test_issues_base_baseissueprovider_is_abstract(self):
        with pytest.raises(TypeError) as exc_info:
            BaseIssueProvider()

        assert "Can't instantiate abstract class" in str(exc_info.value)

    def test_issues_base_baseissueprovider_get_client(self):
        c = DummyBaseIssueProvider(None)
        assert c._get_client("ABC") == "ABC"

    def test_issues_base_baseissueprovider_get_repository(self):
        c = DummyBaseIssueProvider(None)
        assert c._get_repository() == "repo"

    def test_issues_base_baseissueprovider_close_issue_with_labels_impl(self):
        c = DummyBaseIssueProvider(None)
        assert (
            c._close_issue_with_labels_impl("issue_number", "labels_to_set", "comment")
            == "issue_number labels_to_set comment"
        )

    def test_issues_base_baseissueprovider_create_issue_impl(self):
        c = DummyBaseIssueProvider(None)
        assert (
            c._create_issue_impl("title", "body", "labels")
            == "title: title, body: body labels:labels"
        )

    def test_issues_base_baseissueprovider_fetch_issues_impl(self):
        c = DummyBaseIssueProvider(None)
        assert c._fetch_issues_impl("state", "since") == "state: state since: since"

    def test_issues_base_baseissueprovider_get_issue_by_number_impl(self):
        c = DummyBaseIssueProvider(None)
        assert c._get_issue_by_number_impl("issue_number") == "issue_number"

    def test_issues_base_baseissueprovider_issue_url_impl(self):
        c = DummyBaseIssueProvider(None)
        assert c._issue_url_impl("issue_number") == "issue_number"

    def test_issues_base_baseissueprovider_set_labels_to_issue_impl(self):
        c = DummyBaseIssueProvider(None)
        assert (
            c._set_labels_to_issue_impl("issue_number", "labels_to_set")
            == "issue_number: issue_number labels_to_set: labels_to_set"
        )


class TestIssuesBaseBaseIssueProvider:
    """Testing class for :py:mod:`issues.base.BaseIssueProvider` class."""

    @pytest.mark.parametrize(
        "attr",
        ["name", "user", "client", "repo"],
    )
    def test_issues_base_baseissueprovider_inits_attribute_as_none(self, attr):
        assert getattr(BaseIssueProvider, attr) is None


class DummyBaseWebhookHandler(BaseWebhookHandler):
    """Dummy implementation for testing BaseWebhookHandler."""

    def validate(self):
        """Dummy validation that always returns True."""
        return True

    def extract_issue_data(self):
        """Dummy extraction that returns sample issue data."""
        return {"title": "Test Issue", "issue_number": 123, "username": "testuser"}


class InvalidDummyWebhookHandler(BaseWebhookHandler):
    """Dummy implementation with validation failure."""

    def validate(self):
        """Always fails validation."""
        return False

    def extract_issue_data(self):
        """Should not be called due to validation failure."""
        return None


class NoIssueDummyWebhookHandler(BaseWebhookHandler):
    """Dummy implementation with no issue data."""

    def validate(self):
        """Always passes validation."""
        return True

    def extract_issue_data(self):
        """Returns None to simulate non-issue webhook event."""
        return None


class TestBaseWebhookHandler:
    """Testing class for :class:`issues.base.BaseWebhookHandler` interface."""

    def test_issues_base_basewebhookhandler_is_abstract(self, mocker):
        """Test that BaseWebhookHandler cannot be instantiated directly."""
        with pytest.raises(TypeError) as exc_info:
            BaseWebhookHandler(mocker.MagicMock())

        assert "Can't instantiate abstract class" in str(exc_info.value)

    def test_issues_base_basewebhookhandler_init_with_valid_json(self, mocker):
        """Test initialization with valid JSON payload."""
        request = mocker.MagicMock()
        request.body = json.dumps({"test": "data"}).encode("utf-8")
        handler = DummyBaseWebhookHandler(request)
        assert handler.request == request
        assert handler.payload == {"test": "data"}

    def test_issues_base_basewebhookhandler_init_with_invalid_json(self, mocker):
        """Test initialization with invalid JSON payload."""
        request = mocker.MagicMock()
        request.body = b"invalid json"
        handler = DummyBaseWebhookHandler(request)
        assert handler.request == request
        assert handler.payload is None

    def test_issues_base_basewebhookhandler_init_with_decode_error(self, mocker):
        """Test initialization with undecodable body."""
        request = mocker.MagicMock()
        request.body = b"\xff\xfe"  # Invalid UTF-8
        handler = DummyBaseWebhookHandler(request)
        assert handler.request == request
        assert handler.payload is None

    def test_issues_base_basewebhookhandler_process_webhook_success(self, mocker):
        """Test successful webhook processing."""
        request = mocker.MagicMock()
        request.body = json.dumps({"test": "data"}).encode("utf-8")
        handler = DummyBaseWebhookHandler(request)
        response = handler.process_webhook()

        assert isinstance(response, JsonResponse)
        assert response.status_code == 200
        response_data = json.loads(response.content)
        assert response_data["status"] == "success"
        assert response_data["provider"] == "DummyBaseWebhookHandler"
        assert response_data["issue_title"] == "Test Issue"
        assert response_data["issue_number"] == 123
        assert response_data["username"] == "testuser"

    def test_issues_base_basewebhookhandler_process_webhook_validation_failure(
        self, mocker
    ):
        """Test webhook processing with validation failure."""
        request = mocker.MagicMock()
        request.body = json.dumps({"test": "data"}).encode("utf-8")
        handler = InvalidDummyWebhookHandler(request)
        response = handler.process_webhook()

        assert isinstance(response, JsonResponse)
        assert response.status_code == 403
        response_data = json.loads(response.content)
        assert response_data["status"] == "error"
        assert "Webhook validation failed" in response_data["message"]
        assert response_data["provider"] == "InvalidDummyWebhookHandler"

    def test_issues_base_basewebhookhandler_process_webhook_no_issue(self, mocker):
        """Test webhook processing for non-issue events."""
        request = mocker.MagicMock()
        request.body = json.dumps({"test": "data"}).encode("utf-8")
        handler = NoIssueDummyWebhookHandler(request)
        response = handler.process_webhook()

        assert isinstance(response, JsonResponse)
        assert response.status_code == 200
        response_data = json.loads(response.content)
        assert response_data["status"] == "success"
        assert response_data["message"] == "Not an issue creation event"
        assert response_data["provider"] == "NoIssueDummyWebhookHandler"
        assert "issue_title" not in response_data
        assert "issue_number" not in response_data
        assert "username" not in response_data

    def test_issues_base_basewebhookhandler_success_response_with_data(self, mocker):
        """Test _success_response method with issue data."""
        request = mocker.MagicMock()
        request.body = json.dumps({"test": "data"}).encode("utf-8")
        handler = DummyBaseWebhookHandler(request)

        issue_data = {
            "title": "Test Issue",
            "issue_number": 456,
            "username": "anotheruser",
        }

        response = handler._success_response("Test message", issue_data)
        assert isinstance(response, JsonResponse)
        assert response.status_code == 200

        response_data = json.loads(response.content)
        assert response_data["status"] == "success"
        assert response_data["message"] == "Test message"
        assert response_data["provider"] == "DummyBaseWebhookHandler"
        assert response_data["issue_title"] == "Test Issue"
        assert response_data["issue_number"] == 456
        assert response_data["username"] == "anotheruser"

    def test_issues_base_basewebhookhandler_success_response_without_data(self, mocker):
        """Test _success_response method without issue data."""
        request = mocker.MagicMock()
        request.body = json.dumps({"test": "data"}).encode("utf-8")
        handler = DummyBaseWebhookHandler(request)

        response = handler._success_response("Test message")
        assert isinstance(response, JsonResponse)
        assert response.status_code == 200

        response_data = json.loads(response.content)
        assert response_data["status"] == "success"
        assert response_data["message"] == "Test message"
        assert response_data["provider"] == "DummyBaseWebhookHandler"
        assert "issue_title" not in response_data
        assert "issue_number" not in response_data
        assert "username" not in response_data

    def test_issues_base_basewebhookhandler_error_response_default_status(self, mocker):
        """Test _error_response method with default status code."""
        request = mocker.MagicMock()
        request.body = json.dumps({"test": "data"}).encode("utf-8")
        handler = DummyBaseWebhookHandler(request)

        response = handler._error_response("Error message")
        assert isinstance(response, JsonResponse)
        assert response.status_code == 403

        response_data = json.loads(response.content)
        assert response_data["status"] == "error"
        assert response_data["message"] == "Error message"
        assert response_data["provider"] == "DummyBaseWebhookHandler"

    def test_issues_base_basewebhookhandler_error_response_custom_status(self, mocker):
        """Test _error_response method with custom status code."""
        request = mocker.MagicMock()
        request.body = json.dumps({"test": "data"}).encode("utf-8")
        handler = DummyBaseWebhookHandler(request)

        response = handler._error_response("Error message", status=400)
        assert isinstance(response, JsonResponse)
        assert response.status_code == 400

        response_data = json.loads(response.content)
        assert response_data["status"] == "error"
        assert response_data["message"] == "Error message"
        assert response_data["provider"] == "DummyBaseWebhookHandler"

    def test_issues_base_basewebhookhandler_process_issue_creation(self, mocker):
        """Test _process_issue_creation method."""
        request = mocker.MagicMock()
        request.body = json.dumps({"test": "data"}).encode("utf-8")
        handler = DummyBaseWebhookHandler(request)

        issue_data = {
            "title": "Test Issue",
            "issue_number": 789,
            "username": "testuser",
        }

        response = handler._process_issue_creation(issue_data)
        assert isinstance(response, JsonResponse)
        assert response.status_code == 200

        response_data = json.loads(response.content)
        assert response_data["status"] == "success"
        assert (
            f'Issue #{issue_data["issue_number"]} processed' in response_data["message"]
        )
        assert response_data["provider"] == "DummyBaseWebhookHandler"
        assert response_data["issue_title"] == "Test Issue"
        assert response_data["issue_number"] == 789
        assert response_data["username"] == "testuser"


class TestIssuesBaseBaseWebhookHandler:
    """Testing class for :py:mod:`issues.base.BaseWebhookHandler` class."""

    def test_issues_base_basewebhookhandler_abstract_methods(self):
        """Test that abstract methods are defined."""
        assert hasattr(BaseWebhookHandler, "validate")
        assert hasattr(BaseWebhookHandler, "extract_issue_data")

        BaseWebhookHandler.validate(None)
        BaseWebhookHandler.extract_issue_data(None)
