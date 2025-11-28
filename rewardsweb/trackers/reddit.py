"""Module containing class for tracking mentions on Reddit."""

import asyncio
import time
from datetime import datetime

import praw
from asgiref.sync import sync_to_async

from trackers.base import BaseMentionTracker


class RedditTracker(BaseMentionTracker):
    """Tracker for Reddit mentions across specified subreddits.

    :var RedditTracker.reddit: authenticated Reddit instance
    :type RedditTracker.reddit: :class:`praw.Reddit`
    :var RedditTracker.bot_username: username of the bot account
    :type RedditTracker.bot_username: str
    :var RedditTracker.tracked_subreddits: list of subreddits being monitored
    :type RedditTracker.tracked_subreddits: list
    """

    def __init__(self, parse_message_callback, config, subreddits_to_track):
        """Initialize Reddit tracker.

        :param parse_message_callback: function to call when mention is found
        :type parse_message_callback: callable
        :param config: configuration dictionary for Reddit API
        :type config: dict
        :param subreddits_to_track: list of subreddit names to monitor
        :type subreddits_to_track: list
        """
        super().__init__("reddit", parse_message_callback)

        self.reddit = praw.Reddit(
            client_id=config["client_id"],
            client_secret=config["client_secret"],
            user_agent=config["user_agent"],
            username=config.get("username"),
            password=config.get("password"),
        )

        self.bot_username = (
            self.reddit.user.me().name.lower() if config.get("username") else None
        )
        self.tracked_subreddits = subreddits_to_track

        self.logger.info(
            f"Reddit tracker initialized for {len(subreddits_to_track)} subreddits"
        )
        self.log_action(
            "initialized", f"Tracking {len(subreddits_to_track)} subreddits"
        )

    def extract_mention_data(self, item):
        """Extract standardized data from Reddit item.

        :param item: Reddit comment or submission
        :type item: :class:`praw.models.Comment` or :class:`praw.models.Submission`
        :return: standardized mention data dictionary
        :rtype: dict
        """
        if isinstance(item, praw.models.Comment):
            return self._extract_comment_data(item)

        else:
            return self._extract_submission_data(item)

    def _extract_comment_data(self, comment):
        """Extract data from Reddit comment.

        :param comment: Reddit comment object
        :type comment: :class:`praw.models.Comment`
        :var data: extracted data dictionary
        :type data: dict
        :var parent: parent of the comment (comment or submission)
        :type parent: :class:`praw.models.Comment` or :class:`praw.models.Submission`
        :return: standardized mention data
        :rtype: dict
        """
        parent = comment.parent()
        data = {
            "suggester": comment.author.name if comment.author else "[deleted]",
            "suggestion_url": f"https://reddit.com{comment.permalink}",
            "contribution_url": f"https://reddit.com{parent.permalink}",
            "contributor": parent.author.name if parent.author else "[deleted]",
            "type": "comment",
            "subreddit": comment.subreddit.display_name,
            "content": comment.body if comment.body else "",
            "timestamp": datetime.fromtimestamp(comment.created_utc).isoformat(),
            "item_id": comment.id,
        }
        return data

    def _extract_submission_data(self, submission):
        """Extract data from Reddit submission.

        :param submission: Reddit submission object
        :type submission: :class:`praw.models.Submission`
        :var data: extracted data dictionary
        :type data: dict
        :return: standardized mention data
        :rtype: dict
        """
        data = {
            "suggester": submission.author.name if submission.author else "[deleted]",
            "suggestion_url": f"https://reddit.com{submission.permalink}",
            "contribution_url": f"https://reddit.com{submission.permalink}",
            "contributor": submission.author.name if submission.author else "[deleted]",
            "type": "submission",
            "subreddit": submission.subreddit.display_name,
            "content": submission.body,
            "timestamp": datetime.fromtimestamp(submission.created_utc).isoformat(),
            "item_id": submission.id,
        }
        return data

    async def check_mentions(self):
        """Check for new mentions across all tracked subreddits.

        :var mention_count: number of new mentions found
        :type mention_count: int
        :var subreddit_name: name of current subreddit being checked
        :type subreddit_name: str
        :var subreddit: Reddit subreddit object
        :type subreddit: :class:`praw.models.Subreddit`
        :var comment: comment from subreddit
        :type comment: :class:`praw.models.Comment`
        :var submission: submission from subreddit
        :type submission: :class:`praw.models.Submission`
        :var data: extracted mention data
        :type data: dict
        :return: number of new mentions processed
        :rtype: int
        """
        mention_count = 0

        for subreddit_name in self.tracked_subreddits:
            try:
                self.logger.debug(f"Checking r/{subreddit_name}")
                subreddit = self.reddit.subreddit(subreddit_name)

                # Check comments for username mentions
                async for comment in self.subreddit_comments_async(subreddit, limit=25):
                    if (
                        self.bot_username
                        and f"u/{self.bot_username}" in comment.body.lower()
                        and not await sync_to_async(self.is_processed)(comment.id)
                    ):

                        data = self.extract_mention_data(comment)
                        if await self.process_mention(
                            comment.id, data, f"u/{self.bot_username}"
                        ):
                            mention_count += 1

                # Check submissions for username mentions
                async for submission in self.subreddit_new_async(subreddit, limit=10):
                    if (
                        self.bot_username
                        and f"u/{self.bot_username}" in submission.title.lower()
                        and not await sync_to_async(self.is_processed)(submission.id)
                    ):

                        data = self.extract_mention_data(submission)
                        if await self.process_mention(
                            submission.id, data, f"u/{self.bot_username}"
                        ):
                            mention_count += 1

                # Small delay between subreddit checks
                await asyncio.sleep(1)

            except Exception as e:
                self.logger.error(f"Error checking r/{subreddit_name}: {e}")
                await self.log_action(
                    "subreddit_check_error",
                    f"Subreddit: {subreddit_name}, Error: {str(e)}",
                )

        return mention_count

    def run(self, poll_interval_minutes=30, max_iterations=None):
        """Run Reddit mentions tracker.

        Uses the shared base tracker loop for polling and processing mentions.

        :param poll_interval_minutes: how often to check for mentions
        :type poll_interval_minutes: int or float
        :param max_iterations: maximum number of polls before stopping
                            (``None`` for infinite loop)
        :type max_iterations: int or None
        """
        # To run the async check_mentions in a sync method, we need an event loop
        async def _run_async_check_mentions():
            return await self.check_mentions()

        super().run(
            poll_interval_minutes=poll_interval_minutes,
            max_iterations=max_iterations,
            check_mentions_callable=_run_async_check_mentions,
        )

    # Helper async iterators for praw
    @sync_to_async
    def subreddit_comments_async(self, subreddit, limit):
        return list(subreddit.comments(limit=limit))

    @sync_to_async
    def subreddit_new_async(self, subreddit, limit):
        return list(subreddit.new(limit=limit))
