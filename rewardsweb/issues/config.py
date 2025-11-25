"""Module containing issue trackers configuration."""

from utils.helpers import get_env_variable


def bitbucket_config():
    """Return Bitbucket configuration from environment variables.

    :return: Bitbucket configuration dictionary
    :rtype: dict
    """
    return {
        "client_key": get_env_variable("BITBUCKET_CLIENT_KEY", ""),
        "shared_secret": get_env_variable("BITBUCKET_SHARED_SECRET", ""),
    }


def github_config():
    """Return GitHub bot configuration from environment variables.

    :return: GitHub bot configuration dictionary
    :rtype: dict
    """
    return {
        "private_key_filename": get_env_variable("GITHUB_BOT_PRIVATE_KEY_FILENAME", ""),
        "client_id": get_env_variable("GITHUB_BOT_CLIENT_ID", ""),
        "installation_id": get_env_variable("GITHUB_BOT_INSTALLATION_ID", ""),
    }


def gitlab_config():
    """Return Telegram configuration from environment variables.

    :return: Telegram configuration dictionary
    :rtype: dict
    """
    return {
        "url": get_env_variable("GITLAB_URL", "https://gitlab.com"),
        "private_token": get_env_variable("GITLAB_PRIVATE_TOKEN", ""),
        "project_id": get_env_variable("GITLAB_PROJECT_ID", ""),
    }
