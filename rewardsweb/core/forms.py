"""Module containing code dealing with core app's forms."""

from datetime import datetime

from captcha.fields import CaptchaField, CaptchaTextInput
from django.contrib.auth import logout
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.forms import (
    CharField,
    CheckboxSelectMultiple,
    ChoiceField,
    DecimalField,
    Form,
    HiddenInput,
    IntegerField,
    ModelChoiceField,
    MultipleChoiceField,
    NumberInput,
    RadioSelect,
    Select,
    Textarea,
    TextInput,
    ValidationError,
)
from django.forms.models import ModelForm, inlineformset_factory

from core.models import (
    Contribution,
    Contributor,
    Cycle,
    IssueStatus,
    Profile,
    Reward,
    SocialPlatform,
)
from utils.constants.core import (
    ISSUE_CREATION_LABEL_CHOICES,
    ISSUE_PRIORITY_CHOICES,
    TRANPARENCY_REPORT_REQUIRED_FIELDS,
)
from utils.constants.ui import MISSING_OPTION_TEXT, TEXTINPUT_CLASS


class ContributionEditForm(ModelForm):
    """Model form class for editing contribution data.

    :var ContributionEditForm.reward: reward type for the contribution
    :type ContributionEditForm.reward: :class:`django.forms.ModelChoiceField`
    :var ContributionEditForm.percentage: percentage value for the contribution
    :type ContributionEditForm.percentage: :class:`django.forms.DecimalField`
    :var ContributionEditForm.comment: optional comment for the contribution
    :type ContributionEditForm.comment: :class:`django.forms.CharField`
    :var ContributionEditForm.issue_number: tracker issue number
    :type ContributionEditForm.issue_number: :class:`django.forms.IntegerField`
    :var ContributionEditForm.issue_status: Status for newly created issue
    :type ContributionEditForm.issue_status: :class:`django.forms.ChoiceField`
    """

    reward = ModelChoiceField(
        queryset=Reward.objects.filter(active=True),
        empty_label="Select a reward type",
        widget=Select(attrs={"class": "select select-bordered w-full"}),
    )
    percentage = DecimalField(
        max_digits=5,
        decimal_places=2,
        widget=NumberInput(
            attrs={
                "class": TEXTINPUT_CLASS,
                "step": "0.01",
                "min": "0",
                "max": "100",
            }
        ),
    )
    comment = CharField(
        required=False, widget=TextInput(attrs={"class": TEXTINPUT_CLASS})
    )
    issue_number = IntegerField(
        required=False,
        min_value=1,
        widget=NumberInput(
            attrs={
                "class": TEXTINPUT_CLASS,
                "placeholder": "Tracker issue number (optional)",
            }
        ),
    )
    issue_status = ChoiceField(
        choices=IssueStatus.choices,
        widget=RadioSelect(),
        label="Issue Status",
        required=False,
        initial=IssueStatus.ARCHIVED,
    )

    class Meta:
        model = Contribution
        fields = ["reward", "percentage", "comment"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set initial value for issue_number from existing issue
        if self.instance and self.instance.issue:
            self.fields["issue_number"].initial = self.instance.issue.number
            # Set initial issue_status from existing issue
            self.fields["issue_status"].initial = self.instance.issue.status


class ContributionInvalidateForm(ModelForm):
    """Model form class for setting contribution as already existing.

    :var ContributionInvalidateForm.comment: optional comment to add as a reply
    :type ContributionInvalidateForm.comment: :class:`django.forms.CharField`
    """

    comment = CharField(
        widget=Textarea(
            attrs={
                "class": "textarea textarea-bordered w-full h-32",
                "placeholder": "Enter comment text here...",
            }
        ),
        label="Reply",
        max_length=500,
        required=False,
    )

    class Meta:
        model = Contribution
        fields = ["comment"]


class ContributionCreateForm(ModelForm):
    """Model form class for adding new contribution.

    :var ContributionCreateForm.contributor: contribution's contributor instance
    :type ContributionCreateForm.contributor: :class:`django.forms.ModelChoiceField`
    :var ContributionCreateForm.cycle: contribution's cycle instance
    :type ContributionCreateForm.cycle: :class:`django.forms.ModelChoiceField`
    :var ContributionCreateForm.platform: contribution's social platform instance
    :type ContributionCreateForm.platform: :class:`django.forms.ModelChoiceField`
    :var ContributionCreateForm.reward: reward type for the contribution
    :type ContributionCreateForm.reward: :class:`django.forms.ModelChoiceField`
    :var ContributionCreateForm.percentage: percentage value for the contribution
    :type ContributionCreateForm.percentage: :class:`django.forms.DecimalField`
    :var ContributionCreateForm.comment: optional comment for the contribution
    :type ContributionCreateForm.comment: :class:`django.forms.CharField`
    :var ContributionCreateForm.issue_number: tracker issue number
    :type ContributionCreateForm.issue_number: :class:`django.forms.IntegerField`
    :var ContributionCreateForm.issue_status: Status for newly created issue
    :type ContributionCreateForm.issue_status: :class:`django.forms.ChoiceField`
    """

    contributor = ModelChoiceField(
        queryset=Contributor.objects.all(),
        widget=Select(attrs={"class": "select select-bordered w-full"}),
    )
    cycle = ModelChoiceField(
        queryset=Cycle.objects.all(),
        widget=Select(attrs={"class": "select select-bordered w-full"}),
    )
    platform = ModelChoiceField(
        queryset=SocialPlatform.objects.all(),
        widget=Select(attrs={"class": "select select-bordered w-full"}),
    )
    reward = ModelChoiceField(
        queryset=Reward.objects.filter(active=True),
        empty_label="Select a reward type",
        widget=Select(attrs={"class": "select select-bordered w-full"}),
    )
    percentage = DecimalField(
        max_digits=5,
        decimal_places=2,
        initial=1,
        widget=NumberInput(
            attrs={"class": TEXTINPUT_CLASS, "step": "0.01", "min": "0", "max": "100"}
        ),
    )
    comment = CharField(
        required=False,
        widget=TextInput(attrs={"class": TEXTINPUT_CLASS}),
    )

    # Only shown if Issue is NOT pre-set
    issue_number = IntegerField(
        required=False,
        min_value=1,
        widget=NumberInput(
            attrs={
                "class": TEXTINPUT_CLASS,
                "placeholder": "Tracker issue number (optional)",
            }
        ),
    )
    issue_status = ChoiceField(
        choices=IssueStatus.choices,
        widget=RadioSelect(),
        required=False,
        initial=IssueStatus.CREATED,
    )

    class Meta:
        model = Contribution
        fields = [
            "contributor",
            "cycle",
            "platform",
            "reward",
            "percentage",
            "comment",
        ]

    def __init__(self, *args, **kwargs):
        self.preselected_issue = kwargs.pop("preselected_issue", None)
        super().__init__(*args, **kwargs)

        # Default cycle = most recent Cycle (latest start date)
        try:
            latest_cycle = Cycle.objects.latest("start")
            self.fields["cycle"].initial = latest_cycle
        except ObjectDoesNotExist:
            pass  # no cycles exist yet

        # Hide issue fields if issue preselected
        if self.preselected_issue:
            self.fields["issue_number"].widget = HiddenInput()
            self.fields["issue_status"].widget = HiddenInput()


class CreateIssueForm(Form):
    """Form class for creating tracker issues.

    :var CreateIssueForm.labels: issue labels selection
    :type CreateIssueForm.labels: :class:`django.forms.MultipleChoiceField`
    :var CreateIssueForm.priority: issue priority level
    :type CreateIssueForm.priority: :class:`django.forms.ChoiceField`
    :var CreateIssueForm.issue_title: title of the issue
    :type CreateIssueForm.issue_title: :class:`django.forms.CharField`
    :var CreateIssueForm.issue_body: body content of the issue
    :type CreateIssueForm.issue_body: :class:`django.forms.CharField`
    """

    labels = MultipleChoiceField(
        choices=ISSUE_CREATION_LABEL_CHOICES,
        widget=CheckboxSelectMultiple(),
        label="Select labels",
        required=True,
    )
    priority = ChoiceField(
        choices=ISSUE_PRIORITY_CHOICES,
        widget=RadioSelect(),
        label="Priority level",
        required=True,
        initial="medium priority",
    )
    issue_title = CharField(
        max_length=100,
        label="Title",
        widget=TextInput(
            attrs={
                "class": TEXTINPUT_CLASS,
                "placeholder": "Enter issue title...",
            }
        ),
        required=True,
    )
    issue_body = CharField(
        widget=Textarea(
            attrs={
                "class": "textarea textarea-bordered w-full h-32",
                "placeholder": "Enter issue body text here...",
            }
        ),
        label="Body",
        max_length=2000,
        required=True,
    )

    def clean_labels(self):
        """Ensure at least one label is selected.

        Raise ValidationError if no labels are selected.

        :var data: collection of form data
        :type data: dict
        :return: dict
        """
        data = self.cleaned_data["labels"]
        if len(data) < 1:
            raise ValidationError(MISSING_OPTION_TEXT)

        return data


class IssueLabelsForm(Form):
    """Form for adding labels and priority to tracker issues.

    :var IssueLabelsForm.labels: issue labels selection
    :type IssueLabelsForm.labels: :class:`django.forms.MultipleChoiceField`
    :var IssueLabelsForm.priority: issue priority level
    :type IssueLabelsForm.priority: :class:`django.forms.ChoiceField`
    """

    labels = MultipleChoiceField(
        choices=ISSUE_CREATION_LABEL_CHOICES,
        widget=CheckboxSelectMultiple(),
        required=True,
    )
    priority = ChoiceField(
        choices=ISSUE_PRIORITY_CHOICES,
        widget=RadioSelect(),
        required=True,
        initial="medium priority",
    )

    def clean_labels(self):
        """Ensure at least one label is selected.

        Raise ValidationError if no labels are selected.

        :var data: collection of form data
        :type data: dict
        :return: dict
        """
        data = self.cleaned_data["labels"]
        if len(data) < 1:
            raise ValidationError(MISSING_OPTION_TEXT)

        return data


# # PROFILE
class UpdateUserForm(ModelForm):
    """Model form class for editing user's data.

    :var UpdateUserForm.first_name: user's first name field
    :type UpdateUserForm.first_name: :class:`django.forms.CharField`
    :var UpdateUserForm.last_name: user's last name field
    :type UpdateUserForm.last_name: :class:`django.forms.CharField`
    """

    first_name = CharField(
        required=False,
        widget=TextInput(
            attrs={
                "class": TEXTINPUT_CLASS,
                "placeholder": "Enter your first name",
            }
        ),
    )
    last_name = CharField(
        required=False,
        widget=TextInput(
            attrs={
                "class": TEXTINPUT_CLASS,
                "placeholder": "Enter your last name",
            }
        ),
    )

    class Meta:
        model = User
        fields = ["first_name", "last_name"]


class DeactivateProfileForm(Form):
    """Form class for deactivating current user.

    Only requirement is to correctly populate captcha field.
    User object is taken from the request object.

    :var captcha: field holding value that is going to be compared with captcha
    :type captcha: :class:`CaptchaField`
    """

    captcha = CaptchaField(
        widget=CaptchaTextInput(
            attrs={
                "class": "input input-bordered w-full",
                "placeholder": "Enter the captcha text",
            }
        )
    )

    def deactivate_profile(self, request):
        """Logout and deactivate given request's user in database.

        :param request: http request
        :type request: :class:`HttpRequest`
        """
        request.user.is_active = False
        request.user.save()
        logout(request)


class ProfileForm(ModelForm):
    """Form class for editing user profile's data.

    :var ProfileForm.issue_tracker_api_token: user's personal issue tracker access token
    :type ProfileForm.issue_tracker_api_token: :class:`django.forms.CharField`
    """

    issue_tracker_api_token = CharField(
        required=False,
        widget=TextInput(
            attrs={
                "class": TEXTINPUT_CLASS,
                "placeholder": "Enter your issue tracker token (optional)",
            }
        ),
        help_text="Optional: Issue tracker personal access token for accessing issues",
    )

    class Meta:
        model = Profile
        fields = ["issue_tracker_api_token"]
        exclude = ["user"]


ProfileFormSet = inlineformset_factory(
    User, Profile, form=ProfileForm, extra=1, can_delete=False, max_num=1
)
"""Formset for editing profile's data.
It is instantiated together with :class:`UpdateUserForm` form instance
in the common user/profile editing process.
"""


class TransparencyReportForm(Form):
    """Form class for creating transparency report.

    :var TransparencyReportForm.report_type: report type selection
    :type TransparencyReportForm.report_type: :class:`django.forms.ChoiceField`
    :var TransparencyReportForm.month: month selection
    :type TransparencyReportForm.month: :class:`django.forms.ChoiceField`
    :var TransparencyReportForm.quarter: quarter selection
    :type TransparencyReportForm.quarter: :class:`django.forms.ChoiceField`
    :var TransparencyReportForm.year: year selection
    :type TransparencyReportForm.year: :class:`django.forms.ChoiceField`
    :var TransparencyReportForm.start_date: start date selection
    :type TransparencyReportForm.start_date: :class:`django.forms.CharField`
    :var TransparencyReportForm.end_date: end date selection
    :type TransparencyReportForm.end_date: :class:`django.forms.CharField`
    :var TransparencyReportForm.ordering: ordering selection
    :type TransparencyReportForm.ordering: :class:`django.forms.ChoiceField`
    """

    report_type = ChoiceField(
        choices=[
            ("monthly", "Monthly"),
            ("quarterly", "Quarterly"),
            ("yearly", "Yearly"),
            ("custom", "Custom"),
        ],
        widget=RadioSelect(attrs={"class": "radio"}),
        initial="monthly",
    )
    month = ChoiceField(
        required=False,
        choices=[(i, datetime(2000, i, 1).strftime("%B")) for i in range(1, 13)],
        widget=Select(attrs={"class": "select select-bordered w-full"}),
    )
    quarter = ChoiceField(
        required=False,
        choices=[(1, "Q1"), (2, "Q2"), (3, "Q3"), (4, "Q4")],
        widget=Select(attrs={"class": "select select-bordered w-full"}),
    )
    year = ChoiceField(
        required=False,
        widget=Select(attrs={"class": "select select-bordered w-full"}),
    )
    start_date = CharField(
        required=False,
        widget=TextInput(attrs={"class": TEXTINPUT_CLASS, "type": "date"}),
    )
    end_date = CharField(
        required=False,
        widget=TextInput(attrs={"class": TEXTINPUT_CLASS, "type": "date"}),
    )
    ordering = ChoiceField(
        choices=[("chronological", "Chronological"), ("by_type", "By Type")],
        widget=RadioSelect(attrs={"class": "radio"}),
        initial="chronological",
    )

    def clean(self):
        """Clean the form data by ensuring fields are present based on report type.

        :return: cleaned data
        :rtype: dict
        """
        cleaned_data = super().clean()
        report_type = cleaned_data.get("report_type")
        required_fields = TRANPARENCY_REPORT_REQUIRED_FIELDS[report_type]
        errors = {}
        for field in required_fields:
            if not cleaned_data.get(field):
                errors[field] = f"This field is required for {report_type} reports."

        if (
            report_type == "custom"
            and not errors
            and cleaned_data.get("start_date") > cleaned_data.get("end_date")
        ):
            errors["start_date"] = "Start date cannot be after end date"

        if errors:
            raise ValidationError(errors)

        return cleaned_data

    def __init__(self, *args, **kwargs):
        """Initialize the form and set year choices dynamically.

        :param years: list of years to populate the year field
        :type years: list
        """
        years = kwargs.pop("years", [])
        super().__init__(*args, **kwargs)
        if years:
            self.fields["year"].choices = [(str(year), year) for year in years]
