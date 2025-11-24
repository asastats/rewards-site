"""Testing module for :py:mod:`issues.providers` module."""

import pytest
from django.conf import settings

from issues.providers import (
    BaseIssueProvider,
    BitbucketApp,
    BitbucketProvider,
    GitHubApp,
    GithubProvider,
    GitlabProvider,
)
from utils.constants.ui import MISSING_TOKEN_TEXT


class TestIssuesProvidersBitbucketApp:
    """Testing class for :class:`issues.providers.BitbucketApp`."""

    # # jwt_token
    def est_issues_providers_bitbucketapp_jwt_token_no_env_vars(self, mocker):
        mocked_getenv = mocker.patch("os.getenv", return_value=None)
        instance = BitbucketApp()
        assert instance.jwt_token() is None
        mocked_getenv.assert_has_calls(
            [
                mocker.call("BITBUCKET_CLIENT_KEY"),
                mocker.call("BITBUCKET_SHARED_SECRET"),
            ]
        )

    def est_issues_providers_bitbucketapp_jwt_token_success(self, mocker):
        mocker.patch("os.getenv", side_effect=["test_client_key", "test_shared_secret"])
        mock_datetime = mocker.MagicMock()
        mock_timedelta = mocker.MagicMock()
        mocker.patch("bitbucketapp.datetime", mock_datetime)
        mocker.patch("bitbucketapp.timedelta", mock_timedelta)
        mock_jwt = mocker.MagicMock()
        mocker.patch("bitbucketapp.jwt", mock_jwt)

        instance = BitbucketApp()
        instance.jwt_token()

        mock_jwt.encode.assert_called_once()
        args, kwargs = mock_jwt.encode.call_args
        assert kwargs["algorithm"] == "HS256"
        assert "iss" in args[0]
        assert "iat" in args[0]
        assert "exp" in args[0]

    # # access_token
    def est_issues_providers_bitbucketapp_access_token_no_jwt(self, mocker):
        mock_jwt_token = mocker.patch.object(
            BitbucketApp, "jwt_token", return_value=None
        )
        instance = BitbucketApp()
        assert instance.access_token() is None
        mock_jwt_token.assert_called_once_with()

    def est_issues_providers_bitbucketapp_access_token_request_fails(self, mocker):
        mocker.patch.object(BitbucketApp, "jwt_token", return_value="test_jwt")
        mock_response = mocker.MagicMock()
        mock_response.status_code = 400
        mocked_requests = mocker.patch(
            "bitbucketapp.requests.post", return_value=mock_response
        )
        instance = BitbucketApp()
        assert instance.access_token() is None
        mocked_requests.assert_called_once_with(
            "https://bitbucket.org/site/oauth2/access_token",
            headers={"Authorization": "JWT test_jwt"},
            data={"grant_type": "urn:bitbucket:oauth2:jwt"},
        )

    def est_issues_providers_bitbucketapp_access_token_success(self, mocker):
        mocker.patch.object(BitbucketApp, "jwt_token", return_value="test_jwt")
        mock_response = mocker.MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "test_token"}
        mocked_requests = mocker.patch(
            "bitbucketapp.requests.post", return_value=mock_response
        )
        instance = BitbucketApp()
        assert instance.access_token() == "test_token"
        mocked_requests.assert_called_once_with(
            "https://bitbucket.org/site/oauth2/access_token",
            headers={"Authorization": "JWT test_jwt"},
            data={"grant_type": "urn:bitbucket:oauth2:jwt"},
        )


class TestIssuesProvidersGitHubApp:
    """Testing class for :class:`issues.providers.GitHubApp`."""

    # # jwt_token
    def test_issues_providers_githubapp_jwt_token_no_env_vars(self, mocker):
        mocked_get_env_variable = mocker.patch(
            "issues.providers.get_env_variable", return_value=""
        )
        instance = GitHubApp()
        assert instance.jwt_token() is None
        mocked_get_env_variable.assert_has_calls(
            [
                mocker.call("GITHUB_BOT_PRIVATE_KEY_FILENAME", ""),
                mocker.call("GITHUB_BOT_CLIENT_ID", ""),
            ]
        )

    def test_issues_providers_githubapp_jwt_token_success(self, mocker):
        mocked_get_env_variable = mocker.patch(
            "issues.providers.get_env_variable",
            side_effect=["test.pem", "test_id"],
        )
        mock_settings = mocker.MagicMock()
        mock_settings.BASE_DIR.parent = mocker.MagicMock()
        mocker.patch("issues.providers.settings", mock_settings)
        mock_open = mocker.mock_open(read_data=b"test_key")
        mocker.patch("builtins.open", mock_open)
        mock_datetime = mocker.MagicMock()
        mock_timedelta = mocker.MagicMock()
        mocker.patch("issues.providers.datetime", mock_datetime)
        mocker.patch("issues.providers.timedelta", mock_timedelta)
        mock_jwt = mocker.MagicMock()
        mocker.patch("issues.providers.jwt", mock_jwt)

        instance = GitHubApp()
        instance.jwt_token()

        mocked_get_env_variable.assert_has_calls(
            [
                mocker.call("GITHUB_BOT_PRIVATE_KEY_FILENAME", ""),
                mocker.call("GITHUB_BOT_CLIENT_ID", ""),
            ]
        )
        mock_open.assert_called_once_with(
            mock_settings.BASE_DIR.parent / "fixtures" / "test.pem", "rb"
        )
        mock_jwt.encode.assert_called_once()

    # # installation_token
    def test_issues_providers_githubapp_installation_token_no_id(self, mocker):
        mocked_get_env_variable = mocker.patch(
            "issues.providers.get_env_variable", return_value=""
        )
        instance = GitHubApp()
        assert instance.installation_token() is None
        mocked_get_env_variable.assert_called_once_with(
            "GITHUB_BOT_INSTALLATION_ID", ""
        )

    def test_issues_providers_githubapp_installation_token_no_jwt(self, mocker):
        mocker.patch("issues.providers.get_env_variable", return_value="test_id")
        mock_jwt_token = mocker.patch.object(GitHubApp, "jwt_token", return_value=None)
        instance = GitHubApp()
        assert instance.installation_token() is None
        mock_jwt_token.assert_called_once_with()

    def test_issues_providers_githubapp_installation_token_request_fails(self, mocker):
        mocker.patch("issues.providers.get_env_variable", return_value="test_id")
        mocker.patch.object(GitHubApp, "jwt_token", return_value="test_jwt")
        mock_response = mocker.MagicMock()
        mock_response.status_code = 400
        mocked_requests = mocker.patch(
            "issues.providers.requests.post", return_value=mock_response
        )
        instance = GitHubApp()
        assert instance.installation_token() is None
        mocked_requests.assert_called_once()

    def test_issues_providers_githubapp_installation_token_success(self, mocker):
        mocker.patch("issues.providers.get_env_variable", return_value="test_id")
        mocker.patch.object(GitHubApp, "jwt_token", return_value="test_jwt")
        mock_response = mocker.MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"token": "test_token"}
        mocked_requests = mocker.patch(
            "issues.providers.requests.post", return_value=mock_response
        )
        instance = GitHubApp()
        assert instance.installation_token() == "test_token"
        mocked_requests.assert_called_once()

    # # client
    def test_issues_providers_githubapp_client_no_token(self, mocker):
        mock_installation_token = mocker.patch.object(
            GitHubApp, "installation_token", return_value=None
        )
        mocked_github = mocker.patch("issues.providers.Github")
        instance = GitHubApp()
        assert instance.client() is None
        mock_installation_token.assert_called_once_with()
        mocked_github.assert_not_called()

    def test_issues_providers_githubapp_client_success(self, mocker):
        mock_installation_token = mocker.patch.object(
            GitHubApp, "installation_token", return_value="test_token"
        )
        mock_github_instance = mocker.MagicMock()
        mocked_github = mocker.patch(
            "issues.providers.Github", return_value=mock_github_instance
        )
        instance = GitHubApp()
        assert instance.client() == mock_github_instance
        mock_installation_token.assert_called_once_with()
        mocked_github.assert_called_once_with("test_token")


class TestIssuesProvidersBaseIssueProvider:
    """Testing class for :py:mod:`issues.providers.BaseIssueProvider` class."""

    @pytest.mark.parametrize(
        "attr",
        ["name", "user", "client", "repo"],
    )
    def test_issues_providers_baseissueprovider_inits_attribute_as_none(self, attr):
        assert getattr(BaseIssueProvider, attr) is None


class TestIssuesProvidersBitbucketProvider:
    """Testing class for :py:mod:`issues.providers.BitbucketProvider` class."""

    def test_issues_providers_bitbucketprovider_inits_name(self):
        assert BitbucketProvider.name == "bitbucket"

    # # __init__
    def test_issues_providers_bitbucketprovider_init_functionality(self, mocker):
        mocked_client = mocker.patch("issues.providers.BitbucketProvider._get_client")
        mocked_repo = mocker.patch("issues.providers.BitbucketProvider._get_repository")
        user = mocker.MagicMock()
        provider = BitbucketProvider(user)
        assert provider.user == user
        assert provider.client == mocked_client.return_value
        assert provider.repo == mocked_repo.return_value
        mocked_client.assert_called_once_with(issue_tracker_api_token=None)
        mocked_repo.assert_called_once_with()

    # # _get_client
    def test_issues_providers_bitbucketprovider_get_client_with_provided_token(
        self, mocker
    ):
        mock_access_token = mocker.patch.object(
            BitbucketApp, "access_token", return_value="test_app_token"
        )
        mock_bitbucket_client = mocker.patch("issues.providers.Cloud")
        issue_tracker_api_token = mocker.MagicMock()
        provider = BitbucketProvider(mocker.MagicMock())
        mock_access_token.reset_mock()
        mock_bitbucket_client.reset_mock()
        returned = provider._get_client(issue_tracker_api_token=issue_tracker_api_token)
        assert returned == mock_bitbucket_client.return_value
        mock_access_token.assert_not_called()
        mock_bitbucket_client.assert_called_once_with(token=issue_tracker_api_token)

    def test_issues_providers_bitbucketprovider_get_client_with_app_token(self, mocker):
        mock_access_token = mocker.patch.object(
            BitbucketApp, "access_token", return_value="test_app_token"
        )
        mock_bitbucket_client = mocker.patch("issues.providers.Cloud")
        provider = BitbucketProvider(mocker.MagicMock())
        mock_access_token.reset_mock()
        mock_bitbucket_client.reset_mock()
        returned = provider._get_client()
        assert returned == mock_bitbucket_client.return_value
        mock_access_token.assert_called_once_with()
        mock_bitbucket_client.assert_called_once_with(token="test_app_token")

    def test_issues_providers_bitbucketprovider_get_client_with_user_token(
        self, mocker
    ):
        mocker.patch.object(BitbucketApp, "access_token", return_value=None)
        mock_bitbucket_client = mocker.patch("issues.providers.Cloud")
        mock_user = mocker.MagicMock()
        mock_user.profile.issue_tracker_api_token = "test_user_token"
        provider = BitbucketProvider(user=mock_user)
        mock_bitbucket_client.reset_mock()
        returned = provider._get_client()
        assert returned == mock_bitbucket_client.return_value
        mock_bitbucket_client.assert_called_once_with(token="test_user_token")

    def test_issues_providers_bitbucketprovider_get_client_no_token(self, mocker):
        mocker.patch.object(BitbucketApp, "access_token", return_value=None)
        mock_bitbucket_client = mocker.patch("issues.providers.Cloud")
        provider = BitbucketProvider(user=None)
        client = provider._get_client()
        assert client is None
        mock_bitbucket_client.assert_not_called()

    # # _get_repository
    def test_issues_providers_bitbucketprovider_get_repository_for_client_none(
        self, mocker
    ):
        mocker.patch(
            "issues.providers.BitbucketProvider._get_client", return_value=None
        )
        provider = BitbucketProvider(mocker.MagicMock())
        returned = provider._get_repository()
        assert returned is None

    def test_issues_providers_bitbucketprovider_get_repository_functionality(
        self, mocker
    ):
        mock_client = mocker.MagicMock()
        mocker.patch(
            "issues.providers.BitbucketProvider._get_client", return_value=mock_client
        )
        provider = BitbucketProvider(mocker.MagicMock())
        mock_client.repositories.get.reset_mock()
        returned = provider._get_repository()
        assert returned == mock_client.repositories.get.return_value
        mock_client.repositories.get.assert_called_once_with(
            settings.ISSUE_TRACKER_OWNER, settings.ISSUE_TRACKER_NAME
        )

    # # _close_issue_with_labels_impl
    def test_issues_providers_bitbucketprovider_close_issue_with_labels_impl(
        self, mocker
    ):
        mocker.patch("issues.providers.BitbucketProvider._get_client")
        mocker.patch("issues.providers.BitbucketProvider._get_repository")
        user = mocker.MagicMock()
        provider = BitbucketProvider(user)
        provider.repo = ("workspace", "repo_slug")
        provider.client = mocker.MagicMock()
        provider._close_issue_with_labels_impl(1, ["label1"], "comment")
        provider.client.update_issue.assert_called_once()
        provider.client.issue_comment.assert_called_once()
        provider.client.set_issue_status.assert_called_once()

    # # _create_issue_impl
    def test_issues_providers_bitbucketprovider_create_issue_impl(self, mocker):
        mocker.patch("issues.providers.BitbucketProvider._get_client")
        mocker.patch("issues.providers.BitbucketProvider._get_repository")
        user = mocker.MagicMock()
        provider = BitbucketProvider(user)
        provider.repo = ("workspace", "repo_slug")
        provider.client = mocker.MagicMock()
        provider._create_issue_impl("title", "body", ["label1"])
        provider.client.create_issue.assert_called_once()

    # # _fetch_issues_impl
    def test_issues_providers_bitbucketprovider_fetch_issues_impl(self, mocker):
        mocker.patch("issues.providers.BitbucketProvider._get_client")
        mocker.patch("issues.providers.BitbucketProvider._get_repository")
        user = mocker.MagicMock()
        provider = BitbucketProvider(user)
        provider.repo = ("workspace", "repo_slug")
        provider.client = mocker.MagicMock()
        provider._fetch_issues_impl("all", "since")
        provider.client.get_issues.assert_called_once()

    # # _get_issue_by_number_impl
    def test_issues_providers_bitbucketprovider_get_issue_by_number_impl(self, mocker):
        mocker.patch("issues.providers.BitbucketProvider._get_client")
        mocker.patch("issues.providers.BitbucketProvider._get_repository")
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


class TestIssuesProvidersGithubProvider:
    """Testing class for :class:`issues.providers.GithubProvider`."""

    def test_issues_providers_githubprovider_inits_name(self):
        assert GithubProvider.name == "github"

    # # __init__
    def test_issues_providers_githubprovider_init_functionality(self, mocker):
        mocked_client = mocker.patch("issues.providers.GithubProvider._get_client")
        mocked_repo = mocker.patch("issues.providers.GithubProvider._get_repository")
        user = mocker.MagicMock()
        provider = GithubProvider(user)
        assert provider.user == user
        assert provider.client == mocked_client.return_value
        assert provider.repo == mocked_repo.return_value
        mocked_client.assert_called_once_with(issue_tracker_api_token=None)
        mocked_repo.assert_called_once_with()

    # # _get_client
    def test_issues_providers_bitbucketprovider_get_client_with_provided_token(
        self, mocker
    ):
        mocked_auth_token = mocker.patch("issues.providers.Auth.Token")
        mocked_github = mocker.patch("issues.providers.Github")
        mocked_githubapp = mocker.patch("issues.providers.GitHubApp")
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

    # # _get_repository
    def test_issues_providers_githubprovider_get_repository_for_client_none(
        self, mocker
    ):
        mocker.patch("issues.providers.GithubProvider._get_client", return_value=None)
        provider = GithubProvider(mocker.MagicMock())
        returned = provider._get_repository()
        assert returned is None

    def test_issues_providers_githubprovider_get_repository_functionality(self, mocker):
        mock_client = mocker.MagicMock()
        mocker.patch(
            "issues.providers.GithubProvider._get_client", return_value=mock_client
        )
        provider = GithubProvider(mocker.MagicMock())
        mock_client.get_repo.reset_mock()
        returned = provider._get_repository()
        assert returned == mock_client.get_repo.return_value
        mock_client.get_repo.assert_called_once_with(
            f"{settings.ISSUE_TRACKER_OWNER}/{settings.ISSUE_TRACKER_NAME}"
        )

    # # close_issue_with_labels
    def test_issues_providers_githubprovider_close_issue_with_labels_for_no_client(
        self, mocker
    ):
        mocker.patch("issues.providers.GithubProvider._get_client")
        mocker.patch("issues.providers.GithubProvider._get_repository")
        user = mocker.MagicMock()
        provider = GithubProvider(user)
        provider.client = None
        returned = provider.close_issue_with_labels(
            mocker.MagicMock(), mocker.MagicMock()
        )
        assert returned == {"success": False, "error": MISSING_TOKEN_TEXT}

    # # create_issue
    def test_issues_providers_githubprovider_create_issue_for_no_client(self, mocker):
        mocker.patch("issues.providers.GithubProvider._get_client")
        mocker.patch("issues.providers.GithubProvider._get_repository")
        user = mocker.MagicMock()
        provider = GithubProvider(user)
        provider.client = None
        returned = provider.create_issue(mocker.MagicMock(), mocker.MagicMock())
        assert returned == {"success": False, "error": MISSING_TOKEN_TEXT}

    # # fetch_issues
    def test_issues_providers_githubprovider_fetch_issues_for_no_client(self, mocker):
        mocker.patch("issues.providers.GithubProvider._get_client")
        mocker.patch("issues.providers.GithubProvider._get_repository")
        user = mocker.MagicMock()
        provider = GithubProvider(user)
        provider.client = None
        returned = provider.fetch_issues()
        assert returned == []

    # # issue_by_number
    def test_issues_providers_githubprovider_issue_by_number_for_no_client(
        self, mocker
    ):
        mocker.patch("issues.providers.GithubProvider._get_client")
        mocker.patch("issues.providers.GithubProvider._get_repository")
        user = mocker.MagicMock()
        provider = GithubProvider(user)
        provider.client = None
        returned = provider.issue_by_number(mocker.MagicMock())
        assert returned == {"success": False, "error": MISSING_TOKEN_TEXT}

    # # set_labels_to_issue
    def test_issues_providers_githubprovider_set_labels_to_issue_for_no_client(
        self, mocker
    ):
        mocker.patch("issues.providers.GithubProvider._get_client")
        mocker.patch("issues.providers.GithubProvider._get_repository")
        user = mocker.MagicMock()
        provider = GithubProvider(user)
        provider.client = None
        returned = provider.set_labels_to_issue(mocker.MagicMock(), mocker.MagicMock())
        assert returned == {"success": False, "error": MISSING_TOKEN_TEXT}


class TestIssuesProvidersGitlabProvider:
    """Testing class for :class:`issues.providers.GitlabProvider`."""

    def test_issues_providers_gitlabprovider_inits_name(self):
        assert GitlabProvider.name == "gitlab"

    # # __init__
    def test_issues_providers_gitlabprovider_init_functionality(self, mocker):
        mocked_client = mocker.patch("issues.providers.GitlabProvider._get_client")
        mocked_repo = mocker.patch("issues.providers.GitlabProvider._get_repository")
        user = mocker.MagicMock()
        provider = GitlabProvider(user)
        assert provider.user == user
        assert provider.client == mocked_client.return_value
        assert provider.repo == mocked_repo.return_value
        mocked_client.assert_called_once_with(issue_tracker_api_token=None)
        mocked_repo.assert_called_once_with()

    # # _get_client
    def test_issues_providers_gitlabprovider_get_client(self, mocker):
        mocked_gitlab = mocker.patch("issues.providers.Gitlab")
        issue_tracker_api_token = mocker.MagicMock()
        provider = GitlabProvider(mocker.MagicMock())
        mocked_gitlab.reset_mock()
        url = "https://gitlab.com"
        returned = provider._get_client(issue_tracker_api_token=issue_tracker_api_token)
        assert returned == mocked_gitlab.return_value
        mocked_gitlab.assert_called_once_with(
            url=url, private_token=issue_tracker_api_token
        )

    # # _get_repository
    def test_issues_providers_gitlabprovider_get_repository_for_client_none(
        self, mocker
    ):
        mocker.patch("issues.providers.GitlabProvider._get_client", return_value=None)
        provider = GitlabProvider(mocker.MagicMock())
        returned = provider._get_repository()
        assert returned is None

    def test_issues_providers_gitlabprovider_get_repository_functionality(self, mocker):
        mock_client = mocker.MagicMock()
        mocker.patch(
            "issues.providers.GitlabProvider._get_client", return_value=mock_client
        )
        provider = GitlabProvider(mocker.MagicMock())
        mock_client.projects.get.reset_mock()
        returned = provider._get_repository()
        assert returned == mock_client.projects.get.return_value
        mock_client.projects.get.assert_called_once_with(
            f"{settings.ISSUE_TRACKER_OWNER}/{settings.ISSUE_TRACKER_NAME}"
        )

    # # _close_issue_with_labels_impl
    def test_issues_providers_gitlabprovider_close_issue_with_labels_impl(self, mocker):
        mocker.patch("issues.providers.GitlabProvider._get_client")
        mocker.patch("issues.providers.GitlabProvider._get_repository")
        user = mocker.MagicMock()
        provider = GitlabProvider(user)
        mock_issue = mocker.MagicMock()
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

    # # _create_issue_impl
    def test_issues_providers_gitlabprovider_create_issue_impl(self, mocker):
        mocker.patch("issues.providers.GitlabProvider._get_client")
        mocker.patch("issues.providers.GitlabProvider._get_repository")
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
    def test_issues_providers_gitlabprovider_fetch_issues_impl(self, mocker):
        mocker.patch("issues.providers.GitlabProvider._get_client")
        mocker.patch("issues.providers.GitlabProvider._get_repository")
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
    def test_issues_providers_gitlabprovider_get_issue_by_number_impl(self, mocker):
        mocker.patch("issues.providers.GitlabProvider._get_client")
        mocker.patch("issues.providers.GitlabProvider._get_repository")
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

    # # _set_labels_to_issue_impl
    def test_issues_providers_gitlabprovider_set_labels_to_issue_impl(self, mocker):
        mocker.patch("issues.providers.GitlabProvider._get_client")
        mocker.patch("issues.providers.GitlabProvider._get_repository")
        user = mocker.MagicMock()
        provider = GitlabProvider(user)
        mock_issue = mocker.MagicMock()
        provider.repo = mocker.MagicMock()
        provider.repo.issues.get.return_value = mock_issue

        labels_to_set = ["priority::high"]
        result = provider._set_labels_to_issue_impl(1, labels_to_set)

        provider.repo.issues.get.assert_called_once_with(1)
        mock_issue.labels = labels_to_set
        mock_issue.save.assert_called_once()
        assert result["current_labels"] == labels_to_set
