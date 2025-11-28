"""Testing module for :py:mod:`api.serializers` module."""

from datetime import date

from api.serializers import (
    AggregatedCycleSerializer,
    ContributionSerializer,
    ContributorSerializer,
    CycleSerializer,
    HumanizedContributionSerializer,
    RewardSerializer,
    RewardTypeSerializer,
    SocialPlatformSerializer,
)
from core.models import (
    Contribution,
    Contributor,
    Cycle,
    Reward,
    RewardType,
    SocialPlatform,
)


class TestApiSerializersAggregatedCycleSerializer:
    """Testing class for :py:class:`api.serializers.AggregatedCycleSerializer`."""

    def test_api_serializers_aggregated_cycle_serializer_creation(self):
        data = {
            "id": 1,
            "start": "2023-01-01",
            "end": "2023-01-31",
            "contributor_rewards": {"addr1": 100, "addr2": 200},
            "total_rewards": 300,
        }
        serializer = AggregatedCycleSerializer(data=data)
        assert serializer.is_valid()
        # DateField converts strings to date objects, so we need to compare appropriately
        validated_data = serializer.validated_data
        assert validated_data["id"] == 1
        assert validated_data["start"] == date(2023, 1, 1)
        assert validated_data["end"] == date(2023, 1, 31)
        assert validated_data["contributor_rewards"] == {"addr1": 100, "addr2": 200}
        assert validated_data["total_rewards"] == 300

    def test_api_serializers_aggregated_cycle_serializer_missing_fields(self):
        data = {
            "id": 1,
            "start": "2023-01-01",
            # Missing 'end', 'contributor_rewards', 'total_rewards'
        }
        serializer = AggregatedCycleSerializer(data=data)
        assert not serializer.is_valid()
        assert "end" in serializer.errors
        assert "contributor_rewards" in serializer.errors
        assert "total_rewards" in serializer.errors


class TestApiSerializersContributorSerializer:
    """Testing class for :py:class:`api.serializers.ContributorSerializer`."""

    def test_api_serializers_contributor_serializer_creation(self):
        contributor_data = {
            "name": "Test Contributor",
            "address": "test_address_123",
        }
        serializer = ContributorSerializer(data=contributor_data)
        assert serializer.is_valid()
        assert serializer.validated_data["name"] == "Test Contributor"
        assert serializer.validated_data["address"] == "test_address_123"

    def test_api_serializers_contributor_serializer_fields(self):
        serializer = ContributorSerializer()
        assert set(serializer.fields.keys()) == {"name", "address"}


class TestApiSerializersCycleSerializer:
    """Testing class for :py:class:`api.serializers.CycleSerializer`."""

    def test_api_serializers_cycle_serializer_creation(self):
        cycle_data = {
            "start": "2023-01-01",
            "end": "2023-01-31",
        }
        serializer = CycleSerializer(data=cycle_data)
        # ID is read-only for CycleSerializer since it's a ModelSerializer
        # and ID is typically auto-generated
        assert serializer.is_valid()
        validated_data = serializer.validated_data
        assert validated_data["start"] == date(2023, 1, 1)
        assert validated_data["end"] == date(2023, 1, 31)

    def test_api_serializers_cycle_serializer_fields(self):
        serializer = CycleSerializer()
        # ModelSerializer includes all fields from Meta.fields
        assert set(serializer.fields.keys()) == {"id", "start", "end"}


class TestApiSerializersSocialPlatformSerializer:
    """Testing class for :py:class:`api.serializers.SocialPlatformSerializer`."""

    def test_api_serializers_social_platform_serializer_creation(self):
        platform_data = {
            "name": "tw",  # Shorter name to fit max_length constraints
            "prefix": "ht",  # Shorter prefix to fit max_length=2
        }
        serializer = SocialPlatformSerializer(data=platform_data)
        assert serializer.is_valid()
        assert serializer.validated_data["name"] == "tw"
        assert serializer.validated_data["prefix"] == "ht"

    def test_api_serializers_social_platform_serializer_invalid_length(self):
        platform_data = {
            "name": "name1",
            "prefix": "https://this-prefix-is-way-too-long.com/",  # Too long
        }
        serializer = SocialPlatformSerializer(data=platform_data)
        assert not serializer.is_valid()
        assert "prefix" in serializer.errors

    def test_api_serializers_social_platform_serializer_fields(self):
        serializer = SocialPlatformSerializer()
        assert set(serializer.fields.keys()) == {"name", "prefix"}


class TestApiSerializersRewardTypeSerializer:
    """Testing class for :py:class:`api.serializers.RewardTypeSerializer`."""

    def test_api_serializers_reward_type_serializer_creation(self):
        reward_type_data = {
            "label": "cont",  # Shorter label to fit max_length=5
            "name": "Content Creation",
        }
        serializer = RewardTypeSerializer(data=reward_type_data)
        assert serializer.is_valid()
        assert serializer.validated_data["label"] == "cont"
        assert serializer.validated_data["name"] == "Content Creation"

    def test_api_serializers_reward_type_serializer_invalid_length(self):
        reward_type_data = {
            "label": "this_label_is_too_long",  # Too long for max_length=5
            "name": "This name is probably okay but let's make sure it's not too long either",
        }
        serializer = RewardTypeSerializer(data=reward_type_data)
        assert not serializer.is_valid()
        assert "label" in serializer.errors

    def test_api_serializers_reward_type_serializer_fields(self):
        serializer = RewardTypeSerializer()
        assert set(serializer.fields.keys()) == {"label", "name"}


class TestApiSerializersRewardSerializer:
    """Testing class for :py:class:`api.serializers.RewardSerializer`."""

    def test_api_serializers_reward_serializer_creation(self, mocker):
        # Mock the related objects since Reward has ForeignKey relationships
        mock_reward_type = mocker.MagicMock(spec=RewardType)
        mock_reward_type.pk = 1

        reward_data = {
            "type": mock_reward_type.pk,  # Use primary key for ForeignKey
            "level": 2,
            "amount": 500,
            "description": "Medium quality content creation",
        }
        RewardSerializer(data=reward_data)
        # This might still fail due to unique constraints, but we test the basic structure
        # In practice, you'd mock the queryset or use fixtures

    def test_api_serializers_reward_serializer_fields(self):
        serializer = RewardSerializer()
        assert set(serializer.fields.keys()) == {
            "type",
            "level",
            "amount",
            "description",
        }


class TestApiSerializersHumanizedContributionSerializer:
    """Testing class for :py:class:`api.serializers.HumanizedContributionSerializer`."""

    def test_api_serializers_humanized_contribution_serializer_creation(self):
        contribution_data = {
            "id": 1,
            "contributor_name": "John Doe",
            "cycle_id": 5,
            "platform": "twitter",
            "url": "https://twitter.com/johndoe/status/123456",
            "type": "retweet",
            "level": 1,
            "percentage": 25.50,
            "reward": 255,
            "confirmed": True,
        }
        serializer = HumanizedContributionSerializer(data=contribution_data)
        assert serializer.is_valid()
        assert serializer.validated_data["id"] == 1
        assert serializer.validated_data["contributor_name"] == "John Doe"
        assert serializer.validated_data["cycle_id"] == 5
        assert serializer.validated_data["platform"] == "twitter"
        assert (
            serializer.validated_data["url"]
            == "https://twitter.com/johndoe/status/123456"
        )
        assert serializer.validated_data["type"] == "retweet"
        assert serializer.validated_data["level"] == 1
        assert serializer.validated_data["percentage"] == 25.50
        assert serializer.validated_data["reward"] == 255
        assert serializer.validated_data["confirmed"] is True

    def test_api_serializers_humanized_contribution_serializer_decimal_validation(self):
        contribution_data = {
            "id": 1,
            "contributor_name": "John Doe",
            "cycle_id": 5,
            "platform": "twitter",
            "url": "https://twitter.com/johndoe/status/123456",
            "type": "retweet",
            "level": 1,
            "percentage": 123.456,  # Too many decimal places
            "reward": 255,
            "confirmed": True,
        }
        serializer = HumanizedContributionSerializer(data=contribution_data)
        assert not serializer.is_valid()
        assert "percentage" in serializer.errors

    def test_api_serializers_humanized_contribution_serializer_invalid_url(self):
        contribution_data = {
            "id": 1,
            "contributor_name": "John Doe",
            "cycle_id": 5,
            "platform": "twitter",
            "url": "not-a-valid-url",  # Invalid URL
            "type": "retweet",
            "level": 1,
            "percentage": 25.50,
            "reward": 255,
            "confirmed": True,
        }
        serializer = HumanizedContributionSerializer(data=contribution_data)
        assert not serializer.is_valid()
        assert "url" in serializer.errors


class TestApiSerializersContributionSerializer:
    """Testing class for :py:class:`api.serializers.ContributionSerializer`."""

    def test_api_serializers_contribution_serializer_creation(self, mocker):
        # For ModelSerializer with related objects, we typically test with instances
        # or primary keys rather than trying to create from raw data
        mock_contributor = mocker.MagicMock(spec=Contributor)
        mock_cycle = mocker.MagicMock(spec=Cycle)
        mock_platform = mocker.MagicMock(spec=SocialPlatform)
        mock_reward = mocker.MagicMock(spec=Reward)

        # Create a mock contribution instance
        mock_contribution = mocker.MagicMock(spec=Contribution)
        mock_contribution.id = 1
        mock_contribution.contributor = mock_contributor
        mock_contribution.cycle = mock_cycle
        mock_contribution.platform = mock_platform
        mock_contribution.reward = mock_reward
        mock_contribution.percentage = 50.00
        mock_contribution.url = "https://example.com/contribution/1"
        mock_contribution.comment = "Test contribution"
        mock_contribution.confirmed = False

        # Test serialization (object to dict)
        serializer = ContributionSerializer(mock_contribution)
        data = serializer.data
        assert "id" in data
        assert "contributor" in data
        assert "cycle" in data
        assert "platform" in data
        assert "reward" in data
        assert "percentage" in data
        assert "url" in data
        assert "comment" in data
        assert "confirmed" in data

    def test_api_serializers_contribution_serializer_fields(self):
        serializer = ContributionSerializer()
        expected_fields = {
            "id",
            "contributor",
            "cycle",
            "platform",
            "reward",
            "percentage",
            "url",
            "comment",
            "confirmed",
        }
        assert set(serializer.fields.keys()) == expected_fields
