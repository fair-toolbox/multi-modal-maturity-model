# src/multi_modal_maturity_model/collectors/github_metrics.py

"""
GitHub API client for collecting repository health metrics.
"""

import logging
from typing import Any
from statistics import mean

from github import Auth, Github, GithubException
from github.Repository import Repository

logger = logging.getLogger(__name__)


class GitHubMetricsCollector:
    """
    Collect metrics from GitHub repositories.
    Uses PyGithub library for authenticated access.
    """
    
    def __init__(self, token: str, closed_issues_window: int = 300):
        """
        Parameters
        ----------
        token : str
            GitHub personal access token
        closed_issues_window : int
            Number of closed issues to analyze for time-to-close metric
        """
        self.auth = Auth.Token(token)
        self.gh = Github(auth=self.auth)
        self.closed_issues_window = closed_issues_window
        logger.info("GitHubMetricsCollector initialized")
    
    def collect(self, repo_url: str) -> dict[str, Any]:
        """
        Main entry point: collect all metrics for a repository.
        
        Parameters
        ----------
        repo_url : str
            Full GitHub URL (e.g., https://github.com/owner/repo)
            
        Returns
        -------
        dict
            Dictionary with all collected metrics
            
        Raises
        ------
        ValueError
            If repo_url is not a valid GitHub URL
        GithubException
            If API call fails (rate limit, not found, etc.)
        """
        from ..utils import URLParser
        
        try:
            owner_repo = URLParser.to_owner_repo(repo_url)
            logger.debug(f"Collecting metrics for {owner_repo}")
            
            repo = self.gh.get_repo(owner_repo)
            
            return {
                "url": repo_url,
                "repo": owner_repo,
                "default_branch": self._get_default_branch(repo),
                "forks": self._get_forks(repo),
                "open_issues": self._get_open_issues(repo),
                "avg_time_to_close_days": self._get_avg_time_to_close(repo),
                "last_commit_date": self._get_last_commit_date(repo),
                "branches_total": self._get_branch_count(repo),
                "branches_protected": self._get_protected_branch_count(repo),
                "default_branch_is_protected": self._is_default_branch_protected(repo),
                "languages": self._get_languages(repo),
                "contributors": self._get_contributors(repo),
            }
            
        except GithubException as e:
            logger.error(f"GitHub API error for {repo_url}: {e.status} - {e.data}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error collecting metrics for {repo_url}: {e}")
            raise
    
    def _get_default_branch(self, repo: Repository) -> str:
        """Get default branch name."""
        return repo.default_branch
    
    def _get_forks(self, repo: Repository) -> int:
        """Get fork count (Com8 indicator)."""
        return repo.forks_count
    
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
        """Get last commit date on default branch. """
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
                lang for lang, _ in 
                sorted(languages.items(), key=lambda x: x[1], reverse=True)
            ]
        except Exception as e:
            logger.warning(f"Could not get languages: {e}")
            return []
    
    def _get_contributors(self, repo: Repository) -> list[dict[str, Any]]:
        """Get contributors sorted by contribution count."""
        try:
            return [
                {"login": c.login, "total_commits": c.contributions}
                for c in sorted(
                    repo.get_contributors(),
                    key=lambda c: c.contributions,
                    reverse=True
                )
                if c.login is not None
            ]
        except Exception as e:
            logger.warning(f"Could not get contributors: {e}")
            return []
