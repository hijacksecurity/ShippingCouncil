"""Reusable utilities for agent testing in pytest.

Usage in tests:
    from tests.agents.test_utils import AgentTestHarness

    async def test_backend_dev():
        harness = AgentTestHarness("backend_dev")
        result = await harness.send("What repos do we have?")
        assert result.success
        await harness.cleanup()
"""

import sys
from pathlib import Path
from typing import Any

# Ensure src is in path for imports
_src_path = Path(__file__).parent.parent.parent / "src"
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))

# Ensure config is in path
_config_path = Path(__file__).parent.parent.parent / "config"
if str(_config_path.parent) not in sys.path:
    sys.path.insert(0, str(_config_path.parent))


class AgentTestHarness:
    """Test harness for running agent tests.

    Provides a clean interface for testing agents programmatically
    without Discord integration.
    """

    def __init__(
        self,
        agent_name: str,
        model: str | None = None,
        character_mode: bool = True,
    ):
        """Initialize test harness for an agent.

        Args:
            agent_name: Name of agent to test (backend_dev, devops)
            model: Override model (defaults to config)
            character_mode: Enable character personality
        """
        from config.settings import get_settings
        from agents.backend_dev import BackendDevAgent
        from agents.devops import DevOpsAgent

        self.agent_name = agent_name
        self.settings = get_settings()
        self.agent_config = self.settings.get_agent(agent_name)

        if not self.agent_config:
            raise ValueError(f"Unknown agent: {agent_name}")

        self.model = model or self.agent_config.model
        self.character_mode = character_mode
        self.conversation_history: list[dict[str, str]] = []

        # Create agent
        if agent_name == "backend_dev":
            self.agent = BackendDevAgent(
                github_token=self.settings.github_token,
                work_dir=self.settings.work_dir,
                model=self.model,
                character_mode=self.character_mode,
                triggers=self.agent_config.triggers,
                allowed_tools=self.agent_config.tools,
            )
        elif agent_name == "devops":
            self.agent = DevOpsAgent(
                work_dir=self.settings.work_dir,
                model=self.model,
                character_mode=self.character_mode,
                triggers=self.agent_config.triggers,
                allowed_tools=self.agent_config.tools,
            )
        else:
            raise ValueError(f"Agent '{agent_name}' not implemented")

    async def send(self, message: str):
        """Send a message to the agent and get response.

        Args:
            message: User message to send

        Returns:
            AgentResult with response
        """
        self.conversation_history.append({"role": "user", "content": message})
        result = await self.agent.chat(message, character_mode=self.character_mode)
        self.conversation_history.append({"role": "assistant", "content": result.message})
        return result

    async def test_trigger(self, message: str) -> bool:
        """Test if a message triggers this agent."""
        return await self.agent.is_relevant(message, self.agent_config.triggers)

    def reset(self) -> None:
        """Reset conversation state."""
        self.agent.reset()
        self.conversation_history.clear()

    async def cleanup(self) -> None:
        """Clean up agent resources."""
        await self.agent.cleanup()

    @property
    def api_calls(self) -> int:
        """Get number of API calls made."""
        return self.agent._api_call_count

    @property
    def session_id(self) -> str | None:
        """Get current session ID."""
        return self.agent._session_id

    def get_info(self) -> dict[str, Any]:
        """Get agent info for debugging."""
        return {
            "agent_name": self.agent_name,
            "character": self.agent_config.character.name,
            "model": self.model,
            "character_mode": self.character_mode,
            "api_calls": self.api_calls,
            "session_id": self.session_id,
            "triggers": self.agent_config.triggers,
            "tools": self.agent_config.tools,
            "conversation_length": len(self.conversation_history),
        }
