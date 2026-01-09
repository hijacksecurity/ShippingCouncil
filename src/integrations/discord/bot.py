"""Discord bot setup and configuration."""

import asyncio
from typing import Any, Callable

import discord
from discord import app_commands
from discord.ext import commands

from integrations.base import BaseIntegration


class DiscordBot(BaseIntegration):
    """Discord bot for agent communication."""

    def __init__(self, token: str, guild_id: str | None = None):
        """Initialize the Discord bot.

        Args:
            token: Discord bot token
            guild_id: Optional guild ID for faster slash command sync
        """
        self._token = token
        self._guild_id = guild_id

        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True

        self.bot = commands.Bot(command_prefix="!", intents=intents)
        self._setup_events()

    @property
    def name(self) -> str:
        return "discord"

    @property
    def guild(self) -> discord.Object | None:
        """Get the guild object for slash commands."""
        if self._guild_id:
            return discord.Object(id=int(self._guild_id))
        return None

    def _setup_events(self) -> None:
        """Set up bot event handlers."""

        @self.bot.event
        async def on_ready() -> None:
            print(f"Discord bot connected as {self.bot.user}")
            try:
                if self.guild:
                    self.bot.tree.copy_global_to(guild=self.guild)
                    await self.bot.tree.sync(guild=self.guild)
                else:
                    await self.bot.tree.sync()
                print("Slash commands synced successfully")
            except Exception:
                pass  # Slash command sync failed - bot continues without them

    def add_slash_command(
        self,
        name: str,
        description: str,
        callback: Callable[..., Any],
    ) -> None:
        """Add a slash command to the bot.

        Args:
            name: Command name
            description: Command description
            callback: Async function to handle the command
        """
        command = app_commands.Command(
            name=name,
            description=description,
            callback=callback,
        )
        self.bot.tree.add_command(command, guild=self.guild)

    async def send_message(
        self,
        channel_id: int,
        content: str,
        thread: discord.Thread | None = None,
    ) -> discord.Message:
        """Send a message to a channel or thread.

        Args:
            channel_id: Discord channel ID
            content: Message content
            thread: Optional thread to send to

        Returns:
            The sent message
        """
        if thread:
            return await thread.send(content)

        channel = self.bot.get_channel(channel_id)
        if channel and isinstance(channel, discord.TextChannel):
            return await channel.send(content)
        raise ValueError(f"Channel {channel_id} not found or not a text channel")

    async def create_thread(
        self,
        channel_id: int,
        name: str,
        message: discord.Message | None = None,
    ) -> discord.Thread:
        """Create a thread in a channel.

        Args:
            channel_id: Discord channel ID
            name: Thread name
            message: Optional message to create thread from

        Returns:
            The created thread
        """
        channel = self.bot.get_channel(channel_id)
        if not channel or not isinstance(channel, discord.TextChannel):
            raise ValueError(f"Channel {channel_id} not found or not a text channel")

        if message:
            return await message.create_thread(name=name)
        return await channel.create_thread(name=name, type=discord.ChannelType.public_thread)

    async def connect(self) -> None:
        """Start the Discord bot."""
        # Run in background - bot.start() is blocking
        asyncio.create_task(self.bot.start(self._token))
        # Wait for bot to be ready
        await self.bot.wait_until_ready()

    async def disconnect(self) -> None:
        """Stop the Discord bot."""
        await self.bot.close()

    async def health_check(self) -> bool:
        """Check if the Discord bot is connected."""
        return self.bot.is_ready()
