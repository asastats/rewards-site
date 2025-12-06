"""Module containing core app's constants."""

import os
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

ADDRESS_LEN = 58

MISSING_ENVIRONMENT_VARIABLE_ERROR = "Environment variable is not set"

HANDLE_EXCEPTIONS = ("RR", "Di")

CONTRIBUTIONS_TAIL_SIZE = 5

REWARDS_COLLECTION = (
    ("[F] Feature Request", 30000, 60000, 135000),
    ("[B] Bug Report", 30000, 60000, 135000),
    ("[AT] Admin Task", 35000, 70000, 150000),
    ("[CT] Content Task", 100000, 200000, 300000),
    ("[IC] Issue Creation", 30000, 60000, 135000),
    ("[TWR] Twitter Post", 30000, 60000, 135000),
    ("[D] Development", 100000, 200000, 300000),
    ("[ER] Ecosystem Research", 50000, 100000, 200000),
)

DISCORD_EMOJIS = {
    "noted": os.getenv("DISCORD_EMOJI_NOTED", "thumbsup"),
    "addressed": os.getenv("DISCORD_EMOJI_ADDRESSED", "ballot_box_with_check"),
    "wontfix": os.getenv("DISCORD_EMOJI_WONTFIX", "no_entry_sign"),
    "duplicate": os.getenv("DISCORD_EMOJI_DUPLICATE", "heavy_multiplication_x"),
}

ISSUE_CREATION_LABEL_CHOICES = [
    ("feature", "Feature"),
    ("bug", "Bug"),
    ("task", "Task"),
    ("research", "Research"),
    ("mobile", "Mobile"),
    ("work in progress", "Work in progress"),
]

ISSUE_LABEL_CHOICES = ISSUE_CREATION_LABEL_CHOICES + [
    ("wontfix", "Wontfix"),
    ("addressed", "Addressed"),
    ("archived", "Archived"),
]

ISSUE_PRIORITY_CHOICES = [
    ("low priority", "Low Priority"),
    ("medium priority", "Medium Priority"),
    ("high priority", "High Priority"),
    ("blocker", "Blocker"),
]

GITHUB_LABELS = (
    "blocker",
    "high priority",
    "medium priority",
    "low priority",
    "feature",
    "bug",
    "task",
    "research",
    "mobile",
    "addressed",
    "archived",
    "wontfix",
)

GITHUB_ISSUES_START_DATE = datetime.fromtimestamp(
    int(os.getenv("GITHUB_ISSUES_START_DATE", 1649980800)), tz=timezone.utc
)
excluded_contributors = os.getenv("EXCLUDED_CONTRIBUTORS", "")
EXCLUDED_CONTRIBUTORS = [
    contributor.strip()
    for contributor in excluded_contributors.split(",")
    if excluded_contributors.split(",")[0]
]

TRANPARENCY_REPORT_REQUIRED_FIELDS = {
    "monthly": ["month", "year"],
    "quarterly": ["quarter", "year"],
    "yearly": ["year"],
    "custom": ["start_date", "end_date"],
}

ALGORAND_WALLETS = [
    {"id": "pera", "name": "Pera Wallet"},
    {"id": "defly", "name": "Defly Wallet"},
    {"id": "lute", "name": "Lute Wallet"},
]

WALLET_CONNECT_NONCE_PREFIX = "Login to Rewards Suite website: "

WALLET_CONNECT_NETWORK_OPTIONS = ["testnet", "mainnet"]
