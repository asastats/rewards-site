"""Module containing website's ORM models."""

from algosdk.encoding import is_valid_address
from django.contrib.auth.models import User
from django.db import models
from django.db.models import BooleanField, Case, F, Min, Sum, Value, When
from django.db.models.functions import Lower
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.functional import cached_property

from utils.constants.core import ADDRESS_LEN, HANDLE_EXCEPTIONS
from utils.helpers import parse_full_handle


class ContributorManager(models.Manager):
    """Rewards Suite contributor's data manager."""

    def from_full_handle(self, full_handle, address=None):
        """Return contributor model instance created from provided `full_handle`.

        :param full_handle: contributor's unique identifier (platform prefix and handle)
        :type full_handle: str
        :param address: public Algorand address
        :type address: str
        :var prefix: unique social platform's prefix
        :type prefix: str
        :var handle: contributor's handle/username
        :type handle: str
        :var platform: social platform's model instance
        :type platform: :class:`SocialPlatform`
        :var contributor: contributor's model instance
        :type contributor: :class:`Contributor`
        :return: :class:`Handle`
        """
        prefix, handle = parse_full_handle(full_handle)
        contributor = self.from_handle(handle)
        if contributor:
            return contributor

        platform = get_object_or_404(SocialPlatform, prefix=prefix)
        try:
            handle = get_object_or_404(Handle, platform=platform, handle=handle)

        except Http404:
            contributor = self.model(name=full_handle, address=address)
            contributor.save()
            handle = Handle.objects.create(
                contributor=contributor, platform=platform, handle=handle
            )

        return handle.contributor

    def from_handle(self, handle):
        """Return handle model instance located by provided `handle`.

        :param handle: contributor's handle
        :type handle: str
        :var handles: handle instances collection
        :type handles: :class:`django.db.models.query.QuerySet`
        :var count: total number of located contributors
        :type count: int
        :return: :class:`Contributor`
        """
        handles = Handle.objects.filter(handle=handle)
        if not handles:
            handles = Handle.objects.filter(handle__trigram_similar=handle)

        count = len({handle.contributor_id for handle in handles})
        if count == 1:
            return handles[0].contributor

        elif count == 0 or handle in HANDLE_EXCEPTIONS:
            return None

        raise ValueError(
            f"Can't locate a single contributor for {handle} {str(handles)}"
        )


class Contributor(models.Model):
    """Rewards Suite contributor's data model."""

    name = models.CharField(max_length=50)
    address = models.CharField(max_length=ADDRESS_LEN, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ContributorManager()

    class Meta:
        """Define ordering and fields that make unique indexes."""

        constraints = [
            models.UniqueConstraint(
                "name",
                Lower("name"),
                name="unique_contributor_name",
            ),
            models.UniqueConstraint(
                "address",
                name="unique_contributor_address",
            ),
        ]
        ordering = [Lower("name")]

    def __str__(self):
        """Return contributor's instance string representation.

        :return: str
        """
        return parse_full_handle(self.name)[1]

    def get_absolute_url(self):
        """Returns the URL to access a detail record for this contributor."""
        return reverse("contributor_detail", args=[str(self.id)])

    @cached_property
    def sorted_handles(self):
        """Return handles sorted case-insensitively, using prefetched data if available.

        :return: sorted list of handles
        :rtype: list
        """
        # Check if we have prefetched handles
        if hasattr(self, "prefetched_handles"):
            return sorted(self.prefetched_handles, key=lambda h: h.handle.lower())

        # Fallback to database query if not prefetched
        return list(self.handle_set.order_by(Lower("handle")))

    @property
    def info(self):
        """Return contributor information including handles.

        :return: contributor information string
        :rtype: str
        """
        # Use sorted_handles which will use prefetched data when available
        handles = self.sorted_handles
        if len(handles) > 1:
            formatted_handles = ", ".join(
                [f"{h.platform.prefix}{h.handle}" for h in handles]
            )
            return f"{self.name} ({formatted_handles})"

        return self.name

    @cached_property
    def optimized_contribution_data(self):
        """Fetch all contribution data in one query and organize it.

        This method performs a single database query to fetch all contributions
        with their related objects (cycle, reward, reward type, and issue),
        then categorizes them in memory to avoid multiple database hits.

        :return: dict containing organized contribution data
        :rtype: dict
        """
        # Single query to get everything with related data
        if hasattr(self, "prefetched_contributions"):
            all_contributions = self.prefetched_contributions
        else:
            # Fallback to database query
            all_contributions = list(
                self.contribution_set.select_related(
                    "cycle", "reward", "reward__type", "issue"
                ).order_by("cycle__start", "created_at")
            )

        # Categorize contributions in memory
        open_contribs = []
        addressed_contribs = []
        claimable_contribs = []
        archived_contribs = []
        uncategorized_contribs = []
        invalidated_contribs = []

        for contrib in all_contributions:
            if contrib.issue is None:
                uncategorized_contribs.append(contrib)
            elif contrib.issue.status == IssueStatus.ADDRESSED:
                addressed_contribs.append(contrib)
            elif contrib.issue.status == IssueStatus.CLAIMABLE:
                claimable_contribs.append(contrib)
            elif contrib.issue.status == IssueStatus.ARCHIVED:
                archived_contribs.append(contrib)
            elif contrib.issue.status == IssueStatus.WONTFIX:
                invalidated_contribs.append(contrib)
            else:
                open_contribs.append(contrib)

        # Calculate totals for each category
        open_total = sum(c.reward.amount for c in open_contribs)
        addressed_total = sum(c.reward.amount for c in addressed_contribs)
        claimable_total = sum(c.reward.amount for c in claimable_contribs)
        archived_total = sum(c.reward.amount for c in archived_contribs)
        uncategorized_total = sum(c.reward.amount for c in uncategorized_contribs)
        total_rewards = (
            open_total + addressed_total + archived_total + uncategorized_total
        )

        return {
            "open_contributions": open_contribs,
            "addressed_contributions": addressed_contribs,
            "claimable_contributions": claimable_contribs,
            "archived_contributions": archived_contribs,
            "uncategorized_contributions": uncategorized_contribs,
            "invalidated_contributions": invalidated_contribs,
            "contribution_groups": [
                {"name": "Open", "query": open_contribs, "total": open_total},
                {
                    "name": "Addressed",
                    "query": addressed_contribs,
                    "total": addressed_total,
                },
                {
                    "name": "Claimable",
                    "query": claimable_contribs,
                    "total": claimable_total,
                },
                {
                    "name": "Archived",
                    "query": archived_contribs,
                    "total": archived_total,
                },
                {
                    "name": "Uncategorized",
                    "query": uncategorized_contribs,
                    "total": uncategorized_total,
                },
                {"name": "Invalidated", "query": invalidated_contribs, "total": 0},
            ],
            "total_rewards": total_rewards,
        }

    @cached_property
    def open_contributions(self):
        """Return all contributions with issue status CREATED.

        :return: list of Contribution objects
        :rtype: list
        """
        return self.optimized_contribution_data["open_contributions"]

    @cached_property
    def addressed_contributions(self):
        """Return all contributions with issue status ADDRESSED.

        :return: list of Contribution objects
        :rtype: list
        """
        return self.optimized_contribution_data["addressed_contributions"]

    @cached_property
    def archived_contributions(self):
        """Return all contributions with issue status ARCHIVED.

        :return: list of Contribution objects
        :rtype: list
        """
        return self.optimized_contribution_data["archived_contributions"]

    @cached_property
    def claimable_contributions(self):
        """Return all contributions with issue status CLAIMABLE.

        :return: list of Contribution objects
        :rtype: list
        """
        return self.optimized_contribution_data["claimable_contributions"]

    @cached_property
    def uncategorized_contributions(self):
        """Return all contributions without any issue.

        :return: list of Contribution objects
        :rtype: list
        """
        return self.optimized_contribution_data["uncategorized_contributions"]

    @cached_property
    def invalidated_contributions(self):
        """Return all contributions with issue status WONTFIX.

        :return: list of Contribution objects
        :rtype: list
        """
        return self.optimized_contribution_data["invalidated_contributions"]

    @cached_property
    def contribution_groups(self):
        """Return collection of all contribution groups with totals for this instance.

        :return: list of contribution group dictionaries
        :rtype: list
        """
        return self.optimized_contribution_data["contribution_groups"]

    @cached_property
    def total_rewards(self):
        """Return sum of all reward amounts for this contributor (cached).
        Excludes contributions with WONTFIX issue status.

        :return: total reward amount
        :rtype: int
        """
        return self.optimized_contribution_data["total_rewards"]


class Profile(models.Model):
    """App's connection to main Django user model and optionally to Contributor."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True)
    contributor = models.OneToOneField(
        Contributor, on_delete=models.SET_NULL, null=True, blank=True
    )
    issue_tracker_api_token = models.CharField(max_length=100, blank=True)

    def __str__(self):
        """Return string representation of the profile instance

        :return: str
        """
        return self.name

    def get_absolute_url(self):
        """Return url of the profile home page.

        :return: url
        """
        return reverse("profile")

    def log_action(self, action, details=""):
        """Create superuser log action record for this profile from provided arguments.

        :param action: action identifier
        :type action: str
        :param details: detailed data of the action
        :type details: str
        :return: :class:`SuperuserLog`
        """
        if self.user.is_superuser:
            return SuperuserLog.objects.create(
                profile=self, action=action, details=details
            )

    def profile(self):
        """Return self instance for generic templating purposes.

        It is accessed by 'object.profile' in some templates.

        :return: :class:`Profile`
        """
        return self

    @property
    def name(self):
        """Return user/profile name made depending on data fields availability.

        :return: str
        """
        return (
            "{} {}".format(self.user.first_name, self.user.last_name).strip()
            if (self.user.first_name or self.user.last_name)
            else self.user.username or self.user.email.split("@")[0]
        )


class SuperuserLog(models.Model):
    """Rewards Suite website superusers' action logs model."""

    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    action = models.CharField(max_length=50)
    details = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Define ordering of the log entries."""

        ordering = ["-created_at"]

    def __str__(self):
        """Return this ledger row instance's string representation.

        :return: str
        """
        return f"{self.profile.name} - {self.action} - {self.created_at}"


class SocialPlatform(models.Model):
    """Rewards Suite social media platform's data model."""

    name = models.CharField(max_length=50)
    prefix = models.CharField(max_length=2, blank=True)

    class Meta:
        """Define ordering and fields that make unique indexes."""

        constraints = [
            models.UniqueConstraint(
                "name",
                Lower("name"),
                name="unique_socialplatform_name",
            ),
            models.UniqueConstraint(
                "prefix",
                name="unique_socialplatform_prefix",
            ),
        ]
        ordering = [Lower("name")]

    def __str__(self):
        """Return contributor's instance string representation.

        :return: str
        """
        return self.name


class HandleManager(models.Manager):
    """Rewards Suite social media handle data manager."""

    def from_address_and_full_handle(self, address, full_handle):
        """Return handle model instance derived from provided `address` and `full_handle`.

        :param address: public Algorand address
        :type address: str
        :param full_handle: contributor's unique identifier (platform prefix and handle)
        :type full_handle: str
        :var prefix: unique social platform's prefix
        :type prefix: str
        :var handle: contributor's handle/username
        :type handle: str
        :var contributor: contributor's model instance
        :type contributor: :class:`Contributor`
        :var platform: social platform's model instance
        :type platform: :class:`SocialPlatform`
        :return: :class:`Handle`
        """
        prefix, handle = parse_full_handle(full_handle)
        try:
            contributor = get_object_or_404(Contributor, address=address)
        except Http404:
            contributor = Contributor.objects.from_full_handle(
                full_handle, address=address
            )
            contributor.save()

        platform = get_object_or_404(SocialPlatform, prefix=prefix)
        return self.model(contributor=contributor, platform=platform, handle=handle)


class Handle(models.Model):
    """Rewards Suite social media handle data model."""

    contributor = models.ForeignKey(Contributor, default=None, on_delete=models.CASCADE)
    platform = models.ForeignKey(SocialPlatform, default=None, on_delete=models.CASCADE)
    handle = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = HandleManager()

    class Meta:
        """Define ordering and fields that make unique indexes."""

        constraints = [
            # Unique handle per platform
            models.UniqueConstraint(
                fields=["platform", "handle"], name="unique_social_handle"
            )
        ]
        ordering = [Lower("handle")]

    def __str__(self):
        """Return contributor's instance string representation.

        :return: str
        """
        return self.handle + "@" + str(self.platform)


class Cycle(models.Model):
    """Rewards Suite periodic rewards cycle data model.."""

    start = models.DateField()
    end = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Define model's ordering."""

        ordering = ["start"]

    def __str__(self):
        """Return cycle's instance string representation.

        :return: str
        """
        start = self.start.strftime("%d-%m-%y")
        return start + " - " + self.end.strftime("%d-%m-%y") if self.end else start

    def get_absolute_url(self):
        """Returns the URL to access a detail record for this cycle."""
        return reverse("cycle_detail", args=[str(self.id)])

    def info(self):
        """Return extended string representation of the cycle instance

        :return: str
        """
        start = self.start.strftime("%A, %B %d, %Y")
        return (
            "From " + start + " to " + self.end.strftime("%A, %B %d, %Y")
            if self.end
            else "Started on " + start
        )

    @property
    def contributor_rewards(self):
        """Return collection of all contributors and related rewards for cycle (cached).

        :var result: collection of contributors and related total reward amounts
        :type result: :class:`django.db.models.query.QuerySet`
        :return: dict
        """

        # First, calculate the total amount for each contributor considering percentages
        result = (
            self.contribution_set.select_related("contributor")
            .values("contributor__name")
            .annotate(
                total_amount=Sum(
                    F("reward__amount") * F("percentage") / 100.0,
                    output_field=models.DecimalField(),
                ),
                # Use Min to get False if any contribution is not confirmed
                all_confirmed=Min(
                    Case(
                        When(confirmed=True, then=Value(1)),
                        When(confirmed=False, then=Value(0)),
                        output_field=BooleanField(),
                    )
                ),
            )
            .order_by("contributor__name")
        )
        return {
            item["contributor__name"]: (
                int(item.get("total_amount") or 0),
                bool(item["all_confirmed"]),
            )
            for item in result
        }

    @property
    def total_rewards(self):
        """Return sum of all reward amounts for this contributor (cached).
        Excludes contributions with WONTFIX issue status.

        :return: int
        """
        result = (
            self.contribution_set.exclude(issue__status=IssueStatus.WONTFIX)
            .aggregate(total_rewards=Sum("reward__amount"))
            .get("total_rewards")
        )
        return result or 0


class RewardType(models.Model):
    """Rewards Suite reward type data model."""

    label = models.CharField(max_length=5, blank=True)
    name = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Define ordering and fields that make unique indexes."""

        constraints = [
            models.UniqueConstraint(
                "label",
                Lower("label"),
                name="unique_rewardtype_label",
            ),
            models.UniqueConstraint(
                "name",
                Lower("name"),
                name="unique_rewardtype_name",
            ),
        ]
        ordering = ["name"]

    def __str__(self):
        """Return reward type's instance string representation.

        :return: str
        """
        return "[" + self.label + "] " + self.name


class Reward(models.Model):
    """Rewards Suite reward data model."""

    type = models.ForeignKey(RewardType, default=None, on_delete=models.CASCADE)
    level = models.IntegerField(default=1)
    amount = models.IntegerField(default=10000)
    description = models.CharField(max_length=255, blank=True)
    general_description = models.TextField(blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Define ordering and fields that make unique indexes."""

        constraints = [
            models.UniqueConstraint(
                fields=["type", "level", "amount"],
                name="unique_reward_type_level_amount",
            ),
        ]
        ordering = ["type", "level"]

    def __str__(self):
        """Return reward's instance string representation.

        :return: str
        """
        return str(self.type) + " " + str(self.level) + ": " + f"{self.amount:,}"


class IssueManager(models.Manager):
    """Rewards Suite issues data manager."""

    def confirm_contribution_with_issue(self, issue_number, contribution):
        """Create issue from provided number and assign it to confirmed `contribution`.

        :param issue_number: unique GitHub issue number
        :type issue_number: int
        :param contribution: contribution's model instance
        :type contribution: :class:`Contribution`
        :var issue: issue's model instance
        :type issue: :class:`Issue`
        :return: :class:`Issue`
        """
        issue = Issue.objects.create(number=issue_number)
        contribution.issue = issue
        contribution.confirmed = True
        contribution.save()
        return issue


class IssueStatus(models.TextChoices):
    """Rewards Suite GitHub channel issue status choices."""

    CREATED = "created", "Created"
    WONTFIX = "wontfix", "Wontfix"
    ADDRESSED = "addressed", "Addressed"
    CLAIMABLE = "claimable", "Claimable"
    ARCHIVED = "archived", "Archived"


class Issue(models.Model):
    """Rewards Suite GitHub issue model."""

    number = models.IntegerField()
    status = models.CharField(
        max_length=20, choices=IssueStatus.choices, default=IssueStatus.CREATED
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = IssueManager()

    class Meta:
        """Define ordering and fields that make unique indexes."""

        constraints = [models.UniqueConstraint("number", name="unique_issue_number")]
        ordering = ["-number"]

    def __str__(self):
        """Return reward's instance string representation.

        :return: str
        """
        return str(self.number) + " [" + self.status + "]"

    def get_absolute_url(self):
        """Returns the URL to access a detail record for this issue."""
        return reverse("issue_detail", args=[str(self.id)])

    @cached_property
    def sorted_contributions(self):
        """Return contributions sorted by date, using prefetched data if available.

        :return: sorted list of contributions
        :rtype: list
        """
        # Check if we have prefetched contributions
        if hasattr(self, "prefetched_contributions"):
            return sorted(self.prefetched_contributions, key=lambda c: c.created_at)

        # Fallback to database query if not prefetched
        return list(self.contribution_set.order_by("created_at"))

    @property
    def info(self):
        """Return issue information including contributions.

        :return: issue information string
        :rtype: str
        """
        # Use sorted_contributions which will use prefetched data when available
        contributions = self.sorted_contributions

        if len(contributions) > 1:
            formatted_contributions = ", ".join([f"{str(c)}" for c in contributions])
            return f"{str(self.number)} - {formatted_contributions}"

        return (
            f"{str(self.number)} - {str(contributions[0])}"
            if contributions
            else str(self.number)
        )

    objects = IssueManager()


class ContributionManager(models.Manager):
    """Custom manager for the `Contribution` model."""

    def addresses_and_amounts_from_contributions(self, contributions):
        """Create collection of addresses and related amounts from `contributions`.

        :param contributions: all contributions for the user defined by provided `address`
        :type contributions: :class:`django.db.models.query.QuerySet`
        :var amounts: collection of addresses and related contribution amounts
        :type amounts: dict
        :var contrib: collection of addresses and related contribution amounts
        :type contrib: :class:`Contribution`
        :return: two-tuple
        """
        amounts = {}
        for contrib in contributions:
            if is_valid_address(contrib.contributor.address) and contrib.reward.amount:
                amounts[contrib.contributor.address] = amounts.get(
                    contrib.contributor.address, 0
                ) + int(contrib.reward.amount * contrib.percentage)

        return list(amounts.keys()), list(amounts.values())

    def addressed_contributions_addresses_and_amounts(self):
        """Create collection of addressed contributions to be added to smart contract.

        :var contributions: all contributions for the user defined by provided `address`
        :type contributions: :class:`django.db.models.query.QuerySet`
        :return: two-tuple
        """
        contributions = self.filter(issue__status=IssueStatus.ADDRESSED).select_related(
            "contributor", "reward", "issue"
        )
        return self.addresses_and_amounts_from_contributions(contributions)

    def update_issue_statuses_for_addresses(self, addresses, contributions):
        """Create collection of addresses and related amounts from `contributions`.

        :param addresses: colection of addresses to update issue statuses for
        :type addresses: list
        :param contributions: contributions to locate issues from by addresses
        :type contributions: :class:`django.db.models.query.QuerySet`
        :var contrib: colection of addresses and related contribution ammounts
        :type contrib: :class:`Contribution`
        """
        for contrib in contributions:
            if (
                contrib.contributor.address in addresses
                and contrib.reward.amount
                and contrib.issue.status == IssueStatus.ADDRESSED
            ):
                contrib.issue.status = IssueStatus.CLAIMABLE
                contrib.issue.save()

    def user_has_claimed(self, address):
        """Update status of related issues to ARCHIVED for all contributions.

        :param address: public Algorand address
        :type address: str
        :var contributions: all contributions for the user defined by provided `address`
        :type contributions: :class:`django.db.models.query.QuerySet`
        :var issue_ids: collection of contributor's contribution IDs
        :type issue_ids: :class:`django.db.models.query.QuerySet`
        """
        contributions = self.filter(contributor__address=address)
        issue_ids = (
            contributions.exclude(issue__isnull=True)
            .values_list("issue_id", flat=True)
            .distinct()
        )
        Issue.objects.filter(id__in=issue_ids).update(status=IssueStatus.ARCHIVED)


class Contribution(models.Model):
    """Community member contributions data model."""

    contributor = models.ForeignKey(Contributor, default=None, on_delete=models.CASCADE)
    cycle = models.ForeignKey(Cycle, default=None, on_delete=models.CASCADE)
    platform = models.ForeignKey(SocialPlatform, default=None, on_delete=models.CASCADE)
    reward = models.ForeignKey(Reward, default=None, on_delete=models.CASCADE)
    issue = models.ForeignKey(Issue, null=True, blank=True, on_delete=models.CASCADE)
    percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=1, null=True
    )
    url = models.CharField(max_length=255, blank=True, null=True)
    comment = models.CharField(max_length=255, blank=True, null=True)
    confirmed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ContributionManager()

    class Meta:
        """Define model's ordering."""

        ordering = ["cycle", "created_at"]

    def __str__(self):
        """Return contribution's instance string representation.

        :return: str
        """
        return (
            self.contributor.name
            + "/"
            + str(self.platform)
            + "/"
            + self.created_at.strftime("%d-%m-%y")
        )

    def get_absolute_url(self):
        """Returns the URL to access a detail record for this contribution."""
        return reverse("contribution_detail", args=[str(self.id)])

    def info(self):
        """Return basic information for this contribution.

        :var main_text: starting text
        :type main_text: str
        :return: str
        """
        main_text = (
            "["
            + self.created_at.strftime("%d %b %H:%M")
            + "] "
            + self.reward.type.name
            + " by "
            + str(self.contributor)
        )
        if self.comment:
            main_text += " // " + self.comment

        return main_text
