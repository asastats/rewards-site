import pytest


@pytest.fixture
def discord_config():
    return {
        "bot_user_id": "bot_user_id",
        "token": "token",
        "excluded_channels": "12345,67890",
        "included_channels": "123",
        "check_interval": 8,
    }


@pytest.fixture
def reddit_config():
    return {
        "client_id": "test_client_id",
        "client_secret": "test_client_secret",
        "user_agent": "test_user_agent",
        "username": "test_username",
        "password": "test_password",
    }


@pytest.fixture
def reddit_subreddits():
    return ["python", "test"]


@pytest.fixture
def telegram_config():
    return {
        "api_id": "test_api_id",
        "api_hash": "test_api_hash",
        "session_name": "test_session",
        "bot_username": "test_bot",
    }


@pytest.fixture
def telegram_chats():
    return ["group1", "group2"]


@pytest.fixture
def twitter_config():
    return {
        "bearer_token": "test_bearer_token",
        "consumer_key": "test_consumer_key",
        "consumer_secret": "test_consumer_secret",
        "access_token": "test_access_token",
        "access_token_secret": "test_access_token_secret",
    }


@pytest.fixture
def twitterapiio_config():
    return {
        "api_key": "test_api_key",
        "target_handle": "test_target_handle",
        "batch_size": 10,
    }
