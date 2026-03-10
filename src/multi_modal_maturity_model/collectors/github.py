"""
GitHub API client for collecting repository health metrics.
"""

import logging
from typing import Any
from statistics import mean

from github import Auth, Github, GithubException
from github.Repository import Repository

from ..core.models import RepositoryMetrics

logger = logging.getLogger(__name__)


class GitHubCollector:
    """
    Collect metrics from GitHub repositories.
    Uses PyGithub library for authenticated access.
    Parameters
    ----------
    token : str
        GitHub personal access token
    closed_issues_window : int
        Number of closed issues to analyze for time-to-close metric
    """

    def __init__(self, token: str, closed_issues_window: int = 300):
        self.auth = Auth.Token(token)
        self.gh = Github(auth=self.auth)
        self.closed_issues_window = closed_issues_window

    def _get(self, owner_repo: str) -> dict[str, Any]:
        try:
            data = self.gh.get_repo(owner_repo)
            return data
        except GithubException as e:
            logger.warning(f"Error fetching GitHub repository {owner_repo}: {e}")
            raise

    def fetch(self, owner_repo: str) -> dict[str, Any]:
        """
        Fetch repository metadata for a given owner/repo format.

        Parameters
        ----------
        owner_repo : str
            Repository in owner/repo format (e.g., "owner/repo")

        Returns
        -------
        dict
            Dictionary containing the repository metadata.
        """
        logger.debug(f"Fetching GitHub repository {owner_repo}")
        data = self._get(owner_repo)
        logger.info(f"Successfully collected GitHub repository {owner_repo}")
        return data

    def collect(self, owner_repo: str) -> RepositoryMetrics:
        """
        Main entry point: collect all metrics for a repository.

        Parameters
        ----------
        owner_repo : str
            Repository in owner/repo format (e.g., "owner/repo")

        Returns
        -------
        RepositoryMetrics
            Instance containing all collected metrics

        Raises
        ------
        GithubException
            If API call fails (rate limit, not found, etc.)
        """
        try:
            logger.debug(f"Collecting metrics for {owner_repo}")

            repo = self.gh.get_repo(owner_repo)

            return RepositoryMetrics(
                platform="github",
                repo=owner_repo,
                url=repo.html_url,
                default_branch=self._get_default_branch(repo),
                stars=self._get_stars(repo),
                forks=self._get_forks(repo),
                open_issues=self._get_open_issues(repo),
                avg_time_to_close_days=self._get_avg_time_to_close(repo),
                last_commit_date=self._get_last_commit_date(repo),
                branches_total=self._get_branch_count(repo),
                branches_protected=self._get_protected_branch_count(repo),
                default_branch_is_protected=self._is_default_branch_protected(repo),
                languages=self._get_languages(repo),
                has_license=self._get_license(repo),
                contributors=self._get_contributors(repo),
            )

        except GithubException as e:
            logger.error(f"GitHub API error for {owner_repo}: {e.status} - {e.data}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error collecting metrics for {owner_repo}: {e}")
            raise

    def _get_default_branch(self, repo: Repository) -> str:
        """Get default branch name."""
        return repo.default_branch

    def _get_forks(self, repo: Repository) -> int:
        """Get fork count (Com8 indicator)."""
        return repo.forks_count

    def _get_stars(self, repo: Repository) -> int:
        """Get star count."""
        return repo.stargazers_count

    def _get_open_issues(self, repo: Repository) -> int:
        """Get open issues count (Is1 indicator)."""
        return repo.get_issues(state="open").totalCount

    def _get_avg_time_to_close(self, repo: Repository) -> float | None:
        """
        Calculate average time to close issues in days (Is2 indicator).

        Returns
        -------
        float | None
            Average days to close, or None if no closed issues found
        """
        try:
            closed_issues = repo.get_issues(state="closed")
            durations_seconds = []

            for i, issue in enumerate(closed_issues):
                if i >= self.closed_issues_window:
                    break
                # Skip pull requests
                if issue.pull_request is not None:
                    continue
                if issue.created_at and issue.closed_at:
                    duration = (issue.closed_at - issue.created_at).total_seconds()
                    durations_seconds.append(duration)

            if not durations_seconds:
                return None

            avg_seconds = mean(durations_seconds)
            return round(avg_seconds / 86400, 3)  # Convert to days

        except Exception as e:
            logger.warning(f"Could not calculate avg time to close: {e}")
            return None

    def _get_last_commit_date(self, repo: Repository) -> str | None:
        """Get last commit date on default branch."""
        try:
            branch = repo.get_branch(repo.default_branch)
            commit = repo.get_commit(branch.commit.sha)
            return commit.commit.author.date.strftime("%Y-%m-%d")
        except Exception as e:
            logger.warning(f"Could not get last commit date: {e}")
            return None

    def _get_branch_count(self, repo: Repository) -> int:
        """Get total branch count (Co3 indicator)."""
        try:
            return repo.get_branches().totalCount
        except Exception as e:
            logger.warning(f"Could not get branch count: {e}")
            return 0

    def _get_protected_branch_count(self, repo: Repository) -> int:
        """Get protected branch count (Co3 indicator)."""
        try:
            branches = list(repo.get_branches())
            return sum(1 for b in branches if b.protected)
        except Exception as e:
            logger.warning(f"Could not get protected branch count: {e}")
            return 0

    def _is_default_branch_protected(self, repo: Repository) -> bool | None:
        """Check if default branch is protected (Co13 indicator)."""
        try:
            branch = repo.get_branch(repo.default_branch)
            return branch.protected
        except Exception as e:
            logger.warning(f"Could not check default branch protection: {e}")
            return None

    def _get_languages(self, repo: Repository) -> list[str]:
        """Get languages sorted by usage."""
        try:
            languages = repo.get_languages()
            return [
                lang
                for lang, _ in sorted(
                    languages.items(), key=lambda x: x[1], reverse=True
                )
            ]
        except Exception as e:
            logger.warning(f"Could not get languages: {e}")
            return []

    def _get_license(self, repo: Repository) -> bool:
        """Return true if repo has a license, else False."""
        try:
            license_obj = repo.get_license()
            return license_obj is not None
        except GithubException:
            return False
        except Exception as e:
            logger.warning(f"Cannot get license: {e}")
            return False

    def _get_contributors(self, repo: Repository) -> list[dict[str, Any]]:
        """Get contributors sorted by contribution count."""
        try:
            return [
                {"login": c.login, "total_commits": c.contributions}
                for c in sorted(
                    repo.get_contributors(), key=lambda c: c.contributions, reverse=True
                )
                if c.login is not None
            ]
        except Exception as e:
            logger.warning(f"Could not get contributors: {e}")
            return []
