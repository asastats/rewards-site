"""Testing module for :py:mod:`trackers.reddit` module."""

import praw
import pytest

from trackers.base import BaseMentionTracker
from trackers.reddit import RedditTracker


@pytest.mark.django_db
class TestTrackersReddit:
    """Testing class for :class:`trackers.reddit.RedditTracker`."""

    def test_trackers_reddit_reddittracker_is_subclass_of_basementiontracker(self):
        assert issubclass(RedditTracker, BaseMentionTracker)

    # __init__
    def test_trackers_reddittracker_init_success(
        self, mocker, reddit_config, reddit_subreddits
    ):
        # Mock praw.Reddit to prevent actual API calls
        mock_reddit = mocker.patch("trackers.reddit.praw.Reddit")
        mock_user = mocker.MagicMock()
        mock_user.name = "test_bot"
        mock_reddit.return_value.user.me.return_value = mock_user
        # Create instance - this will call the real __init__ but with mocked praw.Reddit
        instance = RedditTracker(lambda x: None, reddit_config, reddit_subreddits)
        mock_reddit.assert_called_once_with(
            client_id="test_client_id",
            client_secret="test_client_secret",
            user_agent="test_user_agent",
            username="test_username",
            password="test_password",
        )
        assert instance.bot_username == "test_bot"
        assert instance.tracked_subreddits == reddit_subreddits

    def test_trackers_reddittracker_init_no_username(self, mocker, reddit_subreddits):
        # Mock praw.Reddit to prevent actual API calls
        mocker.patch("trackers.reddit.praw.Reddit")
        test_config = {
            "client_id": "test_client_id",
            "client_secret": "test_client_secret",
            "user_agent": "test_user_agent",
            # No username/password
        }
        # Create instance
        instance = RedditTracker(lambda x: None, test_config, reddit_subreddits)
        assert instance.bot_username is None

    # extract_mention_data
    def test_trackers_reddittracker_extract_comment_data_functionality_for_ccomment(
        self, mocker, reddit_config, reddit_subreddits
    ):
        # Mock praw.Reddit to prevent actual API calls
        mocker.patch("trackers.reddit.praw.Reddit")
        # Create instance
        instance = RedditTracker(lambda x: None, reddit_config, reddit_subreddits)
        mock_comment = mocker.MagicMock(spec=praw.models.Comment)
        mock_author = mocker.MagicMock()
        mock_author.name = "test_user"
        mock_comment.author = mock_author
        mock_comment.permalink = "/r/test/comments/123"
        mock_comment.body = "Test comment body"
        mock_comment.created_utc = 1609459200  # 2021-01-01
        mock_comment.id = "comment123"
        mock_subreddit = mocker.MagicMock()
        mock_subreddit.display_name = "test"
        mock_comment.subreddit = mock_subreddit
        mock_parent_comment = mocker.MagicMock(spec=praw.models.Comment)
        mock_parent_author = mocker.MagicMock()
        mock_parent_author.name = "parent_user"
        mock_parent_comment.author = mock_parent_author
        mock_parent_comment.permalink = "/r/test/comments/122"
        mock_parent_comment.body = "This is the parent comment."
        mock_comment.parent.return_value = mock_parent_comment
        result = instance._extract_comment_data(mock_comment)
        assert result["suggester"] == "test_user"
        assert result["suggestion_url"] == "https://reddit.com/r/test/comments/123"
        assert result["contribution_url"] == "https://reddit.com/r/test/comments/122"
        assert result["contributor"] == "parent_user"
        assert result["type"] == "comment"
        assert result["subreddit"] == "test"
        assert result["content"] == "Test comment body"
        assert result["contribution"] == "This is the parent comment."

    def test_trackers_reddittracker_extract_comment_data_functionality_for_submission(
        self, mocker, reddit_config, reddit_subreddits
    ):
        # Mock praw.Reddit to prevent actual API calls
        mocker.patch("trackers.reddit.praw.Reddit")
        # Create instance
        instance = RedditTracker(lambda x: None, reddit_config, reddit_subreddits)
        mock_comment = mocker.MagicMock(spec=praw.models.Comment)
        mock_author = mocker.MagicMock()
        mock_author.name = "test_user"
        mock_comment.author = mock_author
        mock_comment.permalink = "/r/test/comments/123"
        mock_comment.body = "Test comment body"
        mock_comment.created_utc = 1609459200  # 2021-01-01
        mock_comment.id = "comment123"
        mock_subreddit = mocker.MagicMock()
        mock_subreddit.display_name = "test"
        mock_comment.subreddit = mock_subreddit
        mock_parent_submission = mocker.MagicMock(spec=praw.models.Submission)
        mock_parent_author = mocker.MagicMock()
        mock_parent_author.name = "parent_user"
        mock_parent_submission.author = mock_parent_author
        mock_parent_submission.permalink = "/r/test/comments/122"
        mock_parent_submission.body = "This is the parent comment."
        mock_parent_submission.selftext = "Post text"
        mock_comment.parent.return_value = mock_parent_submission
        result = instance._extract_comment_data(mock_comment)
        assert result["suggester"] == "test_user"
        assert result["suggestion_url"] == "https://reddit.com/r/test/comments/123"
        assert result["contribution_url"] == "https://reddit.com/r/test/comments/122"
        assert result["contributor"] == "parent_user"
        assert result["type"] == "comment"
        assert result["subreddit"] == "test"
        assert result["content"] == "Test comment body"
        assert result["contribution"] == "Post text"

    def test_trackers_reddittracker_extract_submission_data(
        self, mocker, reddit_config, reddit_subreddits
    ):
        # Mock praw.Reddit to prevent actual API calls
        mocker.patch("trackers.reddit.praw.Reddit")
        # Create instance
        instance = RedditTracker(lambda x: None, reddit_config, reddit_subreddits)
        mock_submission = mocker.MagicMock(spec=praw.models.Submission)
        mock_author = mocker.MagicMock()
        mock_author.name = "test_user"
        mock_submission.author = mock_author
        mock_submission.permalink = "/r/test/comments/123"
        mock_submission.title = "Test submission title"
        mock_submission.selftext = "Test submission selftext"
        mock_submission.created_utc = 1609459200
        mock_submission.id = "submission123"
        mock_subreddit = mocker.MagicMock()
        mock_subreddit.display_name = "test"
        mock_submission.subreddit = mock_subreddit
        result = instance._extract_submission_data(mock_submission)
        assert result["suggester"] == "test_user"
        assert result["suggestion_url"] == "https://reddit.com/r/test/comments/123"
        assert result["contribution_url"] == "https://reddit.com/r/test/comments/123"
        assert result["contributor"] == "test_user"
        assert result["type"] == "submission"
        assert result["subreddit"] == "test"
        assert result["content"] == "Test submission title"
        assert result["contribution"] == "Test submission selftext"

    # check_mentions
    def test_trackers_reddittracker_check_mentions_finds_comments(
        self, mocker, reddit_config, reddit_subreddits
    ):
        # Mock praw.Reddit to prevent actual API calls
        mock_reddit = mocker.patch("trackers.reddit.praw.Reddit")
        mock_user = mocker.MagicMock()
        mock_user.name = "test_bot"
        mock_reddit.return_value.user.me.return_value = mock_user
        # Create instance
        instance = RedditTracker(lambda x: None, reddit_config, reddit_subreddits)
        # Mock only one subreddit to avoid multiple calls
        mock_subreddit = mocker.MagicMock()
        mock_reddit.return_value.subreddit.return_value = mock_subreddit
        mock_comment = mocker.MagicMock()
        mock_comment.body = "Hello u/test_bot, check this out!"
        mock_comment.id = "comment123"
        # Only return comments for one subreddit
        mock_subreddit.comments.return_value = [mock_comment]
        mock_subreddit.new.return_value = []  # No submissions
        mock_process_mention = mocker.patch.object(instance, "process_mention")
        mock_process_mention.return_value = True
        mock_is_processed = mocker.patch.object(instance, "is_processed")
        mock_is_processed.return_value = False
        # Track only one subreddit for this test
        instance.tracked_subreddits = ["python"]
        result = instance.check_mentions()
        assert result == 1
        mock_process_mention.assert_called_once()

    def test_trackers_reddittracker_check_mentions_finds_submissions(
        self, mocker, reddit_config, reddit_subreddits
    ):
        # Mock praw.Reddit to prevent actual API calls
        mock_reddit = mocker.patch("trackers.reddit.praw.Reddit")
        mock_user = mocker.MagicMock()
        mock_user.name = "test_bot"
        mock_reddit.return_value.user.me.return_value = mock_user
        # Create instance
        instance = RedditTracker(lambda x: None, reddit_config, reddit_subreddits)
        mock_subreddit = mocker.MagicMock()
        mock_reddit.return_value.subreddit.return_value = mock_subreddit
        mock_submission = mocker.MagicMock()
        mock_submission.title = "u/test_bot what do you think?"
        mock_submission.id = "submission123"
        mock_subreddit.comments.return_value = []  # No comments
        mock_subreddit.new.return_value = [mock_submission]
        mock_process_mention = mocker.patch.object(instance, "process_mention")
        mock_process_mention.return_value = True
        mock_is_processed = mocker.patch.object(instance, "is_processed")
        mock_is_processed.return_value = False
        # Track only one subreddit for this test
        instance.tracked_subreddits = ["python"]
        result = instance.check_mentions()
        assert result == 1
        mock_process_mention.assert_called_once()

    def test_trackers_reddittracker_check_mentions_skips_processed(
        self, mocker, reddit_config, reddit_subreddits
    ):
        # Mock praw.Reddit to prevent actual API calls
        mock_reddit = mocker.patch("trackers.reddit.praw.Reddit")
        mock_user = mocker.MagicMock()
        mock_user.name = "test_bot"
        mock_reddit.return_value.user.me.return_value = mock_user
        # Create instance
        instance = RedditTracker(lambda x: None, reddit_config, reddit_subreddits)
        mock_subreddit = mocker.MagicMock()
        mock_reddit.return_value.subreddit.return_value = mock_subreddit
        mock_comment = mocker.MagicMock()
        mock_comment.body = "Hello u/test_bot!"
        mock_comment.id = "comment123"
        mock_subreddit.comments.return_value = [mock_comment]
        mock_subreddit.new.return_value = []
        mock_process_mention = mocker.patch.object(instance, "process_mention")
        mock_is_processed = mocker.patch.object(instance, "is_processed")
        mock_is_processed.return_value = True  # Already processed
        # Track only one subreddit for this test
        instance.tracked_subreddits = ["python"]
        result = instance.check_mentions()
        assert result == 0
        mock_process_mention.assert_not_called()

    def test_trackers_reddittracker_check_mentions_handles_exception(
        self, mocker, reddit_config, reddit_subreddits
    ):
        # Mock praw.Reddit to prevent actual API calls
        mock_reddit = mocker.patch("trackers.reddit.praw.Reddit")
        mock_user = mocker.MagicMock()
        mock_user.name = "test_bot"
        mock_reddit.return_value.user.me.return_value = mock_user
        # Create instance
        instance = RedditTracker(lambda x: None, reddit_config, reddit_subreddits)
        mock_reddit.return_value.subreddit.side_effect = Exception("API error")
        mock_log_action = mocker.patch.object(instance, "log_action")
        # Mock the logger.error method
        mock_logger_error = mocker.patch.object(instance.logger, "error")
        result = instance.check_mentions()
        assert result == 0
        # Should be called once for each subreddit (2 subreddits in the fixture)
        assert mock_logger_error.call_count == 2
        mock_log_action.assert_called()

    # run
    def test_trackers_reddittracker_run_wrapper_calls_base_run(
        self, mocker, reddit_config, reddit_subreddits
    ):
        # Patch BaseMentionTracker.run so no real loop runs
        mocked_base_run = mocker.patch("trackers.reddit.BaseMentionTracker.run")
        # Mock praw.Reddit to prevent actual API calls
        mock_reddit = mocker.patch("trackers.reddit.praw.Reddit")
        mock_user = mocker.MagicMock()
        mock_user.name = "test_bot"
        mock_reddit.return_value.user.me.return_value = mock_user
        # Create instance (MessageParser.parse mocked out)
        tracker = RedditTracker(
            parse_message_callback=lambda x: x,
            config=reddit_config,
            subreddits_to_track=reddit_subreddits,
        )
        # Call the wrapper
        tracker.run(poll_interval_minutes=10, max_iterations=5)
        # Ensure BaseMentionTracker.run was called once with correct args
        mocked_base_run.assert_called_once_with(
            poll_interval_minutes=10,
            max_iterations=5,
        )

    # # extract_mention_data
    def test_trackers_reddittracker_extract_mention_data_comment(
        self, mocker, reddit_config, reddit_subreddits
    ):
        """Test extract_mention_data with Comment instance (isinstance condition)."""
        # Mock praw.Reddit to prevent actual API calls
        mocker.patch("trackers.reddit.praw.Reddit")
        # Create instance
        instance = RedditTracker(lambda x: None, reddit_config, reddit_subreddits)
        mock_comment = mocker.MagicMock(spec=praw.models.Comment)
        # Mock _extract_comment_data to verify it's called
        mock_extract_comment = mocker.patch.object(instance, "_extract_comment_data")
        mock_extract_comment.return_value = {"type": "comment"}
        result = instance.extract_mention_data(mock_comment)
        # Verify _extract_comment_data was called for Comment instance
        mock_extract_comment.assert_called_once_with(mock_comment)
        assert result == {"type": "comment"}

    def test_trackers_reddittracker_extract_comment_data_parent_submission(
        self, mocker, reddit_config, reddit_subreddits
    ):
        """Test _extract_comment_data with parent as Submission (else branch)."""
        # Mock praw.Reddit to prevent actual API calls
        mocker.patch("trackers.reddit.praw.Reddit")
        # Create instance
        instance = RedditTracker(lambda x: None, reddit_config, reddit_subreddits)
        mock_comment = mocker.MagicMock(spec=praw.models.Comment)
        mock_author = mocker.MagicMock()
        mock_author.name = "test_user"
        mock_comment.author = mock_author
        mock_comment.permalink = "/r/test/comments/123"
        mock_comment.body = "Test comment body"
        mock_comment.created_utc = 1609459200
        mock_comment.id = "comment123"
        mock_subreddit = mocker.MagicMock()
        mock_subreddit.display_name = "test"
        mock_comment.subreddit = mock_subreddit
        # Parent is a Submission (not Comment) - testing else branch
        mock_parent_submission = mocker.MagicMock(spec=praw.models.Submission)
        mock_parent_author = mocker.MagicMock()
        mock_parent_author.name = "parent_author"
        mock_parent_submission.author = mock_parent_author
        mock_parent_submission.permalink = "/r/test/comments/122"
        mock_parent_submission.selftext = "This is the parent submission."
        mock_comment.parent.return_value = mock_parent_submission
        result = instance._extract_comment_data(mock_comment)
        # Verify else branch was taken (parent is Submission)
        assert result["contribution_url"] == "https://reddit.com/r/test/comments/122"
        assert result["contributor"] == "parent_author"
        assert result["contribution"] == "This is the parent submission."

    def test_trackers_reddittracker_check_mentions_process_mention_true(
        self, mocker, reddit_config, reddit_subreddits
    ):
        """Test check_mentions when process_mention returns True."""
        # Mock praw.Reddit to prevent actual API calls
        mock_reddit = mocker.patch("trackers.reddit.praw.Reddit")
        mock_user = mocker.MagicMock()
        mock_user.name = "test_bot"
        mock_reddit.return_value.user.me.return_value = mock_user
        # Create instance
        instance = RedditTracker(lambda x: None, reddit_config, reddit_subreddits)
        mock_subreddit = mocker.MagicMock()
        mock_reddit.return_value.subreddit.return_value = mock_subreddit
        mock_comment = mocker.MagicMock()
        mock_comment.body = "Hello u/test_bot!"
        mock_comment.id = "comment123"
        mock_subreddit.comments.return_value = [mock_comment]
        mock_subreddit.new.return_value = []
        mock_process_mention = mocker.patch.object(instance, "process_mention")
        mock_process_mention.return_value = True  # process_mention returns True
        mock_is_processed = mocker.patch.object(instance, "is_processed")
        mock_is_processed.return_value = False
        # Track only one subreddit for this test
        instance.tracked_subreddits = ["python"]
        result = instance.check_mentions()
        # Verify mention_count was incremented when process_mention returned True
        assert result == 1
        mock_process_mention.assert_called_once()

    def test_trackers_reddittracker_check_mentions_submission_condition_true(
        self, mocker, reddit_config, reddit_subreddits
    ):
        """Test check_mentions submission condition with bot_username and mention in title."""
        # Mock praw.Reddit to prevent actual API calls
        mock_reddit = mocker.patch("trackers.reddit.praw.Reddit")
        mock_user = mocker.MagicMock()
        mock_user.name = "test_bot"
        mock_reddit.return_value.user.me.return_value = mock_user
        # Create instance
        instance = RedditTracker(lambda x: None, reddit_config, reddit_subreddits)
        instance.bot_username = "test_bot"  # Ensure bot_username is set
        mock_subreddit = mocker.MagicMock()
        mock_reddit.return_value.subreddit.return_value = mock_subreddit
        mock_submission = mocker.MagicMock()
        mock_submission.title = "u/test_bot what do you think?"  # Contains bot username
        mock_submission.id = "submission123"
        mock_subreddit.comments.return_value = []
        mock_subreddit.new.return_value = [mock_submission]
        mock_process_mention = mocker.patch.object(instance, "process_mention")
        mock_process_mention.return_value = True
        mock_is_processed = mocker.patch.object(instance, "is_processed")
        mock_is_processed.return_value = False  # Not processed
        # Track only one subreddit for this test
        instance.tracked_subreddits = ["python"]
        result = instance.check_mentions()
        # Verify submission condition was met and processed
        assert result == 1
        mock_process_mention.assert_called_once()

    def test_trackers_reddittracker_check_mentions_submission_process_true(
        self, mocker, reddit_config, reddit_subreddits
    ):
        """Test check_mentions when submission process_mention returns True."""
        # Mock praw.Reddit to prevent actual API calls
        mock_reddit = mocker.patch("trackers.reddit.praw.Reddit")
        mock_user = mocker.MagicMock()
        mock_user.name = "test_bot"
        mock_reddit.return_value.user.me.return_value = mock_user
        # Create instance
        instance = RedditTracker(lambda x: None, reddit_config, reddit_subreddits)
        mock_subreddit = mocker.MagicMock()
        mock_reddit.return_value.subreddit.return_value = mock_subreddit
        mock_submission = mocker.MagicMock()
        mock_submission.title = "u/test_bot help please"
        mock_submission.id = "submission123"
        mock_subreddit.comments.return_value = []
        mock_subreddit.new.return_value = [mock_submission]
        mock_process_mention = mocker.patch.object(instance, "process_mention")
        mock_process_mention.return_value = True  # process_mention returns True
        mock_is_processed = mocker.patch.object(instance, "is_processed")
        mock_is_processed.return_value = False
        # Track only one subreddit for this test
        instance.tracked_subreddits = ["python"]
        result = instance.check_mentions()
        # Verify mention_count was incremented when process_mention returned True
        assert result == 1
        mock_process_mention.assert_called_once()

    def test_trackers_reddittracker_run_mentions_found_logging(
        self, mocker, reddit_config, reddit_subreddits
    ):
        """Test run method when mentions_found > 0 (logging branch)."""
        # Mock praw.Reddit to prevent actual API calls
        mock_reddit = mocker.patch("trackers.reddit.praw.Reddit")
        mock_user = mocker.MagicMock()
        mock_user.name = "test_bot"
        mock_reddit.return_value.user.me.return_value = mock_user
        # Create instance
        instance = RedditTracker(lambda x: None, reddit_config, reddit_subreddits)
        # Mock check_mentions to return positive number
        mock_check_mentions = mocker.patch.object(instance, "check_mentions")
        mock_check_mentions.return_value = 3  # mentions_found > 0
        mocker.patch("time.sleep", side_effect=StopIteration)
        mock_logger_info = mocker.patch.object(instance.logger, "info")
        # Run one iteration
        try:
            instance.run(poll_interval_minutes=0.1, max_iterations=1)
        except StopIteration:
            pass
        # Verify logger.info was called for mentions_found > 0
        mock_logger_info.assert_any_call("Found 3 new mentions")

    def test_trackers_reddittracker_check_mentions_comment_process_mention_false(
        self, mocker, reddit_config, reddit_subreddits
    ):
        """Test check_mentions when process_mention returns False for comment."""
        # Mock praw.Reddit to prevent actual API calls
        mock_reddit = mocker.patch("trackers.reddit.praw.Reddit")
        mock_user = mocker.MagicMock()
        mock_user.name = "test_bot"
        mock_reddit.return_value.user.me.return_value = mock_user
        # Create instance
        instance = RedditTracker(lambda x: None, reddit_config, reddit_subreddits)
        mock_subreddit = mocker.MagicMock()
        mock_reddit.return_value.subreddit.return_value = mock_subreddit
        mock_comment = mocker.MagicMock()
        mock_comment.body = "Hello u/test_bot, check this out!"
        mock_comment.id = "comment123"
        mock_subreddit.comments.return_value = [mock_comment]
        mock_subreddit.new.return_value = []  # No submissions
        mock_process_mention = mocker.patch.object(instance, "process_mention")
        mock_process_mention.return_value = False  # process_mention returns False
        mock_is_processed = mocker.patch.object(instance, "is_processed")
        mock_is_processed.return_value = False
        # Track only one subreddit for this test
        instance.tracked_subreddits = ["python"]
        result = instance.check_mentions()
        # Should return 0 because process_mention returned False
        assert result == 0
        mock_process_mention.assert_called_once()  # Was called but returned False

    def test_trackers_reddittracker_check_mentions_submission_condition_not_met(
        self, mocker, reddit_config, reddit_subreddits
    ):
        """Test check_mentions when submission condition is not met (already processed)."""
        # Mock praw.Reddit to prevent actual API calls
        mock_reddit = mocker.patch("trackers.reddit.praw.Reddit")
        mock_user = mocker.MagicMock()
        mock_user.name = "test_bot"
        mock_reddit.return_value.user.me.return_value = mock_user
        # Create instance
        instance = RedditTracker(lambda x: None, reddit_config, reddit_subreddits)
        mock_subreddit = mocker.MagicMock()
        mock_reddit.return_value.subreddit.return_value = mock_subreddit
        mock_submission = mocker.MagicMock()
        mock_submission.title = "u/test_bot what do you think?"
        mock_submission.id = "submission123"
        mock_subreddit.comments.return_value = []  # No comments
        mock_subreddit.new.return_value = [mock_submission]
        mock_process_mention = mocker.patch.object(instance, "process_mention")
        mock_is_processed = mocker.patch.object(instance, "is_processed")
        mock_is_processed.return_value = True  # Already processed
        # Track only one subreddit for this test
        instance.tracked_subreddits = ["python"]
        result = instance.check_mentions()
        # Should find 0 mentions because submission is already processed
        assert result == 0
        mock_process_mention.assert_not_called()  # Should not be called
        mock_is_processed.assert_called_once_with("submission123")

    def test_trackers_reddittracker_check_mentions_submission_process_mention_false(
        self, mocker, reddit_config, reddit_subreddits
    ):
        """Test check_mentions when process_mention returns False for submission."""
        # Mock praw.Reddit to prevent actual API calls
        mock_reddit = mocker.patch("trackers.reddit.praw.Reddit")
        mock_user = mocker.MagicMock()
        mock_user.name = "test_bot"
        mock_reddit.return_value.user.me.return_value = mock_user
        # Create instance
        instance = RedditTracker(lambda x: None, reddit_config, reddit_subreddits)
        mock_subreddit = mocker.MagicMock()
        mock_reddit.return_value.subreddit.return_value = mock_subreddit
        mock_submission = mocker.MagicMock()
        mock_submission.title = "u/test_bot help please"
        mock_submission.id = "submission123"
        mock_subreddit.comments.return_value = []
        mock_subreddit.new.return_value = [mock_submission]
        mock_process_mention = mocker.patch.object(instance, "process_mention")
        mock_process_mention.return_value = False  # process_mention returns False
        mock_is_processed = mocker.patch.object(instance, "is_processed")
        mock_is_processed.return_value = False
        # Track only one subreddit for this test
        instance.tracked_subreddits = ["python"]
        result = instance.check_mentions()
        # Should return 0 because process_mention returned False
        assert result == 0
        mock_process_mention.assert_called_once()  # Was called but returned False

    def test_trackers_reddittracker_check_mentions_comment_condition_not_met(
        self, mocker, reddit_config, reddit_subreddits
    ):
        """Test check_mentions when comment condition is not met (already processed)."""
        # Mock praw.Reddit to prevent actual API calls
        mock_reddit = mocker.patch("trackers.reddit.praw.Reddit")
        mock_user = mocker.MagicMock()
        mock_user.name = "test_bot"
        mock_reddit.return_value.user.me.return_value = mock_user
        # Create instance
        instance = RedditTracker(lambda x: None, reddit_config, reddit_subreddits)
        mock_subreddit = mocker.MagicMock()
        mock_reddit.return_value.subreddit.return_value = mock_subreddit
        mock_comment = mocker.MagicMock()
        mock_comment.body = "Hello u/test_bot, check this out!"
        mock_comment.id = "comment123"
        mock_subreddit.comments.return_value = [mock_comment]
        mock_subreddit.new.return_value = []  # No submissions
        mock_process_mention = mocker.patch.object(instance, "process_mention")
        mock_is_processed = mocker.patch.object(instance, "is_processed")
        mock_is_processed.return_value = True  # Already processed
        # Track only one subreddit for this test
        instance.tracked_subreddits = ["python"]
        result = instance.check_mentions()
        # Should find 0 mentions because comment is already processed
        assert result == 0
        mock_process_mention.assert_not_called()  # Should not be called
        mock_is_processed.assert_called_once_with("comment123")
