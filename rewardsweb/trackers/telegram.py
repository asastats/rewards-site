"""Module containing class for tracking mentions on Telegram."""

import asyncio
from datetime import datetime

from asgiref.sync import sync_to_async
from telethon import TelegramClient

from trackers.base import BaseMentionTracker


class TelegramTracker(BaseMentionTracker):
    """Tracker for Telegram mentions in specified groups/channels.

    :param TelegramTracker.client: Telegram client instance
    :type TelegramTracker.client: :class:`telethon.TelegramClient` or None
    :param TelegramTracker.bot_username: username of the bot account
    :type TelegramTracker.bot_username: str
    :param TelegramTracker.tracked_chats: list of chats being monitored
    :type TelegramTracker.tracked_chats: list
    """

    def __init__(self, parse_message_callback, config, chats_collection):
        """Initialize Telegram tracker.

        :param parse_message_callback: function to call when mention is found
        :type parse_message_callback: callable
        :param config: configuration dictionary for Telegram API
        :type config: dict
        :param chats_collection: list of chat usernames or IDs to monitor
        :type chats_collection: list
        """
        super().__init__("telegram", parse_message_callback)

        self.client = TelegramClient(
            session=config.get("session_name", "telegram_tracker"),
            api_id=config["api_id"],
            api_hash=config["api_hash"],
        )

        self.bot_username = config.get("bot_username", "").lower()
        self.tracked_chats = chats_collection

        self.logger.info(
            f"Telegram tracker initialized for {len(chats_collection)} chats"
        )

    async def _post_init_setup(self, chats_collection):
        """Perform asynchronous setup tasks after initialization."""
        await self.log_action_async(
            "initialized", f"Tracking {len(chats_collection)} chats"
        )

    async def cleanup(self):
        """Perform graceful cleanup of the Telegram client."""
        if self.client and self.client.is_connected():
            self.logger.info("Disconnecting Telegram client")
            await self.client.disconnect()

    async def _get_chat_entity(self, chat_identifier):
        """Get chat entity from identifier.

        :param chat_identifier: username or ID of the chat
        :type chat_identifier: str or int
        :var entity: Telegram chat entity
        :type entity: :class:`telethon.tl.types.Channel` or :class:`telethon.tl.types.Chat`
        :return: chat entity object
        :rtype: :class:`telethon.tl.types.Chat` or None
        """
        try:
            entity = await self.client.get_entity(chat_identifier)
            return entity

        except Exception as e:
            self.logger.error(f"Error getting chat entity for {chat_identifier}: {e}")
            return None

    async def _get_sender_info(self, message):
        """Get sender information from message.

        :param message: Telegram message object
        :type message: :class:`telethon.tl.types.Message`
        :var sender: Telegram user object representing the message sender
        :type sender: :class:`telethon.tl.types.User` or None
        :return: dictionary with sender information
        :rtype: dict
        """
        try:
            sender = await message.get_sender()
            # when condition isn't met
            if sender:
                return {
                    "user_id": sender.id,
                    "username": sender.username,
                    "display_name": getattr(sender, "first_name", "")
                    or getattr(sender, "title", ""),
                }
        except Exception as e:
            self.logger.debug(f"Error getting sender info: {e}")

        return {"user_id": message.sender_id, "username": None, "display_name": None}

    async def _get_replied_message_info(self, message):
        """Get information about the message being replied to.

        :param message: Telegram message object with reply
        :type message: :class:`telethon.tl.types.Message`
        :var replied_message: the message that this message replies to
        :type replied_message: :class:`telethon.tl.types.Message` or None
        :var replied_sender: sender information of the replied message
        :type replied_sender: dict
        :return: dictionary with replied message information, including its text
        :rtype: dict
        """
        if not message.reply_to_msg_id:
            return None

        try:
            replied_message = await self.client.get_messages(
                message.chat_id, ids=message.reply_to_msg_id
            )

            # when condition isn't met
            if replied_message:
                replied_sender = await self._get_sender_info(replied_message)
                return {
                    "message_id": replied_message.id,
                    "sender_info": replied_sender,
                    "text": replied_message.text or "",
                }
        except Exception as e:
            self.logger.debug(f"Error getting replied message info: {e}")

        return None

    def _generate_message_url(self, chat, message_id):
        """Generate URL for a message.

        :param chat: Telegram chat object
        :type chat: :class:`telethon.tl.types.Chat` or :class:`telethon.tl.types.Channel`
        :param message_id: ID of the message
        :type message_id: int
        :var chat_username: username of the chat/channel
        :type chat_username: str or None
        :return: URL for the message
        :rtype: str
        """
        chat_username = getattr(chat, "username", None)
        if chat_username:
            return f"https://t.me/{chat_username}/{message_id}"
        else:
            return f"chat_{chat.id}_msg_{message_id}"

    async def extract_mention_data(self, message):
        """Extract standardized data from a Telegram message.

        This method processes a Telegram message to extract structured information
        about the suggester, the suggestion, and any replied-to contribution.

        :param message: The Telegram message object to be processed.
        :type message: :class:`telethon.tl.types.Message`
        :return: A dictionary containing standardized mention data.
        :rtype: dict
        :var chat: The chat where the message was sent.
        :type chat: :class:`telethon.tl.types.Chat` or :class:`telethon.tl.types.Channel`
        :var sender_info: Information about the message sender.
        :type sender_info: dict
        :var replied_info: Information about the replied-to message, if any.
        :type replied_info: dict or None
        :var contribution_url: The URL of the contribution.
        :type contribution_url: str
        :var contributor_info: Information about the contributor.
        :type contributor_info: dict
        :var contribution: The text of the contribution.
        :type contribution: str
        """
        chat = message.chat
        chat_title = getattr(chat, "title", "Private Chat")

        # Get sender information
        sender_info = await self._get_sender_info(message)

        # Generate URLs
        suggestion_url = self._generate_message_url(chat, message.id)

        # Get replied message information if this is a reply
        replied_info = await self._get_replied_message_info(message)

        if replied_info:
            contribution_url = self._generate_message_url(
                chat, replied_info["message_id"]
            )
            contributor_info = replied_info["sender_info"]
            contribution = replied_info["text"]
        else:
            contribution_url = suggestion_url
            contributor_info = sender_info
            contribution = ""

        data = {
            "suggester": sender_info["user_id"],
            "suggester_username": sender_info["username"],
            "suggester_display_name": sender_info["display_name"],
            "suggestion_url": suggestion_url,
            "contribution_url": contribution_url,
            "contributor": contributor_info["user_id"],
            "contributor_username": contributor_info["username"],
            "contributor_display_name": contributor_info["display_name"],
            "type": "message",
            "telegram_chat": chat_title,
            "chat_id": chat.id,
            "chat_username": getattr(chat, "username", None),
            "content": message.text if message.text else "",
            "contribution": contribution,
            "timestamp": (
                message.date.isoformat()
                if hasattr(message, "date")
                else datetime.now().isoformat()
            ),
            "item_id": f"telegram_{chat.id}_{message.id}",
        }

        return data

    async def _check_chat_mentions(self, chat_identifier):
        """Check for mentions in a specific chat.

        :param chat_identifier: username or ID of the chat to check
        :type chat_identifier: str or int
        :var mention_count: number of mentions found in this chat
        :type mention_count: int
        :var chat: chat entity object
        :type chat: :class:`telethon.tl.types.Chat` or None
        :var messages: recent messages from the chat
        :type messages: list of :class:`telethon.tl.types.Message`
        :var message: individual message from chat
        :type message: :class:`telethon.tl.types.Message`
        :var data: extracted mention data
        :type data: dict
        :return: number of new mentions processed in this chat
        :rtype: int
        """
        mention_count = 0
        chat = await self._get_chat_entity(chat_identifier)

        if not chat:
            return 0

        try:
            # Get recent messages (last 50)
            async for message in self.client.iter_messages(chat, limit=50):
                # Check if message mentions the bot
                if (
                    self.bot_username
                    and self.bot_username in (message.text or "").lower()
                    and not await self.is_processed_async(
                        f"telegram_{chat.id}_{message.id}"
                    )
                ):

                    data = await self.extract_mention_data(message)
                    if await self.process_mention_async(
                        f"telegram_{chat.id}_{message.id}",
                        data,
                        f"@{self.bot_username}",
                    ):
                        mention_count += 1

        except Exception as e:
            self.logger.error(f"Error checking chat {chat_identifier}: {e}")
            await self.log_action_async(
                "chat_check_error", f"Chat: {chat_identifier}, Error: {str(e)}"
            )

        return mention_count

    async def check_mentions_async(self):
        """Asynchronously check for new mentions across all tracked chats.

        :var total_mentions: total number of new mentions found
        :type total_mentions: int
        :var chat: chat identifier from tracked chats
        :type chat: str or int
        :var chat_mentions: mentions found in current chat
        :type chat_mentions: int
        :return: total number of new mentions processed
        :rtype: int
        """
        if not self.client:
            return 0

        total_mentions = 0

        for chat in self.tracked_chats:
            chat_mentions = await self._check_chat_mentions(chat)
            total_mentions += chat_mentions
            # delay between chat checks
            await asyncio.sleep(60)

        return total_mentions

    def check_mentions(self):
        """Check for new mentions across all tracked chats.

        :var loop: asyncio event loop
        :type loop: :class:`asyncio.AbstractEventLoop`
        :var mention_count: number of new mentions found
        :type mention_count: int
        :return: number of new mentions processed
        :rtype: int
        """
        if not self.client:
            self.logger.error("Telegram client not available")
            return 0

        try:
            # Start the client and run the check
            with self.client:
                # Ensure an event loop is running for async operations
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                mention_count = loop.run_until_complete(self.check_mentions_async())
                return mention_count

        except Exception as e:
            self.logger.error(f"Error in Telegram mention check: {e}")
            self.log_action("telegram_check_error", f"Error: {str(e)}")
            return 0

    async def is_processed_async(self, item_id):
        return await sync_to_async(self.is_processed)(item_id)

    async def process_mention_async(self, item_id, data, username):
        return await sync_to_async(self.process_mention)(item_id, data, username)

    def run(self, poll_interval_minutes=30, max_iterations=None):
        """Run Telegram mentions tracker.

        Ensures the Telegram client is available before starting. When valid,
        defers to the shared base class run method for polling logic.

        :param poll_interval_minutes: how often to check for mentions
        :type poll_interval_minutes: int or float
        :param max_iterations: maximum number of polls before stopping
                            (``None`` for infinite loop)
        :type max_iterations: int or None
        """
        if not getattr(self, "client", None):
            self.logger.error("Cannot start Telegram tracker - client not available")
            return

        with self.client:
            # Connect client if not already connected
            if not self.client.is_connected():
                self.client.connect()

            self.client.loop.run_until_complete(
                self._post_init_setup(self.tracked_chats)
            )
            try:
                super().run(
                    poll_interval_minutes=poll_interval_minutes,
                    max_iterations=max_iterations,
                )
            finally:
                self.client.loop.run_until_complete(self.cleanup())
