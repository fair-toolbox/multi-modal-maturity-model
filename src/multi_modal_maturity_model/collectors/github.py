"""
GitHub API client for collecting repository health metrics.
"""

import logging
from typing import Any

from github import Auth, Github, GithubException
from github.Repository import Repository


logger = logging.getLogger(__name__)


class GitHubClient:
    """
    Collect metrics from GitHub repositories.
    Uses PyGithub library for authenticated access.
    Parameters
    ----------
    token : str
        GitHub personal access token
    """

    def __init__(self, token: str):
        self.auth = Auth.Token(token)
        self.gh = Github(auth=self.auth)

    def fetch(self, owner_repo: str) -> dict[str, Any]:
        """
        Fetch repository metadata for a given owner/repo format.

        Parameters
        ----------
        owner_repo : str
            Repository in owner/repo format (e.g., "owner/repo")

        Returns
        -------
        dict[str, Any]
            Dictionary containing the repository metadata.
        """
        logger.debug(f"Fetching GitHub repository {owner_repo}")

        data = self._fetch_repository(owner_repo)
        contents = self._fetch_contents(data)
        contributors = self._fetch_contributors(data)
        closed_issues = self._fetch_closed_issues(data)
        languages = self._fetch_languages(data)
        default_branch_protected = self._is_default_branch_protected(data)

        logger.info(f"Successfully collected GitHub repository {owner_repo}")

        result: dict[str, Any] = {
            "repo": data.raw_data,
            "contents": contents,
            "contributors": contributors,
            "closed_issues": closed_issues,
            "languages": languages,
            "default_branch_protected": default_branch_protected,
        }
        return result

    def _fetch_repository(self, owner_repo: str) -> Repository:
        try:
            data = self.gh.get_repo(owner_repo)
            return data
        except GithubException as e:
            logger.warning(f"Error fetching GitHub repository {owner_repo}: {e}")
            raise

    def _fetch_contents(self, repo: Repository) -> list[dict[str, Any]] | None:
        """Get repository contents (file tree)."""
        try:
            contents = repo.get_contents("")
            return [
                {"path": content.path, "type": content.type} for content in contents
            ]
        except GithubException as e:
            logger.warning(f"Could not get repository contents: {e}")
            return None

    def _fetch_contributors(self, repo: Repository) -> list[dict[str, Any]] | None:
        """Get contributors with their commit counts."""
        try:
            contributors = repo.get_contributors()
            return [
                {"login": c.login, "contributions": c.contributions}
                for c in contributors
                if c.login is not None
            ]
        except GithubException as e:
            logger.warning(f"Could not get repository contributors: {e}")
            return None

    def _fetch_closed_issues(self, repo: Repository) -> list[dict[str, Any]] | None:
        """Get closed issues list."""
        try:
            closed_issues = repo.get_issues(state="closed")
            return [
                {
                    "number": issue.number,
                    "title": issue.title,
                    "created_at": (
                        issue.created_at.isoformat() if issue.created_at else None
                    ),
                    "closed_at": (
                        issue.closed_at.isoformat() if issue.closed_at else None
                    ),
                }
                for issue in closed_issues
                if issue.pull_request is None  # Skip pull requests
            ]
        except GithubException as e:
            logger.warning(f"Could not get closed issues: {e}")
            return None

    def _fetch_languages(self, repo: Repository) -> dict[str, int] | None:
        """Get languages with their byte counts."""
        try:
            languages = repo.get_languages()
            return languages
        except GithubException as e:
            logger.warning(f"Could not get repository languages: {e}")
            return None

    def _is_default_branch_protected(self, repo: Repository) -> bool | None:
        """Check if default branch is protected."""
        try:
            branch = repo.get_branch(repo.default_branch)
            return branch.protected
        except GithubException as e:
            logger.warning(f"Could not check default branch protection: {e}")
            return None
