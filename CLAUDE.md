# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ShippingCouncil is a multi-AI agent system with character personalities. Each agent runs as its own Discord bot with distinct tools and capabilities. Uses Claude Agent SDK for AI agents, Discord for communication, and GitHub for code operations.

## Development Commands

```bash
# Install dependencies
uv sync

# Run the Discord bots (multi-agent mode)
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
│   ├── settings.py         # Settings (secrets from .env, config from YAML)
│   ├── config.yaml         # App configuration
│   └── agents.yaml         # Agent definitions (characters, tools, triggers)
├── src/
│   ├── main.py             # Entry point (auto-detects single/multi-bot mode)
│   ├── cli.py              # CLI for testing
│   ├── agents/
│   │   ├── base.py         # Base agent with API limit tracking
│   │   ├── backend_dev/    # Rick Sanchez - backend engineer (git tools)
│   │   │   ├── agent.py
│   │   │   └── prompts.py  # Professional + Rick character prompts
│   │   └── devops/         # Judy Alvarez - DevOps engineer (docker read-only)
│   │       ├── agent.py
│   │       └── prompts.py  # Professional + Judy character prompts
│   ├── core/
│   │   ├── council.py      # Agent orchestration
│   │   └── task.py         # Task management
│   ├── integrations/
│   │   ├── base.py         # Base integration interface
│   │   ├── github/         # GitHub API + git operations
│   │   └── discord/
│   │       ├── bot.py      # Discord bot setup
│   │       ├── handlers.py # Message handlers
│   │       └── multi_bot.py # Multi-bot coordinator
│   └── utils/
│       └── logging.py      # Logging to logs/app.log
├── logs/                   # Log files (gitignored except .gitkeep)
├── tests/
└── .env                    # Secrets (not committed)
```

## Agents

| Agent | Character | Tools | Access |
|-------|-----------|-------|--------|
| Backend Dev | Rick Sanchez (Rick & Morty) | Read, Write, Edit, Glob, Grep, Bash, mcp__git__* | Full write |
| DevOps | Judy Alvarez (Cyberpunk 2077) | Read, Glob, Grep, Bash | Read only (docker via Bash) |

### Character Mode

Toggle in `config/agents.yaml`:
```yaml
global:
  character_mode: true  # false for professional mode
  max_api_calls: 50     # Prevent runaway loops
```

Each agent has two prompts: professional and character. Character mode adds personality without affecting task completion.

## Configuration

**Secrets** (`.env`):
```
ANTHROPIC_API_KEY=your-key
GITHUB_TOKEN=your-token

# Multi-bot mode (each agent = separate bot)
DISCORD_BACKEND_BOT_TOKEN=rick-bot-token
DISCORD_DEVOPS_BOT_TOKEN=judy-bot-token

# Legacy single-bot mode
DISCORD_BOT_TOKEN=your-token
```

**Agent Config** (`config/agents.yaml`):
```yaml
agents:
  backend_dev:
    role: "Senior Backend Engineer"
    model: "claude-sonnet-4-20250514"  # AI model per agent
    discord_token_env: "DISCORD_BACKEND_BOT_TOKEN"
    character:
      name: "Rick Sanchez"
      emoji: "🧪"
    triggers: [backend, api, git, code, repo, feature]
    tools: [Read, Write, Edit, Glob, Grep, Bash, "mcp__git__*"]

  devops:
    role: "Senior DevOps Engineer"
    model: "claude-sonnet-4-20250514"
    discord_token_env: "DISCORD_DEVOPS_BOT_TOKEN"
    character:
      name: "Judy Alvarez"
      emoji: "⚡"
    triggers: [docker, container, k8s, deployment, devops, logs]
    tools: [Read, Glob, Grep, Bash]
```

## Discord Usage

- **Direct @mention** (`@Rick`, `@Judy`): That specific agent responds
- **@everyone / @here**: All agents respond
- **Regular message**: All agents evaluate based on triggers, relevant ones respond
- **DM**: The agent you DM responds directly
- **Slash commands**: `/task`, `/status`, `/repos`, `/cancel`, `/approve`

Example routing:
- "Help me with this Python code" -> Rick responds (triggers: python, code)
- "Check the docker logs" -> Judy responds (triggers: docker, logs)
- "Hello everyone" -> No response (no triggers match)

## Key Patterns

- **Single source of truth**: All agent config lives in `agents.yaml` (model, triggers, tools)
- **Model per agent**: Each agent can use a different Claude model
- **Session continuity**: Agents use `session_id` to maintain conversation context across messages
- **Character mode toggle**: Professional or personality prompts via global config
- **API call limits**: Max 50 calls per session, warning at 80%
- **Read-only tools**: DevOps agent can only view Docker, not modify
- **Multi-bot coordinator**: Each agent is its own Discord bot instance
- **Trigger-based routing**: Agents respond to keywords in their domain (substring match)

## Message Flow

1. Discord message received by all bot clients
2. Each bot's `on_message` handler evaluates:
   - Direct mention → respond
   - @everyone/@here → respond
   - DM → respond
   - Otherwise → check triggers, respond if match
3. Agent's `chat()` method called with message
4. Claude Agent SDK `query()` with model, tools, system prompt
5. Session ID captured for conversation continuity
6. Response sent via `message.reply()`

## Testing Agents

Interactive CLI for testing agents without Discord:

```bash
# Chat with Rick (backend_dev)
uv run python src/cli.py chat backend_dev

# Chat with Judy (devops)
uv run python src/cli.py chat devops

# Professional mode (no character)
uv run python src/cli.py chat backend_dev --no-character

# Override model
uv run python src/cli.py chat devops --model claude-haiku-3-5-20241022
```

Commands during chat:
- `reset` - Clear conversation history
- `info` - Show agent info (model, API calls, session)
- `quit` / `exit` - End conversation

For pytest, use `AgentTestHarness` from `tests/agents/test_utils.py`:

```python
from tests.agents.test_utils import AgentTestHarness

async def test_backend_dev():
    harness = AgentTestHarness("backend_dev")
    result = await harness.send("What repos do we have?")
    assert result.success
    await harness.cleanup()
```

## Debugging

- **AI logs**: `logs/ai_debug.log` - SDK calls, prompts, responses
- **App logs**: `logs/app.log` - General application logs
- **Discord debug**: Set `log_level: DEBUG` in config.yaml

## Adding a New Agent

1. Create `src/agents/{name}/` directory with `agent.py` and `prompts.py`
2. Extend `BaseAgent`, implement `name`, `get_system_prompt()`, `get_mcp_servers()`
3. Add character prompt with personality, catchphrases
4. Add to `config/agents.yaml` with role, model, triggers, tools
5. Create new Discord bot in Developer Portal (enable Message Content Intent)
6. Add `DISCORD_{NAME}_BOT_TOKEN` to `.env`
7. Register in `MultiBotCoordinator._create_agent()`
