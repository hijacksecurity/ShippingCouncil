# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ShippingCouncil is a multi-AI agent system that automates software development tasks. It uses Claude Agent SDK for AI agents, Discord for human-agent communication, and GitHub for code operations.

## Development Commands

```bash
# Install dependencies
uv sync

# Install with dev dependencies
uv sync --dev

# Run the application
uv run python src/main.py

# Run tests
uv run pytest

# Type checking
uv run mypy src/

# Linting
uv run ruff check src/

# Format code
uv run ruff format src/
```

## Project Structure

```
ShippingCouncil/
├── config/                  # Configuration
│   ├── settings.py         # Pydantic settings (loads from .env)
│   └── agents.yaml         # Agent configurations
├── src/                    # Application source code
│   ├── main.py            # Entry point
│   ├── agents/            # AI Agents
│   │   ├── base.py        # Base agent using Claude Agent SDK
│   │   └── developer/     # Developer agent (self-contained)
│   │       ├── agent.py   # Agent implementation
│   │       └── prompts/   # System prompt and templates
│   ├── core/              # Core business logic
│   │   ├── council.py     # Agent orchestration
│   │   └── task.py        # Task management
│   ├── integrations/      # External services
│   │   ├── github/        # GitHub API + git operations
│   │   └── discord/       # Discord bot
│   └── utils/             # Shared utilities
├── tests/                 # Test files
├── docs/                  # Documentation
└── .env                   # Secrets (not committed)
```

## Architecture

### Claude Agent SDK Integration

Agents use the Claude Agent SDK instead of raw API calls:
- Automatic context management
- Built-in tools (Read, Write, Edit, Bash, etc.)
- Custom tools via MCP servers
- Session persistence and conversation continuation

### Self-Contained Agents

Each agent is self-contained in `src/agents/{agent_name}/`:
- `agent.py` - Implementation extending BaseAgent
- `prompts/system.md` - Jinja2 templated system prompt
- `prompts/templates/` - Task-specific templates

The Developer Agent uses:
- Built-in SDK tools for file operations
- Custom MCP tools for git operations (commit, push, create PR)

### Configuration

- `.env` - All secrets (ANTHROPIC_API_KEY, GITHUB_TOKEN, DISCORD_BOT_TOKEN)
- `config/settings.py` - Pydantic settings with validation
- `config/agents.yaml` - Non-sensitive agent configurations

## Key Patterns

- **Claude Agent SDK**: Uses `query()` for tasks, SDK handles tool execution loop
- **MCP Tools**: Custom tools defined with `@tool` decorator and `create_sdk_mcp_server()`
- **Prompts as Markdown**: Jinja2 templates in markdown for easy editing
- **Async-first**: All I/O operations use async/await

## Adding a New Agent

1. Create `src/agents/{agent_name}/` directory
2. Create `agent.py` extending `BaseAgent`:
   - Implement `name` property
   - Implement `get_system_prompt()` method
   - Implement `get_mcp_servers()` for custom tools
3. Create `prompts/system.md` with Jinja2 templating
4. Register in `Council._execute_task()`

## Adding a New Integration

1. Create `src/integrations/{name}/` directory
2. Implement `BaseIntegration` interface
3. Add client and operation files as needed
