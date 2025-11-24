"""Testing module for :py:mod:`core.signals` module."""

import pytest
from django.contrib.auth import get_user_model

from core.models import Profile

user_model = get_user_model()


class TestCoreSignals:
    """Testing class for :py:mod:`core.signals` module."""

    # # create_user_profile
    @pytest.mark.django_db
    def test_core_signals_new_user_creation_creates_its_profile(self):
        user = user_model.objects.create()
        assert isinstance(user.profile, Profile)

    # # save_user_profile
    @pytest.mark.django_db
    def test_core_signals_user_saving_saves_its_profile(self):
        user = user_model.objects.create()
        profile_id = user.profile.id
        issue_tracker_api_token = "issue_tracker_api_token"
        user.profile.issue_tracker_api_token = issue_tracker_api_token
        assert (
            Profile.objects.get(pk=profile_id).issue_tracker_api_token
            != issue_tracker_api_token
        )
        user.save()
        assert (
            Profile.objects.get(pk=profile_id).issue_tracker_api_token
            == issue_tracker_api_token
        )
