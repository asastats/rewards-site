import asyncio
import logging
import signal
import sys
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

from rewardsbot import config
from rewardsbot.controllers.command_handler import SuggestRewardModal
from rewardsbot.services.cycle import CycleService
from rewardsbot.services.user import UserService
from rewardsbot.utils.api import ApiService

# Set up comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            Path(__file__).parent.parent.resolve() / "logs" / " bot.log",
            encoding="utf-8",
            mode="a",
        ),
    ],
)
logger = logging.getLogger("discord.bot")


class RewardsBot(commands.Bot):
    def __init__(self):
        # Configure intents
        intents = discord.Intents.all()

        # Bot presence and activity
        activity = discord.Activity(
            type=discord.ActivityType.watching, name="reward suggestions"
        )

        super().__init__(
            command_prefix="!",
            intents=intents,
            activity=activity,
            status=discord.Status.online,
            # 2.6.4: Better member caching for user lookups
            member_cache_flags=discord.MemberCacheFlags.all(),
            # Enable message content for potential future features
            max_messages=1000,
        )

        # Initialize API service for ADRF endpoints
        self.api_service = ApiService()
        self._shutting_down = False

    async def setup_hook(self):
        """Async setup called when bot starts"""
        logger.info("🚀 Starting bot setup...")

        # Validate configuration
        await self._validate_config()

        # Setup commands and sync with Discord
        await self._setup_commands()

        # Initialize API connections
        await self._initialize_services()

        logger.info("✅ Bot setup completed successfully")

    async def _validate_config(self):
        """Validate all required configuration"""
        if not config.DISCORD_TOKEN:
            raise ValueError("DISCORD_TOKEN not found in configuration")

        if not config.BASE_URL:
            logger.warning("BASE_URL not configured - API features will not work")

        logger.info(
            f"✅ Configuration validated - API Base: "
            f"{getattr(config, 'BASE_URL', 'Not set')}"
        )

    async def _setup_commands(self):
        """Setup and sync application commands"""
        try:
            logger.info("🔄 Setting up application commands...")

            # Sync global commands
            synced = await self.tree.sync()
            logger.info(f"✅ Synced {len(synced)} global command(s)")

            logger.info(f"🔍 Synced global commands: {[cmd.name for cmd in synced]}")

        except Exception as e:
            logger.error(f"❌ Failed to setup commands: {e}")
            raise

    async def _initialize_services(self):
        """Initialize API services and connections"""
        try:
            # Initialize API service (will create aiohttp session)
            await self.api_service.initialize()
            logger.info("✅ API service initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize services: {e}")
            raise

    async def on_ready(self):
        """Called when bot is fully connected and ready"""
        if self._shutting_down:
            return

        logger.info(f"✅ Logged in as {self.user.name} (ID: {self.user.id})")
        logger.info(f"✅ Connected to {len(self.guilds)} guild(s):")

        # Log guild information
        for guild in self.guilds:
            logger.info(
                f"   - {guild.name} (ID: {guild.id}, Members: {guild.member_count})"
            )

        # Log command information
        commands_list = await self.tree.fetch_commands()
        logger.info(f"✅ {len(commands_list)} command(s) available")

        logger.info("------ Bot is fully operational! ------")

    async def on_disconnect(self):
        """Called when bot disconnects from Discord"""
        if not self._shutting_down:
            logger.warning("🔌 Bot disconnected from Discord")

    async def on_resumed(self):
        """Called when bot resumes connection"""
        logger.info("🔁 Bot resumed connection to Discord")

    async def close(self):
        """Clean shutdown - close all resources properly"""
        if self._shutting_down:
            return

        self._shutting_down = True
        logger.info("🛑 Starting bot shutdown sequence...")

        try:
            # Close API service first (aiohttp sessions)
            await self.api_service.close()
            logger.info("✅ API service closed")

            # Call parent close method
            await super().close()
            logger.info("✅ Discord connection closed")

        except Exception as e:
            logger.error(f"❌ Error during shutdown: {e}")
        finally:
            logger.info("✅ Bot shutdown completed successfully")


# Create bot instance
bot = RewardsBot()

# Define command groups
rewards_group = app_commands.Group(
    name="rewards", description="Manage rewards and contributions"
)
bot.tree.add_command(rewards_group)


# Global error handler for all application commands
@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction, error: app_commands.AppCommandError
):
    """Global error handler for application commands"""
    logger.error(
        f"Command error in {interaction.command.name if interaction.command else 'unknown'}: {error}"
    )

    user_info = f"{interaction.user} (ID: {interaction.user.id})"
    guild_info = (
        f"{interaction.guild.name} (ID: {interaction.guild.id})"
        if interaction.guild
        else "DM"
    )

    # Log detailed error information
    logger.error(f"Command error context: User: {user_info}, Guild: {guild_info}")

    # User-friendly error messages based on error type
    if isinstance(error, app_commands.CommandOnCooldown):
        message = f"⏰ This command is on cooldown. Try again in {error.retry_after:.1f} seconds."
    elif isinstance(error, app_commands.MissingPermissions):
        message = "❌ You don't have permission to use this command."
    elif isinstance(error, app_commands.BotMissingPermissions):
        missing = ", ".join(error.missing_permissions)
        message = f"❌ I'm missing permissions to execute this command: {missing}"
    elif isinstance(error, app_commands.CheckFailure):
        message = "❌ You cannot use this command in this context."
    else:
        message = "❌ An unexpected error occurred while executing this command."
        # Log unexpected errors with full traceback
        logger.error("Unexpected command error:", exc_info=error)

    # Send error response
    try:
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)
    except discord.NotFound:
        logger.warning("Could not send error message - interaction already expired")
    except Exception as e:
        logger.error(f"Failed to send error message: {e}")


# Separate cycle commands
@rewards_group.command(name="current", description="Get current cycle information")
async def rewards_cycle_current(interaction: discord.Interaction):
    """Current cycle subcommand"""
    await interaction.response.defer(thinking=True)
    bot = interaction.client
    try:
        info = await CycleService.current_cycle_info(bot.api_service)
        await interaction.followup.send(info)
    except Exception as error:
        logger.error(f"❌ Cycle Current Command Error: {error}", exc_info=True)
        await interaction.followup.send(
            "❌ Failed to get current cycle info.", ephemeral=True
        )


@rewards_group.command(name="date", description="Get cycle end date")
async def rewards_cycle_date(interaction: discord.Interaction):
    """Cycle date subcommand"""
    await interaction.response.defer(thinking=True)
    bot = interaction.client
    try:
        end_date_info = await CycleService.cycle_end_date(bot.api_service)
        await interaction.followup.send(end_date_info)
    except Exception as error:
        logger.error(f"❌ Cycle Date Command Error: {error}", exc_info=True)
        await interaction.followup.send(
            "❌ Failed to get cycle end date.", ephemeral=True
        )


@rewards_group.command(name="contributions", description="Get recent contributions")
async def rewards_contributions_tail(interaction: discord.Interaction):
    """Cycle tail subcommand"""
    await interaction.response.defer(thinking=True)
    bot = interaction.client
    try:
        cycle_last = await CycleService.contributions_tail(bot.api_service)
        await interaction.followup.send(cycle_last)
    except Exception as error:
        logger.error(f"❌ Cycle Tail Command Error: {error}", exc_info=True)
        await interaction.followup.send(
            "❌ Failed to get recent contributions.", ephemeral=True
        )


@rewards_group.command(
    name="cycle", description="Get specific cycle information by number"
)
@app_commands.describe(number="The cycle number to look up")
async def rewards_cycle_specific(interaction: discord.Interaction, number: int):
    """Specific cycle subcommand"""
    await interaction.response.defer(thinking=True)
    bot = interaction.client
    try:
        if number <= 0:
            await interaction.followup.send("❌ Cycle number must be positive.")
            return
        cycle_data = await CycleService.cycle_info(bot.api_service, number)
        await interaction.followup.send(cycle_data)
    except Exception as error:
        logger.error(f"❌ Cycle Specific Command Error: {error}", exc_info=True)
        await interaction.followup.send("❌ Failed to get cycle info.", ephemeral=True)


# User subcommand
@rewards_group.command(name="user", description="Get user contributions")
@app_commands.describe(username="Username to fetch data for")
async def rewards_user(interaction: discord.Interaction, username: str):
    """User subcommand"""
    await interaction.response.defer(thinking=True)

    # Get the bot instance to access the api_service
    bot = interaction.client

    try:
        user_summary = await UserService.user_summary(bot.api_service, username)
        await interaction.followup.send(user_summary)

    except Exception as error:
        logger.error(f"❌ User Command Error: {error}", exc_info=True)
        await interaction.followup.send(
            "❌ Failed to process user command.", ephemeral=True
        )


# Suggest subcommand
@rewards_group.command(name="suggest", description="Suggest a reward for a user")
@app_commands.describe(
    username="The username to suggest a reward for",
    reason="Reason for the reward suggestion",
)
async def rewards_suggest(interaction: discord.Interaction, username: str, reason: str):
    """Suggest subcommand"""
    await interaction.response.defer(thinking=True)

    try:
        # You can implement the suggestion logic here or call your existing handler
        result = f"✅ Reward suggestion recorded for {username}: {reason}"
        await interaction.followup.send(result)

    except Exception as error:
        logger.error(f"❌ Suggest Command Error: {error}", exc_info=True)
        await interaction.followup.send(
            "❌ Failed to process suggestion.", ephemeral=True
        )


# Context menu command for suggesting rewards
@bot.tree.context_menu(name="Suggest Reward")
async def suggest_reward_context(
    interaction: discord.Interaction, message: discord.Message
):
    """Context menu for suggesting rewards on messages"""
    try:
        # Validate the message
        if message.author.bot:
            await interaction.response.send_message(
                "❌ Cannot suggest rewards for bot messages.", ephemeral=True
            )
            return

        if message.author == interaction.user:
            await interaction.response.send_message(
                "❌ Cannot suggest rewards for your own messages.", ephemeral=True
            )
            return

        # Open the suggestion modal
        modal = SuggestRewardModal(target_message=message)
        await interaction.response.send_modal(modal)

        logger.info(
            f"📝 Suggestion modal opened for message {message.id} by {interaction.user}"
        )

    except Exception as e:
        logger.error(f"Context menu error: {e}", exc_info=True)
        try:
            await interaction.response.send_message(
                "❌ Failed to open suggestion form.", ephemeral=True
            )
        except discord.NotFound:
            logger.warning("Interaction expired before error could be sent")


async def clear_all_commands(bot):
    logger.info("🧹 Clearing all registered application commands...")
    try:
        # Clear global commands
        await bot.http.bulk_upsert_global_commands(bot.user.id, [])
        logger.info("✅ Cleared global commands")

        # # Clear guild commands if applicable
        # # NOTE: meanwhile env variable changed to comma separated list
        # if hasattr(config, "GUILD_IDS") and config.GUILD_IDS:
        #     await bot.http.bulk_upsert_guild_commands(bot.user.id, config.GUILD_IDS, [])
        #     logger.info(f"✅ Cleared guild commands for {config.GUILD_IDS}")

    except Exception as e:
        logger.error(f"❌ Error clearing commands: {e}")


# Global interaction logger
@bot.event
async def on_interaction(interaction: discord.Interaction):
    """Log all interactions for debugging and analytics"""
    if interaction.type == discord.InteractionType.application_command:
        command_name = interaction.command.name if interaction.command else "unknown"
        user = f"{interaction.user} (ID: {interaction.user.id})"
        guild = (
            f"{interaction.guild.name} (ID: {interaction.guild.id})"
            if interaction.guild
            else "DM"
        )

        logger.info(f"🔧 Command executed: {command_name} by {user} in {guild}")


# Simplified signal handling
async def shutdown_bot():
    """Perform graceful shutdown"""
    logger.info("🚦 Starting graceful shutdown process...")
    await bot.close()


def handle_signal(sig):
    """Handle shutdown signals"""
    logger.info(f"📡 Received signal {sig.name}, initiating graceful shutdown...")
    asyncio.create_task(shutdown_bot())


async def main():
    """Main entry point with comprehensive error handling"""
    try:
        logger.info("🎯 Starting Rewards Bot...")

        # Validate critical configuration
        if not config.DISCORD_TOKEN:
            logger.error("❌ No Discord token found in configuration")
            return 1

        if not getattr(config, "BASE_URL", None):
            logger.warning("⚠️  BASE_URL not configured - API features will be disabled")

        # Set up signal handlers
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda s=sig: handle_signal(s))

        # Start the bot with context manager for proper resource handling
        async with bot:

            # # NOTE: Hook into on_ready just once for cleanup
            # @bot.event
            # async def on_ready():
            #     logger.info("🚿 Running one-time cleanup...")
            #     await clear_all_commands(bot)
            #     logger.info("✅ Command cleanup complete, shutting down.")
            #     await bot.close()

            await bot.start(config.DISCORD_TOKEN)

        return 0

    except discord.LoginFailure:
        logger.error("❌ Invalid Discord token provided")
        return 1
    except KeyboardInterrupt:
        logger.info("⏹️ Bot stopped by user (KeyboardInterrupt)")
        return 0
    except Exception as e:
        logger.error(f"❌ Unexpected error during bot execution: {e}", exc_info=True)
        return 1
    finally:
        logger.info("👋 Bot session ended")


def run_bot():
    """Main entry point for running the bot."""
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("⏹️ Script interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Fatal error in main: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    run_bot()
