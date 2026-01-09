# ShippingCouncil

Multi-AI agent system for software development with character personalities. Each agent runs as its own Discord bot with distinct tools and capabilities.

## Features

- **Multi-Agent Architecture**: Multiple specialized AI agents, each as a separate Discord bot
- **Character Personalities**: Agents have fun character modes (Rick Sanchez, Judy Alvarez) or professional mode
- **Trigger-Based Routing**: Messages automatically route to relevant agents based on keywords
- **Tool Isolation**: Each agent has specific tool permissions (backend dev can write code, devops is read-only)
- **API Limits**: Built-in safeguards prevent runaway loops (max 50 calls per session)

## Agents

| Agent | Character | Role | Tools |
|-------|-----------|------|-------|
| Backend Dev | Rick Sanchez (Rick & Morty) | Senior Backend Engineer | Read, Write, Edit, Bash, Git |
| DevOps | Judy Alvarez (Cyberpunk 2077) | Senior DevOps Engineer | Read, Glob, Grep, Bash (docker) |

## Quick Start

```bash
# Install dependencies
uv sync

# Copy and configure secrets
cp .env.example .env
# Edit .env with your API keys and Discord bot tokens

# Run Discord bots (multi-agent mode)
uv run python src/main.py

# Or test with CLI (no Discord needed)
uv run python src/cli.py --test
uv run python src/cli.py "Explain this codebase"
```

## Configuration

**Secrets** (`.env`):
```bash
ANTHROPIC_API_KEY=your-key
GITHUB_TOKEN=your-token

# Each agent needs its own Discord bot token
DISCORD_BACKEND_BOT_TOKEN=rick-bot-token
DISCORD_DEVOPS_BOT_TOKEN=judy-bot-token
```

**Agent Config** (`config/agents.yaml`):
```yaml
global:
  character_mode: true  # Toggle character personalities
  max_api_calls: 50     # Prevent runaway loops

agents:
  backend_dev:
    role: "Senior Backend Engineer"
    model: "claude-sonnet-4-20250514"  # AI model per agent
    discord_bot_name: "Rick"
    triggers: [backend, api, python, code, git, repo, bug, fix]
    tools: [Read, Write, Edit, Glob, Grep, Bash]

  devops:
    role: "Senior DevOps Engineer"
    model: "claude-sonnet-4-20250514"
    discord_bot_name: "Judy"
    triggers: [docker, container, k8s, deployment, devops]
    tools: [Read, Glob, Grep, Bash]
```

## Discord Usage

- **Direct mention** (`@Rick` or `@Judy`): That specific agent responds
- **@everyone / @here**: All agents respond
- **Regular message**: All agents evaluate based on triggers, relevant ones respond
- **DM**: The agent you DM responds directly

Example:
- "Help me fix this Python bug" -> Rick responds (matches: python, bug, fix)
- "Check the docker containers" -> Judy responds (matches: docker, container)
- "What's up?" -> No response (no triggers match)

## Project Structure

```
ShippingCouncil/
├── config/
│   ├── settings.py      # Settings loader
│   ├── config.yaml      # App configuration
│   └── agents.yaml      # Agent definitions
├── src/
│   ├── main.py          # Entry point
│   ├── cli.py           # CLI for testing
│   ├── agents/
│   │   ├── base.py      # Base agent class
│   │   ├── backend_dev/ # Rick - backend engineer
│   │   └── devops/      # Judy - DevOps engineer
│   └── integrations/
│       ├── github/      # GitHub API + git operations
│       └── discord/     # Discord bots + multi-bot coordinator
└── tests/
```

## Adding a New Agent

1. Create `src/agents/{name}/` with `agent.py` and `prompts.py`
2. Add agent config to `config/agents.yaml`
3. Create Discord bot in Developer Portal (enable Message Content Intent)
4. Add `DISCORD_{NAME}_BOT_TOKEN` to `.env`
5. Register in `MultiBotCoordinator._create_agent()`

## License

MIT
