"""Module containing class for tracking mentions on Telegram."""

import asyncio
import math
from datetime import datetime
from pathlib import Path

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

from trackers.base import BaseAsyncMentionTracker


class TelegramTracker(BaseAsyncMentionTracker):
    """Tracker for Telegram mentions in specified groups/channels.

    :param TelegramTracker.client: Telegram client instance
    :type TelegramTracker.client: :class:`telethon.TelegramClient` or None
    :param TelegramTracker.bot_username: username of the bot account
    :type TelegramTracker.bot_username: str
    :param TelegramTracker.tracked_chats: list of chats being monitored
    :type TelegramTracker.tracked_chats: list
    :param TelegramTracker._is_connected: is client connected or not
    :type TelegramTracker._is_connected: Boolean
    """

    def __init__(self, parse_message_callback, config, chats_collection):
        """Initialize Telegram tracker.

        :param parse_message_callback: function to call when mention is found
        :type parse_message_callback: callable
        :param config: configuration dictionary for Telegram API
        :type config: dict
        :param chats_collection: list of chat usernames or IDs to monitor
        :type chats_collection: list
        :var session_name: name of the client session
        :type session_name: str
        :var session_path: full path on disk to session database file
        :type session_path: :class:`pathlib.PosixPath`
        """
        super().__init__("telegram", parse_message_callback)

        session_name = config.get("session_name", "telegram_tracker")
        session_path = (
            Path(__file__).resolve().parent.parent
            / "fixtures"
            / f"{session_name}.session"
        )
        self.client = TelegramClient(
            session=session_path,
            api_id=config["api_id"],
            api_hash=config["api_hash"],
        )

        self.bot_username = config.get("bot_username", "").lower()
        self.tracked_chats = chats_collection or []

        self.logger.info(
            f"Telegram tracker initialized for {len(self.tracked_chats)} chats"
        )
        self._is_connected = False

    async def _post_init_setup(self, chats_collection):
        """Perform asynchronous setup tasks after initialization."""
        await self.log_action_async(
            "initialized", f"Tracking {len(chats_collection)} chats"
        )

    async def _ensure_connected(self):
        """Ensure Telegram client is connected.

        :var phone: app creator's phone number
        :type phone: str
        :var code: code received via Telegram app
        :type code: str
        :var password: app creator's 2FA password
        :type password: str
        """
        if not self._is_connected:
            try:
                await self.client.connect()
                if not await self.client.is_user_authorized():
                    phone = input("Please enter your phone number: ")
                    await self.client.send_code_request(phone)
                    code = input("Please enter the code you received: ")
                    await self.client.sign_in(phone, code)

                self._is_connected = True

            except SessionPasswordNeededError:
                password = input("Please enter your 2FA password: ")
                await self.client.sign_in(password=password)
                self._is_connected = True

            except Exception as e:
                self.logger.error(f"Error connecting Telegram client: {e}")
                raise

    async def cleanup(self):
        """Perform graceful cleanup of the Telegram client."""
        if self.client and self._is_connected:
            self.logger.info("Disconnecting Telegram client")
            await self.client.disconnect()
            self._is_connected = False

    async def _get_chat_entity(self, chat_identifier):
        """Get chat entity from identifier.

        :param chat_identifier: username or ID of the chat
        :type chat_identifier: str or int
        :return: chat entity object
        :rtype: :class:`telethon.tl.types.Chat` or None
        """
        try:
            # First try to get by username
            entity = await self.client.get_entity(chat_identifier)
            return entity

        except ValueError:
            try:
                # If it's an integer ID, try getting by ID
                if (
                    isinstance(chat_identifier, int)
                    or chat_identifier.lstrip("-").isdigit()
                ):
                    chat_id = int(chat_identifier)
                    entity = await self.client.get_entity(chat_id)
                    return entity

            except Exception:
                pass

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
        :return: dictionary with replied message information
        :rtype: dict or None
        """
        if not message.reply_to_msg_id:
            return None

        try:
            replied_message = await self.client.get_messages(
                message.chat_id, ids=message.reply_to_msg_id
            )
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
        :rtype: dict
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
            contribution = message.text if message.text else ""

        # For backward compatibility with tests, use username if available, otherwise display_name
        suggester_value = (
            sender_info.get("username")
            or sender_info.get("display_name")
            or str(sender_info.get("user_id"))
        )
        contributor_value = (
            contributor_info.get("username")
            or contributor_info.get("display_name")
            or str(contributor_info.get("user_id"))
        )

        data = {
            "suggester": suggester_value,
            # "suggester_username": sender_info.get("username"),
            # "suggester_display_name": sender_info.get("display_name"),
            "suggestion_url": suggestion_url,
            "contribution_url": contribution_url,
            "contributor": contributor_value,
            # "contributor_username": contributor_info.get("username"),
            # "contributor_display_name": contributor_info.get("display_name"),
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
            self.logger.warning(f"Chat {chat_identifier} not found or inaccessible")
            return 0

        try:
            # Get recent messages (last 50)
            async for message in self.client.iter_messages(chat, limit=50):
                # Check if message mentions the bot
                if (
                    self.bot_username
                    and message.text
                    and self.bot_username in message.text.lower()
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
        if not self.client or not self._is_connected:
            return 0

        # # NOTE: uncomment the following to find group(s) to track
        # async for dialog in self.client.iter_dialogs():
        #     print(f"Name: {dialog.name}, ID: {dialog.id}, Type: {dialog.entity}")

        total_mentions = 0

        for chat in self.tracked_chats:
            chat_mentions = await self._check_chat_mentions(chat)
            total_mentions += chat_mentions
            # Short delay between chat checks
            await asyncio.sleep(2)

        return total_mentions

    def check_mentions(self):
        """Check for new mentions across all tracked chats.

        :return: number of new mentions processed
        :rtype: int
        """
        if not self.client:
            self.logger.error("Telegram client not available")
            return 0

        try:
            # Create event loop for async operations
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Start the client if not connected
            if not self._is_connected:
                loop.run_until_complete(self._ensure_connected())

            # Check mentions
            mention_count = loop.run_until_complete(self.check_mentions_async())
            return mention_count

        except Exception as e:
            self.logger.error(f"Error in Telegram mention check: {e}")
            self.log_action_async("telegram_check_error", f"Error: {str(e)}")
            return 0

        finally:
            # Cleanup the event loop
            loop.close()

    async def run_async(self, poll_interval_minutes=30):
        """Async version of the main run loop.

        :param poll_interval_minutes: how often to check for mentions
        :type poll_interval_minutes: int or float
        """
        # Check client before trying to connect
        if not self.client:
            self.logger.error("Telegram client not available")
            return

        await self._ensure_connected()
        await self.log_action_async(
            "started", f"Tracking {len(self.tracked_chats)} chats"
        )

        iteration = 0

        try:
            while not self.exit_signal:
                iteration += 1
                self.logger.info(
                    f"telegram poll #{iteration} at "
                    f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
                mentions_found = await self.check_mentions_async()
                if mentions_found > 0:
                    self.logger.info(f"Found {mentions_found} new mentions")

                self.logger.info(
                    f"telegram tracker sleeping for {poll_interval_minutes} minutes"
                )
                # Sleep in chunks to respect exit signal
                sleep_seconds = int(math.ceil(poll_interval_minutes * 60))
                for _ in range(sleep_seconds):
                    if self.exit_signal:
                        break

                    await asyncio.sleep(1)

        except asyncio.CancelledError:
            self.logger.info("Telegram tracker cancelled")
            raise

        except KeyboardInterrupt:
            self.logger.info("Telegram tracker stopped by user")

        except Exception as e:
            self.logger.error(f"Telegram tracker error: {e}")
            raise

        finally:
            await self.cleanup()

    def run(self, poll_interval_minutes=30):
        """Run Telegram mentions tracker.

        :param poll_interval_minutes: how often to check for mentions
        :type poll_interval_minutes: int or float
        """
        # Check client first
        if not self.client:
            self.logger.error("Cannot start Telegram tracker - client not available")
            return

        # Register signal handlers
        self._register_signal_handlers()

        # Create and run event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Run the async task
            loop.run_until_complete(self.run_async(poll_interval_minutes))

        except KeyboardInterrupt:
            self.logger.info("Telegram tracker stopped by user")

        finally:
            # Cleanup
            loop.run_until_complete(self.cleanup())
            loop.close()
