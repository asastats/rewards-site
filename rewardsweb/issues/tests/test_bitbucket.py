"""Testing module for :py:mod:`issues.bitbucket` module."""

import json

from django.conf import settings

from issues.bitbucket import (
    BitbucketApp,
    BitbucketProvider,
    BitbucketWebhookHandler,
)


class TestIssuesBitbucketBitbucketApp:
    """Testing class for :class:`issues.bitbucket.BitbucketApp`."""

    # # jwt_token
    def test_issues_bitbucket_bitbucketapp_jwt_token_no_env_vars(self, mocker):
        mocker.patch("issues.bitbucket.bitbucket_config", return_value={})
        instance = BitbucketApp()
        assert instance.jwt_token() is None

    def test_issues_bitbucket_bitbucketapp_jwt_token_success(self, mocker):
        mocker.patch(
            "issues.bitbucket.bitbucket_config",
            return_value={
                "client_key": "test_client_key",
                "shared_secret": "test_shared_secret",
            },
        )
        mock_datetime = mocker.MagicMock()
        mock_timedelta = mocker.MagicMock()
        mocker.patch("issues.bitbucket.datetime", mock_datetime)
        mocker.patch("issues.bitbucket.timedelta", mock_timedelta)
        mock_jwt = mocker.MagicMock()
        mocker.patch("issues.bitbucket.jwt", mock_jwt)
        instance = BitbucketApp()
        instance.jwt_token()
        mock_jwt.encode.assert_called_once()
        args, kwargs = mock_jwt.encode.call_args
        assert kwargs["algorithm"] == "HS256"
        assert "iss" in args[0]
        assert "iat" in args[0]
        assert "exp" in args[0]

    # # access_token
    def test_issues_bitbucket_bitbucketapp_access_token_no_jwt(self, mocker):
        mock_jwt_token = mocker.patch.object(
            BitbucketApp, "jwt_token", return_value=None
        )
        instance = BitbucketApp()
        assert instance.access_token() is None
        mock_jwt_token.assert_called_once_with()

    def test_issues_bitbucket_bitbucketapp_access_token_request_fails(self, mocker):
        mocker.patch.object(BitbucketApp, "jwt_token", return_value="test_jwt")
        mock_response = mocker.MagicMock()
        mock_response.status_code = 400
        mocked_requests = mocker.patch(
            "issues.bitbucket.requests.post", return_value=mock_response
        )
        instance = BitbucketApp()
        assert instance.access_token() is None
        mocked_requests.assert_called_once_with(
            "https://bitbucket.org/site/oauth2/access_token",
            headers={"Authorization": "JWT test_jwt"},
            data={"grant_type": "urn:bitbucket:oauth2:jwt"},
        )

    def test_issues_bitbucket_bitbucketapp_access_token_success(self, mocker):
        mocker.patch.object(BitbucketApp, "jwt_token", return_value="test_jwt")
        mock_response = mocker.MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "test_token"}
        mocked_requests = mocker.patch(
            "issues.bitbucket.requests.post", return_value=mock_response
        )
        instance = BitbucketApp()
        assert instance.access_token() == "test_token"
        mocked_requests.assert_called_once_with(
            "https://bitbucket.org/site/oauth2/access_token",
            headers={"Authorization": "JWT test_jwt"},
            data={"grant_type": "urn:bitbucket:oauth2:jwt"},
        )


class TestIssuesBitbucketBitbucketProvider:
    """Testing class for :py:mod:`issues.bitbucket.BitbucketProvider` class."""

    def test_issues_bitbucket_bitbucketprovider_inits_name(self):
        assert BitbucketProvider.name == "bitbucket"

    # # __init__
    def test_issues_bitbucket_bitbucketprovider_init_functionality(self, mocker):
        mocked_client = mocker.patch("issues.bitbucket.BitbucketProvider._get_client")
        mocked_repo = mocker.patch("issues.bitbucket.BitbucketProvider._get_repository")
        user = mocker.MagicMock()
        provider = BitbucketProvider(user)
        assert provider.user == user
        assert provider.client == mocked_client.return_value
        assert provider.repo == mocked_repo.return_value
        mocked_client.assert_called_once_with(issue_tracker_api_token=None)
        mocked_repo.assert_called_once_with()

    # # _get_client
    def test_issues_bitbucket_bitbucketprovider_get_client_with_provided_token(
        self, mocker
    ):
        mock_access_token = mocker.patch.object(
            BitbucketApp, "access_token", return_value="test_app_token"
        )
        mock_bitbucket_client = mocker.patch("issues.bitbucket.Cloud")
        issue_tracker_api_token = mocker.MagicMock()
        provider = BitbucketProvider(mocker.MagicMock())
        mock_access_token.reset_mock()
        mock_bitbucket_client.reset_mock()
        returned = provider._get_client(issue_tracker_api_token=issue_tracker_api_token)
        assert returned == mock_bitbucket_client.return_value
        mock_access_token.assert_not_called()
        mock_bitbucket_client.assert_called_once_with(token=issue_tracker_api_token)

    def test_issues_bitbucket_bitbucketprovider_get_client_with_app_token(self, mocker):
        mock_access_token = mocker.patch.object(
            BitbucketApp, "access_token", return_value="test_app_token"
        )
        mock_bitbucket_client = mocker.patch("issues.bitbucket.Cloud")
        provider = BitbucketProvider(mocker.MagicMock())
        mock_access_token.reset_mock()
        mock_bitbucket_client.reset_mock()
        returned = provider._get_client()
        assert returned == mock_bitbucket_client.return_value
        mock_access_token.assert_called_once_with()
        mock_bitbucket_client.assert_called_once_with(token="test_app_token")

    def test_issues_bitbucket_bitbucketprovider_get_client_with_user_token(
        self, mocker
    ):
        mocker.patch.object(BitbucketApp, "access_token", return_value=None)
        mock_bitbucket_client = mocker.patch("issues.bitbucket.Cloud")
        mock_user = mocker.MagicMock()
        mock_user.profile.issue_tracker_api_token = "test_user_token"
        provider = BitbucketProvider(user=mock_user)
        mock_bitbucket_client.reset_mock()
        returned = provider._get_client()
        assert returned == mock_bitbucket_client.return_value
        mock_bitbucket_client.assert_called_once_with(token="test_user_token")

    def test_issues_bitbucket_bitbucketprovider_get_client_no_token(self, mocker):
        mocker.patch.object(BitbucketApp, "access_token", return_value=None)
        mock_bitbucket_client = mocker.patch("issues.bitbucket.Cloud")
        provider = BitbucketProvider(user=None)
        client = provider._get_client()
        assert client is None
        mock_bitbucket_client.assert_not_called()

    # # _get_repository
    def test_issues_bitbucket_bitbucketprovider_get_repository_for_client_none(
        self, mocker
    ):
        mocker.patch(
            "issues.bitbucket.BitbucketProvider._get_client", return_value=None
        )
        provider = BitbucketProvider(mocker.MagicMock())
        returned = provider._get_repository()
        assert returned is None

    def test_issues_bitbucket_bitbucketprovider_get_repository_functionality(
        self, mocker
    ):
        mock_client = mocker.MagicMock()
        mocker.patch(
            "issues.bitbucket.BitbucketProvider._get_client", return_value=mock_client
        )
        provider = BitbucketProvider(mocker.MagicMock())
        mock_client.repositories.get.reset_mock()
        returned = provider._get_repository()
        assert returned == mock_client.repositories.get.return_value
        mock_client.repositories.get.assert_called_once_with(
            settings.ISSUE_TRACKER_OWNER, settings.ISSUE_TRACKER_NAME
        )

    # # _close_issue_with_labels_impl
    def test_issues_bitbucket_bitbucketprovider_close_issue_with_labels_impl(
        self, mocker
    ):
        mocker.patch("issues.bitbucket.BitbucketProvider._get_client")
        mocker.patch("issues.bitbucket.BitbucketProvider._get_repository")
        user = mocker.MagicMock()
        provider = BitbucketProvider(user)
        provider.repo = ("workspace", "repo_slug")
        provider.client = mocker.MagicMock()
        provider._close_issue_with_labels_impl(1, ["label1"], "comment")
        provider.client.update_issue.assert_called_once()
        provider.client.issue_comment.assert_called_once()
        provider.client.set_issue_status.assert_called_once()

    def test_issues_bitbucket_bitbucketprovider_close_issue_with_labels_impl_no_labels_or_comment(
        self, mocker
    ):
        mocker.patch("issues.bitbucket.BitbucketProvider._get_client")
        mocker.patch("issues.bitbucket.BitbucketProvider._get_repository")
        user = mocker.MagicMock()
        provider = BitbucketProvider(user)
        provider.repo = ("workspace", "repo_slug")
        provider.client = mocker.MagicMock()
        provider._close_issue_with_labels_impl(1, None, None)
        provider.client.update_issue.assert_not_called()
        provider.client.issue_comment.assert_not_called()
        provider.client.set_issue_status.assert_called_once()

    def test_issues_bitbucket_bitbucketprovider_close_issue_with_labels_impl_only_labels(
        self, mocker
    ):
        mocker.patch("issues.bitbucket.BitbucketProvider._get_client")
        mocker.patch("issues.bitbucket.BitbucketProvider._get_repository")
        user = mocker.MagicMock()
        provider = BitbucketProvider(user)
        provider.repo = ("workspace", "repo_slug")
        provider.client = mocker.MagicMock()
        provider._close_issue_with_labels_impl(1, ["label1"], None)
        provider.client.update_issue.assert_called_once_with(
            repo="repo_slug", issue_id=1, components=["label1"]
        )
        provider.client.issue_comment.assert_not_called()
        provider.client.set_issue_status.assert_called_once_with(
            repo="repo_slug", issue_id=1, status="resolved"
        )

    def test_issues_bitbucket_bitbucketprovider_close_issue_with_labels_impl_only_comment(
        self, mocker
    ):
        mocker.patch("issues.bitbucket.BitbucketProvider._get_client")
        mocker.patch("issues.bitbucket.BitbucketProvider._get_repository")
        user = mocker.MagicMock()
        provider = BitbucketProvider(user)
        provider.repo = ("workspace", "repo_slug")
        provider.client = mocker.MagicMock()
        provider._close_issue_with_labels_impl(1, None, "comment")
        provider.client.update_issue.assert_not_called()
        provider.client.issue_comment.assert_called_once_with(
            repo="repo_slug", issue_id=1, content="comment"
        )
        provider.client.set_issue_status.assert_called_once_with(
            repo="repo_slug", issue_id=1, status="resolved"
        )

    # # _create_issue_impl
    def test_issues_bitbucket_bitbucketprovider_create_issue_impl(self, mocker):
        mocker.patch("issues.bitbucket.BitbucketProvider._get_client")
        mocker.patch("issues.bitbucket.BitbucketProvider._get_repository")
        user = mocker.MagicMock()
        provider = BitbucketProvider(user)
        provider.repo = ("workspace", "repo_slug")
        provider.client = mocker.MagicMock()
        provider._create_issue_impl("title", "body", ["label1"])
        provider.client.create_issue.assert_called_once()

    def test_issues_bitbucket_bitbucketprovider_create_issue_impl_default_fields(
        self, mocker
    ):
        mocker.patch("issues.bitbucket.BitbucketProvider._get_client")
        mocker.patch("issues.bitbucket.BitbucketProvider._get_repository")
        user = mocker.MagicMock()
        provider = BitbucketProvider(user)
        provider.repo = ("workspace", "repo_slug")
        provider.client = mocker.MagicMock()
        title = "Test Title"
        body = "Test Body"
        labels = ["bug"]
        provider._create_issue_impl(title, body, labels)
        provider.client.create_issue.assert_called_once_with(
            repo="repo_slug",
            title=title,
            content=body,
            kind="bug",
            priority="major",
        )

    # # _fetch_issues_impl
    def test_issues_bitbucket_bitbucketprovider_fetch_issues_impl(self, mocker):
        mocker.patch("issues.bitbucket.BitbucketProvider._get_client")
        mocker.patch("issues.bitbucket.BitbucketProvider._get_repository")
        user = mocker.MagicMock()
        provider = BitbucketProvider(user)
        provider.repo = ("workspace", "repo_slug")
        provider.client = mocker.MagicMock()
        provider._fetch_issues_impl("all", "since")
        provider.client.get_issues.assert_called_once()

    # # _get_issue_by_number_impl
    def test_issues_bitbucket_bitbucketprovider_get_issue_by_number_impl(self, mocker):
        mocker.patch("issues.bitbucket.BitbucketProvider._get_client")
        mocker.patch("issues.bitbucket.BitbucketProvider._get_repository")
        user = mocker.MagicMock()
        provider = BitbucketProvider(user)
        provider.repo = ("workspace", "repo_slug")
        provider.client = mocker.MagicMock()
        issue = mocker.MagicMock()
        issue.assignee = None
        issue.reporter = None
        provider.client.get_issue.return_value = issue
        provider._get_issue_by_number_impl(1)
        provider.client.get_issue.assert_called_once_with(repo="repo_slug", issue_id=1)

    def test_issues_bitbucket_bitbucketprovider_get_issue_by_number_impl_resolved(
        self, mocker
    ):
        mocker.patch("issues.bitbucket.BitbucketProvider._get_client")
        mocker.patch("issues.bitbucket.BitbucketProvider._get_repository")
        user = mocker.MagicMock()
        provider = BitbucketProvider(user)
        provider.repo = ("workspace", "repo_slug")
        provider.client = mocker.MagicMock()
        issue = mocker.MagicMock()
        issue.state = "resolved"
        issue.edited_on = "some_date"
        issue.assignee = None
        issue.reporter = None
        provider.client.get_issue.return_value = issue
        result = provider._get_issue_by_number_impl(1)
        assert result["issue"]["closed_at"] == "some_date"

    def test_issues_bitbucket_bitbucketprovider_get_issue_by_number_impl_no_components(
        self, mocker
    ):
        mocker.patch("issues.bitbucket.BitbucketProvider._get_client")
        mocker.patch("issues.bitbucket.BitbucketProvider._get_repository")
        user = mocker.MagicMock()
        provider = BitbucketProvider(user)
        provider.repo = ("workspace", "repo_slug")
        provider.client = mocker.MagicMock()
        issue = mocker.MagicMock()
        # Ensure 'components' attribute does not exist
        del issue.components
        issue.assignee = None
        issue.reporter = None
        provider.client.get_issue.return_value = issue
        result = provider._get_issue_by_number_impl(1)
        assert result["issue"]["labels"] == []

    def test_issues_bitbucket_bitbucketprovider_get_issue_by_number_impl_assign_report(
        self, mocker
    ):
        mocker.patch("issues.bitbucket.BitbucketProvider._get_client")
        mocker.patch("issues.bitbucket.BitbucketProvider._get_repository")
        user = mocker.MagicMock()
        provider = BitbucketProvider(user)
        provider.repo = ("workspace", "repo_slug")
        provider.client = mocker.MagicMock()
        issue = mocker.MagicMock()
        issue.assignee = {"display_name": "test_assignee"}
        issue.reporter = {"display_name": "test_reporter"}
        provider.client.get_issue.return_value = issue
        result = provider._get_issue_by_number_impl(1)
        assert result["issue"]["assignees"] == ["test_assignee"]
        assert result["issue"]["user"] == "test_reporter"

    # # _issue_url_impl
    def test_issues_bitbucket_bitbucketprovider_issue_url_impl(self, mocker):
        mocker.patch("issues.bitbucket.BitbucketProvider._get_client")
        mocker.patch("issues.bitbucket.BitbucketProvider._get_repository")
        user = mocker.MagicMock()
        provider = BitbucketProvider(user)
        provider.repo = ("workspace", "repo_slug")
        provider.client = mocker.MagicMock()
        issue = mocker.MagicMock()
        issue.assignee = {"display_name": "test_assignee"}
        issue.reporter = {"display_name": "test_reporter"}
        provider.client.get_issue.return_value = issue
        result = provider._issue_url_impl(10)
        assert result == "https://bitbucket.org/workspace/repo_slug/issues/10/"

    # # _set_labels_to_issue_impl
    def test_issues_bitbucket_bitbucketprovider_set_labels_to_issue_impl_resolved(
        self, mocker
    ):
        mocker.patch("issues.bitbucket.BitbucketProvider._get_client")
        mocker.patch("issues.bitbucket.BitbucketProvider._get_repository")
        user = mocker.MagicMock()
        provider = BitbucketProvider(user)
        provider.repo = ("workspace", "repo_slug")
        provider.client = mocker.MagicMock()
        issue = mocker.MagicMock()
        issue.components = "components"
        provider.client.get_issue.return_value = issue
        result = provider._set_labels_to_issue_impl(100, ["label1", "label2"])
        assert "Added components" in result["message"]
        assert result["current_labels"] == "components"
        provider.client.update_issue.assert_called_once_with(
            repo="repo_slug", issue_id=100, components=["label1", "label2"]
        )
        provider.client.get_issue.assert_called_once_with(
            repo="repo_slug", issue_id=100
        )

    def test_issues_bitbucket_bitbucketprovider_set_labels_to_issue_impl_no_components(
        self, mocker
    ):
        mocker.patch("issues.bitbucket.BitbucketProvider._get_client")
        mocker.patch("issues.bitbucket.BitbucketProvider._get_repository")
        user = mocker.MagicMock()
        provider = BitbucketProvider(user)
        provider.repo = ("workspace", "repo_slug")
        provider.client = mocker.MagicMock()
        issue = (1, 2)
        provider.client.get_issue.return_value = issue
        result = provider._set_labels_to_issue_impl(100, ["label1", "label2"])
        assert "Added components" in result["message"]
        assert result["current_labels"] == []
        provider.client.update_issue.assert_called_once_with(
            repo="repo_slug", issue_id=100, components=["label1", "label2"]
        )
        provider.client.get_issue.assert_called_once_with(
            repo="repo_slug", issue_id=100
        )


class TestIssuesBitbucketBitbucketWebhookHandler:
    """Testing class for :py:mod:`issues.bitbucket.BitbucketWebhookHandler` class."""

    # # __init__
    def test_issues_bitbucket_bitbucketwebhookhandler_init(self, mocker):
        """Test initialization of BitbucketWebhookHandler."""
        request = mocker.MagicMock()
        request.body = json.dumps({"test": "data"}).encode("utf-8")
        handler = BitbucketWebhookHandler(request)
        assert handler.request == request
        assert handler.payload == {"test": "data"}

    # # validate
    def test_issues_bitbucket_bitbucketwebhookhandler_validate_no_secret(self, mocker):
        """Test validation when no ISSUES_WEBHOOK_SECRET is configured."""
        mocker.patch("issues.bitbucket.os.getenv", return_value="")
        request = mocker.MagicMock()
        request.body = b"test_body"
        request.headers = {}
        handler = BitbucketWebhookHandler(request)
        result = handler.validate()
        assert result is True

    def test_issues_bitbucket_bitbucketwebhookhandler_validate_no_signature(
        self, mocker
    ):
        """Test validation when X-Hub-Signature header is missing."""
        mocker.patch("issues.bitbucket.os.getenv", return_value="test_secret")
        request = mocker.MagicMock()
        request.body = b"test_body"
        request.headers = {}  # No X-Hub-Signature
        handler = BitbucketWebhookHandler(request)
        result = handler.validate()
        assert result is False

    def test_issues_bitbucket_bitbucketwebhookhandler_validate_signature_mismatch(
        self, mocker
    ):
        """Test validation when signature doesn't match."""
        mocker.patch("issues.bitbucket.os.getenv", return_value="test_secret")
        request = mocker.MagicMock()
        request.body = json.dumps({"test": "data"}).encode("utf-8")
        request.headers = {"X-Hub-Signature": "sha256=invalid_signature"}
        handler = BitbucketWebhookHandler(request)
        result = handler.validate()
        assert result is False

    def test_issues_bitbucket_bitbucketwebhookhandler_validate_signature_match(
        self, mocker
    ):
        """Test validation when signature matches."""
        secret = "test_secret"
        mocker.patch("issues.bitbucket.os.getenv", return_value=secret)
        # Mock hmac to return a specific digest
        mock_hmac = mocker.MagicMock()
        mock_hmac.hexdigest.return_value = "expected_digest"
        mocker.patch("issues.bitbucket.hmac.new", return_value=mock_hmac)
        request = mocker.MagicMock()
        request.body = b"test_body"
        expected_signature = "sha256=expected_digest"
        request.headers = {"X-Hub-Signature": expected_signature}
        handler = BitbucketWebhookHandler(request)
        result = handler.validate()
        assert result is True
        import issues.bitbucket

        issues.bitbucket.hmac.new.assert_called_once_with(
            secret.encode(), request.body, issues.bitbucket.hashlib.sha256
        )

    # # extract_issue_data
    def test_issues_bitbucket_bitbucketwebhookhandler_extract_issue_data_no_payload(
        self, mocker
    ):
        """Test extract_issue_data when payload is None."""
        request = mocker.MagicMock()
        request.body = b"invalid_json"
        handler = BitbucketWebhookHandler(request)
        handler.payload = {}
        result = handler.extract_issue_data()
        assert result is None

    def test_issues_bitbucket_bitbucketwebhookhandler_extract_issue_data_cloud_created(
        self, mocker
    ):
        """Test extract_issue_data for Bitbucket Cloud created event."""
        payload = {
            "changes": {"created": True},
            "issue": {
                "id": 123,
                "title": "Test Issue",
                "content": {"raw": "Issue body"},
                "reporter": {"display_name": "testuser"},
                "links": {
                    "html": {"href": "https://bitbucket.org/test/repo/issues/123"}
                },
                "created_on": "2023-01-01T00:00:00Z",
                "state": "new",
            },
            "repository": {"full_name": "test/repo"},
        }
        request = mocker.MagicMock()
        request.body = json.dumps(payload).encode("utf-8")
        handler = BitbucketWebhookHandler(request)
        result = handler.extract_issue_data()
        assert result is not None
        assert result["issue_number"] == 123
        assert result["title"] == "Test Issue"
        assert result["body"] == "Issue body"
        assert result["raw_content"] == "Issue body"
        assert result["username"] == "testuser"
        assert result["issue_url"] == "https://bitbucket.org/test/repo/issues/123"
        assert result["repository"] == "test/repo"
        assert result["created_at"] == "2023-01-01T00:00:00Z"

    def test_issues_bitbucket_bitbucketwebhookhandler_extract_issue_data_cloud_new_state(
        self, mocker
    ):
        """Test extract_issue_data for Bitbucket Cloud new issue state."""
        payload = {
            "changes": {},
            "issue": {
                "id": 456,
                "title": "New Issue",
                "content": {"raw": "New issue body"},
                "reporter": {"display_name": "anotheruser"},
                "links": {
                    "html": {"href": "https://bitbucket.org/test/repo/issues/456"}
                },
                "created_on": "2023-01-02T00:00:00Z",
                "state": "new",
            },
            "repository": {"full_name": "test/repo"},
        }
        request = mocker.MagicMock()
        request.body = json.dumps(payload).encode("utf-8")
        handler = BitbucketWebhookHandler(request)
        result = handler.extract_issue_data()
        assert result is not None
        assert result["issue_number"] == 456
        assert result["title"] == "New Issue"
        assert result["username"] == "anotheruser"

    def test_issues_bitbucket_bitbucketwebhookhandler_extract_issue_data_cloud_no_issue(
        self, mocker
    ):
        """Test extract_issue_data for Bitbucket Cloud non-issue event."""
        payload = {
            "changes": {},
            "issue": {"state": "closed"},  # Not a new issue
            "repository": {"full_name": "test/repo"},
        }
        request = mocker.MagicMock()
        request.body = json.dumps(payload).encode("utf-8")
        handler = BitbucketWebhookHandler(request)
        result = handler.extract_issue_data()
        assert result is None

    def test_issues_bitbucket_bitbucketwebhookhandler_extract_issue_data_server_new(
        self, mocker
    ):
        """Test extract_issue_data for Bitbucket Server new issue."""
        mocker.patch(
            "issues.bitbucket.BitbucketWebhookHandler._extract_bitbucket_cloud_data",
            return_value=None,
        )
        payload = {
            "issue": {
                "id": 789,
                "title": "Server Issue",
                "description": "Server issue description",
                "reporter": {"displayName": "serveruser"},
                "state": "new",
                "createdDate": "2023-01-03T00:00:00Z",
            },
            "repository": {"name": "test-repo"},
        }
        request = mocker.MagicMock()
        request.body = json.dumps(payload).encode("utf-8")
        handler = BitbucketWebhookHandler(request)
        result = handler.extract_issue_data()
        assert result is not None
        assert result["issue_number"] == 789
        assert result["title"] == "Server Issue"
        assert result["body"] == "Server issue description"
        assert result["raw_content"] == "Server issue description"
        assert result["username"] == "serveruser"
        assert result["repository"] == "test-repo"
        assert result["created_at"] == "2023-01-03T00:00:00Z"
        assert result["issue_url"] == ""  # Empty for server

    def test_issues_bitbucket_bitbucketwebhookhandler_extract_issue_data_server_no_issue(
        self, mocker
    ):
        """Test extract_issue_data for Bitbucket Server non-issue event."""
        payload = {
            "issue": {"state": "resolved"},  # Not a new issue
            "repository": {"name": "test-repo"},
        }
        request = mocker.MagicMock()
        request.body = json.dumps(payload).encode("utf-8")
        handler = BitbucketWebhookHandler(request)
        result = handler.extract_issue_data()
        assert result is None

    def test_issues_bitbucket_bitbucketwebhookhandler_extract_issue_data_empty_payload(
        self, mocker
    ):
        """Test extract_issue_data with empty payload."""
        payload = {}
        request = mocker.MagicMock()
        request.body = json.dumps(payload).encode("utf-8")
        handler = BitbucketWebhookHandler(request)
        result = handler.extract_issue_data()
        assert result is None

    # # _extract_bitbucket_cloud_data
    def test_issues_bitbucket_bitbucketwebhookhandler_extract_bitbucket_cloud_created(
        self, mocker
    ):
        """Test _extract_bitbucket_cloud_data with created change."""
        request = mocker.MagicMock()
        request.body = json.dumps({"test": "data"}).encode("utf-8")
        handler = BitbucketWebhookHandler(request)
        handler.payload = {
            "changes": {"created": True},
            "issue": {
                "id": 123,
                "title": "Cloud Issue",
                "content": {"raw": "Cloud content"},
                "reporter": {"display_name": "clouduser"},
                "links": {"html": {"href": "https://example.com/issue"}},
                "created_on": "2023-01-01T00:00:00Z",
            },
            "repository": {"full_name": "cloud/repo"},
        }
        result = handler._extract_bitbucket_cloud_data()
        assert result is not None
        assert result["issue_number"] == 123
        assert result["title"] == "Cloud Issue"
        assert result["username"] == "clouduser"

    def test_issues_bitbucket_bitbucketwebhookhandler_extract_bitbucket_cloud_data_new(
        self, mocker
    ):
        """Test _extract_bitbucket_cloud_data with new state."""
        request = mocker.MagicMock()
        request.body = json.dumps({"test": "data"}).encode("utf-8")
        handler = BitbucketWebhookHandler(request)
        handler.payload = {
            "changes": {},
            "issue": {
                "id": 456,
                "title": "New Cloud Issue",
                "content": {"raw": "New cloud content"},
                "reporter": {"display_name": "newuser"},
                "links": {"html": {"href": "https://example.com/new"}},
                "created_on": "2023-01-02T00:00:00Z",
                "state": "new",
            },
            "repository": {"full_name": "cloud/repo"},
        }
        result = handler._extract_bitbucket_cloud_data()
        assert result is not None
        assert result["issue_number"] == 456
        assert result["title"] == "New Cloud Issue"

    def test_issues_bitbucket_bitbucketwebhookhandler_extract_bitbucket_created_no_issue(
        self, mocker
    ):
        """Test _extract_bitbucket_cloud_data with new state."""
        request = mocker.MagicMock()
        request.body = json.dumps({"test": "data"}).encode("utf-8")
        handler = BitbucketWebhookHandler(request)
        handler.payload = {
            "changes": {"created": True},
            "repository": {"full_name": "cloud/repo"},
        }
        result = handler._extract_bitbucket_cloud_data()
        assert result is None

    def test_issues_bitbucket_bitbucketwebhookhandler_extract_bitbucket_cloud_data_no(
        self, mocker
    ):
        """Test _extract_bitbucket_cloud_data when no issue in payload."""
        request = mocker.MagicMock()
        request.body = json.dumps({"test": "data"}).encode("utf-8")
        handler = BitbucketWebhookHandler(request)
        handler.payload = {"changes": {}, "repository": {"full_name": "cloud/repo"}}
        result = handler._extract_bitbucket_cloud_data()
        assert result is None

    def test_issues_bitbucket_bitbucketwebhookhandler_extract_bitbucket_cloud_not_new(
        self, mocker
    ):
        """Test _extract_bitbucket_cloud_data when issue is not new."""
        request = mocker.MagicMock()
        request.body = json.dumps({"test": "data"}).encode("utf-8")
        handler = BitbucketWebhookHandler(request)
        handler.payload = {
            "changes": {},
            "issue": {"state": "resolved"},  # Not new
            "repository": {"full_name": "cloud/repo"},
        }
        result = handler._extract_bitbucket_cloud_data()
        assert result is None

    # # _extract_bitbucket_server_data
    def test_issues_bitbucket_bitbucketwebhookhandler_extract_bitbucket_server_data_new(
        self, mocker
    ):
        """Test _extract_bitbucket_server_data with new issue."""
        request = mocker.MagicMock()
        request.body = json.dumps({"test": "data"}).encode("utf-8")
        handler = BitbucketWebhookHandler(request)
        handler.payload = {
            "issue": {
                "id": 789,
                "title": "Server Issue",
                "description": "Server description",
                "reporter": {"displayName": "serveruser"},
                "state": "new",
                "createdDate": "2023-01-03T00:00:00Z",
            },
            "repository": {"name": "server-repo"},
        }
        result = handler._extract_bitbucket_server_data()
        assert result is not None
        assert result["issue_number"] == 789
        assert result["title"] == "Server Issue"
        assert result["username"] == "serveruser"

    def test_issues_bitbucket_bitbucketwebhookhandler_extract_bitbucket_server_not_new(
        self, mocker
    ):
        """Test _extract_bitbucket_server_data when issue is not new."""
        request = mocker.MagicMock()
        request.body = json.dumps({"test": "data"}).encode("utf-8")
        handler = BitbucketWebhookHandler(request)
        handler.payload = {
            "issue": {"state": "closed"},  # Not new
            "repository": {"name": "server-repo"},
        }
        result = handler._extract_bitbucket_server_data()
        assert result is None

    def test_issues_bitbucket_bitbucketwebhookhandler_extract_bitbucket_server_no_issue(
        self, mocker
    ):
        """Test _extract_bitbucket_server_data when no issue in payload."""
        request = mocker.MagicMock()
        request.body = json.dumps({"test": "data"}).encode("utf-8")
        handler = BitbucketWebhookHandler(request)
        handler.payload = {"repository": {"name": "server-repo"}}
        result = handler._extract_bitbucket_server_data()
        assert result is None

    def test_issues_bitbucket_bitbucketwebhookhandler_extract_bitbucket_server_missing(
        self, mocker
    ):
        """Test _extract_bitbucket_server_data with missing fields."""
        request = mocker.MagicMock()
        request.body = json.dumps({"test": "data"}).encode("utf-8")
        handler = BitbucketWebhookHandler(request)
        handler.payload = {
            "issue": {
                "state": "new"
                # Missing other required fields
            },
            "repository": {},
        }
        result = handler._extract_bitbucket_server_data()
        assert result is not None  # Should still return data with empty/None values
        assert result["issue_number"] is None
        assert result["title"] == ""
        assert result["username"] == ""

    # # process_webhook (integration test)
    def test_issues_bitbucket_bitbucketwebhookhandler_process_webhook_success(
        self, mocker
    ):
        """Test complete webhook processing for successful case."""
        payload = {
            "changes": {"created": True},
            "issue": {
                "id": 123,
                "title": "Test Issue",
                "content": {"raw": "Issue body"},
                "reporter": {"display_name": "testuser"},
                "links": {"html": {"href": "https://example.com/issue"}},
                "created_on": "2023-01-01T00:00:00Z",
                "state": "new",
            },
            "repository": {"full_name": "test/repo"},
        }
        request = mocker.MagicMock()
        request.body = json.dumps(payload).encode("utf-8")
        request.headers = {}  # No signature needed since no secret
        handler = BitbucketWebhookHandler(request)
        response = handler.process_webhook()
        assert response.status_code == 200
        response_data = json.loads(response.content)
        assert response_data["status"] == "success"
        assert response_data["provider"] == "BitbucketWebhookHandler"
        assert response_data["issue_title"] == "Test Issue"
        assert response_data["issue_number"] == 123
        assert response_data["username"] == "testuser"

    def test_issues_bitbucket_bitbucketwebhookhandler_process_webhook_validation_failed(
        self, mocker
    ):
        """Test webhook processing when validation fails."""
        mocker.patch("issues.bitbucket.os.getenv", return_value="test_secret")
        request = mocker.MagicMock()
        request.body = b"test_body"
        request.headers = {}  # No signature
        handler = BitbucketWebhookHandler(request)
        response = handler.process_webhook()
        assert response.status_code == 403
        response_data = json.loads(response.content)
        assert response_data["status"] == "error"
        assert "Webhook validation failed" in response_data["message"]

    def test_issues_bitbucket_bitbucketwebhookhandler_process_webhook_no_issue_data(
        self, mocker
    ):
        """Test webhook processing when no issue data is found."""
        payload = {
            "changes": {},
            "issue": {"state": "closed"},  # Not a new issue
            "repository": {"full_name": "test/repo"},
        }
        request = mocker.MagicMock()
        request.body = json.dumps(payload).encode("utf-8")
        request.headers = {}
        handler = BitbucketWebhookHandler(request)
        response = handler.process_webhook()
        assert response.status_code == 200
        response_data = json.loads(response.content)
        assert response_data["status"] == "success"
        assert response_data["message"] == "Not an issue creation event"
        assert "issue_title" not in response_data
        assert "issue_number" not in response_data
