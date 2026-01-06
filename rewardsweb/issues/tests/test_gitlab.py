"""Testing module for :py:mod:`issues.gitlab` module."""

import os

from django.conf import settings

from issues.gitlab import     GitlabProvider


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
    def test_issues_gitlab_gitlabprovider_get_repository_for_client_none(
        self, mocker
    ):
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
        mocker.patch(
            "issues.gitlab.GitlabProvider._get_repository", return_value=None
        )
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
