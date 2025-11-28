"""Module containing base tracker class."""

import logging
import os
import signal
import time
from datetime import datetime
from pathlib import Path

import requests

from trackers.config import REWARDS_API_BASE_URL
from trackers.models import Mention, MentionLog
from utils.helpers import get_env_variable, social_platform_prefixes


class BaseMentionTracker:
    """Base class for all social media mention trackers.

    :var BaseMentionTracker.logger: logger instance for this platform
    :type BaseMentionTracker.logger: :class:`logging.Logger`
    :var BaseMentionTracker.exit_signal: flag indicating requested graceful shutdown
    :type BaseMentionTracker.exit_signal: bool
    """

    def __init__(self, platform_name, parse_message_callback):
        """Initialize base tracker.

        :param platform_name: name of the social media platform
        :type platform_name: str
        :param parse_message_callback: function to call when mention is found
        :type parse_message_callback: callable
        """
        self.platform_name = platform_name
        self.parse_message_callback = parse_message_callback
        self.exit_signal = False
        self.setup_logging()

    # # setup
    def setup_logging(self):
        """Setup common logging configuration.

        :var logs_dir: logs directory name
        :type logs_dir: str
        :var log_filename: filename for the log file
        :type log_filename: str
        """
        logs_dir = Path(__file__).parent.parent.resolve() / "logs"
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)

        log_filename = os.path.join(logs_dir, f"{self.platform_name}_tracker.log")

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.FileHandler(log_filename), logging.StreamHandler()],
        )
        self.logger = logging.getLogger(f"{self.platform_name}_tracker")

    # # graceful shutdown helpers
    def _exit_gracefully(self, signum, frame):
        """Signal handler that requests graceful shutdown.

        Sets :pyattr:`BaseMentionTracker.exit_signal` to True when a termination
        signal is received.

        :param signum: received signal number
        :type signum: int
        :param frame: current stack frame (unused)
        :type frame: :class:`frame` or None
        """
        self.logger.info(
            f"{self.platform_name} tracker exit signal received ({signum})"
        )
        self.exit_signal = True

    def _register_signal_handlers(self):
        """Register OS signal handlers for graceful shutdown.

        Handles :data:`signal.SIGINT` and :data:`signal.SIGTERM` by binding them
        to :meth:`BaseMentionTracker._exit_gracefully`.
        """
        signal.signal(signal.SIGINT, self._exit_gracefully)
        signal.signal(signal.SIGTERM, self._exit_gracefully)

    def _interruptible_sleep(self, seconds):
        """Sleep in one-second increments, respecting exit signal.

        :param seconds: total number of seconds to sleep
        :type seconds: int
        """
        for _ in range(int(seconds)):
            if self.exit_signal:
                break

            time.sleep(1)

    # # processing
    def check_mentions(self):
        """Check for new mentions - to be implemented by subclasses.

        :return: number of new mentions found
        :rtype: int
        """
        raise NotImplementedError("Subclasses must implement check_mentions()")

    def is_processed(self, item_id):
        """Check if item has been processed.

        :param item_id: unique identifier for the social media item
        :type item_id: str
        :return: True if item has been processed, False otherwise
        :rtype: bool
        """
        return Mention.objects.is_processed(item_id, self.platform_name)

    def mark_processed(self, item_id, data):
        """Mark item as processed in database.

        :param item_id: unique identifier for the social media item
        :type item_id: str
        :param data: mention data dictionary
        :type data: dict
        """
        Mention.objects.mark_processed(item_id, self.platform_name, data)

    def process_mention(self, item_id, data, username):
        """Common mention processing logic.

        :param item_id: unique identifier for the social media item
        :type item_id: str
        :param data: mention data dictionary
        :type data: dict
        :param username: mentioned username
        :type username: str
        :var parsed_message: parsed message result
        :type parsed_message: dict
        :var contribution_data: formatted contribution data
        :type contribution_data: dict
        :return: True if mention was processed, False otherwise
        :rtype: bool
        """
        try:
            if self.is_processed(item_id):
                return False

            parsed_message = self.parse_message_callback(data.get("content"), username)
            contribution_data = self.prepare_contribution_data(parsed_message, data)
            self.post_new_contribution(contribution_data)
            self.mark_processed(item_id, data)

            self.logger.info(
                f"Processed mention from {data.get('suggester', 'unknown')}"
            )
            self.log_action(
                "mention_processed",
                f"Item: {item_id}, Suggester: {data.get('suggester')}",
            )

            return True

        except Exception as e:
            self.logger.error(f"Error processing mention {item_id}: {e}")
            self.log_action("processing_error", f"Item: {item_id}, Error: {str(e)}")
            return False

    def log_action(self, action, details=""):
        """Log platform actions to database.

        :param action: description of the action performed
        :type action: str
        :param details: additional details about the action
        :type details: str
        """
        MentionLog.objects.log_action(self.platform_name, action, details)

    def prepare_contribution_data(self, parsed_message, message_data):
        """Prepare contribution data for POST request from provided arguments.

        Check if username is among excluded contributors and if it is then set
        the username to suggester value instead of contributor.

        :param parsed_message: parsed message result
        :type parsed_message: dict
        :param message_data: original message data
        :type message_data: dict
        :var platform_name: social media provider name
        :type platform_name: str
        :var platform_prefix: internal username prefix for the platform
        :type platform_prefix: str
        :var username: contributor's username/handle in the platform
        :type username: str
        :return: dict
        """
        platform_name, platform_prefix = next(
            (name, prefix)
            for name, prefix in social_platform_prefixes()
            if name in self.platform_name.capitalize()
        )
        username = message_data.get("contributor")
        if not username or username in get_env_variable("EXCLUDED_CONTRIBUTORS", ""):
            username = message_data.get("suggester")

        return {
            **parsed_message,
            "username": f"{platform_prefix}{username}",
            "url": message_data.get("contribution_url"),
            "platform": platform_name,
        }

    def post_new_contribution(self, contribution_data):
        """Send add contribution POST request to the Request API.

        :param contribution_data: formatted contribution data
        :type contribution_data: dict
        :var base_url: Rewards API base endpoints URL
        :type base_url: str
        :var response: requests' response instance
        :type response: :class:`requests.Response`
        :return: response data from Rewards API
        :rtype: dict
        """
        try:
            response = requests.post(
                f"{REWARDS_API_BASE_URL}/addcontribution",
                json=contribution_data,
                headers={"Content-Type": "application/json"},
                timeout=30,
            )
            response.raise_for_status()  # Raises an HTTPError for bad responses
            return response.json()

        except requests.exceptions.ConnectionError:
            raise Exception(
                "Cannot connect to the API server. Make sure it's running on localhost."
            )

        except requests.exceptions.HTTPError as e:
            raise Exception(
                f"API returned error: {e.response.status_code} - {e.response.text}"
            )

        except requests.exceptions.Timeout:
            raise Exception("API request timed out.")

        except requests.exceptions.RequestException as e:
            raise Exception(f"API request failed: {e}")

    def run(self, poll_interval_minutes=30, max_iterations=None):
        """Main run loop for synchronous mention trackers.

        Implements shared logic for all polling-based trackers:

        * logs tracker startup and poll interval
        * periodically calls :meth:`BaseMentionTracker.check_mentions`
        * logs when new mentions are found
        * sleeps between polls in an interruptible way
        * handles graceful shutdown on :class:`KeyboardInterrupt` and OS signals
        * ensures :meth:`BaseMentionTracker.cleanup` is always called

        :param poll_interval_minutes: how often to check for mentions
        :type poll_interval_minutes: int or float
        :param max_iterations: maximum number of polls before stopping
                              (``None`` for infinite loop)
        :type max_iterations: int or None
        :var iteration: current iteration count
        :type iteration: int
        :var mentions_found: number of new mentions found in current poll
        :type mentions_found: int
        """
        self._register_signal_handlers()

        self.logger.info(
            f"Starting {self.platform_name} tracker with "
            f"{poll_interval_minutes} minute intervals"
        )
        self.log_action("started", f"Poll interval: {poll_interval_minutes} minutes")

        iteration = 0

        try:
            while not self.exit_signal and (
                max_iterations is None or iteration < max_iterations
            ):
                iteration += 1

                self.logger.info(
                    f"{self.platform_name} poll #{iteration} at "
                    f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )

                mentions_found = self.check_mentions()

                if mentions_found and mentions_found > 0:
                    self.logger.info(f"Found {mentions_found} new mentions")

                self.logger.info(
                    f"{self.platform_name} tracker sleeping for "
                    f"{poll_interval_minutes} minutes"
                )
                self._interruptible_sleep(poll_interval_minutes * 60)

        except KeyboardInterrupt:
            self.logger.info(f"{self.platform_name} tracker stopped by user")
            self.log_action("stopped", "User interrupt")

        except Exception as e:
            self.logger.error(f"{self.platform_name} tracker error: {e}")
            self.log_action("error", f"Tracker error: {str(e)}")
            raise
