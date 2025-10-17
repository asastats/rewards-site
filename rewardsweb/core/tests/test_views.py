"""Testing module for :py:mod:`core.views` module."""

from unittest import mock
import time

import pytest
from allauth.account.forms import LoginForm
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase
from django.urls import reverse, reverse_lazy
from django.utils.html import escape
from django.views import View
from django.views.generic import DetailView, UpdateView
from django.views.generic.detail import SingleObjectMixin

from core.forms import ProfileFormSet, UpdateUserForm
from core.views import ProfileDisplay, ProfileEditView, ProfileUpdate
from utils.constants.core import (
    TOO_LONG_USER_FIRST_NAME_ERROR,
    TOO_LONG_USER_LAST_NAME_ERROR,
)

user_model = get_user_model()


# # HELPERS
def get_user_edit_fake_post_data(user, first_name="first_name", last_name="last_name"):
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
    def post_invalid_input(self):
        return self.client.post(reverse("index"), data={"address": "foobar"})

    def test_index_page_renders_index_template(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "index.html")


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
            data=get_user_edit_fake_post_data(self.user, first_name="xyz" * 51),
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
        self.assertContains(response, "profile-0-github_token")

    def test_profile_page_post_ends_in_profile_page(self):
        response = self.client.post(
            reverse("profile"), data=get_user_edit_fake_post_data(self.user)
        )
        self.assertRedirects(response, reverse("profile"))

    def test_profile_page_saving_a_post_request_to_an_existing_user(self):
        self.client.post(
            reverse("profile"),
            data=get_user_edit_fake_post_data(
                self.user, first_name="Newname", last_name="Newlastname"
            ),
        )
        user = user_model.objects.last()
        self.assertEqual(user.first_name, "Newname")
        self.assertEqual(user.last_name, "Newlastname")

    def test_profile_page_for_too_long_first_name_shows_errors_on_page(self):
        response = self.client.post(
            reverse("profile"),
            data=get_user_edit_fake_post_data(self.user, first_name="xyz" * 51),
        )
        self.assertContains(response, escape(TOO_LONG_USER_FIRST_NAME_ERROR))

    def test_profile_page_for_too_long_lastname_shows_errors_on_page(self):
        response = self.client.post(
            reverse("profile"),
            data=get_user_edit_fake_post_data(self.user, last_name="xyz " * 40),
        )
        self.assertContains(response, escape(TOO_LONG_USER_LAST_NAME_ERROR))

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

    def test_for_invalid_input_renders_login_template(self):
        response = self.post_invalid_input()
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "account/login.html")

    def test_login_page_for_invalid_input_passes_form_to_template(self):
        response = self.post_invalid_input()
        self.assertIsInstance(response.context["form"], LoginForm)

    def test_for_invalid_input_shows_errors_on_page(self):
        response = self.post_invalid_input()
        self.assertContains(
            response, "The username and/or password you specified are not correct."
        )

    def test_login_page_links_to_forget_password_page(self):
        response = self.client.get(reverse("account_login"))
        self.assertContains(response, reverse("account_reset_password"))


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
        data = get_user_edit_fake_post_data(self.user)
        view = self.setup_view(view, self.request)

        # Run.
        # form=form, profile_form=profile_form
        view_method = view.post(
            self.request,
            form=UpdateUserForm(instance=self.user, data=data),
        )
        # Check.
        assert isinstance(view_method.context_data["view"], ProfileUpdate)
