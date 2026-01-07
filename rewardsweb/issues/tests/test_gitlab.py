"""Testing module for :py:mod:`issues.gitlab` module."""

import json
import os

from django.conf import settings

from issues.gitlab import GitlabProvider, GitLabWebhookHandler


class TestIssuesGitlabGitlabProvider:
    """Testing class for :class:`issues.gitlab.GitlabProvider`."""

    def test_issues_gitlab_gitlabprovider_inits_name(self):
        assert GitlabProvider.name == "gitlab"

    # # __init__
    def test_issues_gitlab_gitlabprovider_init_functionality(self, mocker):
        mocked_client_instance = mocker.MagicMock()
        mocked_client = mocker.patch(
            "issues.gitlab.GitlabProvider._get_client",
            return_value=mocked_client_instance,
        )
        mocked_repo_instance = mocker.MagicMock()
        mocked_repo = mocker.patch(
            "issues.gitlab.GitlabProvider._get_repository",
            return_value=mocked_repo_instance,
        )
        user = mocker.MagicMock()
        provider = GitlabProvider(user)
        assert provider.user == user
        assert provider.client == mocked_client_instance
        assert provider.repo == mocked_repo_instance
        mocked_client.assert_called_once_with(issue_tracker_api_token=None)
        mocked_repo.assert_called_once_with()

    # # _get_client
    def test_issues_gitlab_gitlabprovider_get_client_with_issue_tracker_api_token(
        self, mocker
    ):
        mocked_config = mocker.patch("issues.gitlab.gitlab_config", return_value={})
        mocked_gitlab = mocker.patch("issues.gitlab.Gitlab")
        mocker.patch("issues.gitlab.GitlabProvider._get_repository")
        issue_tracker_api_token = mocker.MagicMock()
        provider = GitlabProvider(mocker.MagicMock())
        mocked_gitlab.reset_mock()
        mocked_config.reset_mock()
        url = "https://gitlab.com"
        mocked_config = mocker.patch(
            "issues.gitlab.gitlab_config", return_value={"url": url}
        )
        returned = provider._get_client(issue_tracker_api_token=issue_tracker_api_token)
        assert returned == mocked_gitlab.return_value
        mocked_gitlab.assert_called_once_with(
            url=url, private_token=issue_tracker_api_token
        )

    def test_issues_gitlab_gitlabprovider_get_client_with_issue_tracker_token_and_url(
        self, mocker
    ):
        url = "https://mydomain.com"
        mocked_config = mocker.patch(
            "issues.gitlab.gitlab_config", return_value={"url": url}
        )
        mocked_gitlab = mocker.patch("issues.gitlab.Gitlab")
        mocker.patch("issues.gitlab.GitlabProvider._get_repository")
        issue_tracker_api_token = mocker.MagicMock()
        provider = GitlabProvider(mocker.MagicMock())
        mocked_gitlab.reset_mock()
        mocked_config.reset_mock()
        returned = provider._get_client(issue_tracker_api_token=issue_tracker_api_token)
        assert returned == mocked_gitlab.return_value
        mocked_gitlab.assert_called_once_with(
            url=url, private_token=issue_tracker_api_token
        )

    def test_issues_gitlab_gitlabprovider_get_client_with_pat(self, mocker):
        mocked_config = mocker.patch(
            "issues.gitlab.gitlab_config",
            return_value={
                "url": "https://gitlab.com",
                "private_token": "test_pat_token",
            },
        )
        mocked_gitlab = mocker.patch("issues.gitlab.Gitlab")
        mocker.patch("issues.gitlab.GitlabProvider._get_repository")
        user = mocker.MagicMock()
        user.profile.issue_tracker_api_token = None
        provider = GitlabProvider(user)
        mocked_gitlab.reset_mock()
        mocked_config.reset_mock()
        mocked_config = mocker.patch(
            "issues.gitlab.gitlab_config",
            return_value={
                "url": "https://gitlab.com",
                "private_token": "test_pat_token",
            },
        )
        returned = provider._get_client()
        mocked_gitlab.assert_called_once_with(
            url="https://gitlab.com", private_token="test_pat_token"
        )
        assert returned == mocked_gitlab.return_value

    def test_issues_gitlab_gitlabprovider_get_client_no_token(self, mocker):
        mocker.patch("issues.gitlab.GitlabProvider._get_repository")
        mocked_config = mocker.patch("issues.gitlab.gitlab_config", return_value={})
        mock_user = mocker.MagicMock()
        mock_user.profile.issue_tracker_api_token = None
        provider = GitlabProvider(mock_user)
        mocked_config.reset_mock()
        assert provider._get_client() is None

    def test_issues_gitlab_gitlabprovider_get_client_functionality(self, mocker):
        mocker.patch("issues.gitlab.GitlabProvider._get_repository")
        mocked_config = mocker.patch(
            "issues.gitlab.gitlab_config",
            return_value={"url": "https://gitlab.com", "private_token": ""},
        )
        mocked_gitlab = mocker.patch("issues.gitlab.Gitlab")
        mocker.patch.dict(os.environ, {}, clear=True)
        mock_user = mocker.MagicMock()
        token = mocker.MagicMock()
        mock_user.profile.issue_tracker_api_token = token
        provider = GitlabProvider(mock_user)
        mocked_gitlab.reset_mock()
        mocked_config.reset_mock()
        mocked_config = mocker.patch(
            "issues.gitlab.gitlab_config",
            return_value={"url": "https://gitlab.com", "private_token": ""},
        )
        returned = provider._get_client()
        assert returned == mocked_gitlab.return_value
        mocked_gitlab.assert_called_once_with(
            url="https://gitlab.com", private_token=token
        )

    # # _get_repository
    def test_issues_gitlab_gitlabprovider_get_repository_for_client_none(self, mocker):
        mocker.patch("issues.gitlab.GitlabProvider._get_client", return_value=None)
        provider = GitlabProvider(mocker.MagicMock())
        returned = provider._get_repository()
        assert returned is None

    def test_issues_gitlab_gitlabprovider_get_repository_functionality(self, mocker):
        mock_client = mocker.MagicMock()
        mocker.patch(
            "issues.gitlab.GitlabProvider._get_client", return_value=mock_client
        )
        provider = GitlabProvider(mocker.MagicMock())
        mock_client.projects.get.reset_mock()
        returned = provider._get_repository()
        assert returned == mock_client.projects.get.return_value
        mock_client.projects.get.assert_called_once_with(
            f"{settings.ISSUE_TRACKER_OWNER}/{settings.ISSUE_TRACKER_NAME}"
        )

    # # _get_project
    def test_issues_gitlab_gitlabprovider_get_project_no_project_id(self, mocker):
        mocker.patch(
            "issues.gitlab.gitlab_config",
            return_value={},
        )
        mocker.patch(
            "issues.gitlab.GitlabProvider._get_client",
            return_value=mocker.MagicMock(),
        )
        mocker.patch("issues.gitlab.GitlabProvider._get_repository", return_value=None)
        provider = GitlabProvider(mocker.MagicMock())
        assert provider._get_project() is None

    def test_issues_gitlab_gitlabprovider_get_project_functionality(self, mocker):
        mocker.patch(
            "issues.gitlab.gitlab_config",
            return_value={
                "project_id": "test_project_id",
            },
        )
        mock_client = mocker.MagicMock()
        mocker.patch(
            "issues.gitlab.GitlabProvider._get_client", return_value=mock_client
        )
        provider = GitlabProvider(mocker.MagicMock())
        mock_client.projects.get.reset_mock()
        returned = provider._get_project()
        assert returned == mock_client.projects.get.return_value
        mock_client.projects.get.assert_called_once_with("test_project_id")

    # # _close_issue_with_labels_impl
    def test_issues_gitlab_gitlabprovider_close_issue_with_labels_impl(self, mocker):
        mocker.patch("issues.gitlab.GitlabProvider._get_client")
        mocker.patch("issues.gitlab.GitlabProvider._get_repository")
        user = mocker.MagicMock()
        provider = GitlabProvider(user)
        mock_issue = mocker.MagicMock()
        # Use PropertyMock to assert labels attribute setting
        mock_labels_property = mocker.PropertyMock()
        type(mock_issue).labels = mock_labels_property
        provider.repo = mocker.MagicMock()
        provider.repo.issues.get.return_value = mock_issue
        labels_to_set = ["bug", "critical"]
        comment = "Closing this issue."
        result = provider._close_issue_with_labels_impl(1, labels_to_set, comment)
        provider.repo.issues.get.assert_called_once_with(1)
        mock_issue.labels = labels_to_set
        mock_issue.notes.create.assert_called_once_with({"body": comment})
        mock_issue.state_event = "close"
        mock_issue.save.assert_called_once()
        assert result["issue_state"] == mock_issue.state
        assert result["current_labels"] == mock_issue.labels

    def test_issues_gitlab_gitlabprovider_close_issue_with_labels_impl_no_labels(
        self, mocker
    ):
        mocker.patch("issues.gitlab.GitlabProvider._get_client")
        mocker.patch("issues.gitlab.GitlabProvider._get_repository")
        user = mocker.MagicMock()
        provider = GitlabProvider(user)
        mock_issue = mocker.MagicMock()
        mock_issue.labels = []  # Initialize labels as an empty list
        provider.repo = mocker.MagicMock()
        provider.repo.issues.get.return_value = mock_issue
        comment = "Closing this issue."
        provider._close_issue_with_labels_impl(1, None, comment)
        assert mock_issue.labels == []

    def test_issues_gitlab_gitlabprovider_close_issue_with_labels_impl_no_comment(
        self, mocker
    ):
        mocker.patch("issues.gitlab.GitlabProvider._get_client")
        mocker.patch("issues.gitlab.GitlabProvider._get_repository")
        user = mocker.MagicMock()
        provider = GitlabProvider(user)
        mock_issue = mocker.MagicMock()
        provider.repo = mocker.MagicMock()
        provider.repo.issues.get.return_value = mock_issue
        labels_to_set = ["bug", "critical"]
        provider._close_issue_with_labels_impl(1, labels_to_set, None)
        mock_issue.notes.create.assert_not_called()

    # # _create_issue_impl
    def test_issues_gitlab_gitlabprovider_create_issue_impl(self, mocker):
        mocker.patch("issues.gitlab.GitlabProvider._get_client")
        mocker.patch("issues.gitlab.GitlabProvider._get_repository")
        user = mocker.MagicMock()
        provider = GitlabProvider(user)
        mock_issue = mocker.MagicMock()
        provider.repo = mocker.MagicMock()
        provider.repo.issues.create.return_value = mock_issue
        title = "New GitLab Issue"
        body = "Description of the issue."
        labels = ["feature"]
        result = provider._create_issue_impl(title, body, labels)
        provider.repo.issues.create.assert_called_once_with(
            {"title": title, "description": body, "labels": labels}
        )
        assert result["issue_number"] == mock_issue.iid
        assert result["issue_url"] == mock_issue.web_url

    # # _fetch_issues_impl
    def test_issues_gitlab_gitlabprovider_fetch_issues_impl(self, mocker):
        mocker.patch("issues.gitlab.GitlabProvider._get_client")
        mocker.patch("issues.gitlab.GitlabProvider._get_repository")
        user = mocker.MagicMock()
        provider = GitlabProvider(user)
        mock_issues_list = mocker.MagicMock()
        provider.repo = mocker.MagicMock()
        provider.repo.issues.list.return_value = mock_issues_list
        state = "opened"
        since = mocker.MagicMock()
        result = provider._fetch_issues_impl(state, since)
        provider.repo.issues.list.assert_called_once_with(
            state=state, sort="updated_at", since=since
        )
        assert result == mock_issues_list

    # # _get_issue_by_number_impl
    def test_issues_gitlab_gitlabprovider_get_issue_by_number_impl(self, mocker):
        mocker.patch("issues.gitlab.GitlabProvider._get_client")
        mocker.patch("issues.gitlab.GitlabProvider._get_repository")
        user = mocker.MagicMock()
        provider = GitlabProvider(user)
        mock_issue = mocker.MagicMock()
        mock_issue.iid = 1
        mock_issue.title = "GitLab Issue"
        mock_issue.description = "Desc"
        mock_issue.state = "opened"
        mock_issue.created_at = "2023-01-01"
        mock_issue.updated_at = "2023-01-02"
        mock_issue.closed_at = None
        mock_issue.labels = ["label_gl"]
        mock_issue.assignees = [{"username": "gl_user1"}]
        mock_issue.author = {"username": "gl_author"}
        mock_issue.web_url = "http://gitlab.com/issue/1"
        mock_issue.notes.list.return_value = [mocker.MagicMock()]
        provider.repo = mocker.MagicMock()
        provider.repo.issues.get.return_value = mock_issue
        result = provider._get_issue_by_number_impl(1)
        provider.repo.issues.get.assert_called_once_with(1)
        assert result["issue"]["number"] == mock_issue.iid
        assert result["issue"]["title"] == mock_issue.title

    def test_issues_gitlab_gitlabprovider_get_issue_by_number_impl_with_assignees(
        self, mocker
    ):
        mocker.patch("issues.gitlab.GitlabProvider._get_client")
        mocker.patch("issues.gitlab.GitlabProvider._get_repository")
        user = mocker.MagicMock()
        provider = GitlabProvider(user)
        mock_issue = mocker.MagicMock()
        mock_issue.iid = 1
        mock_issue.title = "GitLab Issue With Assignees"
        mock_issue.description = "Desc"
        mock_issue.state = "opened"
        mock_issue.created_at = "2023-01-01"
        mock_issue.updated_at = "2023-01-02"
        mock_issue.closed_at = None
        mock_issue.labels = ["label_gl"]
        mock_issue.assignees = [{"username": "gl_user1"}, {"username": "gl_user2"}]
        mock_issue.author = {"username": "gl_author"}
        mock_issue.web_url = "http://gitlab.com/issue/1"
        mock_issue.notes.list.return_value = [mocker.MagicMock()]
        provider.repo = mocker.MagicMock()
        provider.repo.issues.get.return_value = mock_issue
        result = provider._get_issue_by_number_impl(1)
        assert result["issue"]["assignees"] == ["gl_user1", "gl_user2"]

    # # _issue_url_impl
    def test_issues_gitlab_gitlabprovider_issue_url_impl(self, mocker):
        mocker.patch("issues.gitlab.GitlabProvider._get_client")
        mocker.patch("issues.gitlab.GitlabProvider._get_repository")
        provider = GitlabProvider(mocker.MagicMock())
        result = provider._issue_url_impl(10)
        assert result == (
            f"https://gitlab.com/{settings.ISSUE_TRACKER_OWNER}/"
            f"{settings.ISSUE_TRACKER_NAME}/-/issues/10"
        )

    # # _set_labels_to_issue_impl
    def test_issues_gitlab_gitlabprovider_set_labels_to_issue_impl(self, mocker):
        mocker.patch("issues.gitlab.GitlabProvider._get_client")
        mocker.patch("issues.gitlab.GitlabProvider._get_repository")
        user = mocker.MagicMock()
        provider = GitlabProvider(user)
        mock_issue = mocker.MagicMock()
        provider.repo = mocker.MagicMock()
        provider.repo.issues.get.return_value = mock_issue
        labels_to_set = ["priority::high"]
        result = provider._set_labels_to_issue_impl(1, labels_to_set)
        mock_issue.labels = labels_to_set
        mock_issue.save.assert_called_once()
        assert result["current_labels"] == labels_to_set


class TestIssuesGitlabGitlabWebhookHandler:
    """Testing class for :py:mod:`issues.gitlab.GitLabWebhookHandler` class."""

    # # __init__
    def test_issues_gitlab_gitlabwebhookhandler_init(self, mocker):
        """Test initialization of GitLabWebhookHandler."""
        request = mocker.MagicMock()
        request.body = json.dumps({"test": "data"}).encode("utf-8")
        handler = GitLabWebhookHandler(request)
        assert handler.request == request
        assert handler.payload == {"test": "data"}

    # # extract_issue_data
    def test_issues_gitlab_gitlabwebhookhandler_extract_issue_data_no_payload(
        self, mocker
    ):
        """Test extract_issue_data when payload is None."""
        request = mocker.MagicMock()
        request.body = b"invalid_json"
        handler = GitLabWebhookHandler(request)
        handler.payload = {}
        result = handler.extract_issue_data()
        assert result is None

    def test_issues_gitlab_gitlabwebhookhandler_extract_issue_data_no_object_attributes(
        self, mocker
    ):
        """Test extract_issue_data when payload is None."""
        request = mocker.MagicMock()
        request.body = b"invalid_json"
        handler = GitLabWebhookHandler(request)
        handler.payload = {}
        result = handler.extract_issue_data()
        assert result is None

    def test_issues_gitlab_gitlabwebhookhandler_extract_issue_data_issue_open(
        self, mocker
    ):
        """Test extract_issue_data for issue open event."""
        payload = {
            "object_kind": "issue",
            "object_attributes": {
                "action": "open",
                "iid": 123,
                "title": "Test Issue",
                "description": "Issue description",
                "url": "https://gitlab.com/test/repo/issues/123",
                "created_at": "2023-01-01T00:00:00Z",
                "author": {"username": "testuser"},
            },
            "project": {"id": 456, "name": "test-project"},
        }
        request = mocker.MagicMock()
        request.body = json.dumps(payload).encode("utf-8")
        handler = GitLabWebhookHandler(request)
        result = handler.extract_issue_data()
        assert result is not None
        assert result["issue_number"] == 123
        assert result["comment"] == "Test Issue"
        assert result["body"] == "Issue description"
        assert result["raw_content"] == "Issue description"
        assert result["username"] == "g@testuser"
        assert result["url"] == "https://gitlab.com/test/repo/issues/123"
        assert result["project_id"] == 456
        assert result["project_name"] == "test-project"
        assert result["created_at"] == "2023-01-01T00:00:00Z"

    def test_issues_gitlab_gitlabwebhookhandler_extract_issue_data_wrong_object_kind(
        self, mocker
    ):
        """Test extract_issue_data for wrong object_kind."""
        payload = {
            "object_kind": "merge_request",  # Not issue
            "object_attributes": {
                "action": "open",
                "iid": 123,
                "title": "Test MR",
                "description": "MR description",
                "url": "https://gitlab.com/test/repo/merge_requests/123",
                "created_at": "2023-01-01T00:00:00Z",
                "author": {"username": "testuser"},
            },
            "project": {"id": 456, "name": "test-project"},
        }
        request = mocker.MagicMock()
        request.body = json.dumps(payload).encode("utf-8")
        handler = GitLabWebhookHandler(request)
        result = handler.extract_issue_data()
        assert result is None

    def test_issues_gitlab_gitlabwebhookhandler_extract_issue_data_wrong_action(
        self, mocker
    ):
        """Test extract_issue_data for wrong action."""
        payload = {
            "object_kind": "issue",
            "object_attributes": {
                "action": "close",  # Not open
                "iid": 123,
                "title": "Test Issue",
                "description": "Issue description",
                "url": "https://gitlab.com/test/repo/issues/123",
                "created_at": "2023-01-01T00:00:00Z",
                "author": {"username": "testuser"},
            },
            "project": {"id": 456, "name": "test-project"},
        }
        request = mocker.MagicMock()
        request.body = json.dumps(payload).encode("utf-8")
        handler = GitLabWebhookHandler(request)
        result = handler.extract_issue_data()
        assert result is None

    def test_issues_gitlab_gitlabwebhookhandler_extract_issue_data_missing_action(
        self, mocker
    ):
        """Test extract_issue_data when action is missing."""
        payload = {
            "object_kind": "issue",
            "object_attributes": {
                "iid": 123,
                "title": "Test Issue",
                "description": "Issue description",
                "url": "https://gitlab.com/test/repo/issues/123",
                "created_at": "2023-01-01T00:00:00Z",
                "author": {"username": "testuser"},
            },
            "project": {"id": 456, "name": "test-project"},
        }
        request = mocker.MagicMock()
        request.body = json.dumps(payload).encode("utf-8")
        handler = GitLabWebhookHandler(request)
        result = handler.extract_issue_data()
        assert result is None

    def test_issues_gitlab_gitlabwebhookhandler_extract_issue_data_empty_object_attributes(
        self, mocker
    ):
        """Test extract_issue_data when object_attributes is empty."""
        payload = {
            "object_kind": "issue",
            "object_attributes": {},
            "project": {"id": 456, "name": "test-project"},
        }
        request = mocker.MagicMock()
        request.body = json.dumps(payload).encode("utf-8")
        handler = GitLabWebhookHandler(request)
        result = handler.extract_issue_data()
        assert result is None

    def test_issues_gitlab_gitlabwebhookhandler_extract_issue_data_missing_fields(
        self, mocker
    ):
        """Test extract_issue_data with missing fields in payload."""
        payload = {
            "object_kind": "issue",
            "object_attributes": {
                "action": "open",
                "iid": 123,
                "title": "Test Issue",
                # Missing description, url, created_at, author
            },
            "project": {},  # Missing id and name
        }
        request = mocker.MagicMock()
        request.body = json.dumps(payload).encode("utf-8")
        handler = GitLabWebhookHandler(request)
        result = handler.extract_issue_data()
        assert result is not None  # Should return dict with default values
        assert result["issue_number"] == 123
        assert result["comment"] == "Test Issue"
        assert result["body"] == ""  # Default empty string
        assert result["raw_content"] == ""  # Default empty string
        assert result["username"] == ""  # Default empty string
        assert result["url"] == ""  # Default empty string
        assert result["project_id"] is None  # Default None
        assert result["project_name"] == ""  # Default empty string
        assert result["created_at"] == ""  # Default empty string

    def test_issues_gitlab_gitlabwebhookhandler_extract_issue_data_no_project(
        self, mocker
    ):
        """Test extract_issue_data when project is missing."""
        payload = {
            "object_kind": "issue",
            "object_attributes": {
                "action": "open",
                "iid": 123,
                "title": "Test Issue",
                "description": "Issue description",
                "url": "https://gitlab.com/test/repo/issues/123",
                "created_at": "2023-01-01T00:00:00Z",
                "author": {"username": "testuser"},
            },
            # No project key
        }
        request = mocker.MagicMock()
        request.body = json.dumps(payload).encode("utf-8")
        handler = GitLabWebhookHandler(request)
        result = handler.extract_issue_data()
        assert result is not None
        assert result["issue_number"] == 123
        assert result["comment"] == "Test Issue"
        assert result["project_id"] is None
        assert result["project_name"] == ""

    # # process_webhook
    def test_issues_gitlab_gitlabwebhookhandler_process_webhook_success(self, mocker):
        """Test complete webhook processing for successful case."""
        payload = {
            "object_kind": "issue",
            "object_attributes": {
                "action": "open",
                "iid": 123,
                "title": "Test Issue",
                "description": "Issue description",
                "url": "https://gitlab.com/test/repo/issues/123",
                "created_at": "2023-01-01T00:00:00Z",
                "author": {"username": "testuser"},
            },
            "project": {"id": 456, "name": "test-project"},
        }
        request = mocker.MagicMock()
        request.body = json.dumps(payload).encode("utf-8")
        request.headers = {}  # No token needed since no secret
        mocker.patch("issues.gitlab.GitLabWebhookHandler.validate", return_value=True)
        mocker.patch("requests.post")
        handler = GitLabWebhookHandler(request)
        response = handler.process_webhook()
        assert response.status_code == 200
        response_data = json.loads(response.content)
        assert response_data["status"] == "success"
        assert response_data["provider"] == "GitLabWebhookHandler"
        assert response_data["issue_title"] == "Test Issue"
        assert response_data["issue_number"] == 123
        assert response_data["username"] == "g@testuser"

    def test_issues_gitlab_gitlabwebhookhandler_process_webhook_validation_failed(
        self, mocker
    ):
        """Test webhook processing when validation fails."""
        mocker.patch("issues.gitlab.os.getenv", return_value="expected_token")
        request = mocker.MagicMock()
        request.body = b"test_body"
        request.headers = {}  # No X-Gitlab-Token
        handler = GitLabWebhookHandler(request)
        response = handler.process_webhook()
        assert response.status_code == 403
        response_data = json.loads(response.content)
        assert response_data["status"] == "error"
        assert "Webhook validation failed" in response_data["message"]

    def test_issues_gitlab_gitlabwebhookhandler_process_webhook_no_issue_data(
        self, mocker
    ):
        """Test webhook processing when no issue data is found."""
        payload = {
            "object_kind": "issue",
            "object_attributes": {
                "action": "close",  # Not open
                "iid": 123,
                "title": "Test Issue",
                "description": "Issue description",
                "url": "https://gitlab.com/test/repo/issues/123",
                "created_at": "2023-01-01T00:00:00Z",
                "author": {"username": "testuser"},
            },
            "project": {"id": 456, "name": "test-project"},
        }
        request = mocker.MagicMock()
        request.body = json.dumps(payload).encode("utf-8")
        request.headers = {}
        mocker.patch("issues.gitlab.GitLabWebhookHandler.validate", return_value=True)
        handler = GitLabWebhookHandler(request)
        response = handler.process_webhook()
        assert response.status_code == 200
        response_data = json.loads(response.content)
        assert response_data["status"] == "success"
        assert response_data["message"] == "Not an issue creation event"
        assert "issue_title" not in response_data
        assert "issue_number" not in response_data

    # # validate
    def test_issues_gitlab_gitlabwebhookhandler_validate_no_token_configured(
        self, mocker
    ):
        """Test validation when no ISSUES_WEBHOOK_SECRET is configured."""
        mocker.patch("issues.gitlab.os.getenv", return_value=None)
        request = mocker.MagicMock()
        request.body = json.dumps({"test": "data"}).encode("utf-8")
        request.headers = {}  # No X-Gitlab-Token
        handler = GitLabWebhookHandler(request)
        result = handler.validate()
        assert result is True

    def test_issues_gitlab_gitlabwebhookhandler_validate_empty_token_configured(
        self, mocker
    ):
        """Test validation when empty ISSUES_WEBHOOK_SECRET is configured."""
        mocker.patch("issues.gitlab.os.getenv", return_value="")
        request = mocker.MagicMock()
        request.body = json.dumps({"test": "data"}).encode("utf-8")
        request.headers = {}  # No X-Gitlab-Token
        handler = GitLabWebhookHandler(request)
        result = handler.validate()
        assert result is True

    def test_issues_gitlab_gitlabwebhookhandler_validate_no_header_token(self, mocker):
        """Test validation when X-Gitlab-Token header is missing but token is configured."""
        mocker.patch("issues.gitlab.os.getenv", return_value="expected_token")
        request = mocker.MagicMock()
        request.body = json.dumps({"test": "data"}).encode("utf-8")
        request.headers = {}  # No X-Gitlab-Token
        handler = GitLabWebhookHandler(request)
        result = handler.validate()
        assert result is False

    def test_issues_gitlab_gitlabwebhookhandler_validate_token_mismatch(self, mocker):
        """Test validation when token doesn't match."""
        mocker.patch("issues.gitlab.os.getenv", return_value="expected_token")
        request = mocker.MagicMock()
        request.body = json.dumps({"test": "data"}).encode("utf-8")
        request.headers = {"X-Gitlab-Token": "wrong_token"}
        handler = GitLabWebhookHandler(request)
        result = handler.validate()
        assert result is False

    def test_issues_gitlab_gitlabwebhookhandler_validate_token_match(self, mocker):
        """Test validation when token matches."""
        expected_token = "expected_token"
        mocker.patch("issues.gitlab.os.getenv", return_value=expected_token)
        request = mocker.MagicMock()
        request.body = json.dumps({"test": "data"}).encode("utf-8")
        request.headers = {"X-Gitlab-Token": expected_token}
        handler = GitLabWebhookHandler(request)
        result = handler.validate()
        assert result is True
