"""Testing module for :py:mod:`core.models` module."""

from datetime import datetime

import pytest
from django.core.exceptions import ValidationError
from django.db import DataError, models
from django.db.utils import IntegrityError
from django.utils import timezone

from core.models import Contribution, Contributor, Cycle, Reward


class TestContributorModel:
    """Testing class for :class:`Contributor` model."""

    # # field characteristics
    @pytest.mark.parametrize(
        "name,typ",
        [
            ("name", models.CharField),
            ("address", models.CharField),
            ("reddit", models.CharField),
            ("github", models.CharField),
            ("twitter", models.CharField),
            ("discord", models.CharField),
            ("created_at", models.DateTimeField),
            ("updated_at", models.DateTimeField),
        ],
    )
    def test_contributor_model_fields(self, name, typ):
        assert hasattr(Contributor, name)
        assert isinstance(Contributor._meta.get_field(name), typ)

    @pytest.mark.django_db
    def test_contributor_model_name_is_not_optional(self):
        with pytest.raises(ValidationError):
            Contributor().full_clean()

    @pytest.mark.django_db
    def test_contributor_model_cannot_save_too_long_name(self):
        contributor = Contributor(name="a" * 100)
        with pytest.raises(DataError):
            contributor.save()
            contributor.full_clean()

    @pytest.mark.django_db
    def test_contributor_model_cannot_save_too_long_address(self):
        contributor = Contributor(address="a" * 100)
        with pytest.raises(DataError):
            contributor.save()
            contributor.full_clean()

    @pytest.mark.django_db
    def test_contributor_model_cannot_save_too_long_reddit(self):
        contributor = Contributor(reddit="a" * 100)
        with pytest.raises(DataError):
            contributor.save()
            contributor.full_clean()

    @pytest.mark.django_db
    def test_contributor_model_cannot_save_too_long_github(self):
        contributor = Contributor(reddit="a" * 100)
        with pytest.raises(DataError):
            contributor.save()
            contributor.full_clean()

    @pytest.mark.django_db
    def test_contributor_model_cannot_save_too_long_twitter(self):
        contributor = Contributor(reddit="a" * 100)
        with pytest.raises(DataError):
            contributor.save()
            contributor.full_clean()

    @pytest.mark.django_db
    def test_contributor_model_cannot_save_too_long_discord(self):
        contributor = Contributor(reddit="a" * 100)
        with pytest.raises(DataError):
            contributor.save()
            contributor.full_clean()

    # # Meta
    @pytest.mark.django_db
    def test_contributor_model_ordering(self):
        contributor1 = Contributor.objects.create(name="Abcde", address="address1")
        contributor2 = Contributor.objects.create(name="aabcde", address="address2")
        contributor3 = Contributor.objects.create(name="bcde", address="address3")
        contributor4 = Contributor.objects.create(name="Bcde", address="address4")
        assert list(Contributor.objects.all()) == [
            contributor2,
            contributor1,
            contributor3,
            contributor4,
        ]

    # # save
    @pytest.mark.django_db
    def test_contributor_model_save_duplicate_name_is_invalid(self):
        Contributor.objects.create(name="name1")
        with pytest.raises(IntegrityError):
            contributor = Contributor(name="name1")
            contributor.save()

    @pytest.mark.django_db
    def test_contributor_model_save_duplicate_address_is_invalid(self):
        Contributor.objects.create(address="address1")
        with pytest.raises(IntegrityError):
            contributor = Contributor(address="address1")
            contributor.save()

    # # __str__
    @pytest.mark.django_db
    def test_contributor_model_string_representation_is_contributor_name(self):
        contributor = Contributor(name="user name")
        assert str(contributor) == "user name"


class TestCycleModel:
    """Testing class for :class:`Cycle` model."""

    # # field characteristics
    @pytest.mark.parametrize(
        "name,typ",
        [
            ("start", models.DateField),
            ("end", models.DateField),
            ("created_at", models.DateTimeField),
            ("updated_at", models.DateTimeField),
        ],
    )
    def test_cycle_model_fields(self, name, typ):
        assert hasattr(Cycle, name)
        assert isinstance(Cycle._meta.get_field(name), typ)

    @pytest.mark.django_db
    def test_cycle_model_start_is_not_optional(self):
        with pytest.raises(ValidationError):
            Cycle().full_clean()

    @pytest.mark.django_db
    def test_cycle_model_created_at_datetime_field_set(self):
        cycle = Cycle.objects.create(start=datetime(2025, 3, 22))
        assert cycle.created_at <= timezone.now()

    @pytest.mark.django_db
    def test_cycle_model_updated_at_datetime_field_set(self):
        cycle = Cycle.objects.create(start=datetime(2025, 3, 22))
        assert cycle.updated_at <= timezone.now()

    # # Meta
    @pytest.mark.django_db
    def test_cycle_model_ordering(self):
        cycle1 = Cycle.objects.create(start=datetime(2025, 3, 25))
        cycle2 = Cycle.objects.create(start=datetime(2025, 3, 22))
        cycle3 = Cycle.objects.create(start=datetime(2024, 4, 22))
        assert list(Cycle.objects.all()) == [cycle3, cycle2, cycle1]

    # # __str__
    @pytest.mark.django_db
    def test_cycle_model_string_representation_for_end(self):
        cycle = Cycle.objects.create(
            start=datetime(2025, 3, 25), end=datetime(2025, 4, 25)
        )
        assert str(cycle) == "25-03-25 - 25-04-25"

    @pytest.mark.django_db
    def test_cycle_model_string_representation_without_end(self):
        cycle = Cycle.objects.create(start=datetime(2025, 3, 25))
        assert str(cycle) == ""


class TestContributionModel:
    """Testing class for :class:`Contribution` model."""

    # # field characteristics
    @pytest.mark.parametrize(
        "name,typ",
        [
            ("contributor", models.ForeignKey),
            ("cycle", models.ForeignKey),
            ("platform", models.CharField),
            ("url", models.CharField),
            ("type", models.CharField),
            ("level", models.IntegerField),
            ("percentage", models.DecimalField),
            ("reward", models.DecimalField),
            ("comment", models.CharField),
            ("confirmed", models.BooleanField),
            ("created_at", models.DateTimeField),
            ("updated_at", models.DateTimeField),
        ],
    )
    def test_contribution_model_fields(self, name, typ):
        assert hasattr(Contribution, name)
        assert isinstance(Contribution._meta.get_field(name), typ)

    @pytest.mark.django_db
    def test_contribution_model_is_related_to_contributor(self):
        contributor = Contributor.objects.create(
            name="mynamecontr", address="addressfoocontr"
        )
        cycle = Cycle.objects.create(start=datetime(2025, 3, 22))
        contribution = Contribution(cycle=cycle)
        contribution.contributor = contributor
        contribution.save()
        assert contribution in contributor.contribution_set.all()

    @pytest.mark.django_db
    def test_contribution_model_is_related_to_cycle(self):
        contributor = Contributor.objects.create(
            name="mynamecycle", address="addresscycle"
        )
        cycle = Cycle.objects.create(start=datetime(2025, 3, 22))
        contribution = Contribution(contributor=contributor)
        contribution.cycle = cycle
        contribution.save()
        assert contribution in cycle.contribution_set.all()

    @pytest.mark.django_db
    def test_contribution_model_cannot_save_too_long_platform(self):
        contributor = Contributor.objects.create()
        contribution = Contribution(contributor=contributor, platform="*" * 100)
        with pytest.raises(DataError):
            contribution.save()
            contribution.full_clean()

    @pytest.mark.django_db
    def test_contribution_model_cannot_save_too_long_url(self):
        contributor = Contributor.objects.create()
        contribution = Contribution(contributor=contributor, url="xyz" * 200)
        with pytest.raises(DataError):
            contribution.save()
            contribution.full_clean()

    @pytest.mark.django_db
    def test_contribution_model_cannot_save_too_long_type(self):
        contributor = Contributor.objects.create()
        contribution = Contribution(contributor=contributor, type="a" * 50)
        with pytest.raises(DataError):
            contribution.save()
            contribution.full_clean()

    @pytest.mark.django_db
    def test_contribution_model_cannot_save_too_big_percentage(self):
        contributor = Contributor.objects.create()
        contribution = Contribution(contributor=contributor, percentage=10e6)
        with pytest.raises(DataError):
            contribution.save()
            contribution.full_clean()

    @pytest.mark.django_db
    def test_contribution_model_cannot_save_too_big_reward(self):
        contributor = Contributor.objects.create()
        contribution = Contribution(contributor=contributor, percentage=10e12)
        with pytest.raises(DataError):
            contribution.save()
            contribution.full_clean()

    @pytest.mark.django_db
    def test_contribution_model_cannot_save_too_long_comment(self):
        contributor = Contributor.objects.create()
        contribution = Contribution(contributor=contributor, comment="abc" * 100)
        with pytest.raises(DataError):
            contribution.save()
            contribution.full_clean()

    @pytest.mark.django_db
    def test_contribution_model_created_at_datetime_field_set(self):
        contributor = Contributor.objects.create(
            name="mynamecreated", address="addressfoocreated"
        )
        cycle = Cycle.objects.create(start=datetime(2025, 3, 22))
        contribution = Contribution.objects.create(
            contributor=contributor, cycle=cycle, platform="platform"
        )
        assert contribution.created_at <= timezone.now()

    @pytest.mark.django_db
    def test_contribution_model_updated_at_datetime_field_set(self):
        contributor = Contributor.objects.create(
            name="mynameupd", address="addressfooupd"
        )
        cycle = Cycle.objects.create(start=datetime(2025, 3, 22))
        contribution = Contribution.objects.create(
            contributor=contributor, cycle=cycle, platform="platform"
        )
        assert contribution.updated_at <= timezone.now()

    # # Meta
    @pytest.mark.django_db
    def test_contribution_model_contributions_ordering(self):
        cycle1 = Cycle.objects.create(start=datetime(2025, 3, 22))
        cycle2 = Cycle.objects.create(start=datetime(2025, 4, 20))
        cycle3 = Cycle.objects.create(start=datetime(2025, 5, 20))
        contributor1 = Contributor.objects.create(name="myname", address="addressfoo")
        contributor2 = Contributor.objects.create(name="myname2", address="addressfoo2")
        contribution1 = Contribution.objects.create(
            contributor=contributor1, cycle=cycle1
        )
        contribution2 = Contribution.objects.create(
            contributor=contributor2, cycle=cycle2
        )
        contribution3 = Contribution.objects.create(
            contributor=contributor2, cycle=cycle1
        )
        contribution4 = Contribution.objects.create(
            contributor=contributor1, cycle=cycle3
        )
        contribution5 = Contribution.objects.create(
            contributor=contributor1, cycle=cycle2
        )
        assert list(Contribution.objects.all()) == [
            contribution1,
            contribution3,
            contribution2,
            contribution5,
            contribution4,
        ]

    # #  __str__
    @pytest.mark.django_db
    def test_contribution_model_string_representation(self):
        contributor = Contributor.objects.create(name="MyName")
        cycle = Cycle.objects.create(start=datetime(2025, 3, 22))
        contribution = Contribution.objects.create(
            contributor=contributor, cycle=cycle, platform="platform2"
        )
        assert "/".join(str(contribution).split("/")[:2]) == "MyName/platform2"


class TestRewardModel:
    """Testing class for :class:`Reward` model."""

    # # field characteristics
    @pytest.mark.parametrize(
        "name,typ",
        [
            ("type", models.CharField),
            ("level", models.IntegerField),
            ("reward", models.DecimalField),
            ("description", models.CharField),
            ("general_description", models.TextField),
            ("created_at", models.DateTimeField),
            ("updated_at", models.DateTimeField),
        ],
    )
    def test_reward_model_fields(self, name, typ):
        assert hasattr(Reward, name)
        assert isinstance(Reward._meta.get_field(name), typ)

    def test_reward_model_default_level(self):
        reward = Reward()
        assert reward.level == 1

    @pytest.mark.django_db
    def test_contribution_model_cannot_save_too_long_type(self):
        reward = Reward(type="*" * 50)
        with pytest.raises(DataError):
            reward.save()
            reward.full_clean()

    @pytest.mark.django_db
    def test_contribution_model_cannot_save_too_big_reward(self):
        reward = Reward(reward=10e12)
        with pytest.raises(DataError):
            reward.save()
            reward.full_clean()

    @pytest.mark.django_db
    def test_contribution_model_cannot_save_too_long_description(self):
        reward = Reward(reward="*" * 500)
        with pytest.raises(ValidationError):
            reward.save()
            reward.full_clean()

    @pytest.mark.django_db
    def test_reward_model_created_at_datetime_field_set(self):
        reward = Reward.objects.create()
        assert reward.created_at <= timezone.now()

    @pytest.mark.django_db
    def test_reward_model_updated_at_datetime_field_set(self):
        reward = Reward.objects.create()
        assert reward.updated_at <= timezone.now()

    # # Meta
    @pytest.mark.django_db
    def test_reward_model_ordering(self):
        reward1 = Reward.objects.create(type="type2", level=2)
        reward2 = Reward.objects.create(type="type1", level=2)
        reward3 = Reward.objects.create(type="type2", level=1)
        assert list(Reward.objects.all()) == [reward2, reward3, reward1]

    # save
    @pytest.mark.django_db
    def test_contributor_model_save_duplicate_type_and_level_combination(self):
        Reward.objects.create(type="type1", level=2)
        with pytest.raises(IntegrityError):
            contributor = Reward(type="type1", level=2)
            contributor.save()

    # # __str__
    @pytest.mark.django_db
    def test_reward_model_string_representation(self):
        reward = Reward.objects.create(type="type2", level=1)
        assert str(reward) == "type2 1"
