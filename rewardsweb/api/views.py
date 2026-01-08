"""Module containing Rewards Suite API views."""

import logging

from adrf.views import APIView
from asgiref.sync import sync_to_async
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from api.serializers import (
    AggregatedCycleSerializer,
    ContributionSerializer,
    CycleSerializer,
    HumanizedContributionSerializer,
    IssueSerializer,
)
from core.models import (
    Contribution,
    Contributor,
    Cycle,
    IssueStatus,
    Reward,
    RewardType,
    SocialPlatform,
)
from utils.constants.core import CONTRIBUTIONS_TAIL_SIZE
from utils.helpers import humanize_contributions

logger = logging.getLogger(__name__)


class IsLocalhostPermission(BasePermission):
    """Allow access only to requests from localhost."""

    def has_permission(self, request, view):
        """Allow only localhost to access API endpoint.

        :param request: HTTP request object
        :type request: :class:`rest_framework.request.Request`
        :var xff_address: forwarded address
        :type xff_address: str
        :var remote_addr: address that called the endpoint
        :type remote_addr: str
        :return: Boolean
        """
        xff_address = request.META.get("HTTP_X_FORWARDED_FOR")
        # xff_address could be: "127.0.0.1, 10.0.0.1"
        remote_addr = (
            xff_address.split(",")[0].strip()
            if xff_address
            else request.META.get("REMOTE_ADDR")
        )
        return remote_addr in ["127.0.0.1", "::1"]


# # HELPERS
async def aggregated_cycle_response(cycle: Cycle):
    """Generate aggregated cycle response with contributor rewards data.

    :param cycle: Cycle instance to aggregate data for
    :type cycle: :class:`core.models.Cycle`
    :return: DRF Response with aggregated cycle data
    :rtype: :class:`rest_framework.response.Response`
    """
    if not cycle:
        return Response({"error": "Cycle not found"}, status=status.HTTP_404_NOT_FOUND)

    contributor_rewards = await sync_to_async(lambda: cycle.contributor_rewards)()
    total_rewards = await sync_to_async(lambda: cycle.total_rewards)()

    data = {
        "id": cycle.id,
        "start": cycle.start,
        "end": cycle.end,
        "contributor_rewards": contributor_rewards,
        "total_rewards": total_rewards or 0,
    }

    serializer = AggregatedCycleSerializer(data=data)
    serializer.is_valid()
    return Response(serializer.data)


async def contributions_response(contributions):
    """Fetch, humanize, serialize, and return contributions.

    :param contributions: QuerySet of Contribution objects
    :type contributions: :class:`django.db.models.QuerySet`
    :return: DRF Response with humanized contributions data
    :rtype: :class:`rest_framework.response.Response`
    """

    # Run DB-dependent humanization on a thread pool
    data = await sync_to_async(lambda: humanize_contributions(contributions))()
    serializer = HumanizedContributionSerializer(data=data, many=True)
    serializer.is_valid()
    return Response(serializer.data)


class LocalhostAPIView(APIView):
    """Base APIView that restricts access to localhost by default."""

    permission_classes = [IsLocalhostPermission]


class CycleAggregatedView(LocalhostAPIView):
    """API view to retrieve aggregated data for a specific cycle.

    :var cycle_id: URL parameter specifying the cycle identifier
    :type cycle_id: int
    """

    async def get(self, request, cycle_id):
        """Handle GET request for specific cycle aggregated data.

        :param request: HTTP request object
        :type request: :class:`rest_framework.request.Request`
        :param cycle_id: cycle identifier from URL
        :type cycle_id: int
        :return: aggregated cycle data response
        :rtype: :class:`rest_framework.response.Response`
        """
        cycle = await sync_to_async(lambda: Cycle.objects.filter(id=cycle_id).first())()
        return await aggregated_cycle_response(cycle)


class CurrentCycleAggregatedView(LocalhostAPIView):
    """API view to retrieve aggregated data for the current cycle."""

    async def get(self, request):
        """Handle GET request for current cycle aggregated data.

        :param request: HTTP request object
        :type request: :class:`rest_framework.request.Request`
        :return: aggregated current cycle data response
        :rtype: :class:`rest_framework.response.Response`
        """
        cycle = await sync_to_async(lambda: Cycle.objects.latest("start"))()
        return await aggregated_cycle_response(cycle)


class CyclePlainView(LocalhostAPIView):
    """API view to retrieve plain cycle data for a specific cycle.

    :var cycle_id: URL parameter specifying the cycle identifier
    :type cycle_id: int
    """

    async def get(self, request, cycle_id):
        """Handle GET request for specific cycle plain data.

        :param request: HTTP request object
        :type request: :class:`rest_framework.request.Request`
        :param cycle_id: cycle identifier from URL
        :type cycle_id: int
        :return: plain cycle data response
        :rtype: :class:`rest_framework.response.Response`
        """
        cycle = await sync_to_async(lambda: Cycle.objects.filter(id=cycle_id).first())()
        if not cycle:
            return Response(
                {"error": "Cycle not found"}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = CycleSerializer(cycle)
        return Response(serializer.data)


class CurrentCyclePlainView(LocalhostAPIView):
    """API view to retrieve plain cycle data for the current cycle."""

    async def get(self, request):
        """Handle GET request for current cycle plain data.

        :param request: HTTP request object
        :type request: :class:`rest_framework.request.Request`
        :return: plain current cycle data response
        :rtype: :class:`rest_framework.response.Response`
        """
        # Async database query
        cycle = await sync_to_async(lambda: Cycle.objects.latest("start"))()
        serializer = CycleSerializer(cycle)
        return Response(serializer.data)


class ContributionsView(LocalhostAPIView):
    """API view to retrieve contributions with optional contributor filtering."""

    async def get(self, request):
        """Handle GET request for contributions data.

        :param request: HTTP request object with optional 'name' query parameter
        :type request: :class:`rest_framework.request.Request`
        :var username: contributor's username
        :type username: str
        :var contributor: contributor's model instance
        :type contributor: :class:`core.models.Contributor`
        :var queryset: QuerySet of Contribution objects
        :type queryset: :class:`django.db.models.QuerySet`
        :return: contributions data response
        :rtype: :class:`rest_framework.response.Response`
        """
        username = request.GET.get("name")

        if username:
            contributor = await sync_to_async(
                lambda: Contributor.objects.from_handle(username)
            )()
            queryset = Contribution.objects.filter(contributor=contributor)
        else:
            queryset = Contribution.objects.order_by("-id")[
                : CONTRIBUTIONS_TAIL_SIZE * 2
            ]

        return await contributions_response(queryset)


class ContributionsTailView(LocalhostAPIView):
    """API view to retrieve the most recent contributions (tail)."""

    async def get(self, request):
        """Handle GET request for recent contributions tail.

        :param request: HTTP request object
        :type request: :class:`rest_framework.request.Request`
        :return: recent contributions data response
        :rtype: :class:`rest_framework.response.Response`
        """
        queryset = Contribution.objects.order_by("-id")[:CONTRIBUTIONS_TAIL_SIZE]
        return await contributions_response(queryset)


@sync_to_async
def process_contribution(raw_data, confirmed=False):
    """Process contribution data synchronously in thread pool.

    :param raw_data: raw contribution data from request
    :type raw_data: dict
    :param confirmed: should contribution be created as confirmed or not
    :type confirmed: Boolean
    :var contributor: contributor instance
    :type contributor: :class:`core.models.Contributor`
    :var cycle: rewards cycle instance
    :type cycle: :class:`core.models.Cycle`
    :var platform: social platform instance
    :type platform: :class:`core.models.SocialPlatform`
    :var label: reward name
    :type label: str
    :var name: reward label
    :type name: int
    :var reward_type: reward type instance
    :type reward_type: :class:`core.models.RewardType`
    :var rewards: queryset of Reward objects
    :type rewards: :class:`django.db.models.QuerySet`
    :var data: prepared contribution data
    :type data: dict
    :var serializer: contribution serializer instance
    :type serializer: :class:`api.serializers.ContributionSerializer`
    :return: tuple of (serialized_data, errors)
    :rtype: two-tuple
    """
    contributor = Contributor.objects.from_full_handle(raw_data.get("username"))
    cycle = Cycle.objects.latest("start")
    platform = SocialPlatform.objects.get(name=raw_data.get("platform"))
    label, name = (
        raw_data.get("type").split(" ", 1)[0].strip("[]"),
        raw_data.get("type").split(" ", 1)[1].strip(),
    )
    reward_type = get_object_or_404(RewardType, label=label, name=name)
    rewards = Reward.objects.filter(
        type=reward_type, level=int(raw_data.get("level", 1)), active=True
    )
    data = {
        "contributor": contributor.id,
        "cycle": cycle.id,
        "platform": platform.id,
        "reward": rewards[0].id,
        "percentage": 1,
        "url": raw_data.get("url"),
        "comment": raw_data.get("comment"),
        "confirmed": confirmed,
    }

    logger.info(f"Contribution received: {raw_data.get('url')}")
    serializer = ContributionSerializer(data=data)
    if serializer.is_valid():
        with transaction.atomic():
            serializer.save()

        logger.info(f"Contribution saved: {serializer.data.get('id')}")
        return serializer.data, None

    logger.error(f"Errors: {serializer.errors}")
    return None, serializer.errors


@sync_to_async
def process_issue(raw_data):
    """Process issue data synchronously in thread pool.

    :param raw_data: raw issue data from request
    :type raw_data: dict
    :var data: prepared issue data
    :type data: dict
    :var serializer: issue serializer instance
    :type serializer: :class:`api.serializers.IssueSerializer`
    :return: tuple of (serialized_data, errors)
    :rtype: tuple
    """
    data = {"number": raw_data.get("issue_number"), "status": IssueStatus.CREATED}
    logger.info(f"Issue received: {raw_data.get('issue_number')}")
    serializer = IssueSerializer(data=data)
    if serializer.is_valid():
        with transaction.atomic():
            serializer.save()

        logger.info(f"Issue saved: {serializer.data.get('id')}")
        return serializer.data, None

    logger.error(f"Errors: {serializer.errors}")
    return None, serializer.errors


class AddContributionView(LocalhostAPIView):
    """API view to add new contribution."""

    async def post(self, request):
        """Handle POST request to create a new contribution.

        :param request: HTTP request object with contribution data
        :type request: :class:`rest_framework.request.Request`
        :var data: prepared contribution data
        :type data: dict
        :var errors: collection of error messages
        :type errors: dict
        :return: created contribution data or validation errors
        :rtype: :class:`rest_framework.response.Response`
        """
        data, errors = await process_contribution(request.data)
        if data:
            return Response(data, status=status.HTTP_201_CREATED)

        return Response(errors, status=status.HTTP_400_BAD_REQUEST)


class AddIssueView(LocalhostAPIView):
    """API view to add new issue and related contribution."""

    async def post(self, request):
        """Handle POST request to create a new issue.

        :param request: HTTP request object with issue data
        :type request: :class:`rest_framework.request.Request`
        :var contribution_data: prepared contribution data
        :type contribution_data: dict
        :var data: prepared issue data
        :type data: dict
        :var errors: collection of error messages
        :type errors: dictomment
        :return: created issue data or validation errors
        :rtype: :class:`rest_framework.response.Response`
        """
        contribution_data, errors = await process_contribution(
            request.data, confirmed=True
        )
        if contribution_data:
            data, errors = await process_issue(request.data)
            if data:
                await sync_to_async(
                    lambda: Contribution.objects.assign_issue(
                        data.get("id"), contribution_data.get("id")
                    )
                )()
                return Response(data, status=status.HTTP_201_CREATED)

        return Response(errors, status=status.HTTP_400_BAD_REQUEST)
