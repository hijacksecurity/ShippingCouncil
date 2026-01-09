"""DevOps agent implementation using Claude Agent SDK."""

import traceback
from pathlib import Path
from typing import Any

from claude_agent_sdk import (
    ClaudeAgentOptions,
    query,
    AssistantMessage,
    TextBlock,
)

from agents.base import AgentConfig, AgentResult, BaseAgent
from agents.devops.prompts import get_system_prompt, get_chat_prompt
from utils.logging import get_ai_logger


class DevOpsAgent(BaseAgent):
    """DevOps agent (Judy Alvarez) - monitors Docker with read-only access."""

    def __init__(
        self,
        work_dir: Path | None = None,
        model: str = "claude-sonnet-4-20250514",
        character_mode: bool = True,
        triggers: list[str] | None = None,
        allowed_tools: list[str] | None = None,
    ):
        """Initialize the DevOps agent.

        Args:
            work_dir: Working directory for operations
            model: AI model to use (from agents.yaml)
            character_mode: Whether to use Judy Alvarez personality
            triggers: Keywords that activate this agent (from agents.yaml)
            allowed_tools: Tools this agent can use (from agents.yaml)
        """
        # Use tools from config, or sensible defaults
        tools = allowed_tools or ["Read", "Glob", "Grep", "Bash"]

        config = AgentConfig(
            name="devops",
            allowed_tools=tools,
            character_mode=character_mode,
        )

        super().__init__(config, work_dir or Path.cwd())

        self._model = model
        self._character_mode = character_mode
        self._triggers = triggers or []  # Triggers come from agents.yaml

    @property
    def name(self) -> str:
        return "devops"

    @property
    def character_name(self) -> str:
        return "Judy" if self._character_mode else "DevOps"

    def get_system_prompt(self, **context: Any) -> str:
        """Get the DevOps system prompt."""
        context_info = context.get("context_info")
        return get_system_prompt(
            character_mode=self._character_mode,
            context_info=context_info,
        )

    def get_mcp_servers(self) -> dict[str, Any]:
        """Get MCP servers configuration.

        Currently empty - Docker commands run via Bash tool.
        """
        return {}

    async def chat(self, message: str, character_mode: bool | None = None) -> AgentResult:
        """Handle a general chat message using the AI agent.

        Args:
            message: The user's message
            character_mode: Override character mode for this chat

        Returns:
            AgentResult with the response
        """
        ai_log = get_ai_logger()
        use_character = character_mode if character_mode is not None else self._character_mode

        ai_log.info(f"=== Chat request ({self.character_name}) ===")
        ai_log.info(f"User message: {message}")
        ai_log.info(f"Character mode: {use_character}")

        # Build options using tools from config
        options = ClaudeAgentOptions(
            model=self._model,
            system_prompt=get_chat_prompt(character_mode=use_character),
            allowed_tools=self.config.allowed_tools,
            mcp_servers=self.get_mcp_servers(),
            max_turns=5,
            cwd=self.work_dir,
        )

        # Resume from previous session if available (maintains conversation context)
        if self._session_id:
            options.resume = self._session_id
            ai_log.info(f"Resuming session: {self._session_id[:8]}...")

        ai_log.info("Calling Claude Agent SDK...")
        ai_log.debug(f"Options: allowed_tools={options.allowed_tools}")
        ai_log.debug(f"Working directory: {self.work_dir}")
        final_message = ""
        try:
            self._check_api_limit()
            async for msg in query(prompt=message, options=options):
                # Capture session ID for conversation continuity
                if hasattr(msg, "session_id") and msg.session_id:
                    self._session_id = msg.session_id

                ai_log.debug(f"Received message type: {type(msg).__name__}")
                if isinstance(msg, AssistantMessage):
                    for block in msg.content:
                        ai_log.debug(f"Block type: {type(block).__name__}")
                        if isinstance(block, TextBlock):
                            final_message += block.text

            ai_log.info(f"AI response length: {len(final_message)} chars")
            return AgentResult(
                success=True,
                message=final_message,
            )
        except Exception as e:
            tb = traceback.format_exc()
            ai_log.error(f"AI query failed: {e}")
            ai_log.error(f"Traceback:\n{tb}")
            return AgentResult(
                success=False,
                message="Failed to process message",
                error=str(e),
            )

    async def is_relevant(self, message: str, triggers: list[str] | None = None) -> bool:
        """Check if this agent should respond to a message."""
        check_triggers = triggers or self._triggers
        message_lower = message.lower()
        return any(trigger.lower() in message_lower for trigger in check_triggers)

    async def cleanup(self) -> None:
        """Clean up resources."""
        await self.end_conversation()
