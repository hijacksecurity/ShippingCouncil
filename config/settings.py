"""Application settings - secrets from .env, config from config.yaml."""

from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _load_config() -> dict[str, Any]:
    """Load configuration from config.yaml."""
    config_path = Path(__file__).parent / "config.yaml"
    if config_path.exists():
        with open(config_path) as f:
            return yaml.safe_load(f) or {}
    return {}


_config = _load_config()


class Secrets(BaseSettings):
    """Secrets loaded from .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    anthropic_api_key: str = Field(..., description="Anthropic API key")
    github_token: str = Field("", description="GitHub personal access token")
    discord_bot_token: str = Field("", description="Discord bot token (optional)")


class Settings:
    """Application settings combining secrets and config."""

    def __init__(self, secrets: Secrets, config: dict[str, Any]):
        self._secrets = secrets
        self._config = config

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


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    secrets = Secrets()
    return Settings(secrets, _config)
