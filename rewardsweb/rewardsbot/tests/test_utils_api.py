"""Unit tests for :py:mod:`rewardsbot.utils.api` module.

This module contains tests for the ApiService class and its
HTTP request functionality.
"""

from unittest import mock

import aiohttp
import pytest

from rewardsbot.utils.api import BASE_URL, ApiService


class TestUtilsApi:
    """Testing class for :py:mod:`rewardsbot.utils.api` components."""

    # # ApiService initialization and lifecycle
    @pytest.mark.asyncio
    async def test_utils_api_api_service_initialization(self):
        """Test ApiService initialization without session."""
        api_service = ApiService()
        assert api_service.session is None

    @pytest.mark.asyncio
    async def test_utils_api_initialize_success(self, mocker):
        """Test initialize creates aiohttp session."""
        api_service = ApiService()

        with mock.patch("aiohttp.ClientSession") as mock_session_class, mock.patch(
            "rewardsbot.utils.api.logger"
        ) as mock_logger:

            mock_session_instance = mocker.AsyncMock()
            mock_session_class.return_value = mock_session_instance

            await api_service.initialize()

            mock_session_class.assert_called_once_with(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={"Content-Type": "application/json"},
            )
            mock_logger.info.assert_any_call("🔗 Initializing API service...")
            mock_logger.info.assert_any_call("✅ API service initialized")
            assert api_service.session == mock_session_instance

    @pytest.mark.asyncio
    async def test_utils_api_close_with_session(self, mocker):
        """Test close properly closes existing session."""
        api_service = ApiService()
        mock_session = mocker.AsyncMock()
        api_service.session = mock_session

        with mock.patch("rewardsbot.utils.api.logger") as mock_logger:
            await api_service.close()

            mock_session.close.assert_called_once()
            mock_logger.info.assert_called_once_with("✅ API service closed")

    @pytest.mark.asyncio
    async def test_utils_api_close_without_session(self, mocker):
        """Test close handles missing session gracefully."""
        api_service = ApiService()
        api_service.session = None

        with mock.patch("rewardsbot.utils.api.logger") as mock_logger:
            await api_service.close()

            mock_logger.info.assert_not_called()

    # # ApiService.make_request - test error cases only (simpler approach)
    @pytest.mark.asyncio
    async def test_utils_api_make_request_without_initialization(self):
        """Test make_request raises error without session initialization."""
        api_service = ApiService()
        # session is None by default

        with pytest.raises(AttributeError):
            await api_service.make_request("test/endpoint")

    @pytest.mark.asyncio
    async def test_utils_api_make_request_error_handling(self, mocker):
        """Test make_request error handling through endpoint methods."""
        api_service = ApiService()
        api_service.make_request = mocker.AsyncMock()

        # Test that errors from make_request are propagated
        test_error = aiohttp.ClientConnectionError("Connection failed")
        api_service.make_request.side_effect = test_error

        with mock.patch("rewardsbot.utils.api.logger") as mock_logger:
            with pytest.raises(aiohttp.ClientConnectionError):
                await api_service.fetch_current_cycle()

            api_service.make_request.assert_called_once_with("cycles/current")
            mock_logger.info.assert_called_once_with("🔗 fetch_current_cycle called")

    @pytest.mark.asyncio
    async def test_utils_api_make_request_for_get(self, mocker):
        mock_aiohttp = mocker.patch("rewardsbot.utils.api.aiohttp")
        mock_session = mock.Mock()
        mock_session_get_cm = mock.AsyncMock()
        mock_aiohttp.ClientSession.return_value = mock_session
        mock_session.get.return_value = mock_session_get_cm
        data = "this is the data"
        mocked_response = mock_session_get_cm.__aenter__.return_value
        status = "status1"
        mocked_response.status = status
        mocked_response.json.return_value = data
        api_service = ApiService()
        await api_service.initialize()
        mocked_logger = mocker.patch("rewardsbot.utils.api.logger")
        cycle_number = 505
        endpoint = f"cycles/{cycle_number}"
        params = {"param": 1}
        url = f"{BASE_URL}/{endpoint}"
        returned = await api_service.make_request(endpoint, params=params)
        assert returned == data
        calls = [
            mocker.call(f"🌐 API Request: GET {url} with params: {params}"),
            mocker.call(f"📡 API Response Status: {status} for {url}"),
            mocker.call(
                f"✅ API Response received for {endpoint}: {len(str(data))} bytes"
            ),
        ]
        mocked_logger.info.assert_has_calls(calls, any_order=True)
        assert mocked_logger.info.call_count == 3
        mocked_response.raise_for_status.assert_called_once_with()
        mocked_response.json.assert_called_once_with()

    @pytest.mark.asyncio
    async def test_utils_api_make_request_for_post(self, mocker):
        mock_aiohttp = mocker.patch("rewardsbot.utils.api.aiohttp")
        mock_session = mock.Mock()
        mock_session_post_cm = mock.AsyncMock()
        mock_aiohttp.ClientSession.return_value = mock_session
        mock_session.post.return_value = mock_session_post_cm
        data = "this is the data"
        mocked_response = mock_session_post_cm.__aenter__.return_value
        status = "status1"
        mocked_response.status = status
        mocked_response.json.return_value = data
        api_service = ApiService()
        await api_service.initialize()
        mocked_logger = mocker.patch("rewardsbot.utils.api.logger")
        cycle_number = 505
        endpoint = f"cycles/{cycle_number}"
        params = {"param": 1}
        url = f"{BASE_URL}/{endpoint}"
        returned = await api_service.make_request(
            endpoint, params=params, method="POST"
        )
        assert returned == data
        calls = [
            mocker.call(f"🌐 API Request: POST {url} with params: {params}"),
            mocker.call(f"📡 API Response Status: {status} for {url}"),
            mocker.call(
                f"✅ API Response received for {endpoint}: {len(str(data))} bytes"
            ),
        ]
        mocked_logger.info.assert_has_calls(calls, any_order=True)
        assert mocked_logger.info.call_count == 3
        mocked_response.raise_for_status.assert_called_once_with()
        mocked_response.json.assert_called_once_with()

    @pytest.mark.asyncio
    async def test_utils_api_make_request_for_clienterror(self, mocker):
        mock_aiohttp = mocker.patch("rewardsbot.utils.api.aiohttp")
        mock_session = mock.Mock()
        mock_session_get_cm = mock.AsyncMock()
        mock_aiohttp.ClientSession.return_value = mock_session
        mock_session.post.side_effect = aiohttp.ClientError("error 1")
        mocked_response = mock_session_get_cm.__aenter__.return_value
        status = "status1"
        mocked_response.status = status
        mocked_response.json.side_effect = aiohttp.ClientError("error 1")
        api_service = ApiService()
        await api_service.initialize()
        mocked_logger = mocker.patch("rewardsbot.utils.api.logger")
        cycle_number = 505
        endpoint = f"cycles/{cycle_number}"
        params = {"param": 1}
        url = f"{BASE_URL}/{endpoint}"
        with pytest.raises(Exception):
            await api_service.make_request(endpoint, params=params, method="POST")
        mocked_logger.info.assert_called_once_with(
            f"🌐 API Request: POST {url} with params: {params}"
        )
        mocked_logger.error.assert_called_once_with(
            f"❌ Unexpected API error for {endpoint}: error 1"
        )

    # # ApiService specific endpoint methods - test these instead of make_request directly
    @pytest.mark.asyncio
    async def test_utils_api_fetch_cycle(self, mocker):
        """Test fetch_cycle calls correct endpoint."""
        api_service = ApiService()
        api_service.make_request = mocker.AsyncMock()
        cycle_number = 5
        expected_response = {"id": 5, "status": "active"}
        api_service.make_request.return_value = expected_response

        with mock.patch("rewardsbot.utils.api.logger") as mock_logger:
            result = await api_service.fetch_cycle(cycle_number)

            api_service.make_request.assert_called_once_with(f"cycles/{cycle_number}")
            mock_logger.info.assert_called_once_with("🔗 fetch_cycle called")
            assert result == expected_response

    @pytest.mark.asyncio
    async def test_utils_api_fetch_current_cycle(self, mocker):
        """Test fetch_current_cycle calls correct endpoint."""
        api_service = ApiService()
        api_service.make_request = mocker.AsyncMock()
        expected_response = {"id": 10, "current": True}
        api_service.make_request.return_value = expected_response

        with mock.patch("rewardsbot.utils.api.logger") as mock_logger:
            result = await api_service.fetch_current_cycle()

            api_service.make_request.assert_called_once_with("cycles/current")
            mock_logger.info.assert_called_once_with("🔗 fetch_current_cycle called")
            assert result == expected_response

    @pytest.mark.asyncio
    async def test_utils_api_fetch_current_cycle_plain(self, mocker):
        """Test fetch_current_cycle_plain calls correct endpoint."""
        api_service = ApiService()
        api_service.make_request = mocker.AsyncMock()
        expected_response = {"id": 10, "plain": True}
        api_service.make_request.return_value = expected_response

        with mock.patch("rewardsbot.utils.api.logger") as mock_logger:
            result = await api_service.fetch_current_cycle_plain()

            api_service.make_request.assert_called_once_with("cycles/current/plain")
            mock_logger.info.assert_called_once_with(
                "🔗 fetch_current_cycle_plain called"
            )
            assert result == expected_response

    @pytest.mark.asyncio
    async def test_utils_api_fetch_cycle_by_id(self, mocker):
        """Test fetch_cycle_by_id calls correct endpoint."""
        api_service = ApiService()
        api_service.make_request = mocker.AsyncMock()
        cycle_id = 123
        expected_response = {"id": 123, "data": "cycle_data"}
        api_service.make_request.return_value = expected_response

        with mock.patch("rewardsbot.utils.api.logger") as mock_logger:
            result = await api_service.fetch_cycle_by_id(cycle_id)

            api_service.make_request.assert_called_once_with(f"cycles/{cycle_id}")
            mock_logger.info.assert_called_once_with(
                f"🔗 fetch_cycle_by_id called for cycle {cycle_id}"
            )
            assert result == expected_response

    @pytest.mark.asyncio
    async def test_utils_api_fetch_cycle_by_id_plain(self, mocker):
        """Test fetch_cycle_by_id_plain calls correct endpoint."""
        api_service = ApiService()
        api_service.make_request = mocker.AsyncMock()
        cycle_id = 456
        expected_response = {"id": 456, "plain": True}
        api_service.make_request.return_value = expected_response

        with mock.patch("rewardsbot.utils.api.logger") as mock_logger:
            result = await api_service.fetch_cycle_by_id_plain(cycle_id)

            api_service.make_request.assert_called_once_with(f"cycles/{cycle_id}/plain")
            mock_logger.info.assert_called_once_with(
                f"🔗 fetch_cycle_by_id_plain called for cycle {cycle_id}"
            )
            assert result == expected_response

    @pytest.mark.asyncio
    async def test_utils_api_fetch_contributions_tail(self, mocker):
        """Test fetch_contributions_tail calls correct endpoint."""
        api_service = ApiService()
        api_service.make_request = mocker.AsyncMock()
        expected_response = [{"id": 1}, {"id": 2}, {"id": 3}]
        api_service.make_request.return_value = expected_response

        with mock.patch("rewardsbot.utils.api.logger") as mock_logger:
            result = await api_service.fetch_contributions_tail()

            api_service.make_request.assert_called_once_with("contributions/tail")
            mock_logger.info.assert_called_once_with(
                "🔗 fetch_contributions_tail called"
            )
            assert result == expected_response

    @pytest.mark.asyncio
    async def test_utils_api_fetch_user_contributions(self, mocker):
        """Test fetch_user_contributions calls correct endpoint with params."""
        api_service = ApiService()
        api_service.make_request = mocker.AsyncMock()
        username = "test_user"
        expected_response = [{"user": "test_user", "contributions": []}]
        api_service.make_request.return_value = expected_response

        with mock.patch("rewardsbot.utils.api.logger") as mock_logger:
            result = await api_service.fetch_user_contributions(username)

            api_service.make_request.assert_called_once_with(
                "contributions", {"name": username}
            )
            mock_logger.info.assert_called_once_with(
                f"🔗 fetch_user_contributions called for {username}"
            )
            assert result == expected_response

    @pytest.mark.asyncio
    async def test_utils_api_post_suggestion(self, mocker):
        """Test post_suggestion calls correct endpoint with data."""
        api_service = ApiService()
        api_service.make_request = mocker.AsyncMock()

        contribution_type = "Forum Post"
        level = "2"
        username = "suggestion_user"
        comment = "Great contribution!"
        message_url = "https://discord.com/channels/123/456/789"

        expected_params = {
            "type": contribution_type,
            "level": level,
            "username": username,
            "comment": comment,
            "url": message_url,
            "platform": "Discord",
        }
        expected_response = {"id": 123, "status": "created"}
        api_service.make_request.return_value = expected_response

        with mock.patch("rewardsbot.utils.api.logger") as mock_logger:
            result = await api_service.post_suggestion(
                contribution_type, level, username, comment, message_url
            )

            api_service.make_request.assert_called_once_with(
                "addcontribution", expected_params, "POST"
            )
            mock_logger.info.assert_called_once_with(
                f"🔗 post_suggestion called for {username}"
            )
            assert result == expected_response

    @pytest.mark.asyncio
    async def test_utils_api_post_suggestion_empty_comment(self, mocker):
        """Test post_suggestion handles empty comment."""
        api_service = ApiService()
        api_service.make_request = mocker.AsyncMock()

        contribution_type = "Blog Post"
        level = "1"
        username = "empty_comment_user"
        comment = ""  # Empty comment
        message_url = "https://discord.com/channels/123/456/790"

        expected_params = {
            "type": contribution_type,
            "level": level,
            "username": username,
            "comment": comment,
            "url": message_url,
            "platform": "Discord",
        }
        expected_response = {"id": 124, "status": "created"}
        api_service.make_request.return_value = expected_response

        with mock.patch("rewardsbot.utils.api.logger"):
            result = await api_service.post_suggestion(
                contribution_type, level, username, comment, message_url
            )

            api_service.make_request.assert_called_once_with(
                "addcontribution", expected_params, "POST"
            )
            assert result == expected_response

    @pytest.mark.asyncio
    async def test_utils_api_post_suggestion_none_comment(self, mocker):
        """Test post_suggestion handles None comment."""
        api_service = ApiService()
        api_service.make_request = mocker.AsyncMock()

        contribution_type = "Article Translation"
        level = "3"
        username = "none_comment_user"
        comment = None  # None comment
        message_url = "https://discord.com/channels/123/456/791"

        expected_params = {
            "type": contribution_type,
            "level": level,
            "username": username,
            "comment": comment,
            "url": message_url,
            "platform": "Discord",
        }
        expected_response = {"id": 125, "status": "created"}
        api_service.make_request.return_value = expected_response

        with mock.patch("rewardsbot.utils.api.logger"):
            result = await api_service.post_suggestion(
                contribution_type, level, username, comment, message_url
            )

            api_service.make_request.assert_called_once_with(
                "addcontribution", expected_params, "POST"
            )
            assert result == expected_response

    # # Edge cases
    @pytest.mark.asyncio
    async def test_utils_api_special_characters_in_username(self, mocker):
        """Test API methods handle special characters in usernames."""
        api_service = ApiService()
        api_service.make_request = mocker.AsyncMock()

        special_usernames = [
            "User-With-Dash",
            "User_With_Underscore",
            "User.With.Dots",
            "User With Spaces",
            "User@Special",
            "User123",
        ]

        for username in special_usernames:
            await api_service.fetch_user_contributions(username)

            api_service.make_request.assert_called_with(
                "contributions", {"name": username}
            )

            # Reset mock for next iteration
            api_service.make_request.reset_mock()

    @pytest.mark.asyncio
    async def test_utils_api_endpoint_methods_propagate_errors(self, mocker):
        """Test that all endpoint methods propagate make_request errors."""
        api_service = ApiService()
        api_service.make_request = mocker.AsyncMock()

        error_cases = [
            (aiohttp.ClientConnectionError("Connection failed"), "connection error"),
            (
                aiohttp.ClientResponseError(
                    request_info=mocker.Mock(),
                    history=(),
                    status=500,
                    message="Server Error",
                    headers={},
                ),
                "HTTP error",
            ),
            (ValueError("Unexpected error"), "unexpected error"),
        ]

        test_methods = [
            ("fetch_cycle", lambda: api_service.fetch_cycle(5)),
            ("fetch_current_cycle", lambda: api_service.fetch_current_cycle()),
            (
                "fetch_current_cycle_plain",
                lambda: api_service.fetch_current_cycle_plain(),
            ),
            (
                "fetch_contributions_tail",
                lambda: api_service.fetch_contributions_tail(),
            ),
            (
                "fetch_user_contributions",
                lambda: api_service.fetch_user_contributions("test"),
            ),
        ]

        for error, error_description in error_cases:
            for method_name, method_call in test_methods:
                api_service.make_request.side_effect = error

                with pytest.raises(type(error)):
                    await method_call()

                # Reset mock for next iteration
                api_service.make_request.reset_mock()

    @pytest.mark.asyncio
    async def test_utils_api_post_suggestion_error_propagation(self, mocker):
        """Test post_suggestion propagates make_request errors."""
        api_service = ApiService()
        api_service.make_request = mocker.AsyncMock()

        suggestion_error = aiohttp.ClientResponseError(
            request_info=mocker.Mock(),
            history=(),
            status=400,
            message="Bad Request",
            headers={},
        )
        api_service.make_request.side_effect = suggestion_error

        with mock.patch("rewardsbot.utils.api.logger") as mock_logger:
            with pytest.raises(aiohttp.ClientResponseError):
                await api_service.post_suggestion(
                    "Forum Post", "2", "error_user", "test", "https://example.com"
                )

            api_service.make_request.assert_called_once()
            mock_logger.info.assert_called_once_with(
                "🔗 post_suggestion called for error_user"
            )
