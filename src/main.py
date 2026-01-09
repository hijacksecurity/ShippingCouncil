"""ShippingCouncil main entry point."""

import asyncio
import os
import sys
from pathlib import Path

# Fix SSL certificates for macOS
import certifi
os.environ["SSL_CERT_FILE"] = certifi.where()

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from config.settings import get_settings
from core.council import Council
from core.task import Task
from integrations.discord.bot import DiscordBot
from integrations.discord.handlers import setup_commands, setup_message_handler
from utils.logging import get_logger, setup_logging


async def run_bot() -> None:
    """Run the Discord bot with the council."""
    settings = get_settings()
    setup_logging(settings.log_level)
    logger = get_logger("main")

    logger.info("Starting ShippingCouncil...")

    # Create work directory
    settings.work_dir.mkdir(parents=True, exist_ok=True)

    # Initialize council
    council = Council(
        github_token=settings.github_token,
        work_dir=settings.work_dir,
    )

    # Initialize Discord bot
    discord_bot = DiscordBot(
        token=settings.discord_bot_token,
        guild_id=settings.discord_guild_id,
    )

    # Set up Discord commands and message handler
    setup_commands(discord_bot.bot, council)
    setup_message_handler(discord_bot.bot)

    # Set up status callback to send updates to Discord
    async def status_callback(task: Task, message: str) -> None:
        if task.thread_id:
            try:
                await discord_bot.send_message(task.thread_id, message)
            except Exception as e:
                logger.error("Failed to send status update", error=str(e))

    council.on_status_update(status_callback)

    try:
        # Start council
        await council.start()
        logger.info("Council started")

        # Start Discord bot (blocking)
        logger.info("Starting Discord bot...")
        await discord_bot.bot.start(settings.discord_bot_token)

    except KeyboardInterrupt:
        logger.info("Shutting down...")

    finally:
        await council.stop()
        await discord_bot.disconnect()
        logger.info("Shutdown complete")


def main() -> None:
    """Main entry point."""
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
