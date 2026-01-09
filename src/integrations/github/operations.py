"""Local git operations using GitPython."""

import shutil
from pathlib import Path

from git import Repo
from git.exc import GitCommandError


class GitOperations:
    """Local git operations wrapper using GitPython."""

    def __init__(self, work_dir: Path):
        """Initialize git operations.

        Args:
            work_dir: Working directory for git operations
        """
        self.work_dir = work_dir
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self._repo: Repo | None = None

    @property
    def repo(self) -> Repo:
        """Get the current repository."""
        if self._repo is None:
            raise RuntimeError("No repository loaded. Call clone() first.")
        return self._repo

    @property
    def repo_path(self) -> Path:
        """Get the path to the current repository."""
        return Path(self.repo.working_dir)

    def clone(self, repo_url: str, token: str, repo_name: str | None = None) -> Path:
        """Clone a repository.

        Args:
            repo_url: Repository URL (https://github.com/owner/repo)
            token: GitHub token for authentication
            repo_name: Optional name for the cloned directory

        Returns:
            Path to the cloned repository
        """
        # Extract repo name from URL if not provided
        if repo_name is None:
            repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")

        clone_path = self.work_dir / repo_name

        # Remove existing clone if present
        if clone_path.exists():
            shutil.rmtree(clone_path)

        # Add token to URL for authentication
        if repo_url.startswith("https://github.com/"):
            auth_url = repo_url.replace(
                "https://github.com/", f"https://{token}@github.com/"
            )
        else:
            auth_url = repo_url

        self._repo = Repo.clone_from(auth_url, clone_path)
        return clone_path

    def create_branch(self, branch_name: str, checkout: bool = True) -> None:
        """Create a new branch.

        Args:
            branch_name: Name of the new branch
            checkout: Whether to checkout the new branch
        """
        if checkout:
            self.repo.git.checkout("-b", branch_name)
        else:
            self.repo.create_head(branch_name)

    def checkout(self, branch_name: str) -> None:
        """Checkout an existing branch.

        Args:
            branch_name: Branch to checkout
        """
        self.repo.git.checkout(branch_name)

    def status(self) -> dict[str, list[str]]:
        """Get the current git status.

        Returns:
            Dictionary with 'staged', 'unstaged', and 'untracked' files
        """
        return {
            "staged": [item.a_path for item in self.repo.index.diff("HEAD")],
            "unstaged": [item.a_path for item in self.repo.index.diff(None)],
            "untracked": self.repo.untracked_files,
        }

    def add(self, files: list[str] | None = None) -> None:
        """Stage files for commit.

        Args:
            files: List of files to stage, or None for all changes
        """
        if files is None:
            self.repo.git.add("-A")
        else:
            self.repo.index.add(files)

    def commit(self, message: str) -> str:
        """Create a commit.

        Args:
            message: Commit message

        Returns:
            Commit SHA
        """
        commit = self.repo.index.commit(message)
        return commit.hexsha

    def push(self, branch: str | None = None, set_upstream: bool = True) -> None:
        """Push changes to remote.

        Args:
            branch: Branch to push, or None for current branch
            set_upstream: Whether to set upstream tracking
        """
        if branch is None:
            branch = self.repo.active_branch.name

        origin = self.repo.remote("origin")
        if set_upstream:
            origin.push(branch, set_upstream=True)
        else:
            origin.push(branch)

    def current_branch(self) -> str:
        """Get the current branch name.

        Returns:
            Current branch name
        """
        return self.repo.active_branch.name

    def read_file(self, file_path: str) -> str:
        """Read a file from the repository.

        Args:
            file_path: Relative path to the file

        Returns:
            File contents
        """
        full_path = self.repo_path / file_path
        return full_path.read_text()

    def write_file(self, file_path: str, content: str) -> None:
        """Write content to a file in the repository.

        Args:
            file_path: Relative path to the file
            content: Content to write
        """
        full_path = self.repo_path / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)

    def list_files(self, directory: str = ".") -> list[str]:
        """List files in a directory.

        Args:
            directory: Relative path to the directory

        Returns:
            List of file paths
        """
        dir_path = self.repo_path / directory
        if not dir_path.exists():
            return []
        return [
            str(f.relative_to(self.repo_path))
            for f in dir_path.rglob("*")
            if f.is_file() and ".git" not in str(f)
        ]
