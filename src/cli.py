"""CLI interface for testing agents without Discord.

Usage:
    # Interactive chat with an agent
    uv run python src/cli.py chat backend_dev
    uv run python src/cli.py chat devops --no-character

    # Run a single task
    uv run python src/cli.py "Explain this codebase"

    # Test SDK
    uv run python src/cli.py --test

    # List repos
    uv run python src/cli.py --repos
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Fix SSL certificates for macOS
import certifi
os.environ["SSL_CERT_FILE"] = certifi.where()

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from config.settings import get_settings
from utils.logging import get_logger, setup_logging


async def test_agent_sdk():
    """Test that the Claude Agent SDK is working."""
    from claude_agent_sdk import query, ClaudeAgentOptions

    print("Testing Claude Agent SDK...")
    print("-" * 40)

    async for message in query(
        prompt="Say 'Agent SDK is working!' and nothing else.",
        options=ClaudeAgentOptions(
            allowed_tools=[],
            max_turns=1,
        )
    ):
        if hasattr(message, "content"):
            for block in message.content:
                if hasattr(block, "text"):
                    print(f"Agent: {block.text}")

    print("-" * 40)
    print("SDK test complete!")


async def run_developer_task(task: str, repo: str | None = None):
    """Run a task with the developer agent.

    Args:
        task: Task description
        repo: Optional GitHub repo (owner/repo format)
    """
    settings = get_settings()
    setup_logging(settings.log_level)
    logger = get_logger("cli")

    print(f"\n{'='*50}")
    print("ShippingCouncil Developer Agent")
    print(f"{'='*50}\n")

    if repo:
        print(f"Repository: {repo}")

        if not settings.github_token:
            print("ERROR: GITHUB_TOKEN not set in .env")
            print("Add your GitHub token to work with repositories.")
            return

        from agents.backend_dev import BackendDevAgent

        agent = BackendDevAgent(
            github_token=settings.github_token,
            work_dir=settings.work_dir,
        )

        print(f"Work directory: {settings.work_dir}")
        print(f"\nTask: {task}\n")
        print("-" * 40)

        try:
            # Setup repo
            repo_url = f"https://github.com/{repo}"
            print(f"Cloning {repo}...")
            await agent.setup_repo(repo_url, repo)
            print("Repository ready.\n")

            # Run the task
            print("Running task...")
            result = await agent.implement_feature(task)

            print("\n" + "-" * 40)
            print("RESULT:")
            print(f"  Success: {result['success']}")
            print(f"  Branch: {result.get('branch', 'N/A')}")
            if result.get('error'):
                print(f"  Error: {result['error']}")
            if result.get('cost'):
                print(f"  Cost: ${result['cost']:.4f}")
            print(f"\nMessage:\n{result.get('message', 'No message')[:500]}")

        finally:
            await agent.cleanup()

    else:
        # No repo - just test the SDK
        print(f"Task: {task}\n")
        print("(No repo specified - running as simple query)\n")
        print("-" * 40)

        from claude_agent_sdk import query, ClaudeAgentOptions

        async for message in query(
            prompt=task,
            options=ClaudeAgentOptions(
                allowed_tools=["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
                cwd=Path.cwd(),
            )
        ):
            if hasattr(message, "content"):
                for block in message.content:
                    if hasattr(block, "text"):
                        print(block.text)


def list_repos():
    """List GitHub repositories."""
    from config.settings import get_settings
    settings = get_settings()

    if not settings.github_token:
        print("ERROR: GITHUB_TOKEN not set in .env")
        return

    from github import Auth, Github
    g = Github(auth=Auth.Token(settings.github_token))
    user = g.get_user()

    print(f"\nRepos for {user.login}:")
    print("-" * 40)
    for repo in user.get_repos(sort="updated"):
        print(f"  {repo.full_name}")
    print()


def create_agent(agent_name: str, settings, model: str | None, character_mode: bool):
    """Create an agent instance by name."""
    from agents.backend_dev import BackendDevAgent
    from agents.devops import DevOpsAgent

    agent_config = settings.get_agent(agent_name)
    if not agent_config:
        raise ValueError(f"Unknown agent: {agent_name}. Available: {list(settings.agents.keys())}")

    use_model = model or agent_config.model

    if agent_name == "backend_dev":
        return BackendDevAgent(
            github_token=settings.github_token,
            work_dir=settings.work_dir,
            model=use_model,
            character_mode=character_mode,
            triggers=agent_config.triggers,
            allowed_tools=agent_config.tools,
        )
    elif agent_name == "devops":
        return DevOpsAgent(
            work_dir=settings.work_dir,
            model=use_model,
            character_mode=character_mode,
            triggers=agent_config.triggers,
            allowed_tools=agent_config.tools,
        )
    else:
        raise ValueError(f"Agent '{agent_name}' not implemented")


async def chat_with_agent(agent_name: str, model: str | None, character_mode: bool):
    """Interactive chat with an agent."""
    settings = get_settings()
    agent_config = settings.get_agent(agent_name)
    agent = create_agent(agent_name, settings, model, character_mode)

    char_name = agent_config.character.name if character_mode else agent_name

    print(f"\n{'='*60}")
    print(f"Agent: {agent_name} ({char_name})")
    print(f"Model: {agent._model}")
    print(f"Character mode: {character_mode}")
    print(f"Triggers: {', '.join(agent_config.triggers)}")
    print(f"Tools: {', '.join(agent_config.tools)}")
    print(f"{'='*60}")
    print("Commands: 'quit', 'reset', 'info'")
    print(f"{'='*60}\n")

    try:
        while True:
            try:
                user_input = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n\nGoodbye!")
                break

            if not user_input:
                continue

            if user_input.lower() in ("quit", "exit"):
                print("\nGoodbye!")
                break

            if user_input.lower() == "reset":
                agent.reset()
                print("[Session reset]\n")
                continue

            if user_input.lower() == "info":
                print(f"\n[Agent Info]")
                print(f"  Name: {agent_name}")
                print(f"  Character: {char_name}")
                print(f"  Model: {agent._model}")
                print(f"  API calls: {agent._api_call_count}/{agent.config.max_api_calls}")
                print(f"  Session ID: {agent._session_id or 'None'}")
                print(f"  Triggers: {', '.join(agent_config.triggers)}")
                print(f"  Tools: {', '.join(agent_config.tools)}")
                print()
                continue

            try:
                result = await agent.chat(user_input, character_mode=character_mode)
                if result.success:
                    print(f"{char_name}: {result.message}\n")
                else:
                    print(f"[Error: {result.error}]\n")
            except Exception as e:
                print(f"[Exception: {e}]\n")
    finally:
        await agent.cleanup()


def main():
    parser = argparse.ArgumentParser(
        description="ShippingCouncil CLI - Test agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run python src/cli.py chat backend_dev       # Chat with Rick
  uv run python src/cli.py chat devops            # Chat with Judy
  uv run python src/cli.py chat devops --no-character
  uv run python src/cli.py --test                 # Test SDK
  uv run python src/cli.py --repos                # List repos
  uv run python src/cli.py "Explain this code"    # One-off task
        """
    )

    subparsers = parser.add_subparsers(dest="command")

    # Chat subcommand
    chat_parser = subparsers.add_parser("chat", help="Interactive chat with an agent")
    chat_parser.add_argument(
        "agent",
        choices=["backend_dev", "devops"],
        help="Agent to chat with (backend_dev=Rick, devops=Judy)"
    )
    chat_parser.add_argument(
        "--no-character",
        action="store_true",
        help="Disable character personality"
    )
    chat_parser.add_argument(
        "--model",
        help="Override model (e.g., claude-haiku-3-5-20241022)"
    )

    # Legacy arguments
    parser.add_argument(
        "task",
        nargs="?",
        help="Task for the developer agent",
    )
    parser.add_argument(
        "--repo", "-r",
        help="GitHub repository (owner/repo format)",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run a quick SDK test",
    )
    parser.add_argument(
        "--repos",
        action="store_true",
        help="List your GitHub repositories",
    )

    args = parser.parse_args()

    if args.command == "chat":
        asyncio.run(chat_with_agent(
            args.agent,
            args.model,
            not args.no_character
        ))
    elif args.test:
        asyncio.run(test_agent_sdk())
    elif args.repos:
        list_repos()
    elif args.task:
        asyncio.run(run_developer_task(args.task, args.repo))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
