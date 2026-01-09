"""Application settings - secrets from .env, config from config.yaml."""

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import yaml
from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load .env into os.environ so agent configs can use os.getenv()
load_dotenv()


def _load_config() -> dict[str, Any]:
    """Load configuration from config.yaml."""
    config_path = Path(__file__).parent / "config.yaml"
    if config_path.exists():
        with open(config_path) as f:
            return yaml.safe_load(f) or {}
    return {}


def _load_agents_config() -> dict[str, Any]:
    """Load agent configurations from agents.yaml."""
    config_path = Path(__file__).parent / "agents.yaml"
    if config_path.exists():
        with open(config_path) as f:
            return yaml.safe_load(f) or {}
    return {}


@dataclass
class CharacterConfig:
    """Character personality configuration."""

    name: str
    source: str
    emoji: str
    color: str
    personality: str = ""
    catchphrases: list[str] = field(default_factory=list)


@dataclass
class AgentConfig:
    """Configuration for a single agent."""

    name: str  # Agent identifier (e.g., "backend_dev")
    role: str  # Role description
    discord_token_env: str  # Environment variable name for Discord token
    discord_bot_name: str  # Display name for the bot
    character: CharacterConfig
    triggers: list[str]  # Keywords that activate this agent
    tools: list[str]  # Allowed tools for this agent

    @property
    def discord_token(self) -> str | None:
        """Get the Discord token from environment."""
        return os.getenv(self.discord_token_env)

    @classmethod
    def from_dict(cls, name: str, data: dict[str, Any]) -> "AgentConfig":
        """Create AgentConfig from dictionary."""
        char_data = data.get("character", {})
        character = CharacterConfig(
            name=char_data.get("name", name),
            source=char_data.get("source", ""),
            emoji=char_data.get("emoji", ""),
            color=char_data.get("color", ""),
            personality=char_data.get("personality", ""),
            catchphrases=char_data.get("catchphrases", []),
        )
        return cls(
            name=name,
            role=data.get("role", ""),
            discord_token_env=data.get("discord_token_env", ""),
            discord_bot_name=data.get("discord_bot_name", name),
            character=character,
            triggers=data.get("triggers", []),
            tools=data.get("tools", []),
        )


_config = _load_config()
_agents_config = _load_agents_config()


class Secrets(BaseSettings):
    """Secrets loaded from .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Allow extra env vars for agent-specific tokens
    )

    anthropic_api_key: str = Field(..., description="Anthropic API key")
    github_token: str = Field("", description="GitHub personal access token")
    discord_bot_token: str = Field("", description="Discord bot token (legacy single-bot)")

    # Multi-agent bot tokens (loaded dynamically via AgentConfig.discord_token)
    discord_backend_bot_token: str = Field("", description="Rick bot token")
    discord_devops_bot_token: str = Field("", description="Judy bot token")


class Settings:
    """Application settings combining secrets and config."""

    def __init__(
        self,
        secrets: Secrets,
        config: dict[str, Any],
        agents_config: dict[str, Any],
    ):
        self._secrets = secrets
        self._config = config
        self._agents_config = agents_config
        self._parsed_agents: dict[str, AgentConfig] | None = None

    # Secrets (from .env)
    @property
    def anthropic_api_key(self) -> str:
        return self._secrets.anthropic_api_key

    @property
    def github_token(self) -> str:
        return self._secrets.github_token

    @property
    def discord_bot_token(self) -> str:
        return self._secrets.discord_bot_token

    # Config (from config.yaml)
    @property
    def log_level(self) -> Literal["DEBUG", "INFO", "WARNING", "ERROR"]:
        return self._config.get("app", {}).get("log_level", "INFO")

    @property
    def work_dir(self) -> Path:
        path = self._config.get("app", {}).get("work_dir", "/tmp/shipping-council-work")
        return Path(path)

    @property
    def discord_guild_id(self) -> str | None:
        return self._config.get("discord", {}).get("guild_id")

    @property
    def default_repo(self) -> str | None:
        return self._config.get("github", {}).get("default_repo")

    # Paths
    @property
    def project_root(self) -> Path:
        return Path(__file__).parent.parent

    @property
    def src_dir(self) -> Path:
        return self.project_root / "src"

    @property
    def config_dir(self) -> Path:
        return self.project_root / "config"

    # Agent configuration (from agents.yaml)
    @property
    def max_api_calls(self) -> int:
        """Global max API calls per session."""
        return self._agents_config.get("global", {}).get("max_api_calls", 50)

    @property
    def character_mode(self) -> bool:
        """Global character mode toggle."""
        return self._agents_config.get("global", {}).get("character_mode", True)

    @property
    def agents(self) -> dict[str, AgentConfig]:
        """Get all configured agents."""
        if self._parsed_agents is None:
            self._parsed_agents = {}
            agents_data = self._agents_config.get("agents", {})
            for name, data in agents_data.items():
                self._parsed_agents[name] = AgentConfig.from_dict(name, data)
        return self._parsed_agents

    def get_agent(self, name: str) -> AgentConfig | None:
        """Get a specific agent configuration by name."""
        return self.agents.get(name)

    def get_agent_by_trigger(self, message: str) -> list[AgentConfig]:
        """Get agents whose triggers match keywords in the message."""
        message_lower = message.lower()
        matching = []
        for agent in self.agents.values():
            for trigger in agent.triggers:
                if trigger.lower() in message_lower:
                    matching.append(agent)
                    break
        return matching


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    secrets = Secrets()
    return Settings(secrets, _config, _agents_config)
