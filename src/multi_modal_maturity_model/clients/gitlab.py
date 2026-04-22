"""
GitLab API client for collecting repository health metrics.
"""

import logging
from gitlab import Gitlab, GitlabError
from gitlab.v4.objects import Project
from typing import Any


logger = logging.getLogger(__name__)


class GitLabClient:
    """
    Collect metrics from GitLab repositories.
    Uses library python-gitlab for authenticated access.

    Parameters
    ----------
    token : str
        GitLab personal access token
    """

    def __init__(self, token: str):
        self.gl = Gitlab(private_token=token)

    def fetch(self, group_sub_project: str) -> dict[str, Any]:
        """
        Fetch repository metadata for a given group/sub-project format.

        Parameters
        ----------
        group_sub_project : str
            Repository in group/sub-project format (e.g., "group/project" or "group/subgroup/project")

        Returns
        -------
        dict
            Dictionary containing the repository metadata.
        """
        logger.debug(f"Fetching GitLab repository {group_sub_project}")

        data = self._fetch_project(group_sub_project)
        branches_count = self._fetch_branches_count(data)
        contributors = self._fetch_contributors(data)
        closed_issues = self._fetch_closed_issues(data)
        open_issues_count = self._fetch_open_issues_count(data)
        languages = self._fetch_languages(data)
        repository_tree = self._fetch_repository_tree(data)
        default_branch_protected = self._is_default_branch_protected(data)

        logger.info(
            f"Successfully collected metadata for GitLab repository {group_sub_project}"
        )

        result: dict[str, Any] = {
            "repo": data.attributes,
            "branches_count": branches_count,
            "contributors": contributors,
            "closed_issues": closed_issues,
            "open_issues_count": open_issues_count,
            "languages": languages,
            "repository_tree": repository_tree,
            "default_branch_protected": default_branch_protected,
        }
        return result

    def _fetch_project(self, group_sub_project: str) -> Project:
        try:
            data = self.gl.projects.get(group_sub_project)
            return data
        except GitlabError as e:
            logger.error(f"Error fetching GitLab repository {group_sub_project}: {e}")
            raise

    def _fetch_branches_count(self, project: Project) -> int | None:
        """Get the total number of branches."""
        try:
            branches_count = project.branches.list(iterator=True).total
            return branches_count
        except GitlabError as e:
            logger.warning(
                f"Error fetching branches for {project.path_with_namespace}: {e}"
            )
            return None

    def _fetch_contributors(self, project: Project) -> list | None:
        """Get a list of contributors with their commit counts."""
        try:
            contributors = project.repository_contributors(get_all=True)
            return contributors
        except GitlabError as e:
            logger.warning(
                f"Error fetching contributors for {project.path_with_namespace}: {e}"
            )
            return None

    def _fetch_closed_issues(self, project: Project) -> list | None:
        """Get a list of closed issues."""
        try:
            iterator = project.issues.list(state="closed", iterator=True)
            closed_issues = [issue.attributes for issue in iterator]
            return closed_issues
        except GitlabError as e:
            logger.warning(
                f"Error fetching closed issues for {project.path_with_namespace}: {e}"
            )
            return None

    def _fetch_open_issues_count(self, project: Project) -> int | None:
        """Get the count of open issues."""
        try:
            open_issues_count = project.issues.list(state="opened", iterator=True).total
            return open_issues_count
        except GitlabError as e:
            logger.warning(
                f"Error fetching open issues for {project.path_with_namespace}: {e}"
            )
            return None

    def _fetch_languages(self, project: Project) -> dict | None:
        """Get a dictionary of languages used in the project."""
        try:
            languages = project.languages(get_all=True)
            return languages
        except GitlabError as e:
            logger.warning(
                f"Error fetching languages for {project.path_with_namespace}: {e}"
            )
            return None

    def _fetch_repository_tree(self, project: Project) -> list | None:
        """Get the repository tree for the default branch."""
        try:
            repository_tree = project.repository_tree(
                path="",
                ref=project.default_branch,
                recursive=True,
                get_all=True,
            )
            return repository_tree
        except GitlabError as e:
            logger.warning(
                f"Error fetching repository tree for {project.path_with_namespace}: {e}"
            )
            return None

    def _is_default_branch_protected(self, project: Project) -> bool | None:
        """Check if the default branch is protected."""
        try:
            default_branch = project.branches.get(project.default_branch)
            return default_branch.protected
        except GitlabError as e:
            logger.warning(
                f"Error checking if default branch is protected for {project.path_with_namespace}: {e}"
            )
            return None
