"""Module containing database management class for social media mention tracking."""

import json
import sqlite3
from pathlib import Path

from trackers.config import PLATFORM_CONTEXT_FIELDS


class MentionDatabaseManager:
    """Database manager for social media mention tracking.

    :var MentionDatabaseManager.db_path: path to SQLite database file
    :type MentionDatabaseManager.db_path: str
    :var MentionDatabaseManager.conn: database connection
    :type MentionDatabaseManager.conn: :class:`sqlite3.Connection`
    """

    def __init__(self, db_path=None):
        """Initialize database manager."""
        self.db_path = (
            db_path
            or Path(__file__).parent.parent.resolve()
            / "fixtures"
            / "social_mentions.db"
        )
        self.conn = None
        self.setup_database()

    def setup_database(self):
        """Setup database schema.

        :var cursor: database cursor
        :type cursor: :class:`sqlite3.Cursor`
        """
        self.conn = sqlite3.connect(self.db_path)
        cursor = self.conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS processed_mentions (
                item_id TEXT PRIMARY KEY,
                platform TEXT NOT NULL,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                suggester TEXT,
                context_field TEXT,
                raw_data TEXT
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS mention_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                action TEXT,
                details TEXT
            )
        """
        )
        self.conn.commit()

    def is_processed(self, item_id, platform_name):
        """Check if item has been processed.

        :param item_id: unique identifier for the social media item
        :type item_id: str
        :param platform_name: name of the social media platform
        :type platform_name: str
        :var cursor: database cursor
        :type cursor: :class:`sqlite3.Cursor`
        :return: True if item has been processed, False otherwise
        :rtype: bool
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT 1 FROM processed_mentions WHERE item_id = ? AND platform = ?",
            (item_id, platform_name),
        )
        return cursor.fetchone() is not None

    def mark_processed(self, item_id, platform_name, data):
        """Mark item as processed in database.

        :param item_id: unique identifier for the social media item
        :type item_id: str
        :param platform_name: name of the social media platform
        :type platform_name: str
        :param data: mention data dictionary
        :type data: dict
        :var cursor: database cursor
        :type cursor: :class:`sqlite3.Cursor`
        :var context_field: platform-specific context field value
        :type context_field: str or None
        """
        cursor = self.conn.cursor()

        context_field = None
        if platform_name in PLATFORM_CONTEXT_FIELDS:
            context_field_name = PLATFORM_CONTEXT_FIELDS[platform_name]
            context_field = data.get(context_field_name)

        cursor.execute(
            """INSERT INTO processed_mentions 
               (item_id, platform, suggester, context_field, raw_data) 
               VALUES (?, ?, ?, ?, ?)""",
            (
                item_id,
                platform_name,
                data.get("suggester"),
                context_field,
                json.dumps(data),
            ),
        )
        self.conn.commit()

    def last_processed_timestamp(self, platform_name):
        """Get the timestamp of the last processed mention for a platform.

        This method retrieves the highest timestamp from all processed mentions
        for a specific platform. The timestamp is extracted from the `raw_data`
        JSON field. This is used by trackers to fetch only new mentions since
        the last successfully processed item.

        :param platform_name: The name of the social media platform.
        :type platform_name: str
        :var cursor: The database cursor for executing the query.
        :type cursor: :class:`sqlite3.Cursor`
        :var result: The result of the database query.
        :type result: tuple or None
        :return: The Unix timestamp of the last processed mention, or None if
                 no mentions are found for the platform.
        :rtype: int or None
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """SELECT MAX(CAST(json_extract(raw_data, '$.timestamp') AS INTEGER))
               FROM processed_mentions
               WHERE platform = ?""",
            (platform_name,),
        )
        result = cursor.fetchone()
        if result and result[0] is not None:
            return result[0]
        return None

    def log_action(self, platform_name, action, details=""):
        """Log platform actions to database.

        :param platform_name: name of the social media platform
        :type platform_name: str
        :param action: description of the action performed
        :type action: str
        :param details: additional details about the action
        :type details: str
        :var cursor: database cursor
        :type cursor: :class:`sqlite3.Cursor`
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO mention_logs (platform, action, details) VALUES (?, ?, ?)",
            (platform_name, action, details),
        )
        self.conn.commit()

    def cleanup(self):
        """Cleanup resources.

        Closes database connection if it exists.
        """
        if self.conn:
            self.conn.close()
