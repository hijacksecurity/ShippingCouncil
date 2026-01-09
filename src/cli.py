"""CLI interface for testing the developer agent without Discord."""

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

        from agents.developer import DeveloperAgent

        agent = DeveloperAgent(
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


def main():
    parser = argparse.ArgumentParser(
        description="ShippingCouncil CLI - Test the developer agent"
    )
    parser.add_argument(
        "task",
        nargs="?",
        help="Task for the developer agent",
    )
    parser.add_argument(
        "--repo",
        "-r",
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

    if args.test:
        asyncio.run(test_agent_sdk())
    elif args.repos:
        list_repos()
    elif args.task:
        asyncio.run(run_developer_task(args.task, args.repo))
    else:
        parser.print_help()
        print("\nExamples:")
        print("  python src/cli.py --test")
        print("  python src/cli.py --repos")
        print('  python src/cli.py "Explain this codebase"')
        print('  python src/cli.py "Add a README" --repo owner/repo')


if __name__ == "__main__":
    main()
