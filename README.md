# ShippingCouncil

Multi-AI agent system that automates software development tasks. Uses Claude Agent SDK for AI agents, Discord for communication, and GitHub for code operations.

## Features

- **Developer Agent**: Takes requirements, writes code, creates branches, and opens PRs
- **Discord Integration**: Slash commands for task management (`/task`, `/status`, `/approve`)
- **GitHub Integration**: Clone repos, commit changes, push, create pull requests
- **CLI Interface**: Test agents without Discord

## Quick Start

```bash
# Install dependencies
uv sync

# Copy and configure secrets
cp .env.example .env
# Edit .env with your API keys

# Test the CLI
python src/cli.py --test

# List your GitHub repos
python src/cli.py --repos

# Run a task
python src/cli.py "Explain this codebase"
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
  guild_id: null

github:
  default_repo: null
```

## Project Structure

```
├── config/           # Configuration files
├── src/
│   ├── agents/       # AI agents (developer, etc.)
│   ├── core/         # Council orchestration, task management
│   ├── integrations/ # GitHub, Discord
│   └── cli.py        # CLI interface
└── tests/
```

## License

MIT
test