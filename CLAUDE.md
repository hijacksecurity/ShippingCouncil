# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ShippingCouncil is a multi-AI agent system that automates software development tasks. It uses Claude Agent SDK for AI agents, Discord for human-agent communication, and GitHub for code operations.

## Development Commands

```bash
# Install dependencies
uv sync

# Run the Discord bot
uv run python src/main.py

# Run CLI (for testing without Discord)
uv run python src/cli.py --test
uv run python src/cli.py --repos
uv run python src/cli.py "your task here" --repo owner/repo

# Run tests
uv run pytest

# Type checking
uv run mypy src/

# Linting and formatting
uv run ruff check src/
uv run ruff format src/
```

## Project Structure

```
ShippingCouncil/
├── config/
│   ├── settings.py         # Settings (secrets from .env, config from config.yaml)
│   └── config.yaml         # Non-sensitive configuration
├── src/
│   ├── main.py             # Discord bot entry point
│   ├── cli.py              # CLI for testing
│   ├── agents/
│   │   ├── base.py         # Base agent using Claude Agent SDK
│   │   └── developer/
│   │       ├── agent.py    # Developer agent implementation
│   │       └── prompts.py  # Simple prompt templates
│   ├── core/
│   │   ├── council.py      # Agent orchestration
│   │   └── task.py         # Task management
│   ├── integrations/
│   │   ├── base.py         # Base integration interface
│   │   ├── github/         # GitHub API + git operations
│   │   └── discord/        # Discord bot + handlers
│   └── utils/
│       └── logging.py      # Logging setup
├── tests/
└── .env                    # Secrets (not committed)
```

## Configuration

**Secrets** (`.env`):
```
ANTHROPIC_API_KEY=your-key
GITHUB_TOKEN=your-token
DISCORD_BOT_TOKEN=your-token
```

**Config** (`config/config.yaml`):
```yaml
app:
  log_level: INFO
  work_dir: /tmp/shipping-council-work
discord:
  guild_id: "your-guild-id"  # For faster slash command sync
github:
  default_repo: null
```

## Architecture

### Claude Agent SDK Integration

Agents use the Claude Agent SDK:
- Automatic context management and tool execution
- Built-in tools (Read, Write, Edit, Bash, Glob, Grep)
- Custom tools via MCP servers
- Session persistence

### Developer Agent

The developer agent (`src/agents/developer/`) can:
- Chat and answer questions (e.g., "which repos do I have?")
- Implement features on GitHub repos
- Create branches, commits, and pull requests

### Discord Integration

- Mention the bot to chat: `@ShippingCouncilDev which repos do I have?`
- Slash commands: `/task`, `/status`, `/repos`, `/cancel`, `/approve`

## Key Patterns

- **Simple prompts**: Plain Python strings in `prompts.py`, no complex templating
- **Async-first**: All I/O operations use async/await
- **Self-contained agents**: Each agent has its own folder with agent.py and prompts.py

## Adding a New Agent

1. Create `src/agents/{name}/` directory
2. Create `agent.py` extending `BaseAgent`
3. Create `prompts.py` with simple string templates
4. Register in `Council._execute_task()`
