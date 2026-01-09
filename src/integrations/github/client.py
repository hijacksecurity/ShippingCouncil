"""GitHub API client wrapper."""

from github import Auth, Github
from github.Repository import Repository

from integrations.base import BaseIntegration


class GitHubClient(BaseIntegration):
    """GitHub API client using PyGithub."""

    def __init__(self, token: str):
        """Initialize GitHub client.

        Args:
            token: GitHub personal access token
        """
        self._token = token
        self._client: Github | None = None

    @property
    def name(self) -> str:
        return "github"

    @property
    def client(self) -> Github:
        """Get the GitHub client instance."""
        if self._client is None:
            raise RuntimeError("GitHub client not connected. Call connect() first.")
        return self._client

    async def connect(self) -> None:
        """Establish connection to GitHub."""
        auth = Auth.Token(self._token)
        self._client = Github(auth=auth)

    async def disconnect(self) -> None:
        """Close connection to GitHub."""
        if self._client:
            self._client.close()
            self._client = None

    async def health_check(self) -> bool:
        """Check if GitHub connection is healthy."""
        if not self._client:
            return False
        try:
            self._client.get_user().login
            return True
        except Exception:
            return False

    def get_repo(self, repo_full_name: str) -> Repository:
        """Get a repository by full name.

        Args:
            repo_full_name: Full repository name (e.g., "owner/repo")

        Returns:
            Repository object
        """
        return self.client.get_repo(repo_full_name)

    def get_user_repos(self) -> list[Repository]:
        """Get repositories for the authenticated user.

        Returns:
            List of Repository objects
        """
        return list(self.client.get_user().get_repos())

    async def create_pull_request(
        self,
        repo_full_name: str,
        title: str,
        body: str,
        head: str,
        base: str = "main",
    ) -> str:
        """Create a pull request.

        Args:
            repo_full_name: Full repository name
            title: PR title
            body: PR description
            head: Branch with changes
            base: Target branch

        Returns:
            URL of the created PR
        """
        repo = self.get_repo(repo_full_name)
        pr = repo.create_pull(title=title, body=body, head=head, base=base)
        return pr.html_url
