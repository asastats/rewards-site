"""Module containing main functions for issues management."""

import logging
from datetime import datetime

from django.conf import settings

from core.models import Contributor
from issues.providers import BitbucketProvider, GithubProvider, GitlabProvider
from utils.bot import message_from_url

ISSUE_TRACKER_PROVIDERS_REGISTRY = {
    "github": GithubProvider,
    "gitlab": GitlabProvider,
    "bitbucket": BitbucketProvider,
}

logger = logging.getLogger(__name__)


class IssueProvider:
    """Main provider class that delegates to the configured provider.

    :var IssueProvider.name: name of the provider to use
    :type IssueProvider.name: str
    :var IssueProvider.user: Django user instance
    :type IssueProvider.user: class:`django.contrib.auth.models.User`
    :var IssueProvider._provider_instance: instance of the issue provider
    :type IssueProvider._provider_instance: :class:`BaseIssueProvider`
    """

    name = None
    user = None
    _provider_instance = None

    def __init__(self, user, **kwargs):
        """Initialize issue provider with configured provider.

        :param user: Django user instance
        :type user: class:`django.contrib.auth.models.User`
        """
        self.name = settings.ISSUE_TRACKER_PROVIDER
        self.user = user
        self._provider_instance = self._get_provider_instance(**kwargs)

    def _get_provider_instance(self, **kwargs):
        """Get the provider instance from registry, fallback to GitHub.

        :var provider_class: provider class from registry
        :type provider_class: class
        :return: instance of the issue provider
        :rtype: :class:`BaseIssueProvider`
        """
        provider_class = ISSUE_TRACKER_PROVIDERS_REGISTRY.get(self.name)
        return provider_class(
            self.user, issue_tracker_api_token=kwargs.get("issue_tracker_api_token")
        )

    def __getattr__(self, name):
        """Delegate all method calls to the provider instance.

        :param name: method name to delegate
        :type name: str
        :return: method from provider instance
        """
        return getattr(self._provider_instance, name)


# # PREPARE ISSUE
def _contributor_link(handle):
    """Create link to contributor defined by provided Discord `handle`.

    :param handle: Discord handle/username
    :type handle: str
    :param contributor: contributor's model instance
    :type contributor: :class:`core.models.Contributor`
    :return: str
    """
    try:
        contributor = Contributor.objects.from_handle(handle)

    except ValueError:
        contributor = None

    if contributor is None:
        return handle

    return f"[{handle}]({contributor.get_absolute_url()})"


def _prepare_issue_body_from_contribution(contribution, profile):
    """Prepare the body content for a GitHub issue from provided arguments.

    :param contribution: contribution instance to extract data from
    :type contribution: :class:`core.models.Contribution`
    :param profile: superuser's profile instance
    :type profile: :class:`core.models.Profile`
    :var issue_body: default issue body template
    :type issue_body: str
    :var message: parsed message data from contribution URL
    :type message: dict
    :var contributor: link to contributor's page on Rewards Suite website
    :type contributor: str
    :return: str
    """
    issue_body = "** Please provide the necessary information **"
    if not contribution.url:
        return issue_body

    message = message_from_url(contribution.url)
    if message.get("success"):
        timestamp = datetime.strptime(
            message.get("timestamp"), "%Y-%m-%dT%H:%M:%S.%f%z"
        ).strftime("%d %b %H:%M")
        contributor = _contributor_link(message.get("author"))
        issue_body = (
            f"By {contributor} on {timestamp} in [Discord]"
            f"({contribution.url}): // su: {str(profile)}\n"
        )
        for line in message.get("content").split("\n"):
            issue_body += f"> {line}\n"

    return issue_body


def _prepare_issue_labels_from_contribution(contribution):
    """Prepare labels for a GitHub issue based on contribution reward type.

    :param contribution: contribution instance to extract data from
    :type contribution: :class:`core.models.Contribution`
    :var labels: collection of labels to apply to the issue
    :type labels: list
    :return: list
    """
    labels = []
    if "Bug" in contribution.reward.type.name:
        labels.append("bug")

    elif "Feature" in contribution.reward.type.name:
        labels.append("feature")

    elif "Task" in contribution.reward.type.name:
        labels.append("task")

    elif "Twitter" in contribution.reward.type.name:
        labels.append("task")

    elif "Research" in contribution.reward.type.name:
        labels.append("research")

    return labels


def _prepare_issue_priority_from_contribution(contribution):
    """Prepare priority level for a GitHub issue based on contribution reward type.

    :param contribution: contribution instance to extract data from
    :type contribution: :class:`core.models.Contribution`
    :return: str
    """
    if "Bug" in contribution.reward.type.name:
        return "high priority"

    return "medium priority"


def _prepare_issue_title_from_contribution(contribution):
    """Prepare title for a GitHub issue from contribution data.

    :param contribution: contribution instance to extract data from
    :type contribution: :class:`core.models.Contribution`
    :var issue_title: formatted issue title with reward type and level
    :type issue_title: str
    :return: str
    """
    issue_title = f"[{contribution.reward.type.label}{contribution.reward.level}] "
    if contribution.comment:
        issue_title += contribution.comment

    return issue_title


def issue_data_for_contribution(contribution, profile):
    """Prepare complete issue data dictionary from a contribution.

    :param contribution: contribution instance to extract data from
    :type contribution: :class:`core.models.Contribution`
    :param profile: superuser's profile instance
    :type profile: :class:`core.models.Profile`
    :return: dict
    """
    return {
        "issue_title": _prepare_issue_title_from_contribution(contribution),
        "issue_body": _prepare_issue_body_from_contribution(contribution, profile),
        "labels": _prepare_issue_labels_from_contribution(contribution),
        "priority": _prepare_issue_priority_from_contribution(contribution),
    }
