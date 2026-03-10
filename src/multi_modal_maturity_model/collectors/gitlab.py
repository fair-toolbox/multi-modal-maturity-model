"""
GitLab API client for collecting repository health metrics.
"""

import logging
from datetime import datetime
from gitlab import Gitlab, GitlabError
from matplotlib.pylab import mean
from typing import Any

from ..core.models import RepositoryMetrics

logger = logging.getLogger(__name__)


class GitLabClient:
    """
    Collect metrics from GitLab repositories.
    Uses  library python-gitlab for authenticated access.

    Parameters
    ----------
    token : str
        GitLab personal access token
    closed_issues_window : int
        Number of closed issues to analyze for time-to-close metric
    """

    def __init__(self, token: str, closed_issues_window: int = 300):
        self.gl = Gitlab(private_token=token)
        self.closed_issues_window = closed_issues_window

    def _get(self, group_sub_project: str) -> dict[str, Any]:
        try:
            data = self.gl.projects.get(group_sub_project)
            return data
        except GitlabError as e:
            logger.warning(f"Error fetching GitLab repository {group_sub_project}: {e}")
            raise

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
        data = self._get(group_sub_project)
        logger.info(
            f"Successfully collected metadata for GitLab repository {group_sub_project}"
        )
        return data

    def collect(self, group_sub_project: str) -> RepositoryMetrics:
        """
        Main entry point: collect all metrics for a repository.

        Parameters
        ----------
        group_sub_project : str
            Group and sub-project name (e.g., "group/project" or "group/subgroup/project")

        Returns
        -------
        RepositoryMetrics
            Instance containing all collected metrics

        Raises
        ------
        ValueError
            If group_sub_project is not a valid GitLab project identifier
        GitlabException
            If API call fails (rate limit, not found, etc.)
        """
        try:
            logger.debug(f"Collecting metrics for {group_sub_project}")

            project = self.gl.projects.get(group_sub_project)

            return RepositoryMetrics(
                platform="gitlab",
                url=project.http_url_to_repo,
                repo=group_sub_project,
                default_branch=project.default_branch,
                forks=project.forks_count,
                stars=project.star_count,
                open_issues=project.issues.list(state="opened", iterator=True).total,
                avg_time_to_close_days=self._get_avg_time_to_close(project),
                last_commit_date=self._get_last_commit_date(project),
                branches_total=project.branches.list(get_all=True),
                branches_protected=project.protectedbranches.list(iterator=True).total,
                default_branch_is_protected=project.branches.get(
                    project.default_branch
                ).protected,
                languages=project.languages(),
                has_license=self._get_has_license(project),
                contributors=project.repository_contributors(),  # name, email, commits, additions, deletions
            )
        except GitlabError as e:
            logger.error(
                f"GitLab API error for {group_sub_project}: {e.response_code} - {e.error_message}"
            )
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error collecting metrics for {group_sub_project}: {e}"
            )
            raise

    def _get_avg_time_to_close(self, project) -> float | None:
        """Calculate average time to close issues in days."""
        closed_issues = project.issues.list(state="closed", iterator=True)
        closed_issues = list(closed_issues)

        durations = []
        for i in closed_issues:
            if i.closed_at:
                closed = datetime.fromisoformat(i.closed_at)
                created = datetime.fromisoformat(i.created_at)
                duration_days = (closed - created).total_seconds() / 86400
                durations.append(duration_days)

        return round(mean(durations), 3) if durations else None

    def _get_last_commit_date(self, project) -> str | None:
        """Get the date of the last commit on the default branch."""
        default_branch = project.default_branch
        last_commit = project.commits.list(
            ref_name=default_branch, per_page=1, get_all=False
        )

        if last_commit:
            return last_commit[0].committed_date
        else:
            raise ValueError(
                f"No commits found for default branch '{default_branch}' in project '{project.path_with_namespace}'"
            )

    def _get_has_license(self, project) -> bool:
        """Check if the project has a license file."""
        try:
            repo_tree = project.repository_tree(
                path="", ref=project.default_branch, per_page=100
            )
            for file in repo_tree:
                if (
                    "license" in file["name"].lower()
                    or "copying" in file["name"].lower()
                ):
                    return True
        except GitlabError as e:
            logger.warning(f"Could not retrieve repository tree for license check: {e}")
        return False
