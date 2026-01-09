"""Discord command and message handlers."""

from typing import TYPE_CHECKING

import discord
from discord import Interaction

if TYPE_CHECKING:
    from core.council import Council

from agents.backend_dev import BackendDevAgent
from agents.base import BaseAgent
from config.settings import get_settings, AgentConfig as ConfigAgentConfig
from utils.logging import get_ai_logger


def setup_agent_message_handler(
    bot: "discord.ext.commands.Bot",
    agent: BaseAgent,
    agent_config: ConfigAgentConfig | None = None,
    character_mode: bool = True,
) -> None:
    """Set up message handler for a specific agent's bot.

    This is used by MultiBotCoordinator for multi-agent setups.

    Args:
        bot: Discord bot instance
        agent: Agent instance to handle messages
        agent_config: Agent configuration from settings
        character_mode: Whether to use character personality
    """
    ai_log = get_ai_logger()
    triggers = agent_config.triggers if agent_config else []

    @bot.event
    async def on_message(message: discord.Message) -> None:
        # Ignore messages from bots
        if message.author.bot:
            return

        # Ignore command prefix messages
        if message.content.startswith("!"):
            await bot.process_commands(message)
            return

        # Check if this bot is mentioned
        is_mentioned = bot.user in message.mentions
        is_dm = isinstance(message.channel, discord.DMChannel)

        # Check for @all
        content_lower = message.content.lower()
        is_all_mention = "@all" in content_lower or "all agents" in content_lower

        # Only respond if mentioned, in DM, or @all
        if not is_mentioned and not is_dm and not is_all_mention:
            return

        # For @all mentions, check if this agent is relevant
        if is_all_mention and not is_mentioned:
            is_relevant = await agent.is_relevant(message.content, triggers)
            if not is_relevant:
                ai_log.debug(f"Agent {agent.name} not relevant for message")
                return

        ai_log.info(f"=== Discord message for {agent.name} ===")
        ai_log.info(f"Author: {message.author.name}")
        ai_log.info(f"Content: {message.content}")

        # Remove the mention from the message
        content = message.content
        if bot.user:
            content = content.replace(f"<@{bot.user.id}>", "").strip()

        if not content:
            await message.reply("How can I help you?")
            return

        # Show typing indicator
        async with message.channel.typing():
            ai_log.info(f"Processing with {agent.name} agent...")
            result = await agent.chat(content, character_mode=character_mode)

            if result.success:
                ai_log.info(f"Response success, length: {len(result.message)}")
                response = result.message
                if len(response) > 1900:
                    response = response[:1900] + "..."

                # Add character emoji if available
                if character_mode and agent_config:
                    emoji = agent_config.character.emoji
                    if emoji:
                        response = f"{emoji} {response}"

                await message.reply(response)
                ai_log.info("Reply sent to Discord")
            else:
                ai_log.error(f"Response failed: {result.error}")
                await message.reply(f"Sorry, I encountered an error: {result.error}")


def setup_message_handler(bot: "discord.ext.commands.Bot") -> None:
    """Set up message handler for AI agent interaction (legacy single-bot mode).

    Args:
        bot: Discord bot instance
    """
    settings = get_settings()

    # Create a backend dev agent for chat (backward compatible)
    agent = BackendDevAgent(
        github_token=settings.github_token,
        work_dir=settings.work_dir,
        character_mode=settings.character_mode,
    )

    ai_log = get_ai_logger()

    @bot.event
    async def on_message(message: discord.Message) -> None:
        # Ignore messages from the bot itself
        if message.author == bot.user:
            return

        # Ignore messages that start with command prefix
        if message.content.startswith("!"):
            await bot.process_commands(message)
            return

        # Check if bot is mentioned or if it's a DM
        is_mentioned = bot.user in message.mentions
        is_dm = isinstance(message.channel, discord.DMChannel)

        # Only respond if mentioned or in DM
        if not is_mentioned and not is_dm:
            return

        ai_log.info(f"=== Discord message received ===")
        ai_log.info(f"Author: {message.author.name}")
        ai_log.info(f"Channel: {message.channel}")
        ai_log.info(f"Content: {message.content}")

        # Remove the mention from the message
        content = message.content.replace(f"<@{bot.user.id}>", "").strip()
        if not content:
            await message.reply("How can I help you?")
            return

        ai_log.info(f"Cleaned content: {content}")

        # Show typing indicator
        async with message.channel.typing():
            ai_log.info("Processing with AI agent...")
            # Process with the AI agent
            result = await agent.chat(content)

            if result.success:
                ai_log.info(f"AI response success, length: {len(result.message)}")
                # Split long messages if needed (Discord has 2000 char limit)
                response = result.message
                if len(response) > 1900:
                    response = response[:1900] + "..."
                await message.reply(response)
                ai_log.info("Reply sent to Discord")
            else:
                ai_log.error(f"AI response failed: {result.error}")
                await message.reply(f"Sorry, I encountered an error: {result.error}")


def setup_commands(bot: "discord.ext.commands.Bot", council: "Council") -> None:
    """Set up Discord slash commands.

    Args:
        bot: Discord bot instance
        council: Council instance for task management
    """
    from discord import app_commands

    @bot.tree.command(name="task", description="Create a new task for the developer agent")
    @app_commands.describe(description="What should the developer do?")
    async def task_command(interaction: Interaction, description: str) -> None:
        """Create a new development task."""
        await interaction.response.defer()

        # Create a thread for this task
        if interaction.channel and isinstance(interaction.channel, discord.TextChannel):
            thread = await interaction.channel.create_thread(
                name=f"Task: {description[:50]}...",
                type=discord.ChannelType.public_thread,
            )

            # Start the task
            task = await council.create_task(
                description=description,
                agent_type="developer",
                thread_id=thread.id,
            )

            await interaction.followup.send(
                f"Task created! Follow progress in {thread.mention}\n"
                f"Task ID: `{task.id}`"
            )

            # Send initial message to thread
            await thread.send(
                f"**New Task**\n"
                f"Description: {description}\n\n"
                f"The developer agent is working on this..."
            )
        else:
            await interaction.followup.send("Could not create task thread.")

    @bot.tree.command(name="status", description="Get status of a task")
    @app_commands.describe(task_id="The task ID to check")
    async def status_command(interaction: Interaction, task_id: str) -> None:
        """Check task status."""
        task = council.get_task(task_id)
        if task:
            await interaction.response.send_message(
                f"**Task Status**\n"
                f"ID: `{task.id}`\n"
                f"Status: {task.status.value}\n"
                f"Description: {task.description}"
            )
        else:
            await interaction.response.send_message(f"Task `{task_id}` not found.")

    @bot.tree.command(name="cancel", description="Cancel a running task")
    @app_commands.describe(task_id="The task ID to cancel")
    async def cancel_command(interaction: Interaction, task_id: str) -> None:
        """Cancel a task."""
        success = await council.cancel_task(task_id)
        if success:
            await interaction.response.send_message(f"Task `{task_id}` cancelled.")
        else:
            await interaction.response.send_message(
                f"Could not cancel task `{task_id}`. It may not exist or is already completed."
            )

    @bot.tree.command(name="approve", description="Approve a task result (e.g., merge PR)")
    @app_commands.describe(task_id="The task ID to approve")
    async def approve_command(interaction: Interaction, task_id: str) -> None:
        """Approve a completed task."""
        success = await council.approve_task(task_id)
        if success:
            await interaction.response.send_message(f"Task `{task_id}` approved!")
        else:
            await interaction.response.send_message(
                f"Could not approve task `{task_id}`. It may not be ready for approval."
            )

    @bot.tree.command(name="repos", description="List available repositories")
    async def repos_command(interaction: Interaction) -> None:
        """List available repos."""
        await interaction.response.defer()
        repos = await council.list_repos()
        if repos:
            repo_list = "\n".join(f"- `{r}`" for r in repos[:10])
            await interaction.followup.send(f"**Available Repositories**\n{repo_list}")
        else:
            await interaction.followup.send("No repositories found.")
