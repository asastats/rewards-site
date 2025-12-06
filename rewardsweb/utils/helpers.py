"""Module containing projects' helper functions."""

import base64
import logging
import os
import pickle
from calendar import monthrange
from datetime import datetime
from pathlib import Path

import pandas as pd
from algosdk import encoding
from django.core.exceptions import ImproperlyConfigured
from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey

from utils.constants.core import MISSING_ENVIRONMENT_VARIABLE_ERROR

logger = logging.getLogger(__name__)


def calculate_transpareny_report_period(
    report_type,
    month=None,
    quarter=None,
    year=None,
    start_date_str=None,
    end_date_str=None,
):
    """Calculate start and end dates based on report type and parameters.

    :param report_type: Type of report (monthly, quarterly, yearly, custom)
    :type report_type: str
    :param month: Month number (1-12) for monthly reports
    :type month: int or None
    :param quarter: Quarter number (1-4) for quarterly reports
    :type quarter: int or None
    :param year: Year for reports
    :type year: int or None
    :param start_date_str: Start date string for custom reports (YYYY-MM-DD)
    :type start_date_str: str or None
    :param end_date_str: End date string for custom reports (YYYY-MM-DD)
    :type end_date_str: str or None
    :return: Tuple of (start_date, end_date)
    :rtype: two-tuple
    """
    year = int(year) if year else None

    if report_type == "yearly":
        # First day of the year
        start_date = datetime(year, 1, 1)
        # Last day of the year
        end_date = datetime(year, 12, 31)

    elif report_type == "monthly":
        month = int(month)
        # First day of the month
        start_date = datetime(year, month, 1)
        # Last day of the month
        _, last_day = monthrange(year, month)
        end_date = datetime(year, month, last_day)

    elif report_type == "quarterly":
        quarter = int(quarter)

        # Define quarter start and end months
        quarter_map = {
            1: (1, 3),  # Q1: Jan-Mar
            2: (4, 6),  # Q2: Apr-Jun
            3: (7, 9),  # Q3: Jul-Sep
            4: (10, 12),  # Q4: Oct-Dec
        }

        start_month, end_month = quarter_map[quarter]
        # First day of first month in quarter
        start_date = datetime(year, start_month, 1)
        # Last day of last month in quarter
        _, last_day = monthrange(year, end_month)
        end_date = datetime(year, end_month, last_day)

    else:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d")

    return start_date, end_date


def convert_and_clean_excel(input_file, output_file, legacy_contributions):
    """Convert and clean Excel file to CSV format for import.

    :param input_file: Path to input Excel file
    :type input_file: str
    :param output_file: Path to output CSV file for current contributions
    :type output_file: str
    :param legacy_contributions: Path to output CSV file for legacy contributions
    :type legacy_contributions: str
    """
    df = pd.read_excel(input_file, sheet_name=3, header=None).iloc[2:]

    with pd.option_context("future.no_silent_downcasting", True):
        df = df.fillna("NULL").infer_objects(copy=False)

    df.drop(columns=[4, 11, 12, 13, 14, 15, 16], inplace=True)

    df = df[~df[0].str.startswith("Period below")]

    df = df.map(lambda x: str(x).replace(" 00:00:00", ""))

    df.loc[df[1] == "45276", 1] = "2023-12-16"
    df.loc[df[2] == "45303", 2] = "2024-01-12"
    df.loc[df[2] == "Legal entity research", 6] = "[AT] Admin Task"
    df.loc[df[2] == "Legal entity research", 2] = "NULL"
    df.loc[df[1] == "NULL", 1] = (
        "2021-12-10"  # Legal entity, add date (assign to cycle)
    )
    df.loc[df[2] == "NULL", 2] = (
        "2021-12-31"  # Legal entity, add date (assign to cycle)
    )

    df = df[~df[0].str.startswith("NULL")]  # Clean rows where first column is 'NULL'

    # in this part we are moving a historic cycle appended at the end of the file
    # to where it should be, chronologically
    MOVED_CYCLE_LENGTH = 66  # constant length of the historic cycle
    df_len = len(df.index) - 1

    replacement_index = df_len - MOVED_CYCLE_LENGTH

    print("Dataframe size: " + str(len(df.index)))

    df1 = df.iloc[:855]  # start part
    df2 = df.iloc[replacement_index:]  # Part to cut and insert
    df3 = df.iloc[855:replacement_index]  # final part

    df = pd.concat([df1, df2, df3])
    df[0] = df[0].str.strip()  # Remove leading and trailing spaces from column 0

    # full csv export for debugging
    path = Path(__file__).resolve().parent.parent / "fixtures" / "fullcsv.csv"
    df.to_csv(path, index=False, header=None, na_rep="NULL")

    # FINAL EXPORT

    legacy_df = df.iloc[:82]
    df = df.iloc[82:]

    df.to_csv(output_file, index=False, header=None, na_rep="NULL")
    legacy_df.to_csv(legacy_contributions, index=False, header=None, na_rep="NULL")


def get_env_variable(name, default=None):
    """Return environment variable with provided `name`.

    Raise `ImproperlyConfigured` exception if such variable isn't set.

    :param name: name of environment variable
    :type name: str
    :param default: environment variable's default value
    :type default: str
    :return: str
    """
    try:
        return os.environ[name]

    except KeyError:
        if default is None:
            raise ImproperlyConfigured(
                "{} {}!".format(name, MISSING_ENVIRONMENT_VARIABLE_ERROR)
            )
        return default


def humanize_contributions(contributions):
    """Return collection of provided `contributions` formatted for output.

    :param contributions: collectin of users' contribution instances
    :type contributions: :class:`django.db.models.query.QuerySet`
    :return: list
    """
    return [
        {
            "id": c.id,
            "contributor_name": c.contributor.name,
            "cycle_id": c.cycle.id,
            "platform": c.platform.name,
            "url": c.url,
            "type": c.reward.type,
            "level": c.reward.level,
            "percentage": c.percentage,
            "reward": c.reward.amount,
            "confirmed": c.confirmed,
        }
        for c in contributions
    ]


def parse_full_handle(full_handle):
    """Return social platform's prefix and user's handle from provided `full_handle`.

    :param full_handle: contributor's unique identifier (platform prefix and handle)
    :type full_handle: str
    :var prefix: unique social platform's prefix
    :type prefix: str
    :var handle: contributor's handle/username
    :type handle: str
    :var platform: social platform's model instance
    :return: two-tuple
    """
    prefix, handle = "", full_handle
    if "@" in full_handle[:2]:
        prefix = full_handle[: full_handle.index("@") + 1]
        handle = full_handle[full_handle.index("@") + 1 :]

    elif full_handle.startswith("u/"):
        prefix = "u/"
        handle = full_handle[2:]

    return prefix, handle


def read_pickle(filename):
    """Return collection of key and values created from provided `filename` pickle file.

    :param filename: full path to pickle file
    :type filename: :class:`pathlib.Path`
    :return: dict with loaded data or empty dict if file doesn't exist or is corrupted
    """
    if os.path.exists(filename):
        try:
            with open(filename, "rb") as pickle_file:
                return pickle.load(pickle_file)
        except (pickle.PickleError, EOFError, AttributeError, ImportError):
            # Handle various pickle-related errors
            pass
    return {}


def social_platform_prefixes():
    """Return list of social platforms with their prefixes.

    :return: List of tuples (platform_name, prefix)
    :rtype: list
    """
    return [
        ("Discord", ""),
        ("Twitter", "@"),
        ("Reddit", "u/"),
        ("GitHub", "g@"),
        ("Telegram", "t@"),
        ("Forum", "f@"),
    ]


def user_display(user):
    """Return human readable representation of provided `user` instance.

    :param user: user instance
    :type user: class:`django.contrib.auth.models.User`
    :return: str
    """
    return user.profile.name


def verify_signed_transaction(stxn):
    """Verify the signature of a signed transaction.

    This function checks whether a signed Algorand transaction has a valid signature.
    It handles both regular transactions and transactions with rekeying by verifying
    the signature against the appropriate public key (sender or authorizing address).

    :param stxn: signed transaction instance to verify
    :type stxn: :class:`algosdk.transaction.SignedTransaction`
    :return: True if the signature is valid, False otherwise
    :rtype: bool

    :raises: This function catches BadSignatureError internally and returns False,
             so it doesn't raise any exceptions for invalid signatures.
    """
    if stxn.signature is None or len(stxn.signature) == 0:
        return False

    public_key = stxn.transaction.sender
    if stxn.authorizing_address is not None:
        public_key = stxn.authorizing_address

    verify_key = VerifyKey(encoding.decode_address(public_key))

    prefixed_message = b"TX" + base64.b64decode(
        encoding.msgpack_encode(stxn.transaction)
    )

    try:
        verify_key.verify(prefixed_message, base64.b64decode(stxn.signature))
        return True

    except BadSignatureError:
        return False
