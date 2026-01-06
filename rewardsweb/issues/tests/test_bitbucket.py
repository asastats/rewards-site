"""Testing module for :py:mod:`issues.bitbucket` module."""

from django.conf import settings

from issues.bitbucket import BitbucketApp, BitbucketProvider


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
