"""Pytest fixtures for ShippingCouncil tests."""

import pytest


@pytest.fixture
def mock_settings(monkeypatch):
    """Provide mock settings for testing."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-api-key")
    monkeypatch.setenv("GITHUB_TOKEN", "test-github-token")
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "test-discord-token")
