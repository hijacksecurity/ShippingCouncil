"""Multi-bot coordinator for managing multiple Discord bot instances."""

import asyncio
import logging
from typing import Any

import discord
from agents.base import AgentResult, BaseAgent
from agents.backend_dev import BackendDevAgent
from agents.devops import DevOpsAgent
from config.settings import Settings, AgentConfig as ConfigAgentConfig
from integrations.discord.bot import DiscordBot
from utils.logging import get_ai_logger

logger = logging.getLogger(__name__)


class MultiBotCoordinator:
    """Manages multiple Discord bot instances, one per agent."""

    def __init__(self, settings: Settings):
        """Initialize the multi-bot coordinator.

        Args:
            settings: Application settings with agent configurations
        """
        self.settings = settings
        self.bots: dict[str, discord.Client] = {}
        self.agents: dict[str, BaseAgent] = {}
        self._running = False
        self._ai_log = get_ai_logger()

    def _create_agent(
        self,
        agent_name: str,
        agent_config: ConfigAgentConfig,
    ) -> BaseAgent | None:
        """Create an agent instance based on configuration.

        Args:
            agent_name: Name of the agent (e.g., "backend_dev", "devops")
            agent_config: Agent configuration from agents.yaml

        Returns:
            Agent instance or None if creation failed
        """
        character_mode = self.settings.character_mode

        # All config comes from agents.yaml
        if agent_name == "backend_dev":
            return BackendDevAgent(
                github_token=self.settings.github_token,
                work_dir=self.settings.work_dir,
                character_mode=character_mode,
                triggers=agent_config.triggers,
                allowed_tools=agent_config.tools,
            )
        elif agent_name == "devops":
            return DevOpsAgent(
                work_dir=self.settings.work_dir,
                character_mode=character_mode,
                triggers=agent_config.triggers,
                allowed_tools=agent_config.tools,
            )

        logger.warning(f"Unknown agent type: {agent_name}")
        return None

    async def start_all(self) -> None:
        """Start all configured bots."""
        logger.info("Starting multi-bot coordinator...")

        # Ensure work directory exists
        if self.settings.work_dir:
            self.settings.work_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Work directory: {self.settings.work_dir}")

        for agent_name, agent_config in self.settings.agents.items():
            # Get Discord token for this agent
            token = agent_config.discord_token
            if not token:
                logger.warning(
                    f"No Discord token for agent {agent_name} "
                    f"(set {agent_config.discord_token_env})"
                )
                continue

            # Create agent
            agent = self._create_agent(agent_name, agent_config)
            if not agent:
                continue

            # Create client with basic intents (same as working test)
            intents = discord.Intents.default()
            intents.message_content = True

            client = discord.Client(intents=intents)

            # Capture variables for this iteration
            _client = client
            _agent = agent
            _agent_config = agent_config
            _agent_name = agent_name
            _char_mode = self.settings.character_mode
            _ai_log = self._ai_log

            @_client.event
            async def on_ready(
                c=_client, name=_agent_name, config=_agent_config
            ):
                logger.info(f"Bot '{config.discord_bot_name}' ({name}) connected as {c.user}")
                logger.info(f"[{name}] Connected to {len(c.guilds)} guilds")

            @_client.event
            async def on_message(
                message,
                c=_client, ag=_agent, ag_config=_agent_config, ag_name=_agent_name,
                char_mode=_char_mode, ai_log=_ai_log
            ):
                # Debug log
                logger.debug(f"[{ag_name}] MSG: {message.author}: {message.content[:50] if message.content else '(empty)'}")

                # Ignore own messages
                if message.author == c.user:
                    return

                # Ignore other bots
                if message.author.bot:
                    return

                # Check message type
                is_mentioned = c.user in message.mentions
                is_dm = isinstance(message.channel, discord.DMChannel)
                is_everyone = message.mention_everyone  # @everyone or @here

                # Decide if we should respond:
                # 1. Direct mention (@Rick or @Judy) - always respond
                # 2. @everyone or @here - all agents respond
                # 3. DM - always respond
                # 4. Any other message - check if relevant to this agent's triggers
                should_respond = False

                if is_mentioned:
                    should_respond = True
                    ai_log.info(f"[{ag_name}] Responding: directly mentioned")
                elif is_everyone:
                    should_respond = True
                    ai_log.info(f"[{ag_name}] Responding: @everyone mention")
                elif is_dm:
                    should_respond = True
                    ai_log.info(f"[{ag_name}] Responding: DM")
                else:
                    # Check relevance based on triggers (like AICouncil)
                    is_relevant = await ag.is_relevant(message.content, ag_config.triggers)
                    if is_relevant:
                        should_respond = True
                        ai_log.info(f"[{ag_name}] Responding: trigger matched")

                if not should_respond:
                    return

                ai_log.info(f"=== Processing message for {ag_name} ===")

                # Remove mentions from content
                content = message.content
                if c.user:
                    content = content.replace(f"<@{c.user.id}>", "")
                content = content.replace("@everyone", "").replace("@here", "").strip()

                if not content:
                    await message.channel.send("How can I help you?", reference=message)
                    return

                # Process with agent
                async with message.channel.typing():
                    result = await ag.chat(content, character_mode=char_mode)

                    if result.success:
                        response = result.message
                        if len(response) > 1900:
                            response = response[:1900] + "..."
                        if char_mode:
                            response = f"{ag_config.character.emoji} {response}"
                        await message.channel.send(response, reference=message)
                    else:
                        await message.channel.send(
                            f"Sorry, I encountered an error: {result.error}",
                            reference=message
                        )

            bot = client  # Use client as bot for consistency

            # Store bot and agent
            self.bots[agent_name] = bot
            self.agents[agent_name] = agent

            # Start bot in background
            asyncio.create_task(bot.start(token))
            logger.info(f"Started bot for {agent_name}")

        # Wait for all bots to be ready
        await asyncio.sleep(3)
        self._running = True
        logger.info(f"All bots started: {list(self.bots.keys())}")

    async def stop_all(self) -> None:
        """Stop all running bots."""
        logger.info("Stopping all bots...")
        self._running = False

        for agent_name, bot in self.bots.items():
            try:
                await bot.close()
                logger.info(f"Stopped bot for {agent_name}")
            except Exception as e:
                logger.error(f"Error stopping bot {agent_name}: {e}")

        # Cleanup agents
        for agent_name, agent in self.agents.items():
            try:
                await agent.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up agent {agent_name}: {e}")

        self.bots.clear()
        self.agents.clear()

    async def broadcast_message(self, message: str) -> list[tuple[str, AgentResult]]:
        """Send a message to all agents and collect responses.

        Args:
            message: Message to broadcast

        Returns:
            List of (agent_name, result) tuples for agents that responded
        """
        results = []

        for agent_name, agent in self.agents.items():
            agent_config = self.settings.get_agent(agent_name)
            if not agent_config:
                continue

            # Check if agent is relevant
            is_relevant = await agent.is_relevant(message, agent_config.triggers)
            if not is_relevant:
                continue

            # Get response from agent
            result = await agent.chat(message, character_mode=self.settings.character_mode)
            if result.success:
                results.append((agent_name, result))

        return results

    def is_running(self) -> bool:
        """Check if the coordinator is running."""
        return self._running

    def get_agent(self, name: str) -> BaseAgent | None:
        """Get a specific agent by name."""
        return self.agents.get(name)

    def get_bot(self, name: str) -> discord.Client | None:
        """Get a specific bot by name."""
        return self.bots.get(name)
