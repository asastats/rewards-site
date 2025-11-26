"""Module containing Rewards Suite API serializers."""

from adrf.serializers import ModelSerializer, Serializer
from rest_framework.serializers import (
    BooleanField,
    CharField,
    DateField,
    DecimalField,
    DictField,
    IntegerField,
    URLField,
)

from core.models import (
    Contribution,
    Contributor,
    Cycle,
    Reward,
    RewardType,
    SocialPlatform,
)


class AggregatedCycleSerializer(Serializer):
    """Serializer for aggregated cycle data with contributor rewards summary.

    :var id: cycle identifier
    :type id: :class:`rest_framework.serializers.IntegerField`
    :var start: cycle start date
    :type start: :class:`rest_framework.serializers.DateField`
    :var end: cycle end date
    :type end: :class:`rest_framework.serializers.DateField`
    :var contributor_rewards: dictionary mapping contributor addresses to reward amounts
    :type contributor_rewards: :class:`rest_framework.serializers.DictField`
    :var total_rewards: total rewards distributed in the cycle
    :type total_rewards: :class:`rest_framework.serializers.IntegerField`
    """

    id = IntegerField()
    start = DateField()
    end = DateField()
    contributor_rewards = DictField()
    total_rewards = IntegerField()


class ContributorSerializer(ModelSerializer):
    """Serializer for Contributor model.

    :var name: contributor's display name
    :type name: :class:`rest_framework.serializers.CharField`
    :var address: contributor's wallet address
    :type address: :class:`rest_framework.serializers.CharField`
    """

    class Meta:
        model = Contributor
        fields = ("name", "address")


class CycleSerializer(ModelSerializer):
    """Serializer for Cycle model.

    :var id: cycle identifier
    :type id: :class:`rest_framework.serializers.IntegerField`
    :var start: cycle start date
    :type start: :class:`rest_framework.serializers.DateField`
    :var end: cycle end date
    :type end: :class:`rest_framework.serializers.DateField`
    """

    class Meta:
        model = Cycle
        fields = ("id", "start", "end")


class SocialPlatformSerializer(ModelSerializer):
    """Serializer for SocialPlatform model.

    :var name: platform name (e.g., 'twitter', 'discord')
    :type name: :class:`rest_framework.serializers.CharField`
    :var prefix: URL prefix for platform contributions
    :type prefix: :class:`rest_framework.serializers.CharField`
    """

    class Meta:
        model = SocialPlatform
        fields = ("name", "prefix")


class RewardTypeSerializer(ModelSerializer):
    """Serializer for RewardType model.

    :var label: reward type identifier label
    :type label: :class:`rest_framework.serializers.CharField`
    :var name: human-readable reward type name
    :type name: :class:`rest_framework.serializers.CharField`
    """

    class Meta:
        model = RewardType
        fields = ("label", "name")


class RewardSerializer(ModelSerializer):
    """Serializer for Reward model.

    :var type: reward type
    :type type: :class:`rest_framework.serializers.CharField`
    :var level: reward level/tier
    :type level: :class:`rest_framework.serializers.IntegerField`
    :var amount: reward amount
    :type amount: :class:`rest_framework.serializers.IntegerField`
    :var description: reward description
    :type description: :class:`rest_framework.serializers.CharField`
    """

    class Meta:
        model = Reward
        fields = ("type", "level", "amount", "description")


class HumanizedContributionSerializer(Serializer):
    """Serializer for human-readable contribution data with computed fields.

    :var id: contribution identifier
    :type id: :class:`rest_framework.serializers.IntegerField`
    :var contributor_name: contributor's display name
    :type contributor_name: :class:`rest_framework.serializers.CharField`
    :var cycle_id: cycle identifier
    :type cycle_id: :class:`rest_framework.serializers.IntegerField`
    :var platform: social platform name
    :type platform: :class:`rest_framework.serializers.CharField`
    :var url: contribution URL
    :type url: :class:`rest_framework.serializers.URLField`
    :var type: contribution type
    :type type: :class:`rest_framework.serializers.CharField`
    :var level: contribution level/tier
    :type level: :class:`rest_framework.serializers.IntegerField`
    :var percentage: reward percentage for this contribution
    :type percentage: :class:`rest_framework.serializers.DecimalField`
    :var reward: calculated reward amount
    :type reward: :class:`rest_framework.serializers.IntegerField`
    :var confirmed: whether contribution is confirmed
    :type confirmed: :class:`rest_framework.serializers.BooleanField`
    """

    id = IntegerField()
    contributor_name = CharField()
    cycle_id = IntegerField()
    platform = CharField()
    url = URLField()
    type = CharField()
    level = IntegerField()
    percentage = DecimalField(max_digits=5, decimal_places=2)
    reward = IntegerField()
    confirmed = BooleanField()


class ContributionSerializer(ModelSerializer):
    """Serializer for Contribution model.

    :var id: contribution identifier
    :type id: :class:`rest_framework.serializers.IntegerField`
    :var contributor: contributor who made the contribution
    :type contributor: :class:`core.models.Contributor`
    :var cycle: cycle the contribution belongs to
    :type cycle: :class:`core.models.Cycle`
    :var platform: social platform where contribution was made
    :type platform: :class:`core.models.SocialPlatform`
    :var reward: reward associated with the contribution
    :type reward: :class:`core.models.Reward`
    :var percentage: reward percentage for this contribution
    :type percentage: :class:`rest_framework.serializers.DecimalField`
    :var url: contribution URL
    :type url: :class:`rest_framework.serializers.URLField`
    :var comment: optional comment about the contribution
    :type comment: :class:`rest_framework.serializers.CharField`
    :var confirmed: whether contribution is confirmed
    :type confirmed: :class:`rest_framework.serializers.BooleanField`
    """

    class Meta:
        model = Contribution
        fields = (
            "id",
            "contributor",
            "cycle",
            "platform",
            "reward",
            "percentage",
            "url",
            "comment",
            "confirmed",
        )
