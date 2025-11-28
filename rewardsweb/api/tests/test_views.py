"""Testing module for :py:mod:`api.views` module."""

from unittest.mock import AsyncMock, patch

import pytest
from adrf.views import APIView
from rest_framework import status
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from api.views import (
    AddContributionView,
    ContributionsTailView,
    ContributionsView,
    CurrentCycleAggregatedView,
    CurrentCyclePlainView,
    CycleAggregatedView,
    CyclePlainView,
    IsLocalhostPermission,
    LocalhostAPIView,
    aggregated_cycle_response,
    contributions_response,
)
from core.models import Contributor, Cycle, Reward, RewardType, SocialPlatform


class TestIsLocalhostPermission:
    """Testing class for :class:`api.permissions.IsLocalhostPermission`."""

    # # IsLocalhostPermission
    def test_api_permissions_islocalhostpermission_issubclass_of_basepermission(self):
        assert issubclass(IsLocalhostPermission, BasePermission)

    @pytest.mark.parametrize(
        "meta",
        [
            {"REMOTE_ADDR": "127.0.0.1"},
            {"REMOTE_ADDR": "localhost"},
            {"REMOTE_ADDR": "::1"},
        ],
    )
    def test_api_permissions_islocalhostpermission_has_permission_for_true(
        self, meta, mocker
    ):
        request = mocker.MagicMock()
        request.META = meta
        permission = IsLocalhostPermission()
        assert permission.has_permission(request, mocker.MagicMock()) is True

    @pytest.mark.parametrize(
        "meta",
        [
            {},
            {"REMOTE_ADDR1": "127.0.0.1"},
            {"REMOTE_ADDR": "localhost1"},
            {"REMOTE_ADDR": "192.168.0.1"},
            {"REMOTE_ADDR": "192.168.1.1"},
            {"REMOTE_ADDR": "192.168.1.100"},
        ],
    )
    def test_api_permissions_islocalhostpermission_has_permission_for_false(
        self, meta, mocker
    ):
        request = mocker.MagicMock()
        request.META = meta
        permission = IsLocalhostPermission()
        assert permission.has_permission(request, mocker.MagicMock()) is False


class TestApiViewsHelpers:
    """Testing class for :py:mod:`api.views` helper functions."""

    @pytest.mark.asyncio
    async def test_api_views_aggregated_cycle_response_with_none_cycle(self):
        response = await aggregated_cycle_response(None)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data == {"error": "Cycle not found"}

    @pytest.mark.asyncio
    async def test_api_views_aggregated_cycle_response_with_valid_cycle(self, mocker):
        mock_cycle = mocker.MagicMock(spec=Cycle)
        mock_cycle.id = 1
        mock_cycle.start = "2023-01-01"
        mock_cycle.end = "2023-01-31"
        mock_cycle.contributor_rewards = {"addr1": 100, "addr2": 200}
        mock_cycle.total_rewards = 300

        # Mock sync_to_async calls to return awaitable objects
        with patch("api.views.sync_to_async") as mock_sync_to_async:
            # Create awaitable mocks that return the expected values
            mock_contributor_rewards = AsyncMock(
                return_value={"addr1": 100, "addr2": 200}
            )
            mock_total_rewards = AsyncMock(return_value=300)
            mock_sync_to_async.side_effect = [
                mock_contributor_rewards,
                mock_total_rewards,
            ]

            # Mock serializer
            mock_serializer = mocker.MagicMock()
            mock_serializer.data = {"id": 1, "start": "2023-01-01", "end": "2023-01-31"}
            mock_serializer.is_valid.return_value = True
            with patch(
                "api.views.AggregatedCycleSerializer", return_value=mock_serializer
            ):
                response = await aggregated_cycle_response(mock_cycle)

        assert isinstance(response, Response)
        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_api_views_contributions_response(self, mocker):
        mock_contributions = mocker.MagicMock()
        mock_humanized_data = [{"id": 1, "contributor_name": "test"}]

        # Mock sync_to_async to return awaitable
        with patch("api.views.sync_to_async") as mock_sync_to_async:
            mock_humanize = AsyncMock(return_value=mock_humanized_data)
            mock_sync_to_async.return_value = mock_humanize

            # Mock serializer
            mock_serializer = mocker.MagicMock()
            mock_serializer.data = mock_humanized_data
            mock_serializer.is_valid.return_value = True
            with patch(
                "api.views.HumanizedContributionSerializer",
                return_value=mock_serializer,
            ):
                response = await contributions_response(mock_contributions)

        assert isinstance(response, Response)
        assert response.status_code == status.HTTP_200_OK


class TestLocalhostAPIView:
    """Testing class for :py:class:`api.views.LocalhostAPIView`."""

    # # IsLocalhostPermission
    def test_api_views_localhostview_is_subclass_of_apiview(self):
        assert issubclass(LocalhostAPIView, APIView)

    def test_api_views_localhostview_permission_classes(self):
        assert LocalhostAPIView.permission_classes == [IsLocalhostPermission]


class TestApiViewsCycleAggregatedView:
    """Testing class for :py:class:`api.views.CycleAggregatedView`."""

    def test_api_views_cycleaggregatedview_is_subclass_of_localhostapiview(self):
        assert issubclass(CycleAggregatedView, LocalhostAPIView)

    @pytest.mark.asyncio
    async def test_api_views_cycle_aggregated_view_get_existing_cycle(self, mocker):
        view = CycleAggregatedView()
        mock_request = mocker.MagicMock()
        cycle_id = 1

        mock_cycle = mocker.MagicMock(spec=Cycle)

        # Mock sync_to_async to return awaitable that returns the cycle
        with patch("api.views.sync_to_async") as mock_sync_to_async:
            mock_db_call = AsyncMock(return_value=mock_cycle)
            mock_sync_to_async.return_value = mock_db_call

            with patch(
                "api.views.aggregated_cycle_response", new_callable=AsyncMock
            ) as mock_response:
                mock_response.return_value = Response({"id": cycle_id})

                response = await view.get(mock_request, cycle_id)

                mock_sync_to_async.assert_called_once()
                mock_response.assert_called_once_with(mock_cycle)
                assert isinstance(response, Response)

    @pytest.mark.asyncio
    async def test_api_views_cycle_aggregated_view_get_nonexistent_cycle(self, mocker):
        view = CycleAggregatedView()
        mock_request = mocker.MagicMock()
        cycle_id = 999

        # Mock sync_to_async to return awaitable that returns None
        with patch("api.views.sync_to_async") as mock_sync_to_async:
            mock_db_call = AsyncMock(return_value=None)
            mock_sync_to_async.return_value = mock_db_call

            with patch(
                "api.views.aggregated_cycle_response", new_callable=AsyncMock
            ) as mock_response:
                mock_response.return_value = Response(
                    {"error": "Cycle not found"}, status=404
                )

                response = await view.get(mock_request, cycle_id)

                mock_response.assert_called_once_with(None)
                assert isinstance(response, Response)


class TestApiViewsCurrentCycleAggregatedView:
    """Testing class for :py:class:`api.views.CurrentCycleAggregatedView`."""

    def test_api_views_currentcycleaggregatedview_is_subclass_of_localhostapiview(self):
        assert issubclass(CurrentCycleAggregatedView, LocalhostAPIView)

    @pytest.mark.asyncio
    async def test_api_views_current_cycle_aggregated_view_get(self, mocker):
        view = CurrentCycleAggregatedView()
        mock_request = mocker.MagicMock()

        mock_cycle = mocker.MagicMock(spec=Cycle)

        # Mock sync_to_async to return awaitable
        with patch("api.views.sync_to_async") as mock_sync_to_async:
            mock_db_call = AsyncMock(return_value=mock_cycle)
            mock_sync_to_async.return_value = mock_db_call

            with patch(
                "api.views.aggregated_cycle_response", new_callable=AsyncMock
            ) as mock_response:
                mock_response.return_value = Response({"id": 1})

                response = await view.get(mock_request)

                mock_sync_to_async.assert_called_once()
                mock_response.assert_called_once_with(mock_cycle)
                assert isinstance(response, Response)


class TestApiViewsCyclePlainView:
    """Testing class for :py:class:`api.views.CyclePlainView`."""

    def test_api_views_cycleplainview_is_subclass_of_localhostapiview(self):
        assert issubclass(CyclePlainView, LocalhostAPIView)

    @pytest.mark.asyncio
    async def test_api_views_cycle_plain_view_get_existing_cycle(self, mocker):
        view = CyclePlainView()
        mock_request = mocker.MagicMock()
        cycle_id = 1

        mock_cycle = mocker.MagicMock(spec=Cycle)

        # Mock sync_to_async to return awaitable
        with patch("api.views.sync_to_async") as mock_sync_to_async:
            mock_db_call = AsyncMock(return_value=mock_cycle)
            mock_sync_to_async.return_value = mock_db_call

            with patch("api.views.CycleSerializer") as mock_serializer:
                mock_serializer_instance = mocker.MagicMock()
                mock_serializer_instance.data = {"id": cycle_id}
                mock_serializer.return_value = mock_serializer_instance

                response = await view.get(mock_request, cycle_id)

                mock_serializer.assert_called_once_with(mock_cycle)
                assert isinstance(response, Response)
                assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_api_views_cycle_plain_view_get_nonexistent_cycle(self, mocker):
        view = CyclePlainView()
        mock_request = mocker.MagicMock()
        cycle_id = 999

        # Mock sync_to_async to return awaitable that returns None
        with patch("api.views.sync_to_async") as mock_sync_to_async:
            mock_db_call = AsyncMock(return_value=None)
            mock_sync_to_async.return_value = mock_db_call

            response = await view.get(mock_request, cycle_id)

            assert isinstance(response, Response)
            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert response.data == {"error": "Cycle not found"}


class TestApiViewsCurrentCyclePlainView:
    """Testing class for :py:class:`api.views.CurrentCyclePlainView`."""

    def test_api_views_currentcycleplainview_is_subclass_of_localhostapiview(self):
        assert issubclass(CurrentCyclePlainView, LocalhostAPIView)

    @pytest.mark.asyncio
    async def test_api_views_current_cycle_plain_view_get(self, mocker):
        view = CurrentCyclePlainView()
        mock_request = mocker.MagicMock()

        mock_cycle = mocker.MagicMock(spec=Cycle)

        # Mock sync_to_async to return awaitable
        with patch("api.views.sync_to_async") as mock_sync_to_async:
            mock_db_call = AsyncMock(return_value=mock_cycle)
            mock_sync_to_async.return_value = mock_db_call

            with patch("api.views.CycleSerializer") as mock_serializer:
                mock_serializer_instance = mocker.MagicMock()
                mock_serializer_instance.data = {"id": 1}
                mock_serializer.return_value = mock_serializer_instance

                response = await view.get(mock_request)

                mock_serializer.assert_called_once_with(mock_cycle)
                assert isinstance(response, Response)
                assert response.status_code == status.HTTP_200_OK


class TestApiViewsContributionsView:
    """Testing class for :py:class:`api.views.ContributionsView`."""

    def test_api_views_contributionsview_is_subclass_of_localhostapiview(self):
        assert issubclass(ContributionsView, LocalhostAPIView)

    @pytest.mark.asyncio
    async def test_api_views_contributions_view_get_with_username(self, mocker):
        view = ContributionsView()
        mock_request = mocker.MagicMock()
        mock_request.GET = mocker.MagicMock()
        mock_request.GET.get.return_value = "testuser"

        mock_contributor = mocker.MagicMock(spec=Contributor)
        mock_queryset = mocker.MagicMock()

        # Mock sync_to_async calls to return awaitables
        with patch("api.views.sync_to_async") as mock_sync_to_async:
            mock_contributor_call = AsyncMock(return_value=mock_contributor)
            mock_queryset_call = AsyncMock(return_value=mock_queryset)
            mock_sync_to_async.side_effect = [mock_contributor_call, mock_queryset_call]

            with patch("api.views.Contribution.objects") as mock_contribution_objects:
                mock_contribution_objects.filter.return_value = mock_queryset
                with patch(
                    "api.views.contributions_response", new_callable=AsyncMock
                ) as mock_response:
                    mock_response.return_value = Response([{"id": 1}])

                    response = await view.get(mock_request)

                    mock_request.GET.get.assert_called_with("name")
                    mock_contribution_objects.filter.assert_called_once_with(
                        contributor=mock_contributor
                    )
                    mock_response.assert_called_once_with(mock_queryset)
                    assert isinstance(response, Response)

    @pytest.mark.asyncio
    async def test_api_views_contributions_view_get_without_username(self, mocker):
        view = ContributionsView()
        mock_request = mocker.MagicMock()
        mock_request.GET = mocker.MagicMock()
        mock_request.GET.get.return_value = None

        mock_queryset = mocker.MagicMock()

        # Mock sync_to_async to return awaitable
        with patch("api.views.sync_to_async") as mock_sync_to_async:
            mock_db_call = AsyncMock(return_value=mock_queryset)
            mock_sync_to_async.return_value = mock_db_call

            with patch("api.views.Contribution.objects") as mock_contribution_objects:
                # Mock the chain: objects.order_by().__getitem__()
                mock_order_by = mocker.MagicMock()
                mock_order_by.__getitem__.return_value = mock_queryset
                mock_contribution_objects.order_by.return_value = mock_order_by

                with patch(
                    "api.views.contributions_response", new_callable=AsyncMock
                ) as mock_response:
                    mock_response.return_value = Response([{"id": 1}])

                    response = await view.get(mock_request)

                    mock_request.GET.get.assert_called_with("name")
                    mock_contribution_objects.order_by.assert_called_once_with("-id")
                    mock_order_by.__getitem__.assert_called_once_with(
                        slice(None, 10)
                    )  # CONTRIBUTIONS_TAIL_SIZE * 2 = 5 * 2 = 10
                    mock_response.assert_called_once_with(mock_queryset)
                    assert isinstance(response, Response)


class TestApiViewsContributionsTailView:
    """Testing class for :py:class:`api.views.ContributionsTailView`."""

    def test_api_views_contributionstailview_is_subclass_of_localhostapiview(self):
        assert issubclass(ContributionsTailView, LocalhostAPIView)

    @pytest.mark.asyncio
    async def test_api_views_contributions_tail_view_get(self, mocker):
        view = ContributionsTailView()
        mock_request = mocker.MagicMock()

        mock_queryset = mocker.MagicMock()

        # Mock sync_to_async to return awaitable
        with patch("api.views.sync_to_async") as mock_sync_to_async:
            mock_db_call = AsyncMock(return_value=mock_queryset)
            mock_sync_to_async.return_value = mock_db_call

            with patch("api.views.Contribution.objects") as mock_contribution_objects:
                # Mock the chain: objects.order_by().__getitem__()
                mock_order_by = mocker.MagicMock()
                mock_order_by.__getitem__.return_value = mock_queryset
                mock_contribution_objects.order_by.return_value = mock_order_by

                with patch(
                    "api.views.contributions_response", new_callable=AsyncMock
                ) as mock_response:
                    mock_response.return_value = Response([{"id": 1}])

                    response = await view.get(mock_request)

                    mock_contribution_objects.order_by.assert_called_once_with("-id")
                    mock_order_by.__getitem__.assert_called_once_with(
                        slice(None, 5)
                    )  # CONTRIBUTIONS_TAIL_SIZE = 5
                    mock_response.assert_called_once_with(mock_queryset)
                    assert isinstance(response, Response)


class TestApiViewsAddContributionView:
    """Testing class for :py:class:`api.views.AddContributionView`."""

    def test_api_views_addcontributionview_is_subclass_of_localhostapiview(self):
        assert issubclass(AddContributionView, LocalhostAPIView)

    @pytest.mark.asyncio
    async def test_api_views_add_contribution_view_post_success(self, mocker):
        """Test successful contribution creation."""
        view = AddContributionView()
        mock_request = mocker.MagicMock()

        # Mock request data
        mock_request.data = {
            "username": "testuser",
            "platform": "twitter",
            "type": "[reward] Test Reward",
            "level": 1,
            "url": "http://example.io/contribution",
            "comment": "Test comment",
        }

        # Mock the sync_to_async wrapped function to return success
        with patch("api.views.sync_to_async") as mock_sync_to_async:
            mock_serializer_data = {"id": 1, "contributor": 1, "cycle": 1}
            async_mock = AsyncMock(return_value=(mock_serializer_data, None))
            mock_sync_to_async.return_value = async_mock

            response = await view.post(mock_request)

            # Verify sync_to_async was called with our request data
            mock_sync_to_async.assert_called_once()
            async_mock.assert_called_once_with(mock_request.data)

            # Verify response
            assert response.status_code == status.HTTP_201_CREATED
            assert response.data == mock_serializer_data

    @pytest.mark.asyncio
    async def test_api_views_add_contribution_view_post_validation_error(self, mocker):
        """Test contribution creation with validation errors."""
        view = AddContributionView()
        mock_request = mocker.MagicMock()

        # Mock request data
        mock_request.data = {
            "username": "testuser",
            "platform": "twitter",
            "type": "[reward] Test Reward",
            "level": 1,
            "url": "http://example.io/contribution",
            "comment": "Test comment",
        }

        # Mock validation errors
        validation_errors = {"url": ["Invalid URL"]}

        # Mock the sync_to_async wrapped function to return errors
        with patch("api.views.sync_to_async") as mock_sync_to_async:
            async_mock = AsyncMock(return_value=(None, validation_errors))
            mock_sync_to_async.return_value = async_mock

            response = await view.post(mock_request)

            # Verify error response
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert response.data == validation_errors

    @pytest.mark.asyncio
    async def test_api_views_add_contribution_view_post_integration(self, mocker):
        """Test the actual process_contribution function logic with proper mocks."""
        view = AddContributionView()
        mock_request = mocker.MagicMock()

        # Mock request data - using simple format that matches the parsing logic
        mock_request.data = {
            "username": "testuser",
            "platform": "twitter",
            "type": "[reward] Test Reward",  # Simple format: [single_word_label] name
            "level": 2,
            "url": "http://example.io/contribution",
            "comment": "Test comment",
        }

        # Mock all database objects
        mock_contributor = mocker.MagicMock(spec=Contributor)
        mock_contributor.id = 1

        mock_cycle = mocker.MagicMock(spec=Cycle)
        mock_cycle.id = 1

        mock_platform = mocker.MagicMock(spec=SocialPlatform)
        mock_platform.id = 1

        mock_reward_type = mocker.MagicMock(spec=RewardType)

        mock_reward = mocker.MagicMock(spec=Reward)
        mock_reward.id = 1

        mock_rewards_queryset = mocker.MagicMock()
        mock_rewards_queryset.__getitem__.return_value = mock_reward

        mock_serializer = mocker.MagicMock()
        mock_serializer_data = {"id": 1, "contributor": 1, "cycle": 1}
        mock_serializer.is_valid.return_value = True
        mock_serializer.data = mock_serializer_data

        # Mock the actual database calls inside process_contribution
        with patch("api.views.sync_to_async") as mock_sync_to_async:
            with patch("api.views.Contributor.objects") as mock_cntrs:
                mock_cntrs.from_full_handle.return_value = mock_contributor

                with patch("api.views.Cycle.objects") as mock_cycle_objs:
                    mock_cycle_objs.latest.return_value = mock_cycle

                    with patch(
                        "api.views.SocialPlatform.objects"
                    ) as mock_platform_objs:
                        mock_platform_objs.get.return_value = mock_platform

                        with patch("api.views.get_object_or_404") as mock_get_object:
                            mock_get_object.return_value = mock_reward_type

                            with patch("api.views.Reward.objects") as mock_reward_objs:
                                mock_reward_objs.filter.return_value = (
                                    mock_rewards_queryset
                                )

                                with patch(
                                    "api.views.ContributionSerializer"
                                ) as mock_serializer_class:
                                    mock_serializer_class.return_value = mock_serializer

                                    with patch("api.views.transaction.atomic"):
                                        # Mock sync_to_async to call the actual
                                        # function but in a sync context
                                        def sync_wrapper(func):
                                            # Instead of making it async,
                                            # just call the function directly
                                            async def async_func(*args, **kwargs):
                                                return func(*args, **kwargs)

                                            return async_func

                                        mock_sync_to_async.side_effect = sync_wrapper

                                        response = await view.post(mock_request)

                                        # Verify database calls with correct parsing
                                        mock_cntrs.from_full_handle.assert_called_once_with(
                                            "testuser"
                                        )
                                        mock_cycle_objs.latest.assert_called_once_with(
                                            "start"
                                        )
                                        mock_platform_objs.get.assert_called_once_with(
                                            name="twitter"
                                        )
                                        mock_get_object.assert_called_once_with(
                                            RewardType,
                                            label="reward",
                                            name="Test Reward",
                                        )
                                        mock_reward_objs.filter.assert_called_once_with(
                                            type=mock_reward_type, level=2, active=True
                                        )
                                        mock_serializer_class.assert_called_once_with(
                                            data={
                                                "contributor": 1,
                                                "cycle": 1,
                                                "platform": 1,
                                                "reward": 1,
                                                "percentage": 1,
                                                "url": "http://example.io/contribution",
                                                "comment": "Test comment",
                                                "confirmed": False,
                                            }
                                        )

                                        assert (
                                            response.status_code
                                            == status.HTTP_201_CREATED
                                        )
                                        assert response.data == mock_serializer_data

    @pytest.mark.asyncio
    async def test_api_views_add_contribution_view_post_type_parsing_edge_cases(
        self, mocker
    ):
        """Test type field parsing with various formats."""
        view = AddContributionView()

        test_cases = [
            # (input_type, expected_label, expected_name)
            ("[reward] Test Reward", "reward", "Test Reward"),
            ("[bug] Fix Critical Bug", "bug", "Fix Critical Bug"),
            (
                "[feature] New Feature Implementation",
                "feature",
                "New Feature Implementation",
            ),
        ]

        for input_type, expected_label, expected_name in test_cases:
            mock_request = mocker.MagicMock()
            mock_request.data = {
                "username": "testuser",
                "platform": "twitter",
                "type": input_type,
                "level": 1,
                "url": "http://example.io/contribution",
                "comment": "Test comment",
            }

            with patch("api.views.sync_to_async") as mock_sync_to_async:
                with patch("api.views.Contributor.objects"):
                    with patch("api.views.Cycle.objects"):
                        with patch("api.views.SocialPlatform.objects"):
                            with patch(
                                "api.views.get_object_or_404"
                            ) as mock_get_object:
                                with patch("api.views.Reward.objects"):
                                    with patch(
                                        "api.views.ContributionSerializer"
                                    ) as mock_serializer_class:
                                        mock_serializer = mocker.MagicMock()
                                        mock_serializer.is_valid.return_value = True
                                        mock_serializer_class.return_value = (
                                            mock_serializer
                                        )

                                        with patch("api.views.transaction.atomic"):

                                            def sync_wrapper(func):
                                                async def async_func(*args, **kwargs):
                                                    return func(*args, **kwargs)

                                                return async_func

                                            mock_sync_to_async.side_effect = (
                                                sync_wrapper
                                            )

                                            await view.post(mock_request)

                                            # Verify type parsing for each test case
                                            mock_get_object.assert_called_with(
                                                RewardType,
                                                label=expected_label,
                                                name=expected_name,
                                            )
                                            # Reset the mock for next iteration
                                            mock_get_object.reset_mock()

    @pytest.mark.asyncio
    async def test_api_views_add_contribution_view_post_missing_level(self, mocker):
        """Test contribution creation with missing level (should default to 1)."""
        view = AddContributionView()
        mock_request = mocker.MagicMock()

        # Mock request data without level
        mock_request.data = {
            "username": "testuser",
            "platform": "twitter",
            "type": "[reward] Test Reward",
            "url": "http://example.io/contribution",
            # level is missing
        }

        mock_contributor = mocker.MagicMock(spec=Contributor)
        mock_contributor.id = 1

        mock_cycle = mocker.MagicMock(spec=Cycle)
        mock_cycle.id = 1

        mock_platform = mocker.MagicMock(spec=SocialPlatform)
        mock_platform.id = 1

        mock_reward_type = mocker.MagicMock(spec=RewardType)

        mock_reward = mocker.MagicMock(spec=Reward)
        mock_reward.id = 1

        mock_rewards_queryset = mocker.MagicMock()
        mock_rewards_queryset.__getitem__.return_value = mock_reward

        mock_serializer = mocker.MagicMock()
        mock_serializer_data = {"id": 1, "contributor": 1, "cycle": 1}
        mock_serializer.is_valid.return_value = True
        mock_serializer.data = mock_serializer_data

        with patch("api.views.sync_to_async") as mock_sync_to_async:
            with patch("api.views.Contributor.objects") as mock_contributor_objects:
                mock_contributor_objects.from_handle.return_value = mock_contributor

                with patch("api.views.Cycle.objects") as mock_cycle_objects:
                    mock_cycle_objects.latest.return_value = mock_cycle

                    with patch(
                        "api.views.SocialPlatform.objects"
                    ) as mock_platform_objects:
                        mock_platform_objects.get.return_value = mock_platform

                        with patch("api.views.get_object_or_404") as mock_get_object:
                            mock_get_object.return_value = mock_reward_type

                            with patch(
                                "api.views.Reward.objects"
                            ) as mock_reward_objects:
                                mock_reward_objects.filter.return_value = (
                                    mock_rewards_queryset
                                )

                                with patch(
                                    "api.views.ContributionSerializer"
                                ) as mock_serializer_class:
                                    mock_serializer_class.return_value = mock_serializer

                                    with patch("api.views.transaction.atomic"):

                                        def sync_wrapper(func):
                                            async def async_func(*args, **kwargs):
                                                return func(*args, **kwargs)

                                            return async_func

                                        mock_sync_to_async.side_effect = sync_wrapper

                                        await view.post(mock_request)

                                        # Verify level defaults to 1 when missing
                                        mock_reward_objects.filter.assert_called_once_with(
                                            type=mock_reward_type, level=1, active=True
                                        )

    @pytest.mark.asyncio
    async def test_api_views_add_contribution_view_post_serializer_invalid(
        self, mocker
    ):
        """Test contribution creation when serializer validation fails."""
        view = AddContributionView()
        mock_request = mocker.MagicMock()

        # Mock request data
        mock_request.data = {
            "username": "testuser",
            "platform": "twitter",
            "type": "[reward] Test Reward",
            "level": 1,
            "url": "http://example.io/contribution",
            "comment": "Test comment",
        }

        # Mock all database objects
        mock_contributor = mocker.MagicMock(spec=Contributor)
        mock_contributor.id = 1

        mock_cycle = mocker.MagicMock(spec=Cycle)
        mock_cycle.id = 1

        mock_platform = mocker.MagicMock(spec=SocialPlatform)
        mock_platform.id = 1

        mock_reward_type = mocker.MagicMock(spec=RewardType)

        mock_reward = mocker.MagicMock(spec=Reward)
        mock_reward.id = 1

        mock_rewards_queryset = mocker.MagicMock()
        mock_rewards_queryset.__getitem__.return_value = mock_reward

        mock_serializer = mocker.MagicMock()
        mock_serializer.is_valid.return_value = False
        mock_serializer.errors = {
            "url": ["Enter a valid URL."],
            "contributor": ["This field is required."],
        }

        # Mock the actual database calls inside process_contribution
        with patch("api.views.sync_to_async") as mock_sync_to_async:
            with patch("api.views.Contributor.objects") as mock_contributor_objects:
                mock_contributor_objects.from_full_handle.return_value = mock_contributor

                with patch("api.views.Cycle.objects") as mock_cycle_objects:
                    mock_cycle_objects.latest.return_value = mock_cycle

                    with patch(
                        "api.views.SocialPlatform.objects"
                    ) as mock_platform_objects:
                        mock_platform_objects.get.return_value = mock_platform

                        with patch("api.views.get_object_or_404") as mock_get_object:
                            mock_get_object.return_value = mock_reward_type

                            with patch("api.views.Reward.objects") as mock_reward_objs:
                                mock_reward_objs.filter.return_value = (
                                    mock_rewards_queryset
                                )

                                with patch(
                                    "api.views.ContributionSerializer"
                                ) as mock_serializer_class:
                                    mock_serializer_class.return_value = mock_serializer

                                    # Mock transaction.atomic to verify it's NOT called
                                    with patch(
                                        "api.views.transaction.atomic"
                                    ) as mock_atomic:
                                        # Mock sync_to_async to call the actual function but in a sync context
                                        def sync_wrapper(func):
                                            async def async_func(*args, **kwargs):
                                                return func(*args, **kwargs)

                                            return async_func

                                        mock_sync_to_async.side_effect = sync_wrapper

                                        response = await view.post(mock_request)

                                        # Verify database calls were made
                                        mock_contributor_objects.from_full_handle.assert_called_once_with(
                                            "testuser"
                                        )
                                        mock_cycle_objects.latest.assert_called_once_with(
                                            "start"
                                        )
                                        mock_platform_objects.get.assert_called_once_with(
                                            name="twitter"
                                        )
                                        mock_get_object.assert_called_once_with(
                                            RewardType,
                                            label="reward",
                                            name="Test Reward",
                                        )
                                        mock_reward_objs.filter.assert_called_once_with(
                                            type=mock_reward_type, level=1, active=True
                                        )

                                        # Verify serializer was called with correct data
                                        mock_serializer_class.assert_called_once_with(
                                            data={
                                                "contributor": 1,
                                                "cycle": 1,
                                                "platform": 1,
                                                "reward": 1,
                                                "percentage": 1,
                                                "url": "http://example.io/contribution",
                                                "comment": "Test comment",
                                                "confirmed": False,
                                            }
                                        )

                                        # Verify serializer validation was checked
                                        mock_serializer.is_valid.assert_called_once()

                                        # Verify transaction.atomic
                                        # was NOT entered because validation failed
                                        mock_atomic.assert_not_called()

                                        # Verify serializer.save()
                                        # was NOT called due to validation failure
                                        mock_serializer.save.assert_not_called()

                                        # Verify error response
                                        assert (
                                            response.status_code
                                            == status.HTTP_400_BAD_REQUEST
                                        )
                                        assert response.data == {
                                            "url": ["Enter a valid URL."],
                                            "contributor": ["This field is required."],
                                        }

    @pytest.mark.asyncio
    async def test_api_views_add_contribution_view_post_serializer_valid_with_txn(
        self, mocker
    ):
        """Test that transaction.atomic IS called when serializer is valid."""
        view = AddContributionView()
        mock_request = mocker.MagicMock()

        mock_request.data = {
            "username": "testuser",
            "platform": "twitter",
            "type": "[reward] Test Reward",
            "level": 1,
            "url": "http://example.io/contribution",
            "comment": "Test comment",
        }

        mock_serializer = mocker.MagicMock()
        mock_serializer.is_valid.return_value = True
        mock_serializer.data = {"id": 1, "contributor": 1, "cycle": 1}

        with patch("api.views.sync_to_async") as mock_sync_to_async:
            with patch("api.views.Contributor.objects"):
                with patch("api.views.Cycle.objects"):
                    with patch("api.views.SocialPlatform.objects"):
                        with patch("api.views.get_object_or_404"):
                            with patch("api.views.Reward.objects"):
                                with patch(
                                    "api.views.ContributionSerializer"
                                ) as mock_serializer_class:
                                    mock_serializer_class.return_value = mock_serializer

                                    # Mock transaction.atomic as a context manager
                                    mock_atomic_ctx = mocker.MagicMock()
                                    with patch(
                                        "api.views.transaction.atomic",
                                        return_value=mock_atomic_ctx,
                                    ):

                                        def sync_wrapper(func):
                                            async def async_func(*args, **kwargs):
                                                return func(*args, **kwargs)

                                            return async_func

                                        mock_sync_to_async.side_effect = sync_wrapper

                                        response = await view.post(mock_request)

                                        # Verify transaction.atomic context WAS
                                        # entered because validation passed
                                        # The context manager should be entered
                                        # (__enter__) and exited (__exit__)
                                        mock_atomic_ctx.__enter__.assert_called_once()
                                        mock_atomic_ctx.__exit__.assert_called_once()

                                        # Verify serializer.save() WAS called
                                        mock_serializer.save.assert_called_once()

                                        # Verify success response
                                        assert (
                                            response.status_code
                                            == status.HTTP_201_CREATED
                                        )
