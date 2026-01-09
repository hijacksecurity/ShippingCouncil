"""Council orchestrator for managing agents and tasks."""

import asyncio
from pathlib import Path
from typing import Any, Callable

from agents.backend_dev import BackendDevAgent
from agents.devops import DevOpsAgent
from core.task import Task, TaskManager, TaskStatus
from integrations.github.client import GitHubClient


class Council:
    """Orchestrates agents and manages task execution."""

    def __init__(
        self,
        github_token: str,
        work_dir: Path,
        default_repo: str | None = None,
    ):
        """Initialize the council.

        Args:
            github_token: GitHub token
            work_dir: Working directory for operations
            default_repo: Default repository (owner/repo format)
        """
        self._github_token = github_token
        self._work_dir = work_dir
        self._default_repo = default_repo

        self._task_manager = TaskManager()
        self._github_client: GitHubClient | None = None
        self._status_callback: Callable[[Task, str], Any] | None = None
        self._running_tasks: dict[str, asyncio.Task[Any]] = {}

    async def start(self) -> None:
        """Start the council and initialize connections."""
        self._github_client = GitHubClient(self._github_token)
        await self._github_client.connect()

    async def stop(self) -> None:
        """Stop the council and clean up resources."""
        # Cancel running tasks
        for task_id, async_task in self._running_tasks.items():
            async_task.cancel()

        if self._github_client:
            await self._github_client.disconnect()

    def on_status_update(self, callback: Callable[[Task, str], Any]) -> None:
        """Set a callback for task status updates.

        Args:
            callback: Async function called with (task, message)
        """
        self._status_callback = callback

    async def _notify_status(self, task: Task, message: str) -> None:
        """Send a status update notification.

        Args:
            task: The task
            message: Status message
        """
        if self._status_callback:
            await self._status_callback(task, message)

    async def create_task(
        self,
        description: str,
        agent_type: str,
        repo_url: str | None = None,
        repo_full_name: str | None = None,
        thread_id: int | None = None,
        auto_start: bool = True,
    ) -> Task:
        """Create a new task.

        Args:
            description: What the task should accomplish
            agent_type: Type of agent (e.g., "developer")
            repo_url: Repository URL (uses default if not provided)
            repo_full_name: Full repository name (owner/repo)
            thread_id: Discord thread ID for updates
            auto_start: Whether to start execution immediately

        Returns:
            The created task
        """
        # Use default repo if not specified
        if not repo_full_name and self._default_repo:
            repo_full_name = self._default_repo
            repo_url = f"https://github.com/{repo_full_name}"

        task = self._task_manager.create_task(
            description=description,
            agent_type=agent_type,
            repo_url=repo_url,
            repo_full_name=repo_full_name,
            thread_id=thread_id,
        )

        await self._notify_status(task, f"Task created: {task.id}")

        if auto_start:
            await self._start_task(task)

        return task

    async def _start_task(self, task: Task) -> None:
        """Start executing a task.

        Args:
            task: Task to execute
        """
        task.update_status(TaskStatus.IN_PROGRESS)
        await self._notify_status(task, "Task started")

        # Create async task for execution
        async_task = asyncio.create_task(self._execute_task(task))
        self._running_tasks[task.id] = async_task

    async def _execute_task(self, task: Task) -> None:
        """Execute a task with the appropriate agent.

        Args:
            task: Task to execute
        """
        try:
            if task.agent_type in ("developer", "backend_dev"):
                await self._execute_backend_dev_task(task)
            elif task.agent_type == "devops":
                await self._execute_devops_task(task)
            else:
                task.set_error(f"Unknown agent type: {task.agent_type}")
                await self._notify_status(task, "Error: Unknown agent type")

        except asyncio.CancelledError:
            task.update_status(TaskStatus.CANCELLED)
            await self._notify_status(task, "Task cancelled")

        except Exception as e:
            task.set_error(str(e))
            await self._notify_status(task, f"Error: {str(e)}")

        finally:
            # Clean up
            if task.id in self._running_tasks:
                del self._running_tasks[task.id]

    async def _execute_backend_dev_task(self, task: Task) -> None:
        """Execute a backend developer task.

        Args:
            task: Task to execute
        """
        if not task.repo_url or not task.repo_full_name:
            task.set_error("No repository specified")
            return

        await self._notify_status(task, "Setting up repository...")

        # Create backend dev agent (SDK handles API key via ANTHROPIC_API_KEY env var)
        agent = BackendDevAgent(
            github_token=self._github_token,
            work_dir=self._work_dir,
        )

        try:
            # Set up the repository
            await agent.setup_repo(task.repo_url, task.repo_full_name)
            await self._notify_status(task, "Repository cloned")

            # Implement the feature
            await self._notify_status(task, "Working on implementation...")
            result = await agent.implement_feature(task.description)

            if result["success"]:
                task.branch_name = result.get("branch")
                task.set_result(result)
                task.update_status(TaskStatus.AWAITING_APPROVAL)
                await self._notify_status(
                    task,
                    f"Implementation complete! Branch: {task.branch_name}\n"
                    f"Use `/approve {task.id}` to merge."
                )
            else:
                task.set_error(result.get("error", "Unknown error"))
                await self._notify_status(task, f"Failed: {result.get('error')}")

        finally:
            await agent.cleanup()

    async def _execute_devops_task(self, task: Task) -> None:
        """Execute a DevOps task.

        Args:
            task: Task to execute
        """
        await self._notify_status(task, "DevOps agent analyzing...")

        # Create DevOps agent (read-only Docker access)
        agent = DevOpsAgent(work_dir=self._work_dir)

        try:
            # DevOps tasks are typically diagnostic/monitoring
            result = await agent.chat(task.description)

            if result.success:
                task.set_result({"message": result.message})
                task.update_status(TaskStatus.COMPLETED)
                await self._notify_status(task, f"Analysis complete:\n{result.message[:500]}")
            else:
                task.set_error(result.error or "Unknown error")
                await self._notify_status(task, f"Failed: {result.error}")

        finally:
            await agent.cleanup()

    def get_task(self, task_id: str) -> Task | None:
        """Get a task by ID.

        Args:
            task_id: Task ID

        Returns:
            Task or None
        """
        return self._task_manager.get_task(task_id)

    def list_tasks(self, status: TaskStatus | None = None) -> list[Task]:
        """List tasks.

        Args:
            status: Optional status filter

        Returns:
            List of tasks
        """
        return self._task_manager.list_tasks(status=status)

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task.

        Args:
            task_id: Task ID

        Returns:
            True if cancelled
        """
        task = self._task_manager.get_task(task_id)
        if not task:
            return False

        if task.status not in [TaskStatus.PENDING, TaskStatus.IN_PROGRESS]:
            return False

        # Cancel async task if running
        if task_id in self._running_tasks:
            self._running_tasks[task_id].cancel()

        task.update_status(TaskStatus.CANCELLED)
        await self._notify_status(task, "Task cancelled")
        return True

    async def approve_task(self, task_id: str) -> bool:
        """Approve a completed task.

        Args:
            task_id: Task ID

        Returns:
            True if approved
        """
        task = self._task_manager.get_task(task_id)
        if not task or task.status != TaskStatus.AWAITING_APPROVAL:
            return False

        task.update_status(TaskStatus.APPROVED)
        await self._notify_status(task, "Task approved!")

        # TODO: Implement PR merge logic here
        task.update_status(TaskStatus.COMPLETED)
        return True

    async def list_repos(self) -> list[str]:
        """List available repositories.

        Returns:
            List of repository names
        """
        if not self._github_client:
            return []

        try:
            repos = self._github_client.get_user_repos()
            return [r.full_name for r in repos]
        except Exception:
            return []
