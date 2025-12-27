"""Module containing helper functions for GitHub issues mapping."""

import pickle
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any, List

from django.conf import settings
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404

from core.models import (
    Contribution,
    Contributor,
    Cycle,
    Handle,
    Issue,
    IssueStatus,
    Reward,
    RewardType,
    SocialPlatform,
)
from issues.main import IssueProvider
from utils.constants.core import (
    CONTRIBUTOR_TEXT_EXCEPTIONS,
    EXCLUDED_CONTRIBUTORS,
    GITHUB_ISSUES_START_DATE,
    ISSUE_CREATION_LABEL_CHOICES,
    REWARDS_COLLECTION,
)
from utils.helpers import read_pickle

URL_EXCEPTIONS = ["discord.com/invite"]
REWARD_LABELS = [
    entry[0].split("]")[0].strip("[]")
    for entry in REWARDS_COLLECTION
    if entry and isinstance(entry[0], str)
]
REWARD_PATTERN = re.compile(rf"^\[({'|'.join(REWARD_LABELS)})(1|2|3)\]")


## HELPERS
@dataclass
class CustomIssue:
    """A simple data class for issues and comments."""

    issue: Any
    comments: List[Any]


def _build_reward_mapping():
    """Build mapping from issue detection labels to active rewards.

    :return: mapping from label type to reward object
    :rtype: dict of str: :class:`core.models.Reward`
    """
    reward_mapping = {}

    # Regex pattern to extract code between brackets: [CODE] Description
    bracket_pattern = r"\[([^\]]+)\]"

    for label_type, label_name in ISSUE_CREATION_LABEL_CHOICES[:4]:
        # Find first occurrence in REWARDS_COLLECTION where
        # label_name appears in the first element
        reward_config = next(
            config
            for config in REWARDS_COLLECTION
            if label_name.lower() in config[0].lower()
        )
        # Extract label code using regex (e.g., "AT" from "[AT] Admin Task")
        match = re.search(bracket_pattern, reward_config[0])
        if match:
            label_code = match.group(1)  # Get the content between brackets
            amount = reward_config[1]  # Get the amount

            # Find active reward with matching type label and amount
            try:
                reward = Reward.objects.get(
                    type__label=label_code, amount=amount, active=True
                )
                reward_mapping[label_type] = reward

            except Reward.DoesNotExist:
                print(f"No active reward found for {label_code} with amount {amount}")
                continue

            except Reward.MultipleObjectsReturned:
                reward = Reward.objects.filter(
                    type__label=label_code, amount=amount, active=True
                ).first()
                reward_mapping[label_type] = reward
                print(f"Multiple rewards found for {label_code}, using first one")

        else:
            print(f"Could not extract label code from: {reward_config[0]}")

    return reward_mapping


def _extract_url_text(body, platform_id):
    """Extract URL from issue body in markdown format.

    :param body: GitHub issue body text
    :type body: str
    :param platform_id: platform ID to help identify relevant URLs
    :type platform_id: int
    :return: extracted URL if found, None otherwise
    :rtype: str or None
    """
    # Get platform name for URL matching
    try:
        platform = SocialPlatform.objects.get(id=platform_id)
        platform_name = platform.name.lower()
    except SocialPlatform.DoesNotExist:
        return None

    # Look for markdown links [text](url)
    url_pattern = r"\[[^\]]*\]\(([^)]+)\)"
    matches = re.findall(url_pattern, body)

    for url in matches:
        if (
            url.startswith("http")
            and platform_name in url.lower()
            and not any(text in url.lower() for text in URL_EXCEPTIONS)
        ):
            return url

    return None


def _fetch_and_categorize_issues(issue_tracker_api_token, refetch=False):
    """Fetch all GitHub issues and return them categorized.

    :param issue_tracker_api_token: GitHub API token
    :type issue_tracker_api_token: str
    :param refetch: should recorded issues be refetched or not
    :type refetch: Boolean
    :var github_issues: collection of categorized GitHub issue instances
    :type github_issues: dict
    :var counter: currently processed issue ordinal
    :type counter: int
    :var issue: currently processed issue
    :type issue: :class:`github.Issue.Issue`
    :return: collection of categorized GitHub issue instances
    :rtype: dict
    """
    github_issues = _load_saved_issues() if not refetch else defaultdict(list)

    if not issue_tracker_api_token:
        return github_issues

    issue = None
    for counter, issue in enumerate(
        IssueProvider(
            None, issue_tracker_api_token=issue_tracker_api_token
        ).fetch_issues(
            state="all",
            since=github_issues.get("timestamp", GITHUB_ISSUES_START_DATE),
        )
    ):
        if issue.pull_request:
            continue

        comments = (
            [comment.body for comment in issue.get_comments()] if issue.comments else []
        )
        custom_issue = CustomIssue(issue, comments)

        github_issues[issue.state].append(custom_issue)
        if divmod(counter, 10)[1] == 0:
            print("Issue number: ", issue.number)
            _save_issues(github_issues, issue.updated_at)

    # # Remove duplicates
    # github_issues["closed"] = sorted(
    #     list(set(github_issues["closed"])), key=lambda i: getattr(i, "number")
    # )
    # github_issues["open"] = sorted(
    #     list(set(github_issues["open"])), key=lambda i: getattr(i, "number")
    # )
    # _save_issues(github_issues, github_issues["timestamp"])

    if issue:
        _save_issues(github_issues, issue.updated_at + timedelta(seconds=10))

    print(
        "Number of issues: "
        f"{len(github_issues.get('closed', [])) + len(github_issues.get('open', []))}"
    )
    return github_issues


def _identify_contributor_from_text(text, contributors):
    """Identify contributor from issue body by matching contributor info and handles.

    :param body: GitHub issue body and comments text
    :type body: str
    :param contributors: mapping from contributor info to ID
    :type contributors: dict of str: int
    :return: contributor ID if found, None otherwise
    :rtype: int or None
    """
    # Handle None or empty text
    if not text:
        return None

    # Convert body to lowercase for case-insensitive matching
    text_lower = text.lower()

    for contributor_info, contributor_id in contributors.items():
        # If contributor info doesn't have parentheses, search for the whole info
        if "(" not in contributor_info:
            # For simple format, require exact word match to avoid false positives
            contrib_lower = contributor_info.lower()
            if (
                contrib_lower not in CONTRIBUTOR_TEXT_EXCEPTIONS
                and contrib_lower in text_lower
            ):
                return contributor_id

        else:
            # If contributor info has parentheses, extract and search for handles
            # Format: "Name (handle1, handle2, ...)"
            name_part = contributor_info.split("(")[0].strip()
            handles_part = contributor_info[contributor_info.index("(") + 1 : -1]

            # Split handles by comma and clean up
            handles = [handle.strip() for handle in handles_part.split(",")]

            # Search for the name part in body - require exact word match
            if name_part.lower() in text_lower:
                return contributor_id

            # Search for individual handles in body - allow partial matches
            for handle in handles:
                if handle.lower() in text_lower:
                    return contributor_id

    return None


def _identify_contributor_from_user(user, contributors, strict=True):
    """Identify contributor from issue body by matching contributor info and handles.

    :param user: GitHub username
    :type user: str
    :param contributors: mapping from contributor info to ID
    :type contributors: dict of str: int
    :return: contributor ID if found, None otherwise
    :rtype: int or None
    """
    # Handle None or empty user
    if not user:
        return None

    # Convert to lowercase for case-insensitive matching
    user_lower = user.lower()
    handle = "g@" + user_lower if strict else user_lower

    for contributor_info, contributor_id in contributors.items():
        if handle in contributor_info.lower():
            return contributor_id

    return None


def _identify_platform_from_text(text, platforms):
    """Identify platform from issue body by matching platform names.

    :param body: GitHub issue body and comments text
    :type body: str
    :param platforms: mapping from platform name to ID
    :type platforms: dict of str: int
    :return: platform ID if found, None otherwise
    :rtype: int or None
    """
    for platform_name, platform_id in platforms.items():
        if platform_name.lower() in text.lower():
            return platform_id

    return None


def _identify_reward_from_labels(labels, reward_mapping):
    """Identify reward based on GitHub issue labels.

    :param labels: list of GitHub issue label objects
    :type labels: list of :class:`github.Label.Label`
    :param reward_mapping: mapping from label types to rewards
    :type reward_mapping: dict of str: :class:`core.models.Reward`
    :return: reward object if found, None otherwise
    :rtype: :class:`core.models.Reward` or None
    """
    for label in labels:
        label_name = label.name.lower()

        # Check for exact matches first
        for label_type in reward_mapping.keys():
            if label_type.lower() == label_name:
                return reward_mapping[label_type]

        # Check for partial matches
        for label_type in reward_mapping.keys():
            if label_type.lower() in label_name:
                return reward_mapping[label_type]

    return None


def _identify_reward_from_issue_title(title, active=True):
    """Checks if the provided title text starts with a valid reward pattern like:

    [F(1)], [B(2)], [ER(3)], etc.

    :param title: GitHub issue's title
    :type title: str
    :param active: is reward active or not
    :type active: Boolean
    return: :class:`core.models.Reward`
    """
    if not title:
        return None

    match = REWARD_PATTERN.match(title.strip())
    if not match:
        return None

    label, level = match.groups()
    level = int(level)

    reward_type = get_object_or_404(RewardType, label=label)
    return Reward.objects.filter(type=reward_type, level=level, active=active).first()


def _is_url_github_issue(url):
    """Check if a URL matches the pattern of a issue in the configured repository.

    :param url: URL to check
    :type url: str
    :return: tracker issue number if URL matches pattern, False otherwise
    :rtype: int or bool
    :var pattern: regex pattern for tracker issue URL matching
    :type pattern: str
    :var match: regex match object
    :type match: :class:`re.Match` or None
    """
    pattern = (
        rf"^.*github\.com/{settings.ISSUE_TRACKER_OWNER}/"
        rf"{settings.ISSUE_TRACKER_NAME}/issues/(\d+).*"
    )
    match = re.match(pattern, url)
    if not match:
        return False

    return int(match.groups()[0])


## I/O
def _load_saved_issues():
    """Load saved GitHub issues from pickle file.

    :return: defaultdict containing GitHub issues data
    """
    github_issues = defaultdict(list)
    path = Path(__file__).resolve().parent.parent / "fixtures" / "github_issues.pkl"
    data = read_pickle(path)

    for key in data:
        github_issues[key] = data[key]

    return github_issues


def _save_issues(github_issues, timestamp):
    """Save GitHub issues to pickle file with timestamp.

    :param github_issues: dictionary containing GitHub issues data
    :param timestamp: timestamp to include in the saved data
    """
    path = Path(__file__).resolve().parent.parent / "fixtures" / "github_issues.pkl"
    github_issues["timestamp"] = timestamp

    # Create directory if it doesn't exist
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "wb") as pickle_file:
        pickle.dump(github_issues, pickle_file)


## MAPPING
def _create_contributor_from_text(text, contributors):
    """Create a new contributor from text by extracting handle from common patterns.

    :param text: GitHub issue body and comments text
    :type text: str
    :param contributors: mapping from contributor info to ID
    :type contributors: dict of str: int
    :return: tuple of (contributor_id, updated_contributors_dict) or (None, contributors) if no handle found
    :rtype: tuple (int or None, dict)
    """
    if not text:
        return None, contributors

    # Single pattern: "By " followed by any string, then "in" or "on" followed by platform with or without brackets
    pattern = r"By ([\w\s\-_.]+) (?:in|on) \[?(Discord|Twitter|Reddit)\]?"

    handle = None
    platform_name = None

    matches = re.findall(pattern, text, re.IGNORECASE)
    if matches:
        handle_candidate, platform_candidate = matches[0]
        handle = handle_candidate.strip()
        platform_name = platform_candidate

    if not handle or not platform_name:
        return None, contributors

    platform = SocialPlatform.objects.get(name=platform_name)

    # Check if contributor with this name already exists
    existing_contributor = Contributor.objects.from_handle(handle)
    if existing_contributor:
        # Contributor exists, create handle if it doesn't exist
        Handle.objects.get_or_create(
            contributor=existing_contributor,
            platform=platform,
            defaults={"handle": handle},
        )
        # Update contributors mapping
        contributors[existing_contributor.info] = existing_contributor.id
        return existing_contributor.id, contributors

    else:
        # Create new contributor
        new_contributor = Contributor.objects.create(name=handle)

        Handle.objects.create(
            contributor=new_contributor, platform=platform, handle=handle
        )

        # Update contributors mapping
        contributors[new_contributor.info] = new_contributor.id

        return new_contributor.id, contributors


def _create_issues_bulk(issue_assignments):
    """Bulk create issues and assign them to contributions in optimized database operations.

    This function processes issue-contribution assignments in bulk to minimize
    database round-trips. It creates missing issues and updates contributions
    with their assigned issues using bulk operations.

    :param issue_assignments: list of issue number and contribution ID pairs to assign
    :type issue_assignments: list of tuple (int, int)
    :var unique_issue_numbers: set of distinct tracker issue numbers to process
    :type unique_issue_numbers: set of int
    :var existing_issues: existing Issue objects from database
    :type existing_issues: QuerySet of :class:`core.models.Issue`
    :var existing_issue_numbers: set of issue numbers that already exist in database
    :type existing_issue_numbers: set of int
    :var issues_to_create: list of Issue instances to create in bulk
    :type issues_to_create: list of :class:`core.models.Issue`
    :var fetch_issues_dict: mapping from issue number to Issue instance
    :type fetch_issues_dict: dict of int: :class:`core.models.Issue`
    :var contribution_updates: list of contribution ID and Issue instance pairs
    :type contribution_updates: list of tuple (int, :class:`core.models.Issue`)
    :var contribution_ids: list of contribution IDs to update
    :type contribution_ids: list of int
    :var contributions: Contribution objects to be updated
    :type contributions: QuerySet of :class:`core.models.Contribution`
    :var issue_by_contribution_id: mapping from contribution ID to assigned Issue
    :type issue_by_contribution_id: dict of int: :class:`core.models.Issue`
    """
    if not issue_assignments:
        return

    # Get unique issue numbers
    unique_issue_numbers = {number: status for number, _, status in issue_assignments}

    # Get existing issues
    existing_issues = Issue.objects.filter(number__in=unique_issue_numbers)
    existing_issue_numbers = set(existing_issues.values_list("number", flat=True))

    # Create missing issues
    issues_to_create = [
        Issue(number=number, status=status)
        for number, status in unique_issue_numbers.items()
        if number not in existing_issue_numbers
    ]

    if issues_to_create:
        Issue.objects.bulk_create(issues_to_create)

    # Get all issues (newly created + existing)
    fetch_issues_dict = {
        issue.number: issue
        for issue in Issue.objects.filter(number__in=unique_issue_numbers)
    }

    # Prepare contribution updates
    contribution_updates = []
    for issue_number, contribution_id, _ in issue_assignments:
        if issue_number in fetch_issues_dict:
            contribution_updates.append(
                (contribution_id, fetch_issues_dict[issue_number])
            )

    # Bulk update contributions
    if contribution_updates:
        contribution_ids = [cont_id for cont_id, _ in contribution_updates]
        contributions = Contribution.objects.filter(id__in=contribution_ids)

        # Create mapping for updates
        issue_by_contribution_id = {
            cont_id: issue for cont_id, issue in contribution_updates
        }

        # Update in bulk
        for contribution in contributions:
            contribution.issue = issue_by_contribution_id[contribution.id]

        Contribution.objects.bulk_update(contributions, ["issue"])


@transaction.atomic
def _map_closed_addressed_issues(github_issues):
    """Fetch GitHub issues with "addressed" label and create contributions.

    This function processes GitHub issues labeled as "addressed" and:
    1. Creates Issue objects with ADDRESSED status
    2. Identifies contributors from issue text and user
    3. Creates new contributors from text patterns if none found
    4. Identifies platforms from issue text
    5. Determines rewards based on issue labels
    6. Extracts URLs from issue bodies
    7. Creates contributions for each identified contributor

    :param github_issues: collection of GitHub issue instances
    :type github_issues: list
    :return: True if operation completed successfully, False if no issues found
    :rtype: bool
    """
    # Filter issues with "addressed" label
    addressed_issues = [
        issue
        for issue in github_issues
        if hasattr(issue, "issue")
        and hasattr(issue.issue, "labels")
        and any(
            (getattr(label, "name", label) or "").lower() == "addressed"
            for label in issue.issue.labels or []
        )
    ]

    if not addressed_issues:
        return False

    # Fetch existing rewards mapping
    reward_mapping = _build_reward_mapping()

    # Fetch all contributors and create info mapping
    contributors = {
        c.info: c.id
        for c in Contributor.objects.all()
        if not any(u in c.info for u in EXCLUDED_CONTRIBUTORS)
    }

    # Fetch all platforms by name
    platforms = {
        platform.name: platform.id for platform in SocialPlatform.objects.all()
    }

    # Define current cycle (using latest end date as specified)
    cycle = Cycle.objects.latest("end")

    # Process each addressed issue
    for github_issue in addressed_issues:
        # Skip issues with no body/comments or internal titles
        if not (github_issue.issue.body or github_issue.comments):
            continue

        if "[Internal]" in github_issue.issue.title:
            continue

        number = github_issue.issue.number

        # Combine body and comments for text analysis
        search_text = "\n".join([github_issue.issue.body or "", *github_issue.comments])

        # Identify platform from issue body
        platform_id = _identify_platform_from_text(search_text, platforms)
        if not platform_id:
            # Fallback to GitHub
            platform_id = platforms.get("GitHub")

        reward = _identify_reward_from_issue_title(github_issue.issue.title)
        if not reward:
            reward = _identify_reward_from_labels(
                github_issue.issue.labels, reward_mapping
            )
            if not reward:
                continue  # Skip if no reward identified

        # Extract URL from issue body
        url = _extract_url_text(search_text, platform_id)

        # Get or create issue with ADDRESSED status
        try:
            issue = Issue.objects.get(number=number)
            # Update status to ADDRESSED if it was previously CREATED
            if issue.status == IssueStatus.CREATED:
                issue.status = IssueStatus.ADDRESSED
                issue.save()

        except Issue.DoesNotExist:
            issue = Issue.objects.create(number=number, status=IssueStatus.ADDRESSED)

        # Identify contributors - try multiple methods
        contributor_ids = set()

        # Method 1: Identify from issue user
        user_contributor_id = _identify_contributor_from_user(
            github_issue.issue.user.login, contributors, strict=False
        )
        if user_contributor_id:
            contributor_ids.add(user_contributor_id)

        # Method 2: Identify from issue text
        text_contributor_id = _identify_contributor_from_text(search_text, contributors)
        if text_contributor_id:
            contributor_ids.add(text_contributor_id)

        # Method 3: Create new contributor from text patterns if none found
        if not contributor_ids:
            created_contributor_id, updated_contributors = (
                _create_contributor_from_text(search_text, contributors)
            )
            if created_contributor_id:
                contributor_ids.add(created_contributor_id)
                # Update the contributors dict with the new contributor
                contributors.update(updated_contributors)

            else:
                continue

        # Create contributions for each identified contributor
        for contributor_id in contributor_ids:
            # Check if contribution already exists for this issue and contributor
            existing_contribution = Contribution.objects.filter(
                issue=issue, contributor_id=contributor_id
            ).first()

            if not existing_contribution:
                Contribution.objects.create(
                    contributor_id=contributor_id,
                    cycle=cycle,
                    platform_id=platform_id,
                    reward=reward,
                    issue=issue,
                    percentage=1,  # Default as specified
                    url=url,
                    confirmed=True,  # As specified
                )

    return True


@transaction.atomic
def _map_closed_archived_issues(github_issues):
    """Fetch GitHub issues and assign them to contributions based on URL matching.

    This function traverses all closed GitHub issues and attempts to match them with
    existing contributions by searching for contribution URLs in the issue bodies.
    When a match is found, creates an Issue record and assigns it to the contribution.

    :param github_issues: collection of GitHub issue instances
    :type github_issues: list
    :var contributions: all the existing contribution instances
    :type contributions: QuerySet of :class:`core.models.Contribution`
    :var url_to_contribution: mapping from URL to contribution instance
    :type url_to_contribution: dict of str: :class:`core.models.Contribution`
    :var issue_assignments: collection of issue number, ID and status to process
    :type issue_assignments: set of tuple (int, int)
    :var unprocessed_github_issues: collection of unprocessed GitHub issues
    :type unprocessed_github_issues: list
    :return: list
    """
    if not github_issues:
        return []

    # Get all contributions in one query
    contributions = Contribution.objects.all().only("id", "url")
    if not contributions:
        return []

    # Create a mapping from trackerGitHub issue number to issue object for quick lookup
    github_issues_by_number = {
        issue.issue.number: issue.issue for issue in github_issues
    }

    # Collect all assignments in memory first
    issue_assignments = set()

    # Process each contribution and try to find matching GitHub issues
    without_url = []
    for contribution in contributions:
        if not contribution.url:
            without_url.append(contribution.id)
            continue

        # Method 1: Check if contribution URL is a GitHub issue URL
        issue_number = _is_url_github_issue(contribution.url)
        if issue_number and issue_number in github_issues_by_number:
            # This contribution URL points directly to a GitHub issue
            issue_assignments.add((issue_number, contribution.id, IssueStatus.ARCHIVED))
            continue  # Skip body matching if we found a direct GitHub issue match

        # Method 2: Search through issues for this contribution's URL in their bodies
        for github_issue in github_issues:
            search_text = "\n".join(
                [github_issue.issue.body or "", *github_issue.comments]
            )
            if contribution.url in search_text:
                issue_assignments.add(
                    (github_issue.issue.number, contribution.id, IssueStatus.ARCHIVED)
                )
                break  # One issue per contribution (first match found)

    if without_url:
        print("MISSING URL:", without_url)

    # Process all assignments in bulk
    _create_issues_bulk(list(issue_assignments))

    unprocessed_github_issues = [
        issue
        for issue in github_issues
        if issue.issue.number not in {_number for _number, _, _ in issue_assignments}
        and "[Internal]" not in issue.issue.title
        and "wontfix" not in [label.name for label in issue.issue.labels]
        and "addressed" not in [label.name for label in issue.issue.labels]
    ]

    return unprocessed_github_issues


@transaction.atomic
def _map_open_issues(github_issues):
    """Fetch open GitHub issues and create contributions for detected contributors.

    This function retrieves all open GitHub issues and attempts to:
    1. Identify contributors from issue bodies
    2. Identify platforms from issue bodies
    3. Determine rewards based on issue labels
    4. Extract URLs from issue bodies
    5. Create contributions with the detected information

    :param github_issues: collection of GitHub issue instances
    :type github_issues: list
    :var contributors: mapping from contributor info to contributor ID
    :type contributors: dict of str: int
    :var platforms: mapping from platform name to platform ID
    :type platforms: dict of str: int
    :var cycle: current active cycle
    :type cycle: :class:`core.models.Cycle`
    :var reward_mapping: mapping from label types to reward configurations
    :type reward_mapping: dict of str: tuple
    :return: True if operation completed successfully, False if no token provided
    :rtype: bool
    """
    if not github_issues:
        return False

    # Fetch existing rewards mapping
    reward_mapping = _build_reward_mapping()

    # Fetch all contributors and create info mapping
    contributors = {
        contributor.info: contributor.id
        for contributor in Contributor.objects.all()
        if not any(username in contributor.info for username in EXCLUDED_CONTRIBUTORS)
    }

    # Fetch all platforms by name
    platforms = {
        platform.name: platform.id for platform in SocialPlatform.objects.all()
    }

    # Define current cycle
    cycle = Cycle.objects.latest("start")

    # Process each open issue
    for github_issue in github_issues:
        if (
            not (github_issue.issue.body or github_issue.comments)
            or "[Internal]" in github_issue.issue.title
        ):
            continue

        number = github_issue.issue.number

        search_text = "\n".join([github_issue.issue.body or "", *github_issue.comments])

        # Identify contributor from issue user or text
        contributor_id = _identify_contributor_from_user(
            github_issue.issue.user.login, contributors, strict=False
        )
        if not contributor_id:
            contributor_id = _identify_contributor_from_text(search_text, contributors)
            if not contributor_id:
                print("No contributor for GitHub issue", number)
                continue  # Skip if no contributor identified

        # Identify platform from issue body
        platform_id = _identify_platform_from_text(search_text, platforms)
        if not platform_id:
            platform_id = next(
                platform_id
                for platform_name, platform_id in platforms.items()
                if platform_name == "GitHub"
            )

        reward = _identify_reward_from_issue_title(github_issue.issue.title)
        if not reward:
            reward = _identify_reward_from_labels(
                github_issue.issue.labels, reward_mapping
            )
            if not reward:
                print("No reward for GitHub issue", number)
                continue  # Skip if no reward identified

        # Extract URL from issue body
        url = _extract_url_text(search_text, platform_id)

        # Get or create issue
        try:
            issue = get_object_or_404(Issue, number=number, status=IssueStatus.CREATED)

        except Http404:
            issue = Issue.objects.create(number=number, status=IssueStatus.CREATED)

        # Create contribution
        Contribution.objects.create(
            contributor_id=contributor_id,
            cycle=cycle,
            platform_id=platform_id,
            reward=reward,
            issue=issue,
            percentage=1,
            url=url,
            confirmed=True,
        )

    return True


@transaction.atomic
def _map_unprocessed_closed_archived_issues(github_issues):
    """Create contributions based on closing date from GitHub issues.

    This function processes GitHub issues labeled as "archived" and:
    1. Determines the appropriate cycle based on issue closing date
    2. Creates Issue objects with ARCHIVED status
    3. Identifies contributors from issue text and user
    4. Creates new contributors from text patterns if none found
    5. Identifies platforms from issue text
    6. Determines rewards based on issue labels
    7. Extracts URLs from issue bodies
    8. Creates contributions for each identified contributor

    :param github_issues: collection of GitHub issue instances
    :type github_issues: list
    :return: True if operation completed successfully, False if no issues found
    :rtype: bool
    """
    # Filter issues with "archived" label
    archived_issues = [
        issue
        for issue in github_issues
        if any(label.name.lower() == "archived" for label in issue.issue.labels)
    ]

    if not archived_issues:
        return False

    # Fetch existing rewards mapping
    reward_mapping = _build_reward_mapping()

    # Fetch all contributors and create info mapping
    contributors = {
        contributor.info: contributor.id
        for contributor in Contributor.objects.all()
        if not any(username in contributor.info for username in EXCLUDED_CONTRIBUTORS)
    }

    # Fetch all platforms by name
    platforms = {
        platform.name: platform.id for platform in SocialPlatform.objects.all()
    }

    # Process each archived issue
    for github_issue in archived_issues:
        if (
            not (github_issue.issue.body or github_issue.comments)
            or "[Internal]" in github_issue.issue.title
        ):
            continue

        number = github_issue.issue.number

        # Skip if issue already has an associated Issue record
        if Issue.objects.filter(number=number).exists():
            continue

        # Determine cycle based on closing date
        if not github_issue.issue.closed_at:
            print(f"No closing date for archived GitHub issue {number}, skipping")
            continue

        cycle = Cycle.objects.filter(
            start__lte=github_issue.issue.closed_at,
            end__gte=github_issue.issue.closed_at,
        ).first()

        if not cycle:
            print(
                f"No cycle found for closing date {github_issue.issue.closed_at}"
                " in issue {number}, skipping"
            )
            continue

        # Combine body and comments for text analysis
        search_text = "\n".join([github_issue.issue.body or "", *github_issue.comments])

        # Identify platform from issue body
        platform_id = _identify_platform_from_text(search_text, platforms)
        if not platform_id:
            platform_id = next(
                platform_id
                for platform_name, platform_id in platforms.items()
                if platform_name == "GitHub"
            )

        reward = _identify_reward_from_issue_title(
            github_issue.issue.title, active=False
        )
        if not reward:
            reward = _identify_reward_from_labels(
                github_issue.issue.labels, reward_mapping
            )
            if not reward:
                print(f"No reward for archived GitHub issue {number}")
                continue  # Skip if no reward identified

        # Extract URL from issue body
        url = _extract_url_text(search_text, platform_id)

        # Create issue with ARCHIVED status
        issue = Issue.objects.create(number=number, status=IssueStatus.ARCHIVED)

        # Identify contributors - try multiple methods
        contributor_ids = set()

        # Method 1: Identify from issue user
        user_contributor_id = _identify_contributor_from_user(
            github_issue.issue.user.login, contributors, strict=False
        )
        if user_contributor_id:
            contributor_ids.add(user_contributor_id)

        # Method 2: Identify from issue text
        text_contributor_id = _identify_contributor_from_text(search_text, contributors)
        if text_contributor_id:
            contributor_ids.add(text_contributor_id)

        # Method 3: Create new contributor from text patterns if none found
        if not contributor_ids:
            created_contributor_id, contributors = _create_contributor_from_text(
                search_text, contributors
            )
            if created_contributor_id:
                contributor_ids.add(created_contributor_id)
            else:
                print(f"No contributors found for archived GitHub issue {number}")
                continue

        # Create contributions for each identified contributor
        for contributor_id in contributor_ids:
            Contribution.objects.create(
                contributor_id=contributor_id,
                cycle=cycle,
                platform_id=platform_id,
                reward=reward,
                issue=issue,
                percentage=1,  # Default as specified
                url=url,
                confirmed=True,  # As specified
            )

    return True


def map_github_issues(issue_tracker_api_token=""):
    """Fetch existing GitHub issues and create database records from them.

    :param issue_tracker_api_token: GitHub API token
    :type issue_tracker_api_token: str
    :var github_issues: collection of GitHub issue instances
    :type github_issues: list
    :var closed_size: number of issues created from closed GitHub issues
    :type closed_size: int
    :var size: number of issues created from GitHub issues
    :type size: int
    :return: Boolean
    """
    github_issues = _fetch_and_categorize_issues(issue_tracker_api_token)

    print("Fetched closed issues size: ", len(github_issues.get("closed", [])))
    unprocessed_github_issues = _map_closed_archived_issues(
        github_issues.get("closed", [])
    )
    closed_size = len(Issue.objects.all())
    print("Issues created from closed archived GitHub issues: ", closed_size)

    _map_unprocessed_closed_archived_issues(unprocessed_github_issues)
    print(
        "Issues created from unprocessed archived GitHub issues: ",
        len(Issue.objects.all()) - closed_size,
    )
    closed_size = len(Issue.objects.all())

    _map_closed_addressed_issues(github_issues.get("closed", []))
    print(
        "Issues created from closed addressed GitHub issues: ",
        len(Issue.objects.all()) - closed_size,
    )

    closed_size = len(Issue.objects.all())
    print("Issues created from closed GitHub issues: ", closed_size)

    print("Fetched open issues size: ", len(github_issues.get("open", [])))
    _map_open_issues(github_issues.get("open", []))
    size = len(Issue.objects.all())
    print("Issues created from open GitHub issues: ", size - closed_size)

    print("Total number of issues created: ", size)
    return False
