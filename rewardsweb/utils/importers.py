"""Module containing functions for importing existing data to database."""

import re
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db.utils import IntegrityError
from django.http import Http404
from django.shortcuts import get_object_or_404

from core.models import (
    Contribution,
    Contributor,
    Cycle,
    Handle,
    Reward,
    RewardType,
    SocialPlatform,
)
from utils.constants.core import REWARDS_COLLECTION
from utils.helpers import get_env_variable, social_platform_prefixes

ADDRESSES_CSV_COLUMNS = ["handle", "address"]
CONTRIBUTION_CSV_COLUMNS = [
    "contributor",
    "cycle_start",
    "cycle_end",
    "platform",
    "url",
    "type",
    "level",
    "percentage",
    "reward",
    "comment",
]


def _append_gaps_to_cycles_dataframe(df):
    """Append gap periods to cycles dataframe and return sorted by start date.

    Identifies periods between existing cycles that are not covered and adds them
    as additional rows to the dataframe. The resulting dataframe contains both
    original cycles and the identified gaps, sorted by cycle_start date.

    :param df: DataFrame with cycle_start and cycle_end columns in 'yyyy-mm-dd' format
    :type df: pandas.DataFrame
    :return: DataFrame with original cycles and gap periods appended
    :rtype: pandas.DataFrame
    """
    # Create a working copy with datetime columns
    df_working = df.copy()
    df_working["cycle_start_dt"] = pd.to_datetime(df_working["cycle_start"])
    df_working["cycle_end_dt"] = pd.to_datetime(df_working["cycle_end"])

    # Sort by start date
    df_working.sort_values(by="cycle_start_dt", inplace=True)
    df_working.reset_index(drop=True, inplace=True)

    # Find the gaps
    gaps = []

    # Find gaps between periods
    for i in range(1, len(df_working)):
        prev_end = df_working.loc[i - 1, "cycle_end_dt"]
        curr_start = df_working.loc[i, "cycle_start_dt"]

        # If there's a gap between the end of previous and start of current
        if prev_end < curr_start - pd.Timedelta(days=1):
            gap_start = prev_end + pd.Timedelta(days=1)
            gap_end = curr_start - pd.Timedelta(days=1)
            gaps.append(
                {
                    "cycle_start": gap_start.strftime("%Y-%m-%d"),
                    "cycle_end": gap_end.strftime("%Y-%m-%d"),
                }
            )

    # Append gaps to original dataframe
    if gaps:
        gaps_df = pd.DataFrame(gaps)
        result_df = pd.concat([df, gaps_df], ignore_index=True)
    else:
        result_df = df.copy()

    # Convert back to datetime for sorting, then back to string
    result_df["cycle_start_dt"] = pd.to_datetime(result_df["cycle_start"])
    result_df.sort_values(by="cycle_start_dt", inplace=True)
    result_df.reset_index(drop=True, inplace=True)
    result_df = result_df[["cycle_start", "cycle_end"]]  # Keep only original columns

    return result_df


def _check_current_cycle(cycle_instance):
    """Check if current cycle has ended and create new cycle if needed.

    :param cycle_instance: The latest cycle instance to check
    :type cycle_instance: :class:`core.models.Cycle`
    """
    if datetime.now().date() > cycle_instance.end:
        start = cycle_instance.end + timedelta(days=1)
        end = start + timedelta(days=92)
        # Adjust to end of month
        end = datetime(end.year, end.month, 1) + timedelta(days=-1)
        Cycle.objects.create(start=start, end=end)


def _create_active_rewards():
    """Create or activate reward objects based on REWARDS_COLLECTION."""
    for index in range(len(REWARDS_COLLECTION)):
        reward = REWARDS_COLLECTION[index]
        reward_name = reward[0]
        for level, amount in enumerate(reward):
            if level == 0:
                continue

            label, name = (
                reward_name.split(" ", 1)[0].strip("[]"),
                reward_name.split(" ", 1)[1].strip(),
            )
            reward_type = get_object_or_404(RewardType, label=label, name=name)
            try:
                reward = Reward.objects.get(
                    type=reward_type, level=level, amount=amount
                )
                reward.active = True
                reward.save()

            except ObjectDoesNotExist:
                Reward.objects.create(
                    type=reward_type, level=level, amount=amount, active=True
                )


def _create_superusers():
    """Create initial superusers from environment variables."""
    superusers_str = get_env_variable("INITIAL_SUPERUSERS", "")
    passwords_str = get_env_variable("INITIAL_SUPERUSER_PASSWORDS", "")
    addresses_str = get_env_variable("INITIAL_SUPERUSER_ADDRESSES", "")

    superusers = [user for user in superusers_str.split(",") if user.strip()]
    passwords = [pwd for pwd in passwords_str.split(",") if pwd.strip()]
    addresses = [adr for adr in addresses_str.split(",") if len(addresses_str) > 50]

    assert len(superusers) == len(passwords)
    assert len(addresses) == 0 or len(addresses) == len(superusers)

    for index, superuser in enumerate(superusers):
        user = User.objects.create_superuser(superuser, password=passwords[index])
        if addresses and addresses[index]:
            address = addresses[index]
            contributor = Contributor.objects.filter(address=address).first()
            if not contributor:
                contributor = Contributor.objects.from_full_handle(
                    user.username, address=address
                )

            user.profile.contributor = contributor
            user.profile.save()


def _dataframe_from_csv(filename, columns=CONTRIBUTION_CSV_COLUMNS):
    """Create pandas DataFrame from CSV file.

    :param filename: Path to the CSV file
    :type filename: str
    :param columns: List of column names for the DataFrame
    :type columns: list
    :return: DataFrame with specified columns or None if file not found/empty
    :rtype: :class:`pandas.DataFrame` or None
    """
    try:
        data = pd.read_csv(filename, header=None, sep=",")
    except (pd.errors.EmptyDataError, FileNotFoundError):
        return None
    data.columns = columns
    return data


def _import_contributions(data, parse_callback, amount_callback):
    """Import contributions from DataFrame to database.

    :param data: DataFrame containing contribution data
    :type data: :class:`pandas.DataFrame`
    :param parse_callback: Function to parse reward type from string
    :type parse_callback: callable
    :param amount_callback: Function to calculate reward amount
    :type amount_callback: callable
    """
    for _, row in data.iterrows():
        contributor = Contributor.objects.from_full_handle(row["contributor"])
        cycle = Cycle.objects.get(start=row["cycle_start"])
        platform = SocialPlatform.objects.get(name__iexact=row["platform"])
        label, name = parse_callback(row["type"])
        reward_type = get_object_or_404(RewardType, label=label, name=name)
        reward = Reward.objects.get(
            type=reward_type,
            level=row["level"] if not pd.isna(row["level"]) else 1,
            amount=amount_callback(row["reward"]),
        )
        percentage = row["percentage"] if not pd.isna(row["percentage"]) else 1
        url = row["url"] if not pd.isna(row["url"]) else None
        comment = row["comment"] if not pd.isna(row["comment"]) else None
        Contribution.objects.create(
            contributor=contributor,
            cycle=cycle,
            platform=platform,
            reward=reward,
            percentage=percentage,
            url=url,
            comment=comment,
            confirmed=True,
        )


def _import_rewards(data, parse_callback, amount_callback):
    """Import rewards from DataFrame to database.

    :param data: DataFrame containing reward data
    :type data: :class:`pandas.DataFrame`
    :param parse_callback: Function to parse reward type from string
    :type parse_callback: callable
    :param amount_callback: Function to calculate reward amount
    :type amount_callback: callable
    """
    for typ, level, reward in data.values.tolist():
        label, name = parse_callback(typ)
        try:
            reward_type = get_object_or_404(RewardType, label=label, name=name)

        except Http404:
            reward_type = RewardType.objects.create(label=label, name=name)

        try:
            Reward.objects.create(
                type=reward_type,
                level=level if not pd.isna(level) else 1,
                amount=amount_callback(reward),
                active=False,
            )
        except IntegrityError:
            pass


def _parse_addresses():
    """Parse addresses from CSV file and group by address.

    :return: List of addresses with associated handles
    :rtype: list
    """
    addresses_filename = (
        Path(__file__).resolve().parent.parent / "fixtures" / "addresses.csv"
    )
    addresses = _dataframe_from_csv(addresses_filename, columns=ADDRESSES_CSV_COLUMNS)

    users_filename = (
        Path(__file__).resolve().parent.parent
        / "fixtures"
        / "users_without_addresses.csv"
    )
    users = _dataframe_from_csv(users_filename, columns=ADDRESSES_CSV_COLUMNS)

    # Handle cases where one or both files are missing/empty
    if addresses is None and users is None:
        return []
    elif addresses is None:
        data = users
    elif users is None:
        data = addresses
    else:
        data = pd.concat([addresses, users])

    data = data[["handle", "address"]].drop_duplicates()
    grouped = (
        data.groupby("address")["handle"]
        .apply(lambda x: x.tolist()[::-1])
        .reset_index()
    )
    return grouped.values.tolist()


def _parse_label_and_name_from_reward_type_legacy(typ):
    """Parse reward type label and name from legacy format.

    :param typ: Reward type string in legacy format
    :type typ: str
    :return: Tuple of (label, name)
    :rtype: tuple
    """
    label, name = _parse_label_and_name_from_reward_type(typ)
    if name == "Custom":
        # Handle None or empty strings
        if not typ:
            return "S", "Suggestion"

        typ_lower = typ.lower()
        if "feature request" in typ_lower:
            return "F", "Feature Request"

        if "bug report" in typ_lower:
            return "B", "Bug Report"

        if "ecosystem research" in typ_lower:
            return "ER", "Ecosystem Research"

        return "S", "Suggestion"

    return label, name


def _parse_label_and_name_from_reward_type(typ):
    """Parse reward type label and name from standard format.

    :param typ: Reward type string in format "[LABEL] Name"
    :type typ: str
    :return: Tuple of (label, name)
    :rtype: tuple
    """
    if not pd.isna(typ):
        pattern = r"\[([^\]]+)\]\s*(.+)"
        match = re.match(pattern, typ)
        if match:
            return match.group(1), match.group(2)

    return "CST", "Custom"


def _reward_amount(reward):
    """Calculate reward amount in base units.

    :param reward: Reward amount
    :type reward: float
    :return: Reward amount in base units
    :rtype: int
    """
    return round(reward * 1_000_000) if not pd.isna(reward) else 0


def _reward_amount_legacy(reward):
    """Calculate legacy reward amount in base units.

    :param reward: Reward amount
    :type reward: float
    :return: Reward amount in base units
    :rtype: int
    """
    return round(round(reward, 2) * 1_000_000) if not pd.isna(reward) else 0


def import_from_csv(contributions_path, legacy_contributions_path):
    """Import contributions from CSV files to database.

    :param contributions_path: Path to current contributions CSV file
    :type contributions_path: str
    :param legacy_contributions_path: Path to legacy contributions CSV file
    :type legacy_contributions_path: str
    :return: Error message string or False if successful
    :rtype: str or bool
    """
    # # CHECK
    if len(SocialPlatform.objects.all()):
        return "ERROR: Database is not empty!"

    # # PLATFORMS
    SocialPlatform.objects.bulk_create(
        SocialPlatform(name=name, prefix=prefix)
        for name, prefix in social_platform_prefixes()
    )
    print("Social platforms created: ", len(SocialPlatform.objects.all()))

    # # ADDRESSES
    addresses = _parse_addresses()
    Contributor.objects.bulk_create(
        Contributor(name=handles[0], address=address) for address, handles in addresses
    )
    print("Contributors imported: ", len(Contributor.objects.all()))
    for address, handles in addresses:
        for full_handle in handles:
            handle = Handle.objects.from_address_and_full_handle(address, full_handle)
            handle.save()
    print("Handles imported: ", len(Handle.objects.all()))

    # # CONTRIBUTIONS
    data = _dataframe_from_csv(contributions_path)
    legacy_data = _dataframe_from_csv(legacy_contributions_path)

    # Handle case where CSV files are missing or empty
    if data is None:
        data = pd.DataFrame(columns=CONTRIBUTION_CSV_COLUMNS)
    if legacy_data is None:
        legacy_data = pd.DataFrame(columns=CONTRIBUTION_CSV_COLUMNS)

    cycles_data = data[["cycle_start", "cycle_end"]].drop_duplicates()
    legacy_cycles_data = legacy_data[["cycle_start", "cycle_end"]].drop_duplicates()
    all_cycles_data = _append_gaps_to_cycles_dataframe(
        pd.concat([cycles_data, legacy_cycles_data]).sort_values(by=["cycle_start"])
    )
    Cycle.objects.bulk_create(
        Cycle(start=start, end=end) for start, end in all_cycles_data.values.tolist()
    )
    _check_current_cycle(Cycle.objects.latest("end"))
    print("Cycles imported: ", len(Cycle.objects.all()))

    _import_rewards(
        data[["type", "level", "reward"]],
        _parse_label_and_name_from_reward_type,
        _reward_amount,
    )
    _import_rewards(
        legacy_data[["type", "level", "reward"]],
        _parse_label_and_name_from_reward_type_legacy,
        _reward_amount_legacy,
    )
    _create_active_rewards()
    print("Rewards imported: ", len(Reward.objects.all()))

    _import_contributions(
        legacy_data,
        _parse_label_and_name_from_reward_type_legacy,
        _reward_amount_legacy,
    )
    _import_contributions(
        data,
        _parse_label_and_name_from_reward_type,
        _reward_amount,
    )
    print("Contributions imported: ", len(Contribution.objects.all()))

    _create_superusers()

    return False
