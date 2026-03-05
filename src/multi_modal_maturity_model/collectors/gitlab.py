"""
GitLab API client for collecting repository health metrics.
"""

import datetime
import logging
from gitlab import Gitlab, GitlabError
from matplotlib.pylab import mean
from typing import Any

logger = logging.getLogger(__name__)


class GitlabCollector:
    """
    Collect metrics from GitLab repositories.
    Uses  library python-gitlab for authenticated access.
    """

    def __init__(self, token: str, closed_issues_window: int = 300):
        """
        Parameters
        ----------
        token : str
            GitLab personal access token
        closed_issues_window : int
            Number of closed issues to analyze for time-to-close metric
        """
        self.gl = Gitlab('https://gitlab.com', private_token=token)
        self.closed_issues_window = closed_issues_window
        logger.info("GitLabCollector initialized")

    def collect(self, repo_url: str) -> dict[str, Any]:
        """
        Main entry point: collect all metrics for a repository.

        Parameters
        ----------
        repo_url : str
            Full GitLab URL (e.g., https://gitlab.com/owner/repo)

        Returns
        -------
        dict
            Dictionary with all collected metrics

        Raises
        ------
        ValueError
            If repo_url is not a valid GitLab URL
        GitlabException
            If API call fails (rate limit, not found, etc.)
        """
        from ..utils import URLParser

        try:
            group_sub_project = URLParser.to_owner_repo(repo_url)
            logger.debug(f"Collecting metrics for {group_sub_project}")

            project = self.gl.projects.get(group_sub_project, )

            return {
                "url": repo_url,
                "repo": group_sub_project,
                "default_branch": project.default_branch,
                "forks": project.forks_count,
                "open_issues": project.issues.list(state='opened', iterator=True).total,
                "avg_time_to_close_days": self._get_avg_time_to_close(project),
                "last_commit_date": self._get_last_commit_date(project),
                "branches_total": project.branches.list(get_all=True),
                "branches_protected": project.protectedbranches.list(iterator=True).total,
                "default_branch_is_protected": project.branches.get(project.default_branch).protected,
                "languages": project.languages(),
                "has_license": self._get_has_license(project),
                "contributors": project.repository_contributors(), # name, email, commits, additions, deletions
                "stars": project.star_count,
            }

        except GitlabError as e:
            logger.error(f"GitLab API error for {repo_url}: {e.response_code} - {e.error_message}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error collecting metrics for {repo_url}: {e}")
            raise


    def _get_avg_time_to_close(self, project) -> float | None:
        closed_issues = project.issues.list(state='closed', iterator=True)
        closed_issues = list(closed_issues)

        durations = []
        for i in closed_issues:
            if i.closed_at:
                closed = datetime.fromisoformat(i.closed_at)
                created = datetime.fromisoformat(i.created_at)
                duration_days = (closed - created).total_seconds() / 86400
                durations.append(duration_days)

        return mean(durations) if durations else None

    def _get_last_commit_date(self, project) -> str | None:
        pass

    def _get_has_license(self, project) -> bool:
        # GitLab API does not have a direct "has_license" field or license_url
        # We can check if the project has a license file in the repository...
        pass
