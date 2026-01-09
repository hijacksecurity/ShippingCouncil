"""Task models and management."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class TaskStatus(Enum):
    """Task status enumeration."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """Represents a task for an agent."""

    description: str
    agent_type: str
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    thread_id: int | None = None
    repo_url: str | None = None
    repo_full_name: str | None = None
    branch_name: str | None = None
    pr_url: str | None = None
    result: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def update_status(self, status: TaskStatus) -> None:
        """Update the task status.

        Args:
            status: New status
        """
        self.status = status
        self.updated_at = datetime.now()

    def set_result(self, result: dict[str, Any]) -> None:
        """Set the task result.

        Args:
            result: Result dictionary
        """
        self.result = result
        self.updated_at = datetime.now()

    def set_error(self, error: str) -> None:
        """Set an error on the task.

        Args:
            error: Error message
        """
        self.error = error
        self.status = TaskStatus.FAILED
        self.updated_at = datetime.now()

    def to_dict(self) -> dict[str, Any]:
        """Convert task to dictionary.

        Returns:
            Task as dictionary
        """
        return {
            "id": self.id,
            "description": self.description,
            "agent_type": self.agent_type,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "thread_id": self.thread_id,
            "repo_url": self.repo_url,
            "repo_full_name": self.repo_full_name,
            "branch_name": self.branch_name,
            "pr_url": self.pr_url,
            "result": self.result,
            "error": self.error,
        }


class TaskManager:
    """Manages tasks and their lifecycle."""

    def __init__(self):
        self._tasks: dict[str, Task] = {}

    def create_task(
        self,
        description: str,
        agent_type: str,
        **kwargs: Any,
    ) -> Task:
        """Create a new task.

        Args:
            description: Task description
            agent_type: Type of agent to handle the task
            **kwargs: Additional task parameters

        Returns:
            The created task
        """
        task = Task(
            description=description,
            agent_type=agent_type,
            **kwargs,
        )
        self._tasks[task.id] = task
        return task

    def get_task(self, task_id: str) -> Task | None:
        """Get a task by ID.

        Args:
            task_id: Task ID

        Returns:
            Task or None if not found
        """
        return self._tasks.get(task_id)

    def list_tasks(
        self,
        status: TaskStatus | None = None,
        agent_type: str | None = None,
    ) -> list[Task]:
        """List tasks with optional filtering.

        Args:
            status: Filter by status
            agent_type: Filter by agent type

        Returns:
            List of matching tasks
        """
        tasks = list(self._tasks.values())

        if status:
            tasks = [t for t in tasks if t.status == status]

        if agent_type:
            tasks = [t for t in tasks if t.agent_type == agent_type]

        return sorted(tasks, key=lambda t: t.created_at, reverse=True)

    def update_task(self, task_id: str, **updates: Any) -> Task | None:
        """Update a task.

        Args:
            task_id: Task ID
            **updates: Fields to update

        Returns:
            Updated task or None if not found
        """
        task = self._tasks.get(task_id)
        if not task:
            return None

        for key, value in updates.items():
            if hasattr(task, key):
                setattr(task, key, value)

        task.updated_at = datetime.now()
        return task

    def delete_task(self, task_id: str) -> bool:
        """Delete a task.

        Args:
            task_id: Task ID

        Returns:
            True if deleted, False if not found
        """
        if task_id in self._tasks:
            del self._tasks[task_id]
            return True
        return False
