"""Module containing class for tracking mentions on X using TwitterAPI.io."""

from datetime import datetime

from trackers.base import BaseMentionTracker


class TwitterapiioTracker(BaseMentionTracker):
    """Tracker for Twitter mentions of the bot account.

    :var TwitterapiioTracker.client: authenticated Twitter client
    :type TwitterapiioTracker.client: :class:`tweepy.Client`
    :var TwitterapiioTracker.bot_user: bot user information from Twitter
    :type TwitterapiioTracker.bot_user: :class:`tweepy.models.User`
    :var TwitterapiioTracker.bot_user_id: ID of the bot user
    :type TwitterapiioTracker.bot_user_id: str
    """

    def __init__(self, parse_message_callback, config):
        """Initialize Twitter tracker.

        :param parse_message_callback: function to call when mention is found
        :type parse_message_callback: callable
        :param config: configuration dictionary for X API
        :type config: dict
        :var client: authenticated Twitter client
        :type client: :class:`tweepy.Client`
        :var bot_user: bot user information from Twitter
        :type bot_user: :class:`tweepy.models.User`
        :var bot_user_id: ID of the bot user
        :type bot_user_id: str
        """
        super().__init__("twitterapiio", parse_message_callback)
        self.api_key = config["api_key"]
        self.target_handle = config["target_handle"]
        self.batch_size = config["batch_size"]

        self.logger.info("TwitterAPI.io tracker initialized")
        self.log_action(
            "initialized", f"Tracking mentions for handle: {self.target_handle}"
        )

    def _get_original_tweet_info(self, referenced_tweet_id):
        """Get original tweet information for reply mentions.

        :param referenced_tweet_id: ID of the referenced tweet
        :type referenced_tweet_id: str
        :var original_tweet: response from Twitter API for the referenced tweet
        :type original_tweet: :class:`tweepy.models.Response`
        :var contribution_url: URL to the original tweet
        :type contribution_url: str
        :var contributor: username of the original tweet author
        :type contributor: str
        :var original_user_map: mapping of user IDs to user objects
        :type original_user_map: dict
        :var author: user object of the original tweet author
        :type author: :class:`tweepy.models.User`
        :return: tuple of (contribution_url, contributor_username)
        :rtype: tuple
        """
        try:
            original_tweet = self.client.get_tweet(
                referenced_tweet_id,
                tweet_fields=["created_at", "author_id", "text"],
                expansions=["author_id"],
            )

            if not original_tweet.data:
                return "", ""

            contribution_url = (
                f"https://twitter.com/i/web/status/{original_tweet.data.id}"
            )

            contributor = ""
            if original_tweet.includes and "users" in original_tweet.includes:
                users = original_tweet.includes["users"]
                original_user_map = {u.id: u.username for u in users}
                author_id = original_tweet.data.author_id
                contributor = original_user_map.get(author_id, "")

            return contribution_url, contributor

        except Exception as e:
            self.logger.warning(
                f"Failed to get original tweet {referenced_tweet_id}: {e}"
            )
            return "", ""

    def _extract_reply_mention_data(self, tweet, user_map):
        """Extract data for reply mentions.

        :param tweet: Twitter tweet object
        :type tweet: :class:`tweepy.models.Tweet`
        :param user_map: mapping of user IDs to usernames
        :type user_map: dict
        :var contribution_url: URL to the contribution tweet
        :type contribution_url: str
        :var contributor: username of the contributor
        :type contributor: str
        :var ref: referenced tweet object
        :type ref: :class:`tweepy.models.ReferencedTweet`
        :return: tuple of (contribution_url, contributor)
        :rtype: tuple
        """
        contribution_url, contributor = "", ""

        if tweet.referenced_tweets:
            for ref in tweet.referenced_tweets:
                if ref.type == "replied_to":
                    contribution_url, contributor = self._get_original_tweet_info(
                        ref.id
                    )
                    break

        return contribution_url, contributor

    def _get_content_preview(self, tweet):
        """Safely get content preview from tweet text.

        :param tweet: Twitter tweet object
        :type tweet: :class:`tweepy.models.Tweet`
        :return: content preview string
        :rtype: str
        """
        if hasattr(tweet, "text") and tweet.text:
            return tweet.text[:200]

        return ""

    def _get_timestamp(self, tweet):
        """Safely get timestamp from tweet.

        :param tweet: Twitter tweet object
        :type tweet: :class:`tweepy.models.Tweet`
        :return: ISO format timestamp string
        :rtype: str
        """
        if hasattr(tweet, "created_at") and tweet.created_at:
            return tweet.created_at.isoformat()

        return datetime.now().isoformat()

    def extract_mention_data(self, tweet, user_map):
        """Extract standardized data from Twitter mention.

        :param tweet: Twitter tweet object
        :type tweet: :class:`tweepy.models.Tweet`
        :param user_map: mapping of user IDs to usernames
        :type user_map: dict
        :var suggester_username: username of the user who mentioned the bot
        :type suggester_username: str
        :var contribution_url: URL to the contribution tweet
        :type contribution_url: str
        :var contributor: username of the contributor
        :type contributor: str
        :var suggestion_url: URL to the suggestion tweet
        :type suggestion_url: str
        :var data: extracted data dictionary
        :type data: dict
        :return: standardized mention data
        :rtype: dict
        """
        # Get suggester username from user_map
        suggester_username = user_map.get(tweet.author_id, "")

        # Handle reply mentions
        contribution_url, contributor = self._extract_reply_mention_data(
            tweet, user_map
        )

        # If not a reply, use current tweet as contribution
        if not contribution_url:
            contribution_url = f"https://twitter.com/i/web/status/{tweet.id}"
            contributor = suggester_username

        suggestion_url = f"https://twitter.com/i/web/status/{tweet.id}"

        data = {
            "suggester": suggester_username,
            "suggestion_url": suggestion_url,
            "contribution_url": contribution_url,
            "contributor": contributor or suggester_username,
            "type": "tweet",
            "content_preview": self._get_content_preview(tweet),
            "timestamp": self._get_timestamp(tweet),
            "item_id": tweet.id,
        }

        return data

    def check_mentions(self):
        """Check for new mentions on Twitter.

        :var mention_count: number of new mentions found
        :type mention_count: int
        :var mentions: recent mentions from Twitter API
        :type mentions: :class:`tweepy.models.Response`
        :var user_map: mapping of user IDs to usernames from API response
        :type user_map: dict
        :var tweet: individual tweet from mentions
        :type tweet: :class:`tweepy.models.Tweet`
        :var data: extracted mention data
        :type data: dict
        :return: number of new mentions processed
        :rtype: int
        """
        mention_count = 0

        try:
            # Get recent mentions
            mentions = self.client.get_users_mentions(
                self.bot_user_id,
                tweet_fields=[
                    "created_at",
                    "conversation_id",
                    "author_id",
                    "text",
                    "referenced_tweets",
                ],
                expansions=["author_id"],
                max_results=20,
            )

            if mentions.data:
                user_map = {
                    u.id: u.username for u in mentions.includes.get("users", [])
                }

                for tweet in mentions.data:
                    if not self.is_processed(tweet.id):
                        data = self.extract_mention_data(tweet, user_map)
                        if self.process_mention(tweet.id, data):
                            mention_count += 1

            self.log_action("mentions_checked", f"Found {mention_count} new mentions")

        except Exception as e:
            self.logger.error(f"Error checking Twitter mentions: {e}")
            self.log_action("twitter_check_error", f"Error: {str(e)}")

        return mention_count

    def run(self, poll_interval_minutes=15, max_iterations=None):
        """Run Twitter mentions tracker.

        Uses the shared base tracker loop for polling and processing mentions.

        :param poll_interval_minutes: how often to check for mentions
        :type poll_interval_minutes: int or float
        :param max_iterations: maximum number of polls before stopping
                            (``None`` for infinite loop)
        :type max_iterations: int or None
        """
        super().run(
            poll_interval_minutes=poll_interval_minutes,
            max_iterations=max_iterations,
        )
