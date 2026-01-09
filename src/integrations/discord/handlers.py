"""Discord command and message handlers."""

from typing import TYPE_CHECKING

import discord
from discord import Interaction

if TYPE_CHECKING:
    from core.council import Council


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
