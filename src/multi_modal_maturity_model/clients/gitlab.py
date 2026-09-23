"""Async client for GitLab API."""

import asyncio
import logging
import httpx

from gidgetlab.exceptions import GitLabException
from gidgetlab.httpx import GitLabAPI
from typing import Any
from urllib.parse import quote_plus

from .base import BaseClient

logger = logging.getLogger(__name__)


class GitLabClient(BaseClient):
    """
    Collect raw data from GitLab API.

    Parameters
    ----------
    repo_url : str
        URL of the GitLab repository to collect data from.
    token : str, optional
        GitLab API token for authentication.

    """

    def __init__(self, repo_url: str, token: str):
        self.token = token
        self.repo_url = repo_url
        self.project_path = self._parse_repo_url()

    def _parse_repo_url(self) -> str:
        """
        Extract project path from GitLab URL.
        Handles https://gitlab.com/owner/repo and https://gitlab.com/group/subgroup/repo.
        """
        path = self.repo_url.removesuffix(".git")
        path = path.split("gitlab.com/")[1]
        return path.rstrip("/")

    def _get_project_id_encoded(self) -> str:
        """URL-encode the project path for GitLab API."""
        # GitLab API needs URL-encoded project path
        return quote_plus(self.project_path)

    async def _fetch_paginated(self, gl: GitLabAPI, url: str) -> list[dict[str, Any]]:
        """Fetch all pages of a paginated GitLab API endpoint."""
        results = []
        async for item in gl.getiter(url):
            results.append(item)
        return results

    async def _fetch_project(self, gl: GitLabAPI) -> dict[str, Any]:
        """Fetch project data from GitLab."""
        try:
            project_id = self._get_project_id_encoded()
            return await gl.getitem(f"/projects/{project_id}")
        except GitLabException as e:
            logger.error(f"Could not fetch project: {e}")
            raise

    async def _fetch_branches_count(self, gl: GitLabAPI, project_id: str) -> int | None:
        """Get the total number of branches."""
        try:
            # Put query params directly in URL
            branches = await self._fetch_paginated(
                gl, f"/projects/{project_id}/repository/branches?per_page=100"
            )
            return len(branches)
        except GitLabException as e:
            logger.warning(f"Error fetching branches: {e}")
            return None

    async def _fetch_contributors(
        self, gl: GitLabAPI, project_id: str
    ) -> list[dict[str, Any]] | None:
        """Get a list of contributors with their commit counts."""
        try:
            return await self._fetch_paginated(
                gl, f"/projects/{project_id}/repository/contributors?per_page=100"
            )
        except GitLabException as e:
            logger.warning(f"Error fetching contributors: {e}")
            return None

    async def _fetch_closed_issues(
        self, gl: GitLabAPI, project_id: str
    ) -> list[dict[str, Any]] | None:
        """Get a list of closed issues."""
        try:
            # Add state in URL query string
            return await self._fetch_paginated(
                gl, f"/projects/{project_id}/issues?state=closed&per_page=100"
            )
        except GitLabException as e:
            logger.warning(f"Error fetching closed issues: {e}")
            return None

    async def _fetch_open_issues_count(
        self, gl: GitLabAPI, project_id: str
    ) -> int | None:
        """Get the count of open issues."""
        try:
            # Add state in URL query string
            issues = await self._fetch_paginated(
                gl, f"/projects/{project_id}/issues?state=opened&per_page=100"
            )
            return len(issues)
        except GitLabException as e:
            logger.warning(f"Error fetching open issues: {e}")
            return None

    async def _fetch_languages(
        self, gl: GitLabAPI, project_id: str
    ) -> dict[str, float] | None:
        """Get a dictionary of languages used in the project."""
        try:
            return await gl.getitem(f"/projects/{project_id}/languages")
        except GitLabException as e:
            logger.warning(f"Error fetching languages: {e}")
            return None

    async def _fetch_repository_tree(
        self, gl: GitLabAPI, project_id: str, default_branch: str
    ) -> list[dict[str, Any]] | None:
        """Get the repository tree for the default branch."""
        try:
            # all query params in URL
            return await self._fetch_paginated(
                gl,
                f"/projects/{project_id}/repository/tree?path=&ref={default_branch}&recursive=true&per_page=100",
            )
        except GitLabException as e:
            logger.warning(f"Error fetching repository tree: {e}")
            return None

    async def _fetch_releases(
        self, gl: GitLabAPI, project_id: str
    ) -> list[dict[str, Any]] | None:
        """Get a list of releases."""
        try:
            return await self._fetch_paginated(
                gl, f"/projects/{project_id}/releases?per_page=100"
            )
        except GitLabException as e:
            logger.warning(f"Could not get repository releases: {e}")
            return None

    async def _is_default_branch_protected(
        self, gl: GitLabAPI, project_id: str, default_branch: str
    ) -> bool | None:
        """Check if the default branch is protected."""
        try:
            branch_name = quote_plus(default_branch)
            branch = await gl.getitem(
                f"/projects/{project_id}/repository/branches/{branch_name}"
            )
            return branch.get("protected", False)
        except GitLabException as e:
            logger.warning(f"Error checking if default branch is protected: {e}")
            return None

    async def fetch(self) -> dict[str, Any]:
        """
        Collect raw repository data from GitLab asynchronously.

        Returns
        -------
        dict
            Dictionary with raw GitLab API responses.
        """
        async with httpx.AsyncClient(timeout=60.0) as client:
            gl = GitLabAPI(
                client, "multi-modal-maturity-model", access_token=self.token
            )

            # Fetch project first to get default branch and project ID
            project = await self._fetch_project(gl)
            default_branch = project.get("default_branch", "main")
            project_id = self._get_project_id_encoded()

            (
                branches_count,
                contributors,
                closed_issues,
                open_issues_count,
                languages,
                repository_tree,
                releases,
                default_branch_protected,
            ) = await asyncio.gather(
                self._fetch_branches_count(gl, project_id),
                self._fetch_contributors(gl, project_id),
                self._fetch_closed_issues(gl, project_id),
                self._fetch_open_issues_count(gl, project_id),
                self._fetch_languages(gl, project_id),
                self._fetch_repository_tree(gl, project_id, default_branch),
                self._fetch_releases(gl, project_id),
                self._is_default_branch_protected(gl, project_id, default_branch),
                return_exceptions=False,
            )

            return {
                "repository": project,
                "branches_count": branches_count,
                "contributors": contributors,
                "closed_issues": closed_issues,
                "open_issues_count": open_issues_count,
                "languages": languages,
                "repository_tree": repository_tree,
                "releases": releases,
                "default_branch_protected": default_branch_protected,
            }
