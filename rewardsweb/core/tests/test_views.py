"""Testing module for :py:mod:`core.views` underlying views."""

import json
import time

import pytest
from allauth.account.forms import LoginForm, SignupForm
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.test import RequestFactory, TestCase
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy
from django.views import View
from django.views.generic import DetailView, FormView, ListView, UpdateView
from django.views.generic.detail import SingleObjectMixin

from core.forms import DeactivateProfileForm, ProfileFormSet, UpdateUserForm
from core.models import Contribution, Contributor, Cycle
from core.views import (
    DeactivateProfileView,
    IndexView,
    IssueWebhookView,
    LoginView,
    ProfileDisplay,
    ProfileEditView,
    ProfileUpdate,
    SignupView,
    TransparencyReportView,
    UnconfirmedContributionsView,
)

user_model = get_user_model()


# # HELPERS
def _get_user_edit_fake_post_data(user, first_name="first_name", last_name="last_name"):
    return {
        "first_name": first_name,
        "last_name": last_name,
        "csrfmiddlewaretoken": "ebklx66wgoqT9kReeo67yxdCyzG2EtoBIRDvGjShzWfvbAnOhsdC4dok2vNta0PQ",
        "profile-TOTAL_FORMS": 1,
        "profile-INITIAL_FORMS": 1,
        "profile-MIN_NUM_FORMS": 0,
        "profile-MAX_NUM_FORMS": 1,
        "profile-0-address": "",
        "profile-0-authorized": False,
        "profile-0-permission": 0,
        "profile-0-currency": "ALGO",
        "profile-0-id": user.profile.id,
        "profile-0-user": user.id,
        "_mutable": False,
    }


class BaseView:
    """Base helper class for testing custom views."""

    def setup_view(self, view, request, *args, **kwargs):
        """Mimic as_view() returned callable, but returns view instance.

        args and kwargs are the same as those passed to ``reverse()``

        """
        view.request = request
        view.args = args
        view.kwargs = kwargs
        return view

    # # helper methods
    def setup_method(self):
        # Setup request
        self.request = RequestFactory().get("/fake-path")


class BaseUserCreatedView(BaseView):
    def setup_method(self):
        # # Setup user
        username = "user{}".format(str(time.time())[5:])
        self.user = user_model.objects.create(
            email="{}@testuser.com".format(username),
            username=username,
        )
        # Setup request
        self.request = RequestFactory().get("/fake-path")
        self.request.user = self.user


class IndexPageTest(TestCase):
    def test_index_page_renders_index_template(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "index.html")


class TestIndexView:
    """Testing class for :class:`core.views.IndexView`."""

    def test_indexview_is_subclass_of_listview(self):
        assert issubclass(IndexView, ListView)

    def test_indexview_model(self):
        view = IndexView()
        assert view.model == Contribution

    def test_indexview_paginate_by(self):
        view = IndexView()
        assert view.paginate_by == 20

    def test_indexview_template_name(self):
        view = IndexView()
        assert view.template_name == "index.html"


@pytest.mark.django_db
class TestDbIndexView:
    """Testing class for :class:`core.views.IndexView` with database."""

    def test_indexview_get_queryset(self, contribution):
        # Create a confirmed contribution that should not appear
        Contribution.objects.create(
            contributor=contribution.contributor,
            cycle=contribution.cycle,
            platform=contribution.platform,
            reward=contribution.reward,
            percentage=100.0,
            confirmed=True,
        )

        view = IndexView()
        queryset = view.get_queryset()

        # Should only include unconfirmed contributions
        assert queryset.filter(confirmed=True).count() == 0
        assert queryset.filter(confirmed=False).count() == 1

    def test_indexview_get_context_data(self, rf):
        request = rf.get("/")

        # Create test data first
        Cycle.objects.create(start="2023-01-01", end="2023-01-31")
        Cycle.objects.create(start="2023-02-01", end="2023-02-28")
        Contributor.objects.create(name="contributor1", address="addr1")
        Contributor.objects.create(name="contributor2", address="addr2")

        # Setup view properly
        view = IndexView()
        view.setup(request)
        view.object_list = Contribution.objects.none()
        view.request = request

        context = view.get_context_data()

        assert context["num_cycles"] == 2
        assert context["num_contributors"] == 2
        assert context["num_contributions"] == 0
        # When there are no contributions, total_rewards can be None
        assert context["total_rewards"] in [0, None]


class EditProfilePageTest(TestCase):
    def setUp(self):
        self.user = user_model.objects.create(
            email="profilepage@testuser.com",
            username="profilepage",
        )
        self.user.set_password("12345o")
        self.user.save()
        self.client.login(username="profilepage", password="12345o")

    def post_invalid_input(self):
        return self.client.post(
            reverse("profile"),
            data=_get_user_edit_fake_post_data(self.user, first_name="xyz" * 51),
        )

    def test_profile_page_uses_profile_template(self):
        response = self.client.get(reverse("profile"))
        self.assertTemplateUsed(response, "profile.html")

    def test_profile_page_passes_correct_user_to_template(self):
        response = self.client.get(reverse("profile"))
        self.assertEqual(response.context["form"].instance.username, self.user.username)

    def test_profile_page_displays_updateuserform_for_edit_user_data(self):
        response = self.client.get(reverse("profile"))
        self.assertIsInstance(response.context["form"], UpdateUserForm)
        self.assertContains(response, "first_name")

    def test_profile_page_displays_profileformset_for_edit_profile_data(self):
        response = self.client.get(reverse("profile"))
        self.assertIsInstance(response.context["profile_form"], ProfileFormSet)
        self.assertContains(response, "profile-0-issue_tracker_api_token")

    def test_profile_page_post_ends_in_profile_page(self):
        response = self.client.post(
            reverse("profile"), data=_get_user_edit_fake_post_data(self.user)
        )
        self.assertRedirects(response, reverse("profile"))

    def test_profile_page_saving_a_post_request_to_an_existing_user(self):
        self.client.post(
            reverse("profile"),
            data=_get_user_edit_fake_post_data(
                self.user, first_name="Newname", last_name="Newlastname"
            ),
        )
        user = user_model.objects.last()
        self.assertEqual(user.first_name, "Newname")
        self.assertEqual(user.last_name, "Newlastname")

    def test_profile_page_edit_profile_for_invalid_input_nothing_saved_to_db(self):
        oldname = self.user.first_name
        self.post_invalid_input()
        self.assertEqual(oldname, self.user.first_name)

    def test_profile_page_for_invalid_input_renders_profile_template(self):
        response = self.post_invalid_input()
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "profile.html")

    def test_profile_page_edit_profile_for_invalid_input_passes_form_to_template(self):
        response = self.post_invalid_input()
        self.assertIsInstance(response.context["form"], UpdateUserForm)


class TestProfileDisplay:
    """Testing class for :class:`core.views.ProfileDisplay`."""

    def test_profiledisplay_is_subclass_of_detailview(self):
        assert issubclass(ProfileDisplay, DetailView)

    def test_profiledisplay_sets_template_name(self):
        assert ProfileDisplay.template_name == "profile.html"

    def test_profiledisplay_sets_model_to_user(self):
        assert ProfileDisplay.model == User


@pytest.mark.django_db
class TestDbProfileDisplayView(BaseUserCreatedView):
    def test_profiledisplay_get_returns_both_forms_by_the_context_data(self):
        # Setup view
        view = ProfileDisplay()
        view = self.setup_view(view, self.request)

        # Run.
        view_object = view.get(self.request)

        # Check.
        assert isinstance(view_object.context_data["form"], UpdateUserForm)
        assert isinstance(view_object.context_data["profile_form"], ProfileFormSet)
        assert isinstance(view_object.context_data["form"].instance, user_model)
        assert isinstance(view_object.context_data["profile_form"].instance, user_model)

    def test_profiledisplay_get_form_fills_form_with_user_data(self):
        # Setup view
        view = ProfileDisplay()
        view = self.setup_view(view, self.request)

        # Run.
        form = view.get_form()

        # Check.
        assert form.data["email"] == self.user.email


class TestProfileUpdate:
    """Testing class for :class:`core.views.ProfileUpdate`."""

    def test_profileupdate_is_subclass_of_updateview(self):
        assert issubclass(ProfileUpdate, UpdateView)

    def test_profileupdate_issubclass_of_singleobjectmixin(self):
        assert issubclass(ProfileUpdate, SingleObjectMixin)

    def test_profileupdate_sets_template_name(self):
        assert ProfileUpdate.template_name == "profile.html"

    def test_profileupdate_sets_model_to_user(self):
        assert ProfileUpdate.model == User

    def test_profileupdate_sets_form_class_to_updateuserform(self):
        assert ProfileUpdate.form_class == UpdateUserForm

    def test_profileupdate_sets_success_url_to_profile(self):
        assert ProfileUpdate.success_url == reverse_lazy("profile")


@pytest.mark.django_db
class TestDbProfileUpdateView(BaseUserCreatedView):
    def test_profileupdateview_get_object_sets_user(self):
        # Setup view
        view = ProfileUpdate()
        view = self.setup_view(view, self.request)

        # Run.
        view_object = view.get_object()

        # Check.
        assert view_object == self.user

    def test_profileupdateview_get_form_returns_updateuserform(self):
        # Setup view
        view = ProfileUpdate()
        view = self.setup_view(view, self.request)
        # view.object = self.user.profile

        # Run.
        view_form = view.get_form()

        # Check.
        assert isinstance(view_form, UpdateUserForm)
        assert view_form.instance == self.user


class TestProfileEditView:
    """Testing class for :class:`core.views.ProfileEditView`."""

    def test_profileeditview_is_subclass_of_view(self):
        assert issubclass(ProfileEditView, View)


@pytest.mark.django_db
class TestDbProfileEditView(BaseUserCreatedView):
    def test_profileeditview_get_instantiates_profiledisplay_view(self):
        # Setup view
        view = ProfileEditView()
        view = self.setup_view(view, self.request)

        # Run.
        view_method = view.get(self.request)

        # Check.
        assert isinstance(view_method.context_data["view"], ProfileDisplay)

    def test_profileeditview_post_instantiates_profileupdate_view(self):
        # Setup view
        view = ProfileEditView()
        data = _get_user_edit_fake_post_data(self.user)
        view = self.setup_view(view, self.request)

        # Run.
        # form=form, profile_form=profile_form
        view_method = view.post(
            self.request,
            form=UpdateUserForm(instance=self.user, data=data),
        )
        # Check.
        assert isinstance(view_method.context_data["view"], ProfileUpdate)


class DeactivateProfilePageTest(TestCase):
    def setUp(self):
        self.user = user_model.objects.create(
            email="deactivate_profile@testuser.com",
            username="deactivate_profile",
        )
        self.user.set_password("12345o")
        self.user.save()
        self.client.login(username="deactivate_profile", password="12345o")

    def post_invalid_input(self):
        return self.client.post(reverse("deactivate_profile"), data={"captcha": "1234"})

    def test_deactivate_profile_page_uses_deactivate_profile_template(self):
        response = self.client.get(reverse("deactivate_profile"))
        self.assertTemplateUsed(response, "deactivate_profile.html")

    def test_deactivate_profile_page_deactivate_uses_deactivateprofileform_object(self):
        response = self.client.get(reverse("deactivate_profile"))
        self.assertIsInstance(response.context["form"], DeactivateProfileForm)
        self.assertContains(response, "captcha_0")

    def test_deactivate_profile_page_for_invalid_input_nothing_changed_in_db(self):
        is_active = self.user.is_active
        self.post_invalid_input()
        self.assertEqual(is_active, self.user.is_active)

    def test_deactivate_profile_page_deactivate_for_invalid_renders_profile_template(
        self,
    ):
        response = self.post_invalid_input()
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "deactivate_profile.html")

    def test_deactivate_profile_page_deactivate_for_invalid_passes_form_to_template(
        self,
    ):
        response = self.post_invalid_input()
        self.assertIsInstance(response.context["form"], DeactivateProfileForm)

    def test_deactivate_profile_page_deactivate_invalid_form_submit(self):
        response = self.client.get(reverse("deactivate_profile"))
        self.assertEqual(response.status_code, 200)
        response = self.client.post(
            reverse("deactivate_profile"),
            dict(captcha_0="abc", captcha_1="wrong response"),
        )
        self.assertFormError(
            response.context_data["form"], "captcha", gettext_lazy("Invalid CAPTCHA")
        )


class TestDeactivateProfileViewTest:
    """Testing class for :class:`core.views.DeactivateProfileView`."""

    # # DeactivateProfileView
    def test_deactivateprofileview_issubclass_of_formview(self):
        assert issubclass(DeactivateProfileView, FormView)

    def test_deactivateprofileview_sets_template_name(self):
        assert DeactivateProfileView.template_name == "deactivate_profile.html"

    def test_deactivateprofileview_sets_form_class_to_deatctivateprofileform(self):
        assert DeactivateProfileView.form_class == DeactivateProfileForm

    def test_deactivateprofileview_sets_success_url(self):
        assert DeactivateProfileView.success_url == "/accounts/inactive/"


@pytest.mark.django_db
class TestDbDeactivateProfileViewTest(BaseUserCreatedView):
    def test_deactivateprofileview_form_valid_calls_deactivate_profile_form_method(
        self, mocker
    ):
        # Setup view
        view = DeactivateProfileView()
        view = self.setup_view(view, self.request)
        # Run.
        form = mocker.MagicMock()
        response = view.form_valid(form)
        # Check.
        assert isinstance(response, HttpResponseRedirect)
        assert response.url == "/accounts/inactive/"
        form.deactivate_profile.assert_called_once()
        form.deactivate_profile.assert_called_with(self.request)


class LoginPageTest(TestCase):
    def post_invalid_input(self):
        return self.client.post(
            reverse("account_login"), data={"login": "logn", "password": "12345"}
        )

    def test_login_page_renders_login_template(self):
        response = self.client.get(reverse("account_login"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "account/login.html")

    def test_login_view_renders_loginform(self):
        response = self.client.get(reverse("account_login"))
        self.assertIsInstance(response.context["form"], LoginForm)

    def test_login_page_or_invalid_input_renders_login_template(self):
        response = self.post_invalid_input()
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "account/login.html")

    def test_login_page_for_invalid_input_passes_form_to_template(self):
        response = self.post_invalid_input()
        self.assertIsInstance(response.context["form"], LoginForm)

    def test_login_page_for_invalid_input_shows_errors_on_page(self):
        response = self.post_invalid_input()
        self.assertContains(
            response, "The username and/or password you specified are not correct."
        )

    def test_login_page_links_to_forget_password_page(self):
        response = self.client.get(reverse("account_login"))
        self.assertContains(response, reverse("account_reset_password"))


@pytest.mark.django_db
class TestLoginViewDb(BaseUserCreatedView):
    """Testing class for :class:`core.views.LoginView`."""

    def test_loginview_get_context_data(self, rf):
        """Verify that the context contains wallet and network data."""
        request = rf.get(reverse("account_login"))
        request.session = {}
        view = LoginView()
        view.setup(request)
        view.request = request

        context = view.get_context_data()

        assert "wallets" in context
        assert len(context["wallets"]) == 3
        assert context["active_network"] == "testnet"

    def test_loginview_get_context_data_with_session_network(self, rf):
        """Verify that the active_network is correctly read from the session."""
        request = rf.get(reverse("account_login"))
        request.session = {"active_network": "mainnet"}
        view = LoginView()
        view.setup(request)
        view.request = request

        context = view.get_context_data()

        assert context["active_network"] == "mainnet"


class SignupPageTest(TestCase):
    def post_invalid_input(self):
        return self.client.post(
            reverse("account_signup"), data={"username": "logn", "password1": "12345"}
        )

    def test_signup_page_renders_signup_template(self):
        response = self.client.get(reverse("account_signup"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "account/signup.html")

    def test_signup_view_renders_signupform(self):
        response = self.client.get(reverse("account_signup"))
        self.assertIsInstance(response.context["form"], SignupForm)

    def test_signup_page_for_invalid_input_renders_signuo_template(self):
        response = self.post_invalid_input()
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "account/signup.html")

    def test_signup_page_for_invalid_input_passes_form_to_template(self):
        response = self.post_invalid_input()
        self.assertIsInstance(response.context["form"], SignupForm)

    def test_signup_page_for_invalid_input_shows_errors_on_page(self):
        response = self.post_invalid_input()
        self.assertContains(response, "This field is required.")

    def test_signup_page_links_to_login_page(self):
        response = self.client.get(reverse("account_signup"))
        self.assertContains(response, reverse("account_login"))


@pytest.mark.django_db
class TestSignupView(BaseUserCreatedView):
    """Testing class for :class:`core.views.SignupView`."""

    def test_signupview_get_context_data(self, rf):
        """Verify that the context contains wallet and network data."""
        request = rf.get(reverse("account_signup"))
        request.session = {}
        view = SignupView()
        view.setup(request)
        view.request = request

        context = view.get_context_data()

        assert "wallets" in context
        assert len(context["wallets"]) == 3
        assert context["active_network"] == "testnet"

    def test_signupview_get_context_data_with_session_network(self, rf):
        """Verify that the active_network is correctly read from the session."""
        request = rf.get(reverse("account_signup"))

        request = rf.get(reverse("account_signup"))
        request.session = {"active_network": "mainnet"}
        view = LoginView()
        view.setup(request)
        view.request = request

        context = view.get_context_data()

        assert context["active_network"] == "mainnet"


class UnconfirmedContributionsPageTest(TestCase):
    """Testing class for :class:`core.views.UnconfirmedContributionsView`."""

    def test_unconfirmedcontributions_page_renders_unconfirmedcontributions_template(
        self,
    ):
        response = self.client.get(reverse("unconfirmed_contributions"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "unconfirmed_contributions.html")


class TestUnconfirmedContributionsView:
    """Testing class for :class:`core.views.UnconfirmedContributionsView`."""

    def test_unconfirmedcontributionsview_is_subclass_of_listview(self):
        assert issubclass(UnconfirmedContributionsView, ListView)

    def test_unconfirmedcontributionsview_model(self):
        view = UnconfirmedContributionsView()
        assert view.model == Contribution

    def test_unconfirmedcontributionsview_paginate_by(self):
        view = UnconfirmedContributionsView()
        assert view.paginate_by == 20

    def test_unconfirmedcontributionsview_template_name(self):
        view = UnconfirmedContributionsView()
        assert view.template_name == "unconfirmed_contributions.html"


@pytest.mark.django_db
class TestDbUnconfirmedContributionsView:
    """Testing class for :class:`core.views.UnconfirmedContributionsView` with database."""

    def test_unconfirmedcontributionsview_get_queryset(self, contribution):
        # Create a confirmed contribution that should not appear
        Contribution.objects.create(
            contributor=contribution.contributor,
            cycle=contribution.cycle,
            platform=contribution.platform,
            reward=contribution.reward,
            percentage=100.0,
            confirmed=True,
        )

        view = UnconfirmedContributionsView()
        queryset = view.get_queryset()

        # Should only include unconfirmed contributions
        assert queryset.filter(confirmed=True).count() == 0
        assert queryset.filter(confirmed=False).count() == 1


@pytest.mark.django_db
class TestTransparencyReportView:
    """Testing class for :class:`core.views.TransparencyReportView`."""

    def test_transparencyreportview_is_subclass_of_formview(self):
        assert issubclass(TransparencyReportView, FormView)

    def test_transparencyreportview_only_accessible_to_superusers(
        self, client, regular_user
    ):
        url = reverse("transparency")
        response = client.get(url)
        assert response.status_code == 302
        client.force_login(regular_user)
        response = client.get(url)
        assert response.status_code == 302

    # # get_context_data
    def test_transparencyreportview_get_context_data_for_no_allocations(
        self, mocker, client, superuser
    ):
        mocked_fetch = mocker.patch("core.views.fetch_app_allocations", return_value=[])
        client.force_login(superuser)
        url = reverse("transparency")
        response = client.get(url)
        assert response.status_code == 200
        assert "min_year" in response.context
        assert "max_year" in response.context
        assert "min_date" not in response.context
        mocked_fetch.assert_called_with(force_update=False)

    def test_transparencyreportview_get_context_data_functionality(
        self, mocker, client, superuser
    ):
        mocked_fetch = mocker.patch(
            "core.views.fetch_app_allocations",
            return_value=[{"round-time": 1672531200}, {"round-time": 1675209600}],
        )
        client.force_login(superuser)
        url = reverse("transparency")
        response = client.get(url)
        assert response.status_code == 200
        assert "min_date" in response.context
        assert "max_date" in response.context
        assert "first_allocation_date" in response.context
        assert "last_allocation_date" in response.context
        assert response.context["min_date"] == "2023-01-01T00:00:00+00:00"
        assert response.context["first_allocation_date"] == "2023-01-01"
        assert response.context["last_allocation_date"] == "2023-02-01"
        mocked_fetch.assert_called_with(force_update=False)

    # # form_valid
    def test_transparencyreportview_form_valid_for_no_data(
        self, mocker, client, superuser
    ):
        mocker.patch(
            "core.views.fetch_app_allocations",
            return_value=[{"round-time": 1672531200}],
        )
        mocked_create = mocker.patch(
            "core.views.create_transparency_report", return_value=""
        )
        client.force_login(superuser)
        url = reverse("transparency")
        data = {
            "report_type": "monthly",
            "month": 1,
            "year": 2023,
            "ordering": "chronological",
        }
        response = client.post(url, data)
        assert response.status_code == 200
        assert "report" in response.context
        assert response.context["report"] == "No data"
        mocked_create.assert_called_once()

    def test_transparencyreportview_form_valid_functionality(
        self, mocker, client, superuser
    ):
        mocked_fetch = mocker.patch(
            "core.views.fetch_app_allocations",
            return_value=[{"round-time": 1672531200}, {"round-time": 1675209600}],
        )
        mocked_create = mocker.patch(
            "core.views.create_transparency_report", return_value="report data"
        )
        client.force_login(superuser)
        url = reverse("transparency")
        data = {
            "report_type": "monthly",
            "month": 1,
            "year": 2023,
            "ordering": "chronological",
        }
        response = client.post(url, data)
        assert response.status_code == 200
        assert "report" in response.context
        assert "first_allocation_date" in response.context
        assert "last_allocation_date" in response.context
        assert response.context["report"] == "report data"
        assert response.context["first_allocation_date"] == "2023-01-01"
        assert response.context["last_allocation_date"] == "2023-02-01"
        mocked_create.assert_called_once()
        mocked_fetch.assert_called_with(force_update=False)


@pytest.mark.django_db
class TestRefreshTransparencyDataView:
    """Testing class for :class:`core.views.RefreshTransparencyDataView`."""

    def test_refreshtransparencydataview_is_subclass_of_redirectview(self, mocker):
        from django.views.generic import RedirectView

        from core.views import RefreshTransparencyDataView

        assert issubclass(RefreshTransparencyDataView, RedirectView)

    def test_refreshtransparencydataview_only_accessible_to_superusers(
        self, client, regular_user
    ):
        url = reverse("refresh_transparency_data")
        response = client.get(url)
        assert response.status_code == 302
        client.force_login(regular_user)
        response = client.get(url)
        assert response.status_code == 302

    def test_refreshtransparencydataview_refreshes_and_redirects(
        self, mocker, client, superuser
    ):
        mocked_refresh = mocker.patch("core.views.refresh_data")
        mocked_messages = mocker.patch("core.views.messages")
        client.force_login(superuser)
        url = reverse("refresh_transparency_data")
        response = client.get(url)
        assert response.status_code == 302
        assert response.url == reverse("transparency")
        mocked_refresh.assert_called_once()
        mocked_messages.success.assert_called_once()


"""Testing module for :py:mod:`core.views` module - IssueWebhookView tests."""

import json
from unittest.mock import Mock

import pytest
from django.http import JsonResponse
from django.test import RequestFactory
from django.urls import reverse

from core.views import IssueWebhookView


@pytest.mark.django_db
class TestIssueWebhookView:
    """Testing class for :class:`core.views.IssueWebhookView`."""

    def test_issuewebhookview_is_subclass_of_view(self):
        """Test that IssueWebhookView is a subclass of View."""
        from django.views.generic import View

        assert issubclass(IssueWebhookView, View)

    def test_issuewebhookview_dispatch_is_csrf_exempt(self):
        """Test that dispatch method has csrf_exempt decorator."""
        view = IssueWebhookView()
        # Check by calling dispatch which should work without CSRF token
        request_factory = RequestFactory()
        request = request_factory.post("/webhook/")
        response = view.dispatch(request)
        # If csrf_exempt is applied, it shouldn't raise CSRF error
        assert response is not None

    def test_issuewebhookview_dispatch_requires_post(self, client):
        """Test that only POST requests are allowed."""
        url = reverse("issue_webhook")
        # GET should be not allowed (405 Method Not Allowed)
        response = client.get(url)
        assert response.status_code == 405
        # POST should be allowed
        response = client.post(url)
        assert response.status_code != 405  # Will be 500 or other error

    def test_issuewebhookview_post_success(self, mocker, client):
        """Test successful webhook processing."""
        # Mock WebhookHandler to return a success response
        mock_handler = mocker.MagicMock()
        # Return a real JsonResponse instead of MagicMock
        mock_response = JsonResponse(
            {"status": "success", "message": "Webhook processed"}, status=200
        )
        mock_handler.process_webhook.return_value = mock_response
        mock_webhook_handler_class = mocker.patch(
            "core.views.WebhookHandler", return_value=mock_handler
        )
        url = reverse("issue_webhook")
        data = {"test": "payload"}
        response = client.post(
            url, data=json.dumps(data), content_type="application/json"
        )
        assert response.status_code == 200
        response_data = json.loads(response.content)
        assert response_data["status"] == "success"
        assert response_data["message"] == "Webhook processed"
        mock_webhook_handler_class.assert_called_once()
        mock_handler.process_webhook.assert_called_once()

    def test_issuewebhookview_post_with_exception(self, mocker, client):
        """Test webhook processing when an exception occurs."""
        # Mock WebhookHandler to raise an exception
        mock_handler = mocker.MagicMock()
        mock_handler.process_webhook.side_effect = Exception("Test error")
        mocker.patch("core.views.WebhookHandler", return_value=mock_handler)
        # Mock logger to verify error logging
        mock_logger = mocker.patch("core.views.logger")
        url = reverse("issue_webhook")
        data = {"test": "payload"}
        response = client.post(
            url, data=json.dumps(data), content_type="application/json"
        )
        assert response.status_code == 500
        response_data = json.loads(response.content)
        assert response_data["status"] == "error"
        assert "Internal server error" in response_data["message"]
        mock_logger.error.assert_called_once_with(
            "Webhook processing failed: Test error"
        )

    def test_issuewebhookview_post_with_webhook_handler_exception(self, mocker, client):
        """Test webhook processing when WebhookHandler itself raises an exception."""
        # Make WebhookHandler instantiation raise an exception
        mocker.patch(
            "core.views.WebhookHandler",
            side_effect=Exception("Handler creation failed"),
        )
        # Mock logger to verify error logging
        mock_logger = mocker.patch("core.views.logger")
        url = reverse("issue_webhook")
        data = {"test": "payload"}
        response = client.post(
            url, data=json.dumps(data), content_type="application/json"
        )
        assert response.status_code == 500
        response_data = json.loads(response.content)
        assert response_data["status"] == "error"
        assert "Internal server error" in response_data["message"]
        mock_logger.error.assert_called_once_with(
            "Webhook processing failed: Handler creation failed"
        )

    def test_issuewebhookview_post_empty_body(self, mocker, client):
        """Test webhook processing with empty request body."""
        mock_handler = mocker.MagicMock()
        # Return a real JsonResponse instead of MagicMock
        mock_response = JsonResponse(
            {"status": "success", "message": "Processed empty payload"}, status=200
        )
        mock_handler.process_webhook.return_value = mock_response
        mocker.patch("core.views.WebhookHandler", return_value=mock_handler)
        url = reverse("issue_webhook")
        response = client.post(url, content_type="application/json")
        assert response.status_code == 200
        mock_handler.process_webhook.assert_called_once()

    def test_issuewebhookview_post_invalid_json(self, mocker, client):
        """Test webhook processing with invalid JSON."""
        mock_handler = mocker.MagicMock()
        # Simulate WebhookHandler handling invalid JSON
        mock_response = JsonResponse(
            {"status": "error", "message": "Invalid JSON"}, status=400
        )
        mock_handler.process_webhook.return_value = mock_response
        mocker.patch("core.views.WebhookHandler", return_value=mock_handler)
        url = reverse("issue_webhook")
        response = client.post(
            url, data="invalid json", content_type="application/json"
        )
        # The view should still return whatever the handler returns
        assert response.status_code == 400
        response_data = json.loads(response.content)
        assert response_data["status"] == "error"
        mock_handler.process_webhook.assert_called_once()

    def test_issuewebhookview_post_with_different_content_types(self, mocker, client):
        """Test webhook processing with different content types."""
        mock_handler = mocker.MagicMock()
        mock_response = JsonResponse({"status": "success"}, status=200)
        mock_handler.process_webhook.return_value = mock_response
        mocker.patch("core.views.WebhookHandler", return_value=mock_handler)

        url = reverse("issue_webhook")

        # Test with application/json
        response = client.post(
            url, data=json.dumps({"test": "data"}), content_type="application/json"
        )
        assert response.status_code == 200

        # Test with text/plain
        response = client.post(url, data="plain text", content_type="text/plain")
        assert response.status_code == 200

        # Test with no content type - provide data as dictionary
        response = client.post(url, data={"test": "no content type"})
        assert response.status_code == 200

        # WebhookHandler should be called 3 times
        assert mock_handler.process_webhook.call_count == 3

    def test_issuewebhookview_post_returns_correct_response_type(self, mocker, client):
        """Test that the view returns JsonResponse."""
        mock_handler = mocker.MagicMock()
        mock_response = JsonResponse({"test": "data"}, status=200)
        mock_handler.process_webhook.return_value = mock_response
        mocker.patch("core.views.WebhookHandler", return_value=mock_handler)
        url = reverse("issue_webhook")
        response = client.post(
            url, data=json.dumps({"test": "payload"}), content_type="application/json"
        )
        # Verify response is JSON
        assert response["Content-Type"] == "application/json"
        assert response.status_code == 200
        json.loads(response.content)  # Should not raise JSONDecodeError

    def test_issuewebhookview_post_with_handler_validation_failure(
        self, mocker, client
    ):
        """Test webhook processing when handler validation fails."""
        mock_handler = mocker.MagicMock()
        mock_response = JsonResponse(
            {"status": "error", "message": "Webhook validation failed"}, status=403
        )
        mock_handler.process_webhook.return_value = mock_response
        mocker.patch("core.views.WebhookHandler", return_value=mock_handler)
        url = reverse("issue_webhook")
        response = client.post(
            url, data=json.dumps({"test": "payload"}), content_type="application/json"
        )
        assert response.status_code == 403
        response_data = json.loads(response.content)
        assert response_data["status"] == "error"
        assert response_data["message"] == "Webhook validation failed"

    def test_issuewebhookview_post_with_handler_no_issue_data(self, mocker, client):
        """Test webhook processing when handler finds no issue data."""
        mock_handler = mocker.MagicMock()
        mock_response = JsonResponse(
            {"status": "success", "message": "Not an issue creation event"}, status=200
        )
        mock_handler.process_webhook.return_value = mock_response
        mocker.patch("core.views.WebhookHandler", return_value=mock_handler)
        url = reverse("issue_webhook")
        response = client.post(
            url, data=json.dumps({"test": "payload"}), content_type="application/json"
        )
        assert response.status_code == 200
        response_data = json.loads(response.content)
        assert response_data["status"] == "success"
        assert response_data["message"] == "Not an issue creation event"

    def test_issuewebhookview_post_direct_view_call(self, mocker):
        """Test calling the view directly with RequestFactory."""
        # This test doesn't use the Django test client
        mock_handler = mocker.MagicMock()
        mock_response = JsonResponse(
            {"status": "success", "message": "Direct test"}, status=200
        )
        mock_handler.process_webhook.return_value = mock_response
        mocker.patch("core.views.WebhookHandler", return_value=mock_handler)
        view = IssueWebhookView()
        request_factory = RequestFactory()
        request = request_factory.post(
            "/webhook/",
            data=json.dumps({"test": "data"}),
            content_type="application/json",
        )
        response = view.post(request)
        assert response.status_code == 200
        response_data = json.loads(response.content)
        assert response_data["status"] == "success"
        mock_handler.process_webhook.assert_called_once()
