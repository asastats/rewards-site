"""Testing module for :py:mod:`trackers.database` module."""

import json
from pathlib import Path

import trackers.database
from trackers.database import MentionDatabaseManager


class TestTrackersMentionDatabaseManager:
    """Testing class for :class:`trackers.database.MentionDatabaseManager` class."""

    # __init__
    def test_trackers_database_mentiondatabasemanager_init_success(self, mocker):
        mock_setup_database = mocker.patch.object(
            MentionDatabaseManager, "setup_database"
        )

        instance = MentionDatabaseManager("test.db")

        assert instance.db_path == "test.db"
        mock_setup_database.assert_called_once()

    def test_trackers_database_mentiondatabasemanager_init_default_path(self, mocker):
        mock_setup_database = mocker.patch.object(
            MentionDatabaseManager, "setup_database"
        )

        instance = MentionDatabaseManager()

        assert (
            instance.db_path
            == Path(trackers.database.__file__).parent.parent.resolve()
            / "fixtures"
            / "social_mentions.db"
        )
        mock_setup_database.assert_called_once()

    # setup_database
    def test_trackers_database_mentiondatabasemanager_setup_database_success(
        self, mocker
    ):
        mock_connect = mocker.patch("sqlite3.connect")
        mock_conn = mocker.MagicMock()
        mock_cursor = mocker.MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        instance = MentionDatabaseManager()
        mock_connect.reset_mock()
        mock_conn.reset_mock()

        instance.setup_database()

        mock_connect.assert_called_once_with(
            Path(trackers.database.__file__).parent.parent.resolve()
            / "fixtures"
            / "social_mentions.db"
        )
        assert mock_cursor.execute.call_count == 2
        mock_conn.commit.assert_called_once()
        assert instance.conn == mock_conn

    # is_processed
    def test_trackers_database_mentiondatabasemanager_is_processed_true(self, mocker):
        instance = MentionDatabaseManager()
        mock_conn = mocker.MagicMock()
        mock_cursor = mocker.MagicMock()
        mock_cursor.fetchone.return_value = [1]
        mock_conn.cursor.return_value = mock_cursor
        instance.conn = mock_conn

        result = instance.is_processed("test_item_id", "test_platform")

        assert result is True
        mock_cursor.execute.assert_called_once_with(
            "SELECT 1 FROM processed_mentions WHERE item_id = ? AND platform = ?",
            ("test_item_id", "test_platform"),
        )

    def test_trackers_database_mentiondatabasemanager_is_processed_false(self, mocker):
        instance = MentionDatabaseManager()
        mock_conn = mocker.MagicMock()
        mock_cursor = mocker.MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn.cursor.return_value = mock_cursor
        instance.conn = mock_conn

        result = instance.is_processed("test_item_id", "test_platform")

        assert result is False

    # mark_processed
    def test_trackers_database_mentiondatabasemanager_mark_processed_reddit(
        self, mocker
    ):
        instance = MentionDatabaseManager()
        mock_conn = mocker.MagicMock()
        mock_cursor = mocker.MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        instance.conn = mock_conn

        test_data = {
            "suggester": "test_user",
            "subreddit": "test_subreddit",
        }

        instance.mark_processed("test_item_id", "reddit", test_data)

        expected_json = json.dumps(test_data)
        mock_cursor.execute.assert_called_once_with(
            """INSERT INTO processed_mentions 
               (item_id, platform, suggester, context_field, raw_data) 
               VALUES (?, ?, ?, ?, ?)""",
            (
                "test_item_id",
                "reddit",
                "test_user",
                "test_subreddit",
                expected_json,
            ),
        )
        mock_conn.commit.assert_called_once()

    def test_trackers_database_mentiondatabasemanager_mark_processed_twitter(
        self, mocker
    ):
        instance = MentionDatabaseManager()
        mock_conn = mocker.MagicMock()
        mock_cursor = mocker.MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        instance.conn = mock_conn

        test_data = {
            "suggester": "test_user",
            "tweet_author": "test_tweeter",
        }

        instance.mark_processed("test_item_id", "twitter", test_data)

        expected_json = json.dumps(test_data)
        mock_cursor.execute.assert_called_once_with(
            """INSERT INTO processed_mentions 
               (item_id, platform, suggester, context_field, raw_data) 
               VALUES (?, ?, ?, ?, ?)""",
            (
                "test_item_id",
                "twitter",
                "test_user",
                "test_tweeter",
                expected_json,
            ),
        )
        mock_conn.commit.assert_called_once()

    def test_trackers_database_mentiondatabasemanager_mark_processed_telegram(
        self, mocker
    ):
        instance = MentionDatabaseManager()
        mock_conn = mocker.MagicMock()
        mock_cursor = mocker.MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        instance.conn = mock_conn

        test_data = {
            "suggester": "test_user",
            "telegram_chat": "test_chat",
        }

        instance.mark_processed("test_item_id", "telegram", test_data)

        expected_json = json.dumps(test_data)
        mock_cursor.execute.assert_called_once_with(
            """INSERT INTO processed_mentions 
               (item_id, platform, suggester, context_field, raw_data) 
               VALUES (?, ?, ?, ?, ?)""",
            (
                "test_item_id",
                "telegram",
                "test_user",
                "test_chat",
                expected_json,
            ),
        )
        mock_conn.commit.assert_called_once()

    def test_trackers_database_mentiondatabasemanager_mark_processed_unknown_platform(
        self, mocker
    ):
        instance = MentionDatabaseManager()
        mock_conn = mocker.MagicMock()
        mock_cursor = mocker.MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        instance.conn = mock_conn

        test_data = {
            "suggester": "test_user",
            "some_field": "some_value",
        }

        instance.mark_processed("test_item_id", "unknown_platform", test_data)

        expected_json = json.dumps(test_data)
        mock_cursor.execute.assert_called_once_with(
            """INSERT INTO processed_mentions 
               (item_id, platform, suggester, context_field, raw_data) 
               VALUES (?, ?, ?, ?, ?)""",
            (
                "test_item_id",
                "unknown_platform",
                "test_user",
                None,
                expected_json,
            ),
        )
        mock_conn.commit.assert_called_once()

    def test_trackers_database_mentiondatabasemanager_mark_processed_no_context_field(
        self, mocker
    ):
        instance = MentionDatabaseManager()
        mock_conn = mocker.MagicMock()
        mock_cursor = mocker.MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        instance.conn = mock_conn

        test_data = {
            "suggester": "test_user",
            # No subreddit field for reddit platform
        }

        instance.mark_processed("test_item_id", "reddit", test_data)

        expected_json = json.dumps(test_data)
        mock_cursor.execute.assert_called_once_with(
            """INSERT INTO processed_mentions 
               (item_id, platform, suggester, context_field, raw_data) 
               VALUES (?, ?, ?, ?, ?)""",
            (
                "test_item_id",
                "reddit",
                "test_user",
                None,
                expected_json,
            ),
        )
        mock_conn.commit.assert_called_once()

    # log_action
    def test_trackers_database_mentiondatabasemanager_log_action_success(self, mocker):
        instance = MentionDatabaseManager()
        mock_conn = mocker.MagicMock()
        mock_cursor = mocker.MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        instance.conn = mock_conn

        instance.log_action("test_platform", "test_action", "test_details")

        mock_cursor.execute.assert_called_once_with(
            "INSERT INTO mention_logs (platform, action, details) VALUES (?, ?, ?)",
            ("test_platform", "test_action", "test_details"),
        )
        mock_conn.commit.assert_called_once()

    # cleanup
    def test_trackers_database_mentiondatabasemanager_cleanup_with_connection(
        self, mocker
    ):
        instance = MentionDatabaseManager()
        mock_conn = mocker.MagicMock()
        instance.conn = mock_conn

        instance.cleanup()

        mock_conn.close.assert_called_once()

    def test_trackers_database_mentiondatabasemanager_cleanup_no_connection(
        self, mocker
    ):
        instance = MentionDatabaseManager()
        instance.conn = None

        # Should not raise an exception
        instance.cleanup()
