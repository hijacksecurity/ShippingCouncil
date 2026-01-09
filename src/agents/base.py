"""Base agent interface using Claude Agent SDK."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
    query,
)


@dataclass
class AgentConfig:
    """Configuration for an agent."""

    name: str
    allowed_tools: list[str] = field(default_factory=list)
    max_turns: int | None = None


@dataclass
class AgentResult:
    """Result from an agent execution."""

    success: bool
    message: str
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    cost: float | None = None


class BaseAgent(ABC):
    """Abstract base class for all AI agents using Claude Agent SDK."""

    def __init__(self, config: AgentConfig, work_dir: Path | None = None):
        """Initialize the agent.

        Args:
            config: Agent configuration
            work_dir: Working directory for agent operations
        """
        self.config = config
        self.work_dir = work_dir or Path.cwd()
        self._session_id: str | None = None
        self._client: ClaudeSDKClient | None = None

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the agent name."""
        ...

    @abstractmethod
    def get_system_prompt(self, **context: Any) -> str:
        """Get the system prompt for this agent.

        Args:
            **context: Context variables for prompt rendering

        Returns:
            The system prompt string
        """
        ...

    @abstractmethod
    def get_mcp_servers(self) -> dict[str, Any]:
        """Get MCP servers for custom tools.

        Returns:
            Dictionary of MCP server configurations
        """
        ...

    def get_options(self, **context: Any) -> ClaudeAgentOptions:
        """Build agent options for the SDK.

        Args:
            **context: Context variables

        Returns:
            Configured ClaudeAgentOptions
        """
        return ClaudeAgentOptions(
            allowed_tools=self.config.allowed_tools,
            system_prompt=self.get_system_prompt(**context),
            mcp_servers=self.get_mcp_servers(),
            max_turns=self.config.max_turns,
            cwd=self.work_dir,
        )

    async def run(self, task: str, **context: Any) -> AgentResult:
        """Run the agent on a task using query().

        Args:
            task: The task description
            **context: Additional context for the agent

        Returns:
            AgentResult with the outcome
        """
        options = self.get_options(**context)

        # Resume from previous session if available
        if self._session_id:
            options.resume = self._session_id

        final_message = ""
        cost = None

        try:
            async for message in query(prompt=task, options=options):
                # Capture session ID for potential resume
                if hasattr(message, "session_id"):
                    self._session_id = message.session_id

                # Collect text responses
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            final_message += block.text

                # Capture result info
                if isinstance(message, ResultMessage):
                    cost = getattr(message, "cost_usd", None)

            return AgentResult(
                success=True,
                message=final_message,
                cost=cost,
            )

        except Exception as e:
            return AgentResult(
                success=False,
                message="Agent execution failed",
                error=str(e),
            )

    async def start_conversation(self) -> None:
        """Start a multi-turn conversation session."""
        self._client = ClaudeSDKClient()
        await self._client.connect()

    async def send_message(self, message: str, **context: Any) -> AgentResult:
        """Send a message in an ongoing conversation.

        Args:
            message: The message to send
            **context: Additional context

        Returns:
            AgentResult with the response
        """
        if not self._client:
            await self.start_conversation()

        options = self.get_options(**context)
        await self._client.query(message, options=options)

        final_message = ""
        cost = None

        try:
            async for msg in self._client.receive_response():
                if isinstance(msg, AssistantMessage):
                    for block in msg.content:
                        if isinstance(block, TextBlock):
                            final_message += block.text

                if isinstance(msg, ResultMessage):
                    cost = getattr(msg, "cost_usd", None)

            return AgentResult(
                success=True,
                message=final_message,
                cost=cost,
            )

        except Exception as e:
            return AgentResult(
                success=False,
                message="Message failed",
                error=str(e),
            )

    async def end_conversation(self) -> None:
        """End the conversation session."""
        if self._client:
            await self._client.disconnect()
            self._client = None

    def reset(self) -> None:
        """Reset the agent state."""
        self._session_id = None
