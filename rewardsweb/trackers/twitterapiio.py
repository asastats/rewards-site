"Module containing class for tracking mentions on X using TwitterAPI.io."

import json
from datetime import datetime
from urllib.parse import urlencode

import requests
from asgiref.sync import sync_to_async

from trackers.base import BaseMentionTracker
from trackers.models import Mention

TWITTERAPIIO_BASE_URL = "https://api.twitterapi.io/twitter"


class TwitterapiioTracker(BaseMentionTracker):
    """Tracker for Twitter mentions of a specific account using the TwitterAPI.io service.

    This class handles fetching new mentions, retrieving the parent tweets of replies
    in efficient batches, and saving the timestamp of the last processed mention
    to avoid reprocessing.

    :var TwitterapiioTracker.api_key: API key for the TwitterAPI.io service
    :type TwitterapiioTracker.api_key: str
    :var TwitterapiioTracker.target_handle: Twitter screen name of the account to track
    :type TwitterapiioTracker.target_handle: str
    :var TwitterapiioTracker.batch_size: number of mentions to collect in a batch
    :type TwitterapiioTracker.batch_size: int
    """

    def __init__(self, parse_message_callback, config):
        """Initialize the TwitterapiioTracker instance.

        :param parse_message_callback: function to call when a mention is found
        :type parse_message_callback: callable
        :param config: configuration dictionary for X API
        :type config: dict
        """
        super().__init__("twitterapiio", parse_message_callback)
        self.api_key = config["api_key"]
        self.target_handle = config["target_handle"]
        self.batch_size = config["batch_size"]

        self.logger.info("TwitterAPI.io tracker initialized")
        self.log_action(
            "initialized", f"Tracking mentions for handle: {self.target_handle}"
        )

    @staticmethod
    def _twitter_created_at_to_unix(created_at):
        """Converts Twitter's 'createdAt' string to a Unix timestamp.

        :param created_at: The timestamp string from the Twitter API.
        :type created_at: str
        :return: The Unix timestamp.
        :rtype: int
        :var dt: The datetime object parsed from the string.
        :type dt: :class:`datetime.datetime`
        """
        dt = datetime.strptime(created_at, "%a %b %d %H:%M:%S %z %Y")
        return int(dt.timestamp())

    def _get_tweets_by_ids(self, tweet_ids):
        """Fetch details for multiple tweets by their IDs in a single API call.

        :param tweet_ids: A list of tweet ID strings to fetch.
        :type tweet_ids: list
        :var headers: The request headers, including the API key.
        :type headers: dict
        :var params: The request parameters, containing the comma-separated tweet IDs.
        :type params: dict
        :var response: The HTTP response from the API.
        :type response: :class:`requests.Response`
        :var data: The JSON response data from the API.
        :type data: dict
        :return: A dictionary mapping tweet IDs to their corresponding tweet objects.
        :rtype: dict
        """
        if not tweet_ids:
            return {}

        headers = {"X-API-Key": self.api_key}
        params = {"tweet_ids": ",".join(tweet_ids)}
        encoded_params = urlencode(params, safe=",")
        try:
            response = requests.get(
                f"{TWITTERAPIIO_BASE_URL}/tweets?{encoded_params}", headers=headers
            )
            response.raise_for_status()
            data = response.json()

            if data.get("status") == "success" and data.get("tweets"):
                return {tweet["id"]: tweet for tweet in data["tweets"]}

            else:
                self.logger.warning(
                    f"API Error fetching tweet IDs: {data.get('message')}"
                )
                return {}

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request error fetching tweet IDs: {e}")
            return {}

        except (
            requests.exceptions.RequestException,
            json.JSONDecodeError,
            ValueError,
        ) as e:
            self.logger.error(f"Failed to decode JSON from response: {e}")
            return {}

    def _get_all_mentions(self, since_time=None):
        """Yield Twitter mentions, fetching in batches together with parent tweet.

        This generator fetches mentions from the TwitterAPI.io service, handles
        pagination, and enriches reply mentions with their parent tweet data.

        :param since_time: A Unix timestamp to fetch mentions on or after this time.
        :type since_time: int, optional
        :return: A generator that yields individual mention tweets, potentially with 'parent_tweet' key.
        :rtype: generator
        :var headers: The request headers, including the API key.
        :type headers: dict
        :var params: The request parameters.
        :type params: dict
        :var cursor: The pagination cursor from the API.
        :type cursor: str
        :var mentions_batch: A list to hold the current batch of mentions.
        :type mentions_batch: list
        :var parent_tweet_ids: A list of unique parent tweet IDs from the batch.
        :type parent_tweet_ids: list
        :var parent_tweets: A dictionary mapping parent tweet IDs to tweet objects.
        :type parent_tweets: dict
        """
        headers = {"X-API-Key": self.api_key}
        params = {"userName": self.target_handle}
        if since_time:
            params["sinceTime"] = since_time

        cursor = ""
        mentions_batch = []

        while True:
            params["cursor"] = cursor
            try:
                response = requests.get(
                    f"{TWITTERAPIIO_BASE_URL}/user/mentions",
                    headers=headers,
                    params=params,
                )
                response.raise_for_status()
                data = response.json()

            except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
                self.logger.error(f"An error occurred while fetching mentions: {e}")
                break

            if data.get("status") != "success":
                self.logger.error(f"API Error: {data.get('message', 'Unknown error')}")
                break

            tweets_page = data.get("tweets", [])
            mentions_batch.extend(tweets_page)

            if len(mentions_batch) >= self.batch_size or not data.get("has_next_page"):
                parent_tweet_ids = sorted(
                    list(
                        set(
                            m["inReplyToId"]
                            for m in mentions_batch
                            if m.get("isReply") and m.get("inReplyToId")
                        )
                    )
                )
                parent_tweets = {}
                for i in range(0, len(parent_tweet_ids), self.batch_size):
                    chunk = parent_tweet_ids[i : i + self.batch_size]
                    parent_tweets.update(self._get_tweets_by_ids(chunk))

                for mention in mentions_batch:
                    if mention.get("isReply"):
                        parent_id = mention.get("inReplyToId")
                        if parent_id in parent_tweets:
                            mention["parent_tweet"] = parent_tweets[parent_id]

                    yield mention

                mentions_batch = []

            cursor = data.get("next_cursor", "")
            if not data.get("has_next_page") or not cursor:
                break

    def extract_mention_data(self, mention):
        """Extract relevant data from a mention tweet.

        :param mention: The mention tweet object from the Twitter API.
        :type mention: dict
        :return: A dictionary containing standardized mention data.
        :rtype: dict
        :var tweet_id: The ID of the mention tweet.
        :type tweet_id: str
        :var parent_tweet_url: The URL of the parent tweet, if it exists.
        :type parent_tweet_url: str
        :var contributor_handle: The Twitter handle of the contributor.
        :type contributor_handle: str
        :var contribution: The text content of the parent tweet.
        :type contribution: str
        """
        tweet_id = mention["id"]
        parent_tweet_url = ""
        contributor_handle = mention["author"]["userName"]
        contribution = ""

        if "parent_tweet" in mention:
            parent = mention["parent_tweet"]
            parent_tweet_url = f"https://twitter.com/i/web/status/{parent['id']}"
            contributor_handle = parent["author"]["userName"]
            contribution = parent["text"]

        return {
            "suggester": mention["author"]["userName"],
            "suggestion_url": f"https://twitter.com/i/web/status/{tweet_id}",
            "contribution_url": parent_tweet_url
            or f"https://twitter.com/i/web/status/{tweet_id}",
            "contributor": contributor_handle,
            "type": "tweet",
            "content": mention["text"],
            "contribution": contribution,
            "timestamp": self._twitter_created_at_to_unix(mention["createdAt"]),
            "item_id": tweet_id,
        }

    def check_mentions(self):
        """Check for new Twitter mentions and process them.

        This method fetches new mentions, filters out any that have already been
        processed, extracts relevant data, and processes the new mentions.

        :return: The number of new mentions found and processed.
        :rtype: int
        :var last_timestamp: The last saved Unix timestamp retrieved from the database.
        :type last_timestamp: int or None
        :var start_time: The Unix timestamp from which to start fetching new mentions.
        :type start_time: int or None
        :var mentions_found: A counter for the number of new mentions found and processed.
        :type mentions_found: int
        :var mention_generator: A generator yielding mention tweet objects.
        :type mention_generator: generator
        :var mention: An individual mention tweet object from the generator.
        :type mention: dict
        :var tweet_id: The ID of the current tweet being processed.
        :type tweet_id: str
        :var data: Standardized mention data prepared for processing.
        :type data: dict
        """
        last_timestamp = Mention.objects.last_processed_timestamp(self.platform_name)
        if not last_timestamp:
            self.logger.info(
                "No previous timestamp found. Fetching all available mentions."
            )

        start_time = last_timestamp + 1 if last_timestamp else None

        mentions_found = 0
        try:
            mention_generator = self._get_all_mentions(since_time=start_time)

            for mention in mention_generator:
                tweet_id = mention["id"]
                if not self.is_processed(tweet_id):
                    data = self.extract_mention_data(mention)
                    if self.process_mention(tweet_id, data, f"@{self.target_handle}"):
                        mentions_found += 1

        except Exception as e:
            self.logger.error(f"Error checking mentions: {e}")
            self.log_action("mentions_check_error", f"Error: {str(e)}")

        self.log_action("mentions_checked", f"Found {mentions_found} new mentions")
        return mentions_found

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
