"""Testing module for :py:mod:`core.forms` module."""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.forms import (
    CharField,
    CheckboxSelectMultiple,
    ChoiceField,
    DecimalField,
    Form,
    HiddenInput,
    IntegerField,
    ModelChoiceField,
    ModelForm,
    MultipleChoiceField,
    NumberInput,
    RadioSelect,
    Select,
    Textarea,
    TextInput,
    ValidationError,
)

from core.forms import (
    ContributionCreateForm,
    ContributionEditForm,
    ContributionInvalidateForm,
    CreateIssueForm,
    IssueLabelsForm,
    ProfileForm,
    ProfileFormSet,
    UpdateUserForm,
)
from core.models import Contribution, Cycle, IssueStatus, Profile
from utils.constants.ui import MISSING_OPTION_TEXT


class TestContributionEditForm:
    """Testing class for :class:`ContributionEditForm`."""

    # # ContributionEditForm
    def test_contributioneditform_issubclass_of_modelform(self):
        assert issubclass(ContributionEditForm, ModelForm)

    def test_contributioneditform_reward_field(self):
        form = ContributionEditForm()
        assert "reward" in form.base_fields
        assert isinstance(form.base_fields["reward"], ModelChoiceField)
        assert isinstance(form.base_fields["reward"].widget, Select)
        assert "class" in form.base_fields["reward"].widget.attrs
        assert form.base_fields["reward"].empty_label == "Select a reward type"

    def test_contributioneditform_percentage_field(self):
        form = ContributionEditForm()
        assert "percentage" in form.base_fields
        assert isinstance(form.base_fields["percentage"], DecimalField)
        assert form.base_fields["percentage"].max_digits == 5
        assert form.base_fields["percentage"].decimal_places == 2
        assert isinstance(form.base_fields["percentage"].widget, NumberInput)
        assert "class" in form.base_fields["percentage"].widget.attrs
        assert "step" in form.base_fields["percentage"].widget.attrs
        assert "min" in form.base_fields["percentage"].widget.attrs
        assert "max" in form.base_fields["percentage"].widget.attrs

    def test_contributioneditform_comment_field(self):
        form = ContributionEditForm()
        assert "comment" in form.base_fields
        assert isinstance(form.base_fields["comment"], CharField)
        assert not form.base_fields["comment"].required
        assert isinstance(form.base_fields["comment"].widget, TextInput)
        assert "class" in form.base_fields["comment"].widget.attrs

    def test_contributioneditform_issue_number_field(self):
        form = ContributionEditForm()
        assert "issue_number" in form.base_fields
        assert isinstance(form.base_fields["issue_number"], IntegerField)
        assert not form.base_fields["issue_number"].required
        assert form.base_fields["issue_number"].min_value == 1
        assert isinstance(form.base_fields["issue_number"].widget, NumberInput)
        assert "class" in form.base_fields["issue_number"].widget.attrs
        assert "placeholder" in form.base_fields["issue_number"].widget.attrs

    def test_contributioneditform_issue_status_field(self):
        form = ContributionEditForm()
        assert "issue_status" in form.base_fields
        assert isinstance(form.base_fields["issue_status"], ChoiceField)
        assert form.base_fields["issue_status"].label == "Issue Status"
        assert not form.base_fields["issue_status"].required
        assert form.base_fields["issue_status"].initial == IssueStatus.ARCHIVED
        assert isinstance(form.base_fields["issue_status"].widget, RadioSelect)
        assert form.base_fields["issue_status"].choices == IssueStatus.choices

    # # Meta
    def test_contributioneditform_meta_model_is_contribution(self):
        form = ContributionEditForm()
        assert form._meta.model == Contribution

    def test_contributioneditform_meta_fields(self):
        form = ContributionEditForm()
        assert form._meta.fields == ["reward", "percentage", "comment"]

    @pytest.mark.django_db
    def test_contributioneditform_initial_issue_number_with_existing_issue(
        self, contribution_with_issue
    ):
        form = ContributionEditForm(instance=contribution_with_issue)
        assert (
            form.fields["issue_number"].initial == contribution_with_issue.issue.number
        )

    @pytest.mark.django_db
    def test_contributioneditform_initial_issue_status_with_existing_issue(
        self, contribution_with_issue
    ):
        form = ContributionEditForm(instance=contribution_with_issue)
        assert (
            form.fields["issue_status"].initial == contribution_with_issue.issue.status
        )

    @pytest.mark.django_db
    def test_contributioneditform_initial_issue_number_without_issue(
        self, contribution
    ):
        form = ContributionEditForm(instance=contribution)
        assert form.fields["issue_number"].initial is None

    @pytest.mark.django_db
    def test_contributioneditform_initial_issue_status_without_issue(
        self, contribution
    ):
        form = ContributionEditForm(instance=contribution)
        assert form.fields["issue_status"].initial == IssueStatus.ARCHIVED


class TestContributionInvalidateForm:
    """Testing class for :class:`ContributionInvalidateForm`."""

    # # ContributionInvalidateForm
    def test_contributioninvalidateform_issubclass_of_modelform(self):
        assert issubclass(ContributionInvalidateForm, ModelForm)

    def test_contributioninvalidateform_comment_field(self):
        form = ContributionInvalidateForm()
        assert "comment" in form.base_fields
        assert isinstance(form.base_fields["comment"], CharField)
        assert not form.base_fields["comment"].required
        assert isinstance(form.base_fields["comment"].widget, Textarea)
        assert "class" in form.base_fields["comment"].widget.attrs

    # # Meta
    def test_contributioninvalidateform_meta_model_is_contribution(self):
        form = ContributionInvalidateForm()
        assert form._meta.model == Contribution

    def test_contributioninvalidateform_meta_fields(self):
        form = ContributionInvalidateForm()
        assert form._meta.fields == ["comment"]


class TestContributionCreateForm:
    """Tests for ContributionCreateForm."""

    def test_contributioncreateform_is_modelform(self):
        assert issubclass(ContributionCreateForm, ModelForm)

    @pytest.mark.django_db
    def test_form_fields_exist(self):
        form = ContributionCreateForm()
        fields = form.base_fields

        assert "contributor" in fields
        assert "cycle" in fields
        assert "platform" in fields
        assert "reward" in fields
        assert "percentage" in fields
        assert "comment" in fields
        assert "issue_number" in fields
        assert "issue_status" in fields

    @pytest.mark.django_db
    def test_contributor_field(self):
        form = ContributionCreateForm()
        assert isinstance(form.base_fields["contributor"], ModelChoiceField)
        assert isinstance(form.base_fields["contributor"].widget, Select)

    @pytest.mark.django_db
    def test_cycle_field(self):
        form = ContributionCreateForm()
        assert isinstance(form.base_fields["cycle"], ModelChoiceField)
        assert isinstance(form.base_fields["cycle"].widget, Select)

    @pytest.mark.django_db
    def test_platform_field(self):
        form = ContributionCreateForm()
        assert isinstance(form.base_fields["platform"], ModelChoiceField)
        assert isinstance(form.base_fields["platform"].widget, Select)

    @pytest.mark.django_db
    def test_reward_field(self):
        form = ContributionCreateForm()
        reward_field = form.base_fields["reward"]
        assert isinstance(reward_field, ModelChoiceField)
        assert reward_field.empty_label == "Select a reward type"
        assert isinstance(reward_field.widget, Select)

    @pytest.mark.django_db
    def test_percentage_field(self):
        form = ContributionCreateForm()
        percentage_field = form.base_fields["percentage"]

        assert isinstance(percentage_field, DecimalField)
        assert percentage_field.max_digits == 5
        assert percentage_field.decimal_places == 2
        assert isinstance(percentage_field.widget, NumberInput)

    @pytest.mark.django_db
    def test_comment_field(self):
        form = ContributionCreateForm()
        comment_field = form.base_fields["comment"]

        assert isinstance(comment_field, CharField)
        assert not comment_field.required
        assert isinstance(comment_field.widget, TextInput)

    @pytest.mark.django_db
    def test_issue_number_field(self):
        form = ContributionCreateForm()
        issue_number = form.base_fields["issue_number"]

        assert isinstance(issue_number, IntegerField)
        assert not issue_number.required
        assert issue_number.min_value == 1
        assert isinstance(issue_number.widget, NumberInput)

    @pytest.mark.django_db
    def test_issue_status_field(self):
        form = ContributionCreateForm()
        issue_status = form.base_fields["issue_status"]

        assert isinstance(issue_status, ChoiceField)
        assert issue_status.choices == IssueStatus.choices
        assert issue_status.initial == IssueStatus.CREATED  # per your view design
        assert isinstance(issue_status.widget, RadioSelect)

    @pytest.mark.django_db
    def test_preselected_issue_hides_issue_fields(self, issue):
        form = ContributionCreateForm(preselected_issue=issue)

        assert isinstance(form.fields["issue_number"].widget, HiddenInput)
        assert isinstance(form.fields["issue_status"].widget, HiddenInput)

    @pytest.mark.django_db
    def test_default_cycle_is_latest(self):
        """Ensure the default cycle is maximum start date."""
        Cycle.objects.create(start="2024-06-01")
        new_cycle = Cycle.objects.create(start="2024-12-01")

        form = ContributionCreateForm()
        assert form.fields["cycle"].initial == new_cycle


class TestCreateIssueForm:
    """Testing class for :class:`CreateIssueForm`."""

    # # CreateIssueForm
    def test_createissueform_issubclass_of_form(self):
        assert issubclass(CreateIssueForm, Form)

    def test_createissueform_labels_field(self):
        form = CreateIssueForm()
        assert "labels" in form.base_fields
        assert isinstance(form.base_fields["labels"], MultipleChoiceField)
        assert isinstance(form.base_fields["labels"].widget, CheckboxSelectMultiple)
        assert form.base_fields["labels"].label == "Select labels"
        assert form.base_fields["labels"].required

    def test_createissueform_priority_field(self):
        form = CreateIssueForm()
        assert "priority" in form.base_fields
        assert isinstance(form.base_fields["priority"], ChoiceField)
        assert isinstance(form.base_fields["priority"].widget, RadioSelect)
        assert form.base_fields["priority"].label == "Priority level"
        assert form.base_fields["priority"].required
        assert form.base_fields["priority"].initial == "medium priority"

    def test_createissueform_issue_title_field(self):
        form = CreateIssueForm()
        assert "issue_title" in form.base_fields
        assert isinstance(form.base_fields["issue_title"], CharField)
        assert form.base_fields["issue_title"].max_length == 100
        assert form.base_fields["issue_title"].label == "Title"
        assert form.base_fields["issue_title"].required
        assert isinstance(form.base_fields["issue_title"].widget, TextInput)
        assert "class" in form.base_fields["issue_title"].widget.attrs
        assert "placeholder" in form.base_fields["issue_title"].widget.attrs

    def test_createissueform_issue_body_field(self):
        form = CreateIssueForm()
        assert "issue_body" in form.base_fields
        assert isinstance(form.base_fields["issue_body"], CharField)
        assert form.base_fields["issue_body"].max_length == 2000
        assert form.base_fields["issue_body"].label == "Body"
        assert form.base_fields["issue_body"].required
        assert isinstance(form.base_fields["issue_body"].widget, Textarea)
        assert "class" in form.base_fields["issue_body"].widget.attrs
        assert "placeholder" in form.base_fields["issue_body"].widget.attrs

    def test_createissueform_clean_labels_valid_data(self):
        form = CreateIssueForm()
        form.cleaned_data = {"labels": ["bug", "enhancement"]}
        result = form.clean_labels()
        assert result == ["bug", "enhancement"]

    def test_createissueform_clean_labels_empty_data(self):
        form = CreateIssueForm()
        form.cleaned_data = {"labels": []}
        with pytest.raises(ValidationError) as exc_info:
            form.clean_labels()
        assert MISSING_OPTION_TEXT in str(exc_info.value)


class TestIssueLabelsForm:
    """Testing class for :class:`IssueLabelsForm`."""

    # # IssueLabelsForm
    def test_issuelabelsform_issubclass_of_form(self):
        assert issubclass(IssueLabelsForm, Form)

    def test_issuelabelsform_labels_field(self):
        form = IssueLabelsForm()
        assert "labels" in form.base_fields
        assert isinstance(form.base_fields["labels"], MultipleChoiceField)
        assert isinstance(form.base_fields["labels"].widget, CheckboxSelectMultiple)
        assert form.base_fields["labels"].required

    def test_issuelabelsform_priority_field(self):
        form = IssueLabelsForm()
        assert "priority" in form.base_fields
        assert isinstance(form.base_fields["priority"], ChoiceField)
        assert isinstance(form.base_fields["priority"].widget, RadioSelect)
        assert form.base_fields["priority"].required
        assert form.base_fields["priority"].initial == "medium priority"

    def test_issuelabelsform_clean_labels_valid_data(self):
        form = IssueLabelsForm()
        form.cleaned_data = {"labels": ["bug", "enhancement"]}
        result = form.clean_labels()
        assert result == ["bug", "enhancement"]

    def test_issuelabelsform_clean_labels_empty_data(self):
        form = IssueLabelsForm()
        form.cleaned_data = {"labels": []}
        with pytest.raises(ValidationError) as exc_info:
            form.clean_labels()
        assert MISSING_OPTION_TEXT in str(exc_info.value)


# # PROFILE
class TestUpdateUserForm:
    """Testing class for :class:`UpdateUserForm`."""

    # # UpdateUserForm
    def test_updateuserform_issubclass_of_modelform(self):
        assert issubclass(UpdateUserForm, ModelForm)

    def test_updateuserform_first_name_field(self):
        form = UpdateUserForm()
        assert "first_name" in form.base_fields
        assert not form.base_fields["first_name"].required
        assert isinstance(form.base_fields["first_name"], CharField)
        assert isinstance(form.base_fields["first_name"].widget, TextInput)
        assert "class" in form.base_fields["first_name"].widget.attrs
        assert "placeholder" in form.base_fields["first_name"].widget.attrs

    def test_updateuserform_last_name_field(self):
        form = UpdateUserForm()
        assert "last_name" in form.base_fields
        assert not form.base_fields["last_name"].required
        assert isinstance(form.base_fields["last_name"], CharField)
        assert isinstance(form.base_fields["last_name"].widget, TextInput)
        assert "class" in form.base_fields["last_name"].widget.attrs
        assert "placeholder" in form.base_fields["last_name"].widget.attrs

    # # Meta
    def test_updateuserform_meta_fields(self):
        form = UpdateUserForm()
        assert form._meta.fields == ["first_name", "last_name"]

    def test_updateuserform_meta_model_is_user(self):
        form = UpdateUserForm()
        assert form._meta.model == User

    # # save
    @pytest.mark.django_db
    def test_updateuserform_save(self):
        user_model = get_user_model()
        user = user_model.objects.create(email="edituser@example.com")
        form = UpdateUserForm(data={"first_name": "John", "last_name": "Doe"})
        form.instance = user
        form.save()
        assert user_model.objects.all()[0].first_name == "John"


class TestProfileForm:
    """Testing class for :class:`ProfileForm`."""

    # # ProfileForm
    def test_profileform_issubclass_of_modelform(self):
        assert issubclass(ProfileForm, ModelForm)

    def test_profileform_issue_tracker_api_token_field(self):
        form = ProfileForm()
        assert "issue_tracker_api_token" in form.base_fields
        assert not form.base_fields["issue_tracker_api_token"].required
        assert isinstance(form.base_fields["issue_tracker_api_token"], CharField)
        assert isinstance(form.base_fields["issue_tracker_api_token"].widget, TextInput)
        assert "class" in form.base_fields["issue_tracker_api_token"].widget.attrs
        assert "placeholder" in form.base_fields["issue_tracker_api_token"].widget.attrs
        assert "GitHub" in form.base_fields["issue_tracker_api_token"].help_text

    # # Meta
    def test_profileform_meta_model_is_profile(self):
        form = ProfileForm()
        assert form._meta.model == Profile

    def test_profileform_meta_fields(self):
        form = ProfileForm()
        assert "issue_tracker_api_token" in form._meta.fields


class TestProfileFormSet:
    """Testing class for ProfileFormSet instance."""

    def test_profileformset_instance_is_user(self):
        formset = ProfileFormSet()
        assert isinstance(formset.instance, User)

    def test_profileformset_model_is_profile(self):
        formset = ProfileFormSet()
        assert formset.model == Profile

    def test_profileformset_issue_tracker_api_token_field(self):
        formset = ProfileFormSet()
        assert isinstance(formset.forms[0], ProfileForm)
        assert formset.extra == 1
        assert not formset.can_delete
        assert formset.max_num == 1
