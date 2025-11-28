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
        test_data = {"suggester": "test_user"}
        instance.mark_processed("test_item_id", "reddit", test_data)
        expected_json = json.dumps(test_data)
        mock_cursor.execute.assert_called_once_with(
            """INSERT INTO processed_mentions 
               (item_id, platform, suggester, raw_data) 
               VALUES (?, ?, ?, ?)""",
            ("test_item_id", "reddit", "test_user", expected_json),
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
        test_data = {"suggester": "test_user"}
        instance.mark_processed("test_item_id", "twitter", test_data)
        expected_json = json.dumps(test_data)
        mock_cursor.execute.assert_called_once_with(
            """INSERT INTO processed_mentions 
               (item_id, platform, suggester, raw_data) 
               VALUES (?, ?, ?, ?)""",
            ("test_item_id", "twitter", "test_user", expected_json),
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
        test_data = {"suggester": "test_user"}
        instance.mark_processed("test_item_id", "telegram", test_data)
        expected_json = json.dumps(test_data)
        mock_cursor.execute.assert_called_once_with(
            """INSERT INTO processed_mentions 
               (item_id, platform, suggester, raw_data) 
               VALUES (?, ?, ?, ?)""",
            ("test_item_id", "telegram", "test_user", expected_json),
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
        test_data = {"suggester": "test_user"}
        instance.mark_processed("test_item_id", "unknown_platform", test_data)
        expected_json = json.dumps(test_data)
        mock_cursor.execute.assert_called_once_with(
            """INSERT INTO processed_mentions 
               (item_id, platform, suggester, raw_data) 
               VALUES (?, ?, ?, ?)""",
            ("test_item_id", "unknown_platform", "test_user", expected_json),
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

    # last_processed_timestamp
    def test_trackers_database_mentiondatabasemanager_last_processed_timestamp_found(
        self, mocker
    ):
        instance = MentionDatabaseManager()
        mock_conn = mocker.MagicMock()
        mock_cursor = mocker.MagicMock()
        mock_cursor.fetchone.return_value = (1672531199,)
        mock_conn.cursor.return_value = mock_cursor
        instance.conn = mock_conn
        result = instance.last_processed_timestamp("test_platform")
        assert result == 1672531199
        mock_cursor.execute.assert_called_once_with(
            """SELECT MAX(CAST(json_extract(raw_data, '$.timestamp') AS INTEGER))
               FROM processed_mentions
               WHERE platform = ?""",
            ("test_platform",),
        )

    def test_trackers_database_mentiondatabasemanager_last_processed_timestamp_not_found(
        self, mocker
    ):
        instance = MentionDatabaseManager()
        mock_conn = mocker.MagicMock()
        mock_cursor = mocker.MagicMock()
        mock_cursor.fetchone.return_value = (None,)
        mock_conn.cursor.return_value = mock_cursor
        instance.conn = mock_conn
        result = instance.last_processed_timestamp("test_platform")
        assert result is None
        mock_cursor.execute.assert_called_once_with(
            """SELECT MAX(CAST(json_extract(raw_data, '$.timestamp') AS INTEGER))
               FROM processed_mentions
               WHERE platform = ?""",
            ("test_platform",),
        )

    def test_trackers_database_mentiondatabasemanager_last_processed_timestamp_no_result(
        self, mocker
    ):
        instance = MentionDatabaseManager()
        mock_conn = mocker.MagicMock()
        mock_cursor = mocker.MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn.cursor.return_value = mock_cursor
        instance.conn = mock_conn
        result = instance.last_processed_timestamp("test_platform")
        assert result is None
        mock_cursor.execute.assert_called_once_with(
            """SELECT MAX(CAST(json_extract(raw_data, '$.timestamp') AS INTEGER))
               FROM processed_mentions
               WHERE platform = ?""",
            ("test_platform",),
        )

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


class TestTrackersDatabaseMentionDatabaseManagerGetMentionByUrl:
    """Testing class for :py:meth:`trackers.database.MentionDatabaseManager.mention_raw_data_by_url` method."""

    def setup_method(self):
        """Set up test method with an in-memory database."""
        self.db_manager = MentionDatabaseManager(db_path=":memory:")
        self.db_manager.setup_database()

        # Insert test data
        test_data_1 = {
            "item_id": "1",
            "platform": "twitter",
            "suggester": "user1",
            "suggestion_url": "https://twitter.com/status/1",
            "contribution_url": "https://twitter.com/contrib/1",
            "content": "Tweet content 1",
            "timestamp": 1678886400,
        }
        test_data_2 = {
            "item_id": "2",
            "platform": "reddit",
            "suggester": "user2",
            "suggestion_url": "https://reddit.com/post/2",
            "contribution_url": "https://reddit.com/comment/2",
            "content": "Reddit content 2",
            "timestamp": 1678886500,
        }

        self.db_manager.mark_processed("1", "twitter", test_data_1)
        self.db_manager.mark_processed("2", "reddit", test_data_2)

    def teardown_method(self):
        """Tear down test method by closing the database connection."""
        self.db_manager.cleanup()

    def test_trackers_database_mentiondatabasemanager_mention_raw_data_by_url_suggestion_url(
        self,
    ):
        """Test retrieving a mention by its suggestion_url."""
        url = "https://twitter.com/status/1"
        mention = self.db_manager.mention_raw_data_by_url(url)
        assert mention is not None
        assert mention["item_id"] == "1"
        assert mention["platform"] == "twitter"
        assert mention["content"] == "Tweet content 1"

    def test_trackers_database_mentiondatabasemanager_mention_raw_data_by_url_contribution_url(
        self,
    ):
        """Test retrieving a mention by its contribution_url."""
        url = "https://reddit.com/comment/2"
        mention = self.db_manager.mention_raw_data_by_url(url)
        assert mention is not None
        assert mention["item_id"] == "2"
        assert mention["platform"] == "reddit"
        assert mention["content"] == "Reddit content 2"

    def test_trackers_database_mentiondatabasemanager_mention_raw_data_by_url_not_found(
        self,
    ):
        """Test retrieving a mention for a URL that does not exist."""
        url = "https://nonexistent.com/url"
        mention = self.db_manager.mention_raw_data_by_url(url)
        assert mention is None
