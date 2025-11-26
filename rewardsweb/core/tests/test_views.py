"""Testing module for :py:mod:`core.views` underlying views."""

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
    LoginView,
    ProfileDisplay,
    ProfileEditView,
    ProfileUpdate,
    SignupView,
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
