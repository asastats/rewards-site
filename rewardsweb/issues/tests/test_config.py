"""Testing module for :py:mod:`issues.config` module."""

from issues.config import bitbucket_config, github_config, gitlab_config


class TestIssuesConfig:
    """Testing class for :py:mod:`issues.config` module."""

    # bitbucket_config
    def test_issues_config_bitbucket_config_functionality(self, mocker):
        mock_env = mocker.patch("issues.config.get_env_variable")
        mock_env.side_effect = lambda key, default=None: {
            "BITBUCKET_CLIENT_KEY": "test_client",
            "BITBUCKET_SHARED_SECRET": "test_secret",
        }.get(key, default)
        result = bitbucket_config()
        expected_config = {
            "client_key": "test_client",
            "shared_secret": "test_secret",
        }
        assert result == expected_config
        calls = [
            mocker.call("BITBUCKET_CLIENT_KEY", ""),
            mocker.call("BITBUCKET_SHARED_SECRET", ""),
        ]
        mock_env.assert_has_calls(calls, any_order=True)
        assert mock_env.call_count == 2

    # github_config
    def test_issues_config_github_config_functionality(self, mocker):
        mock_env = mocker.patch("issues.config.get_env_variable")
        mock_env.side_effect = lambda key, default=None: {
            "GITHUB_BOT_PRIVATE_KEY_FILENAME": "test_filename",
            "GITHUB_BOT_CLIENT_ID": "test_client",
            "GITHUB_BOT_INSTALLATION_ID": "test_installation",
        }.get(key, default)
        result = github_config()
        expected_config = {
            "private_key_filename": "test_filename",
            "client_id": "test_client",
            "installation_id": "test_installation",
        }
        assert result == expected_config
        calls = [
            mocker.call("GITHUB_BOT_PRIVATE_KEY_FILENAME", ""),
            mocker.call("GITHUB_BOT_CLIENT_ID", ""),
            mocker.call("GITHUB_BOT_INSTALLATION_ID", ""),
        ]
        mock_env.assert_has_calls(calls, any_order=True)
        assert mock_env.call_count == 3

    # gitlab_config
    def test_issues_config_gitlab_config_functionality(self, mocker):
        mock_env = mocker.patch("issues.config.get_env_variable")
        mock_env.side_effect = lambda key, default=None: {
            "GITLAB_URL": "test_url",
            "GITLAB_PRIVATE_TOKEN": "test_token",
            "GITLAB_PROJECT_ID": "test_project",
        }.get(key, default)
        result = gitlab_config()
        expected_config = {
            "url": "test_url",
            "private_token": "test_token",
            "project_id": "test_project",
        }
        assert result == expected_config
        calls = [
            mocker.call("GITLAB_URL", "https://gitlab.com"),
            mocker.call("GITLAB_PRIVATE_TOKEN", ""),
            mocker.call("GITLAB_PROJECT_ID", ""),
        ]
        mock_env.assert_has_calls(calls, any_order=True)
        assert mock_env.call_count == 3
