"""Async client for GitHub API."""

import asyncio
import logging
import httpx

from gidgethub import GitHubException
from gidgethub.httpx import GitHubAPI
from typing import Any

from .base import BaseClient

logger = logging.getLogger(__name__)


class GitHubClient(BaseClient):
    """
    Collect raw data from GitHub API using PyGithub.

    Parameters
    ----------
    repo_url : str
        URL of the GitHub repository to collect data from.
    token : str
        GitHub API token for authentication.

    """

    def __init__(self, repo_url: str, token: str):
        self.token = token
        self.repo_url = repo_url
        self.owner, self.repo = self._parse_repo_url()

    def _parse_repo_url(self) -> tuple[str, str]:
        """Extract owner and repo name from GitHub URL."""
        owner, repo = self.repo_url.split("github.com/")[1].split("/")[:2]
        return owner, repo

    async def _fetch_paginated(
        self, gh: GitHubAPI, url: str, **params
    ) -> list[dict[str, Any]]:
        """Fetch paginated GitHub API endpoints."""
        results = []
        async for item in gh.getiter(url, **params):
            results.append(item)
        return results

    async def _fetch_repository(self, gh: GitHubAPI) -> dict[str, Any] | None:
        """Fetch repository data from GitHub."""
        try:
            return await gh.getitem(f"/repos/{self.owner}/{self.repo}")
        except GitHubException as e:
            logger.error(f"Could not fetch repository: {e}")
            raise

    async def _fetch_contents(
        self, gh: GitHubAPI, default_branch: str
    ) -> list[dict[str, Any]] | None:
        """Get recursive repository file tree for the default branch."""
        try:
            data = await gh.getitem(
                f"/repos/{self.owner}/{self.repo}/git/trees/{default_branch}",
                {"recursive": "1"},
            )
            return [
                {"path": item["path"], "type": item["type"]}
                for item in data.get("tree", [])
            ]
        except GitHubException as e:
            logger.warning(f"Could not get repository contents: {e}")
            return None

    async def _fetch_contributors(self, gh: GitHubAPI) -> list[dict[str, Any]] | None:
        """Get contributors with their commit counts."""
        try:
            contributors = await self._fetch_paginated(
                gh, f"/repos/{self.owner}/{self.repo}/contributors"
            )
            return [
                {"login": c["login"], "contributions": c["contributions"]}
                for c in contributors
                if c.get("login")
            ]
        except GitHubException as e:
            logger.warning(f"Could not get repository contributors: {e}")
            return None

    async def _fetch_closed_issues(self, gh: GitHubAPI) -> list[dict[str, Any]] | None:
        """Get closed issues list."""
        try:
            issues = await self._fetch_paginated(
                gh, f"/repos/{self.owner}/{self.repo}/issues?state=closed"
            )
            return [
                {
                    "number": issue["number"],
                    "title": issue["title"],
                    "created_at": issue.get("created_at"),
                    "closed_at": issue.get("closed_at"),
                }
                for issue in issues
                if "pull_request" not in issue  # Skip pull requests
            ]
        except GitHubException as e:
            logger.warning(f"Could not get closed issues: {e}")
            return None

    async def _fetch_languages(self, gh: GitHubAPI) -> dict[str, int] | None:
        """Get languages with their byte counts."""
        try:
            return await gh.getitem(f"/repos/{self.owner}/{self.repo}/languages")
        except GitHubException as e:
            logger.warning(f"Could not get repository languages: {e}")
            return None

    async def _is_default_branch_protected(
        self, gh: GitHubAPI, default_branch: str
    ) -> bool | None:
        """Check if default branch is protected."""
        try:
            data = await gh.getitem(
                f"/repos/{self.owner}/{self.repo}/branches/{default_branch}"
            )
            return data.get("protected", False)
        except GitHubException as e:
            logger.warning(f"Could not check default branch protection: {e}")
            return None

    async def fetch(self) -> dict[str, Any]:
        """
        Collect raw repository data from GitHub asynchronously.

        Returns
        -------
        dict
            Dictionary with raw GitHub API responses.
        """
        async with httpx.AsyncClient(timeout=60.0) as client:
            gh = GitHubAPI(client, "multi-modal-maturity-model", oauth_token=self.token)

            # Fetch repository first to get default branch
            repository = await self._fetch_repository(gh)
            default_branch = repository.get("default_branch", "main")

            contents, contributors, closed_issues, languages, branch_protected = (
                await asyncio.gather(
                    self._fetch_contents(gh, default_branch),
                    self._fetch_contributors(gh),
                    self._fetch_closed_issues(gh),
                    self._fetch_languages(gh),
                    self._is_default_branch_protected(gh, default_branch),
                    return_exceptions=False,
                )
            )

            return {
                "repository": repository,
                "contents": contents,
                "contributors": contributors,
                "closed_issues": closed_issues,
                "languages": languages,
                "default_branch_protected": branch_protected,
            }
