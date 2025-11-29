"""Module containing trackers' ORM models."""

from datetime import datetime, timezone

from asgiref.sync import sync_to_async
from django.db import models
from django.db.models import Max
from django.db.models.expressions import RawSQL


class MentionManager(models.Manager):
    """Social media mention's data manager."""

    def is_processed(self, item_id, platform_name):
        """Check if item has been processed.

        :param item_id: unique identifier for the social media item
        :type item_id: str
        :param platform_name: name of the social media platform
        :type platform_name: str
        :return: True if item has been processed, False otherwise
        :rtype: bool
        """
        return self.filter(item_id=item_id, platform=platform_name).exists()

    def mark_processed(self, item_id, platform_name, data):
        """Mark item as processed in database.

        :param item_id: unique identifier for the social media item
        :type item_id: str
        :param platform_name: name of the social media platform
        :type platform_name: str
        :param data: mention data dictionary
        :type data: dict
        :return: :class:`Mention`
        """
        return self.create(
            item_id=item_id,
            platform=platform_name,
            suggester=data.get("suggester"),
            raw_data=data,
        )

    def last_processed_timestamp(self, platform_name):
        """Get the timestamp of the last processed mention for a platform.

        This method retrieves the highest timestamp from all processed mentions
        for a specific platform. The timestamp is extracted from the `raw_data`
        JSON field. This is used by trackers to fetch only new mentions since
        the last successfully processed item.

        :param platform_name: The name of the social media platform.
        :type platform_name: str
        :return: The Unix timestamp of the last processed mention, or None if
                 no mentions are found for the platform.
        :rtype: int or None
        """
        max_timestamp = self.filter(platform=platform_name).aggregate(
            max_timestamp=Max(RawSQL("CAST(raw_data->>'timestamp' AS BIGINT)", []))
        )["max_timestamp"]
        return max_timestamp

    def _get_mention_by_url(self, url):
        """Get a mention by its URL.

        :param url: The URL to search for.
        :type url: str
        :return: mention instance or None
        :rtype: :class:`Mention` or None
        """
        return self.filter(
            models.Q(raw_data__suggestion_url=url)
            | models.Q(raw_data__contribution_url=url)
        ).first()

    def message_from_url(self, url):
        """Retrieve message content from provided `url`.

        :param url: URL to get message from
        :type url: str
        :var mention: mention data from database
        :type mention: :class:`Mention`
        :return: dictionary with message data
        :rtype: dict
        """
        mention = self._get_mention_by_url(url)

        if mention:
            timestamp = mention.raw_data.get("timestamp")
            dt_object = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            timestamp_str = dt_object.isoformat()
            return {
                "success": True,
                "content": mention.raw_data.get("content", ""),
                "contribution": mention.raw_data.get("contribution", ""),
                "author": mention.raw_data.get("contributor", "Unknown"),
                "timestamp": timestamp_str,
                "message_id": mention.item_id,
                "raw_data": mention.raw_data,
            }
        else:
            return {
                "success": False,
                "error": f"Message not found for URL: {url}",
            }


class Mention(models.Model):
    """Social media mention's data model."""

    item_id = models.CharField(max_length=255, primary_key=True)
    platform = models.CharField(max_length=255)
    processed_at = models.DateTimeField(auto_now_add=True)
    suggester = models.CharField(max_length=255, null=True)
    raw_data = models.JSONField()

    objects = MentionManager()

    class Meta:
        """Define ordering and fields that make unique indexes."""

        indexes = [
            models.Index(fields=["platform"]),
        ]
        ordering = ["-processed_at"]


class MentionLogManager(models.Manager):
    """Social media mention log's data manager."""

    @sync_to_async
    def log_action(self, platform_name, action, details=""):
        """Log platform actions to database.

        :param platform_name: name of the social media platform
        :type platform_name: str
        :param action: description of the action performed
        :type action: str
        :param details: additional details about the action
        :type details: str
        :return: :class:`MentionLog`
        """
        return self.create(platform=platform_name, action=action, details=details)


class MentionLog(models.Model):
    """Social media mention log's data model."""

    platform = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=255)
    details = models.TextField(blank=True)

    objects = MentionLogManager()

    class Meta:
        """Define ordering of the log entries."""

        ordering = ["-timestamp"]
