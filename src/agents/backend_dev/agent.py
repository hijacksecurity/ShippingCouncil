"""Backend developer agent implementation using Claude Agent SDK."""

import traceback
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
from agents.backend_dev.prompts import (
    get_system_prompt,
    get_chat_prompt,
    get_implement_feature_prompt,
)
from integrations.github.client import GitHubClient
from integrations.github.operations import GitOperations
from utils.logging import get_ai_logger


class BackendDevAgent(BaseAgent):
    """Backend developer agent (Rick Sanchez) - writes code and manages git operations."""

    def __init__(
        self,
        github_token: str,
        work_dir: Path,
        character_mode: bool = True,
        triggers: list[str] | None = None,
        allowed_tools: list[str] | None = None,
    ):
        """Initialize the backend developer agent.

        Args:
            github_token: GitHub personal access token
            work_dir: Working directory for git operations
            character_mode: Whether to use Rick Sanchez personality
            triggers: Keywords that activate this agent (from agents.yaml)
            allowed_tools: Tools this agent can use (from agents.yaml)
        """
        # Use tools from config, or sensible defaults
        tools = allowed_tools or ["Read", "Write", "Edit", "Glob", "Grep", "Bash", "mcp__git__*"]

        config = AgentConfig(
            name="backend_dev",
            allowed_tools=tools,
            character_mode=character_mode,
        )

        super().__init__(config, work_dir)

        self._github_token = github_token
        self._git_ops: GitOperations | None = None
        self._github_client: GitHubClient | None = None
        self._repo_context: dict[str, Any] = {}
        self._mcp_server: Any = None
        self._character_mode = character_mode
        self._triggers = triggers or []  # Triggers come from agents.yaml

    @property
    def name(self) -> str:
        return "backend_dev"

    @property
    def character_name(self) -> str:
        return "Rick" if self._character_mode else "Backend Dev"

    async def setup_repo(self, repo_url: str, repo_full_name: str) -> Path:
        """Set up the repository for the agent.

        Args:
            repo_url: Repository URL to clone
            repo_full_name: Full repository name (owner/repo)

        Returns:
            Path to the cloned repository
        """
        self._git_ops = GitOperations(self.work_dir)
        repo_path = self._git_ops.clone(repo_url, self._github_token)
        self.work_dir = repo_path

        self._github_client = GitHubClient(self._github_token)
        await self._github_client.connect()

        self._repo_context = {
            "repo_name": repo_full_name,
            "repo_path": str(repo_path),
        }

        self._mcp_server = self._create_git_mcp_server(repo_full_name)
        return repo_path

    def _create_git_mcp_server(self, repo_full_name: str) -> Any:
        """Create an MCP server with git tools."""
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
        """Get the backend developer system prompt."""
        merged_context = {**self._repo_context, **context}
        return get_system_prompt(
            character_mode=self._character_mode,
            repo_name=merged_context.get("repo_name"),
            branch_name=merged_context.get("branch_name"),
            task_description=merged_context.get("task_description"),
        )

    def get_mcp_servers(self) -> dict[str, Any]:
        """Get MCP servers for custom tools."""
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

        if not branch_name:
            slug = description.lower()[:30]
            slug = "".join(c if c.isalnum() else "-" for c in slug)
            slug = "-".join(filter(None, slug.split("-")))
            branch_name = f"feature/{slug}"

        task_prompt = get_implement_feature_prompt(
            description=description,
            branch_name=branch_name.replace("feature/", ""),
        )

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

    async def chat(self, message: str, character_mode: bool | None = None) -> AgentResult:
        """Handle a general chat message using the AI agent.

        Args:
            message: The user's message
            character_mode: Override character mode for this chat

        Returns:
            AgentResult with the response
        """
        ai_log = get_ai_logger()
        use_character = character_mode if character_mode is not None else self._character_mode

        ai_log.info(f"=== Chat request ({self.character_name}) ===")
        ai_log.info(f"User message: {message}")
        ai_log.info(f"Character mode: {use_character}")

        # Ensure GitHub client is connected
        if not self._github_client:
            ai_log.debug("Connecting to GitHub...")
            self._github_client = GitHubClient(self._github_token)
            await self._github_client.connect()

        # Get the user's repos to include in context
        try:
            ai_log.debug("Fetching user repos...")
            repos = self._github_client.get_user_repos()
            repo_list = [r.full_name for r in repos[:20]]
            repo_context = "\n\nUser's GitHub repositories:\n" + "\n".join(f"- {r}" for r in repo_list)
            ai_log.debug(f"Found {len(repo_list)} repos")
        except Exception as e:
            ai_log.error(f"Failed to fetch repos: {e}")
            repo_context = "\n\n(Could not fetch repositories)"

        full_prompt = f"{message}{repo_context}"

        options = ClaudeAgentOptions(
            system_prompt=get_chat_prompt(character_mode=use_character),
            allowed_tools=self.config.allowed_tools,
            mcp_servers=self.get_mcp_servers(),
            max_turns=5,
            cwd=self.work_dir,
        )

        # Resume from previous session if available (maintains conversation context)
        if self._session_id:
            options.resume = self._session_id
            ai_log.info(f"Resuming session: {self._session_id[:8]}...")

        ai_log.info("Calling Claude Agent SDK...")
        ai_log.debug(f"Options: allowed_tools={options.allowed_tools}")
        ai_log.debug(f"Working directory: {self.work_dir}")
        final_message = ""
        try:
            self._check_api_limit()
            async for msg in query(prompt=full_prompt, options=options):
                # Capture session ID for conversation continuity
                if hasattr(msg, "session_id") and msg.session_id:
                    self._session_id = msg.session_id

                ai_log.debug(f"Received message type: {type(msg).__name__}")
                if isinstance(msg, AssistantMessage):
                    for block in msg.content:
                        if isinstance(block, TextBlock):
                            final_message += block.text

            ai_log.info(f"AI response length: {len(final_message)} chars")
            return AgentResult(
                success=True,
                message=final_message,
            )
        except Exception as e:
            tb = traceback.format_exc()
            ai_log.error(f"AI query failed: {e}")
            ai_log.error(f"Traceback:\n{tb}")
            return AgentResult(
                success=False,
                message="Failed to process message",
                error=str(e),
            )

    async def is_relevant(self, message: str, triggers: list[str] | None = None) -> bool:
        """Check if this agent should respond to a message."""
        check_triggers = triggers or self._triggers
        message_lower = message.lower()
        return any(trigger.lower() in message_lower for trigger in check_triggers)
