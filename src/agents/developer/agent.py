"""Developer agent implementation using Claude Agent SDK."""

from pathlib import Path
from typing import Any

from claude_agent_sdk import (
    ClaudeAgentOptions,
    query,
    AssistantMessage,
    TextBlock,
    tool,
    create_sdk_mcp_server,
)

from agents.base import AgentConfig, AgentResult, BaseAgent
from agents.developer.prompts import get_system_prompt, get_implement_feature_prompt, CHAT_SYSTEM_PROMPT
from integrations.github.client import GitHubClient
from integrations.github.operations import GitOperations


class DeveloperAgent(BaseAgent):
    """Developer agent that writes code and manages git operations using Claude Agent SDK."""

    def __init__(
        self,
        github_token: str,
        work_dir: Path,
        config: AgentConfig | None = None,
    ):
        """Initialize the developer agent.

        Args:
            github_token: GitHub personal access token
            work_dir: Working directory for git operations
            config: Optional agent configuration
        """
        if config is None:
            config = AgentConfig(
                name="developer",
                # Allow built-in tools for file operations plus our custom git tools
                allowed_tools=[
                    "Read",
                    "Write",
                    "Edit",
                    "Glob",
                    "Grep",
                    "Bash",
                    "mcp__git__*",  # Our custom git tools
                ],
            )

        super().__init__(config, work_dir)

        self._github_token = github_token
        self._git_ops: GitOperations | None = None
        self._github_client: GitHubClient | None = None
        self._repo_context: dict[str, Any] = {}
        self._mcp_server: Any = None

    @property
    def name(self) -> str:
        return "developer"

    async def setup_repo(self, repo_url: str, repo_full_name: str) -> Path:
        """Set up the repository for the agent.

        Args:
            repo_url: Repository URL to clone
            repo_full_name: Full repository name (owner/repo)

        Returns:
            Path to the cloned repository
        """
        # Initialize git operations
        self._git_ops = GitOperations(self.work_dir)
        repo_path = self._git_ops.clone(repo_url, self._github_token)

        # Update work_dir to the cloned repo
        self.work_dir = repo_path

        # Initialize GitHub client
        self._github_client = GitHubClient(self._github_token)
        await self._github_client.connect()

        # Store repo context
        self._repo_context = {
            "repo_name": repo_full_name,
            "repo_path": str(repo_path),
        }

        # Create MCP server with git tools
        self._mcp_server = self._create_git_mcp_server(repo_full_name)

        return repo_path

    def _create_git_mcp_server(self, repo_full_name: str) -> Any:
        """Create an MCP server with git tools.

        Args:
            repo_full_name: Full repository name for PR operations

        Returns:
            MCP server instance
        """
        git_ops = self._git_ops
        github_client = self._github_client

        @tool("git_status", "Get the current git status", {})
        async def git_status(args: dict[str, Any]) -> dict[str, Any]:
            if not git_ops:
                return {"content": [{"type": "text", "text": "Repository not set up"}]}
            status = git_ops.status()
            text = (
                f"Branch: {git_ops.current_branch()}\n"
                f"Staged: {', '.join(status['staged']) or 'none'}\n"
                f"Unstaged: {', '.join(status['unstaged']) or 'none'}\n"
                f"Untracked: {', '.join(status['untracked']) or 'none'}"
            )
            return {"content": [{"type": "text", "text": text}]}

        @tool(
            "git_commit",
            "Stage and commit changes",
            {"message": str, "files": list[str] | None},
        )
        async def git_commit(args: dict[str, Any]) -> dict[str, Any]:
            if not git_ops:
                return {"content": [{"type": "text", "text": "Repository not set up"}]}
            git_ops.add(args.get("files"))
            sha = git_ops.commit(args["message"])
            return {"content": [{"type": "text", "text": f"Committed: {sha[:8]}"}]}

        @tool("git_push", "Push commits to the remote repository", {})
        async def git_push(args: dict[str, Any]) -> dict[str, Any]:
            if not git_ops:
                return {"content": [{"type": "text", "text": "Repository not set up"}]}
            git_ops.push()
            return {"content": [{"type": "text", "text": "Pushed to remote"}]}

        @tool("create_branch", "Create and checkout a new branch", {"branch_name": str})
        async def create_branch(args: dict[str, Any]) -> dict[str, Any]:
            if not git_ops:
                return {"content": [{"type": "text", "text": "Repository not set up"}]}
            git_ops.create_branch(args["branch_name"])
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Created and checked out branch: {args['branch_name']}",
                    }
                ]
            }

        @tool(
            "create_pull_request",
            "Create a pull request",
            {"title": str, "body": str, "base": str | None},
        )
        async def create_pull_request(args: dict[str, Any]) -> dict[str, Any]:
            if not git_ops or not github_client:
                return {"content": [{"type": "text", "text": "Repository not set up"}]}
            head = git_ops.current_branch()
            base = args.get("base", "main")
            url = await github_client.create_pull_request(
                repo_full_name=repo_full_name,
                title=args["title"],
                body=args["body"],
                head=head,
                base=base,
            )
            return {"content": [{"type": "text", "text": f"Pull request created: {url}"}]}

        return create_sdk_mcp_server(
            name="git",
            version="1.0.0",
            tools=[git_status, git_commit, git_push, create_branch, create_pull_request],
        )

    def get_system_prompt(self, **context: Any) -> str:
        """Get the developer system prompt.

        Args:
            **context: Context variables for prompt rendering

        Returns:
            The rendered system prompt
        """
        merged_context = {**self._repo_context, **context}
        return get_system_prompt(
            repo_name=merged_context.get("repo_name"),
            branch_name=merged_context.get("branch_name"),
            task_description=merged_context.get("task_description"),
        )

    def get_mcp_servers(self) -> dict[str, Any]:
        """Get MCP servers for custom tools.

        Returns:
            Dictionary of MCP server configurations
        """
        if self._mcp_server:
            return {"git": self._mcp_server}
        return {}

    async def implement_feature(
        self,
        description: str,
        branch_name: str | None = None,
    ) -> dict[str, Any]:
        """Implement a feature.

        Args:
            description: Feature description
            branch_name: Optional branch name (auto-generated if not provided)

        Returns:
            Dictionary with implementation results
        """
        if not self._git_ops:
            return {"success": False, "error": "Repository not set up"}

        # Generate branch name if not provided
        if not branch_name:
            slug = description.lower()[:30]
            slug = "".join(c if c.isalnum() else "-" for c in slug)
            slug = "-".join(filter(None, slug.split("-")))
            branch_name = f"feature/{slug}"

        task_prompt = get_implement_feature_prompt(
            description=description,
            branch_name=branch_name.replace("feature/", ""),
        )

        # Run the agent with context
        context = {
            "branch_name": branch_name,
            "task_description": task_prompt,
        }

        result = await self.run(task_prompt, **context)

        return {
            "success": result.success,
            "message": result.message,
            "branch": branch_name,
            "error": result.error,
            "cost": result.cost,
        }

    async def cleanup(self) -> None:
        """Clean up resources."""
        if self._github_client:
            await self._github_client.disconnect()
        await self.end_conversation()

    async def chat(self, message: str) -> AgentResult:
        """Handle a general chat message using the AI agent.

        This method handles questions and commands that don't require
        a repository to be set up (e.g., "which repos do I have?").

        Args:
            message: The user's message

        Returns:
            AgentResult with the response
        """
        # Ensure GitHub client is connected for repo queries
        if not self._github_client:
            self._github_client = GitHubClient(self._github_token)
            await self._github_client.connect()

        # Get the user's repos to include in context
        try:
            repos = self._github_client.get_user_repos()
            repo_list = [r.full_name for r in repos[:20]]
            repo_context = f"\n\nUser's GitHub repositories:\n" + "\n".join(f"- {r}" for r in repo_list)
        except Exception:
            repo_context = "\n\n(Could not fetch repositories)"

        full_prompt = f"{message}{repo_context}"

        options = ClaudeAgentOptions(
            system_prompt=CHAT_SYSTEM_PROMPT,
            allowed_tools=[],  # Simple chat, no tools needed
            max_turns=1,
        )

        final_message = ""
        try:
            async for msg in query(prompt=full_prompt, options=options):
                if isinstance(msg, AssistantMessage):
                    for block in msg.content:
                        if isinstance(block, TextBlock):
                            final_message += block.text

            return AgentResult(
                success=True,
                message=final_message,
            )
        except Exception as e:
            return AgentResult(
                success=False,
                message="Failed to process message",
                error=str(e),
            )
