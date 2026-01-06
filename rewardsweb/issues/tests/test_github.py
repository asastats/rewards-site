"""Testing module for :py:mod:`issues.github` module."""

from unittest import mock

from django.conf import settings

from issues.github import GitHubApp, GithubProvider
from utils.constants.ui import MISSING_API_TOKEN_TEXT


class TestIssuesGithubGitHubApp:
    """Testing class for :class:`issues.github.GitHubApp`."""

    # # jwt_token
    def test_issues_github_githubapp_jwt_token_no_env_vars(self, mocker):
        mocker.patch("issues.github.github_config", return_value={})
        instance = GitHubApp()
        assert instance.jwt_token() is None

    def test_issues_github_githubapp_jwt_token_success(self, mocker):
        mocker.patch(
            "issues.github.github_config",
            return_value={"private_key_filename": "test.pem", "client_id": "test_id"},
        )
        mock_settings = mocker.MagicMock()
        mock_settings.BASE_DIR.parent = mocker.MagicMock()
        mocker.patch("issues.github.settings", mock_settings)
        mock_open = mocker.mock_open(read_data=b"test_key")
        mocker.patch("builtins.open", mock_open)
        mock_datetime = mocker.MagicMock()
        mock_timedelta = mocker.MagicMock()
        mocker.patch("issues.github.datetime", mock_datetime)
        mocker.patch("issues.github.timedelta", mock_timedelta)
        mock_jwt = mocker.MagicMock()
        mocker.patch("issues.github.jwt", mock_jwt)
        instance = GitHubApp()
        instance.jwt_token()
        mock_open.assert_called_once_with(
            mock_settings.BASE_DIR.parent / "fixtures" / "test.pem", "rb"
        )
        mock_jwt.encode.assert_called_once()

    # # installation_token
    def test_issues_github_githubapp_installation_token_no_id(self, mocker):
        mocker.patch(
            "issues.github.github_config",
            return_value={},
        )
        instance = GitHubApp()
        assert instance.installation_token() is None

    def test_issues_github_githubapp_installation_token_no_jwt(self, mocker):
        mocker.patch(
            "issues.github.github_config",
            return_value={"installation_id": "test_installation"},
        )
        mock_jwt_token = mocker.patch.object(GitHubApp, "jwt_token", return_value=None)
        instance = GitHubApp()
        assert instance.installation_token() is None
        mock_jwt_token.assert_called_once_with()

    def test_issues_github_githubapp_installation_token_request_fails(self, mocker):
        mocker.patch(
            "issues.github.github_config",
            return_value={"installation_id": "test_installation"},
        )
        mocker.patch.object(GitHubApp, "jwt_token", return_value="test_jwt")
        mock_response = mocker.MagicMock()
        mock_response.status_code = 400
        mocked_requests = mocker.patch(
            "issues.github.requests.post", return_value=mock_response
        )
        instance = GitHubApp()
        assert instance.installation_token() is None
        mocked_requests.assert_called_once()

    def test_issues_github_githubapp_installation_token_success(self, mocker):
        mocker.patch(
            "issues.github.github_config",
            return_value={"installation_id": "test_installation"},
        )
        mocker.patch.object(GitHubApp, "jwt_token", return_value="test_jwt")
        mock_response = mocker.MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"token": "test_token"}
        mocked_requests = mocker.patch(
            "issues.github.requests.post", return_value=mock_response
        )
        instance = GitHubApp()
        assert instance.installation_token() == "test_token"
        mocked_requests.assert_called_once()

    # # client
    def test_issues_github_githubapp_client_no_token(self, mocker):
        mock_installation_token = mocker.patch.object(
            GitHubApp, "installation_token", return_value=None
        )
        mocked_github = mocker.patch("issues.github.Github")
        instance = GitHubApp()
        assert instance.client() is None
        mock_installation_token.assert_called_once_with()
        mocked_github.assert_not_called()

    def test_issues_github_githubapp_client_success(self, mocker):
        mock_installation_token = mocker.patch.object(
            GitHubApp, "installation_token", return_value="test_token"
        )
        mock_github_instance = mocker.MagicMock()
        mocked_github = mocker.patch(
            "issues.github.Github", return_value=mock_github_instance
        )
        instance = GitHubApp()
        assert instance.client() == mock_github_instance
        mock_installation_token.assert_called_once_with()
        mocked_github.assert_called_once_with("test_token")


class TestIssuesGithubGithubProvider:
    """Testing class for :class:`issues.github.GithubProvider`."""

    def test_issues_github_githubprovider_inits_name(self):
        assert GithubProvider.name == "github"

    # # __init__
    def test_issues_github_githubprovider_init_functionality(self, mocker):
        mocked_client = mocker.patch("issues.github.GithubProvider._get_client")
        mocked_repo = mocker.patch("issues.github.GithubProvider._get_repository")
        user = mocker.MagicMock()
        provider = GithubProvider(user)
        assert provider.user == user
        assert provider.client == mocked_client.return_value
        assert provider.repo == mocked_repo.return_value
        mocked_client.assert_called_once_with(issue_tracker_api_token=None)
        mocked_repo.assert_called_once_with()

    # # _get_client
    def test_issues_github_githubprovider_get_client_with_provided_token(
        self, mocker
    ):
        mocked_auth_token = mocker.patch("issues.github.Auth.Token")
        mocked_github = mocker.patch("issues.github.Github")
        mocked_githubapp = mocker.patch("issues.github.GitHubApp")
        issue_tracker_api_token = mocker.MagicMock()
        provider = GithubProvider(mocker.MagicMock())
        mocked_auth_token.reset_mock()
        mocked_github.reset_mock()
        mocked_githubapp.reset_mock()
        returned = provider._get_client(issue_tracker_api_token=issue_tracker_api_token)
        assert returned == mocked_github.return_value
        mocked_auth_token.assert_called_once_with(issue_tracker_api_token)
        mocked_github.assert_called_once_with(auth=mocked_auth_token.return_value)
        mocked_githubapp.assert_not_called()

    def test_issues_github_githubprovider_get_client_with_app_token(self, mocker):
        mocked_auth_token = mocker.patch("issues.github.Auth.Token")
        mocked_github = mocker.patch("issues.github.Github")
        mock_app_client = mocker.MagicMock()
        mocker.patch("issues.github.GitHubApp.client", return_value=mock_app_client)
        user = mocker.MagicMock()
        user.profile.issue_tracker_api_token = "some_token"
        provider = GithubProvider(user)
        returned = provider._get_client()
        assert returned == mock_app_client
        mocked_auth_token.assert_not_called()
        mocked_github.assert_not_called()

    def test_issues_github_githubprovider_get_client_no_token(self, mocker):
        mocker.patch("issues.github.GitHubApp.client", return_value=None)
        user = mocker.MagicMock()
        user.profile.issue_tracker_api_token = ""
        provider = GithubProvider(user)
        returned = provider._get_client()
        assert returned is False

    def test_issues_github_githubprovider_get_client_functionality(self, mocker):
        mocked_auth_token = mocker.patch("issues.github.Auth.Token")
        mocked_github = mocker.patch("issues.github.Github")
        mocker.patch("issues.github.GitHubApp.client", return_value=None)
        user, token = mocker.MagicMock(), mocker.MagicMock()
        user.profile.issue_tracker_api_token = token
        provider = GithubProvider(user)
        mocked_auth_token.reset_mock()
        mocked_github.reset_mock()
        returned = provider._get_client()
        assert returned == mocked_github.return_value
        mocked_auth_token.assert_called_once_with(token)
        mocked_github.assert_called_once_with(auth=mocked_auth_token.return_value)

    # # _close_issue_with_labels_impl
    def test_issues_github_githubprovider_close_issue_with_labels_impl_no_labels(
        self, mocker
    ):
        mocker.patch("issues.github.GithubProvider._get_client")
        mocker.patch("issues.github.GithubProvider._get_repository")

        provider = GithubProvider(mocker.MagicMock())
        provider.repo = mocker.MagicMock()
        issue = mocker.MagicMock()
        issue.user = None
        provider.repo.get_issue.return_value = issue
        issue_number, labels_to_set, comment = 101, [], "comment"
        result = provider._close_issue_with_labels_impl(
            issue_number, labels_to_set, comment
        )
        assert "Closed issue" in result["message"]
        assert result["issue_state"] == issue.state
        issue.create_comment.assert_called_once_with(comment)
        issue.set_labels.assert_not_called()

    def test_issues_github_githubprovider_close_issue_with_labels_impl_no_comment(
        self, mocker
    ):
        mocker.patch("issues.github.GithubProvider._get_client")
        mocker.patch("issues.github.GithubProvider._get_repository")
        provider = GithubProvider(mocker.MagicMock())
        provider.repo = mocker.MagicMock()
        issue = mocker.MagicMock()
        provider.repo.get_issue.return_value = issue
        issue_number, labels_to_set, comment = 101, ["label1", "label2"], ""
        result = provider._close_issue_with_labels_impl(
            issue_number, labels_to_set, comment
        )
        assert "Closed issue" in result["message"]
        assert result["issue_state"] == issue.state
        issue.set_labels.assert_called_once_with("label1", "label2")
        issue.create_comment.assert_not_called()

    # # _fetch_issues_impl
    def test_issues_github_githubprovider_fetch_issues_impl_functionality(
        self, mocker
    ):
        mocker.patch("issues.github.GithubProvider._get_client")
        mocker.patch("issues.github.GithubProvider._get_repository")
        provider = GithubProvider(mocker.MagicMock())
        provider.repo = mocker.MagicMock()
        state, since = "state", "since"
        returned = provider._fetch_issues_impl(state, since)
        assert returned == provider.repo.get_issues.return_value
        provider.repo.get_issues.assert_called_once_with(
            state=state, sort="updated", direction="asc", since=since
        )

    # # _get_issue_by_number_impl
    def test_issues_github_githubprovider_get_issue_by_number_impl_no_user(
        self, mocker
    ):
        mocker.patch("issues.github.GithubProvider._get_client")
        mocker.patch("issues.github.GithubProvider._get_repository")
        provider = GithubProvider(mocker.MagicMock())
        provider.repo = mocker.MagicMock()
        issue = mocker.MagicMock()
        issue.user = None
        provider.repo.get_issue.return_value = issue
        result = provider._get_issue_by_number_impl(1)
        assert result["issue"]["user"] is None

    # # _get_repository
    def test_issues_github_githubprovider_get_repository_for_client_none(
        self, mocker
    ):
        mocker.patch("issues.github.GithubProvider._get_client", return_value=None)
        provider = GithubProvider(mocker.MagicMock())
        returned = provider._get_repository()
        assert returned is None

    def test_issues_github_githubprovider_get_repository_functionality(self, mocker):
        mock_client = mocker.MagicMock()
        mocker.patch(
            "issues.github.GithubProvider._get_client", return_value=mock_client
        )
        provider = GithubProvider(mocker.MagicMock())
        mock_client.get_repo.reset_mock()
        returned = provider._get_repository()
        assert returned == mock_client.get_repo.return_value
        mock_client.get_repo.assert_called_once_with(
            f"{settings.ISSUE_TRACKER_OWNER}/{settings.ISSUE_TRACKER_NAME}"
        )

    # # _issue_url_impl
    def test_issues_github_githubprovider_issue_url_impl(self, mocker):
        mocker.patch("issues.github.GithubProvider._get_client")
        mocker.patch("issues.github.GithubProvider._get_repository")
        provider = GithubProvider(mocker.MagicMock())
        result = provider._issue_url_impl(10)
        assert result == (
            f"https://github.com/{settings.ISSUE_TRACKER_OWNER}/"
            f"{settings.ISSUE_TRACKER_NAME}/issues/10"
        )

    # # close_issue_with_labels
    def test_issues_github_githubprovider_close_issue_with_labels_for_no_client(
        self, mocker
    ):
        mocker.patch("issues.github.GithubProvider._get_client")
        mocker.patch("issues.github.GithubProvider._get_repository")
        user = mocker.MagicMock()
        provider = GithubProvider(user)
        provider.client = None
        returned = provider.close_issue_with_labels(
            mocker.MagicMock(), mocker.MagicMock()
        )
        assert returned == {"success": False, "error": MISSING_API_TOKEN_TEXT}

    def test_issues_github_githubprovider_close_issue_with_labels_for_exception(
        self, mocker
    ):
        mocker.patch("issues.github.GithubProvider._get_client")
        mocker.patch("issues.github.GithubProvider._get_repository")
        mocker.patch(
            "issues.github.GithubProvider._close_issue_with_labels_impl",
            side_effect=Exception("error1"),
        )
        user = mocker.MagicMock()
        provider = GithubProvider(user)
        returned = provider.close_issue_with_labels(
            mocker.MagicMock(), mocker.MagicMock()
        )
        assert returned == {"success": False, "error": "error1"}

    def test_issues_github_githubprovider_close_issue_with_labels_functionality(
        self, mocker
    ):
        mocker.patch("issues.github.GithubProvider._get_client")
        mocker.patch("issues.github.GithubProvider._get_repository")
        result = {"foo": "bar"}
        mocker.patch(
            "issues.github.BaseIssueProvider._close_issue_with_labels_impl",
            return_value=result,
        )
        user = mocker.MagicMock()
        provider = GithubProvider(user)
        returned = provider.close_issue_with_labels(
            mocker.MagicMock(), mocker.MagicMock()
        )
        assert returned["success"]
        assert "Closed issue" in returned["message"]

    # # create_issue
    def test_issues_github_githubprovider_create_issue_for_no_client(self, mocker):
        mocker.patch("issues.github.GithubProvider._get_client")
        mocker.patch("issues.github.GithubProvider._get_repository")
        user = mocker.MagicMock()
        provider = GithubProvider(user)
        provider.client = None
        returned = provider.create_issue(mocker.MagicMock(), mocker.MagicMock())
        assert returned == {"success": False, "error": MISSING_API_TOKEN_TEXT}

    def test_issues_github_githubprovider_create_issue_for_exception(self, mocker):
        mocker.patch("issues.github.GithubProvider._get_client")
        mocker.patch("issues.github.GithubProvider._get_repository")
        mocker.patch(
            "issues.github.GithubProvider._create_issue_impl",
            side_effect=Exception("error1"),
        )
        user = mocker.MagicMock()
        provider = GithubProvider(user)
        returned = provider.create_issue(mocker.MagicMock(), mocker.MagicMock())
        assert returned == {"success": False, "error": "error1"}

    def test_issues_github_githubprovider_create_issue_functionality(self, mocker):
        mocker.patch("issues.github.GithubProvider._get_client")
        mocker.patch("issues.github.GithubProvider._get_repository")
        result = {"foo": "bar"}
        mocker.patch(
            "issues.github.BaseIssueProvider._create_issue_impl",
            return_value=result,
        )
        user = mocker.MagicMock()
        provider = GithubProvider(user)
        returned = provider.create_issue(mocker.MagicMock(), mocker.MagicMock())
        assert returned["success"]
        assert "issue_number" in returned

    # # fetch_issues
    def test_issues_github_githubprovider_fetch_issues_for_no_client(self, mocker):
        mocker.patch("issues.github.GithubProvider._get_client")
        mocker.patch("issues.github.GithubProvider._get_repository")
        user = mocker.MagicMock()
        provider = GithubProvider(user)
        provider.client = None
        returned = provider.fetch_issues()
        assert returned == []

    def test_issues_github_githubprovider_fetch_issues_for_exception(self, mocker):
        mocker.patch("issues.github.GithubProvider._get_client")
        mocker.patch("issues.github.GithubProvider._get_repository")
        mocker.patch(
            "issues.github.GithubProvider._fetch_issues_impl",
            side_effect=Exception("error1"),
        )
        user = mocker.MagicMock()
        provider = GithubProvider(user)
        with mock.patch("issues.base.logger") as mocked_logger:
            returned = provider.fetch_issues()
            mocked_logger.error.assert_called_once_with("Error fetching issues: error1")
        assert returned == []

    def test_issues_github_githubprovider_fetch_issues_functionality(self, mocker):
        mocker.patch("issues.github.GithubProvider._get_client")
        mocker.patch("issues.github.GithubProvider._get_repository")
        issues = mocker.MagicMock()
        mocker.patch(
            "issues.github.GithubProvider._fetch_issues_impl",
            return_value=issues,
        )

        user = mocker.MagicMock()
        provider = GithubProvider(user)
        returned = provider.fetch_issues()
        assert returned == issues

    # # issue_by_number
    def test_issues_github_githubprovider_issue_by_number_for_no_client(
        self, mocker
    ):
        mocker.patch("issues.github.GithubProvider._get_client")
        mocker.patch("issues.github.GithubProvider._get_repository")
        user = mocker.MagicMock()
        provider = GithubProvider(user)
        provider.client = None
        returned = provider.issue_by_number(mocker.MagicMock())
        assert returned == {"success": False, "error": MISSING_API_TOKEN_TEXT}

    def test_issues_github_githubprovider_issue_by_number_for_exception(
        self, mocker
    ):
        mocker.patch("issues.github.GithubProvider._get_client")
        mocker.patch("issues.github.GithubProvider._get_repository")
        mocker.patch(
            "issues.github.GithubProvider._get_issue_by_number_impl",
            side_effect=Exception("error1"),
        )
        user = mocker.MagicMock()
        provider = GithubProvider(user)
        returned = provider.issue_by_number(mocker.MagicMock())
        assert returned == {"success": False, "error": "error1"}

    def test_issues_github_githubprovider_issue_by_number_functionality(
        self, mocker
    ):
        mocker.patch("issues.github.GithubProvider._get_client")
        mocker.patch("issues.github.GithubProvider._get_repository")
        result = {"foo": "bar"}
        mocker.patch(
            "issues.github.BaseIssueProvider._get_issue_by_number_impl",
            return_value=result,
        )
        user = mocker.MagicMock()
        provider = GithubProvider(user)
        returned = provider.issue_by_number(mocker.MagicMock())
        assert returned["success"]
        assert "Retrieved issue" in returned["message"]

    # # issue_url
    def test_issues_github_githubprovider_issue_url_functionality(self, mocker):
        mocker.patch("issues.github.GithubProvider._get_client")
        mocker.patch("issues.github.GithubProvider._get_repository")
        provider = GithubProvider(mocker.MagicMock())
        returned = provider.issue_url(10)
        assert returned == (
            f"https://github.com/{settings.ISSUE_TRACKER_OWNER}/"
            f"{settings.ISSUE_TRACKER_NAME}/issues/10"
        )

    # # set_labels_to_issue
    def test_issues_github_githubprovider_set_labels_to_issue_for_no_client(
        self, mocker
    ):
        mocker.patch("issues.github.GithubProvider._get_client")
        mocker.patch("issues.github.GithubProvider._get_repository")
        user = mocker.MagicMock()
        provider = GithubProvider(user)
        provider.client = None
        returned = provider.set_labels_to_issue(mocker.MagicMock(), mocker.MagicMock())
        assert returned == {"success": False, "error": MISSING_API_TOKEN_TEXT}

    def test_issues_github_githubprovider_set_labels_to_issue_for_exception(
        self, mocker
    ):
        mocker.patch("issues.github.GithubProvider._get_client")
        mocker.patch("issues.github.GithubProvider._get_repository")
        mocker.patch(
            "issues.github.GithubProvider._set_labels_to_issue_impl",
            side_effect=Exception("error1"),
        )
        user = mocker.MagicMock()
        provider = GithubProvider(user)
        returned = provider.set_labels_to_issue(mocker.MagicMock(), mocker.MagicMock())
        assert returned == {"success": False, "error": "error1"}

    def test_issues_github_githubprovider_set_labels_to_issue_functionality(
        self, mocker
    ):
        mocker.patch("issues.github.GithubProvider._get_client")
        mocker.patch("issues.github.GithubProvider._get_repository")
        result = {"foo": "bar"}
        mocker.patch(
            "issues.github.BaseIssueProvider._set_labels_to_issue_impl",
            return_value=result,
        )
        user = mocker.MagicMock()
        provider = GithubProvider(user)
        returned = provider.set_labels_to_issue(mocker.MagicMock(), mocker.MagicMock())
        assert returned["success"]
        assert "Added labels" in returned["message"]
