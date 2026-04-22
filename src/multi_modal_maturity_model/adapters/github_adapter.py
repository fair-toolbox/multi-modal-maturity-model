"""
Adapter for transforming GitHub client data into core models.
"""

import logging
from typing import Any

from ..models import Contributor, RepositoryMetrics
from .base_repo_adapter import BaseRepositoryAdapter

logger = logging.getLogger(__name__)


class GitHubAdapter(BaseRepositoryAdapter):
    """
    Transform raw GitHub API data into RepositoryMetrics domain model.
    """

    def to_repository_metrics(self, raw_data: dict[str, Any]) -> RepositoryMetrics:
        """
        Convert raw GitHub data to RepositoryMetrics model.

        Parameters
        ----------
        raw_data : dict[str, Any]
            Raw data dictionary from GitHubClient.fetch()

        Returns
        -------
        RepositoryMetrics
            Structured repository metrics model.
        """
        repo = raw_data["repo"]
        default_branch_protected = raw_data.get("default_branch_protected")

        contributors = self._transform_contributors(raw_data.get("contributors"))
        languages = self._extract_languages(raw_data.get("languages"))
        has_license = repo.get("license") is not None
        repository_tree = raw_data.get("contents")

        has_workflow_integration = self.detect_workflow_support(repository_tree)
        has_distribution_support = self.detect_distribution_support(repository_tree)
        has_security_policy = self.detect_security_policy(repository_tree)
        has_security_scanning = self.detect_security_scanning(repository_tree)
        avg_time_to_close = self.calculate_avg_time_to_close(
            raw_data.get("closed_issues")
        )
        inverse_simpson_index = self.calculate_inverse_simpson_index(contributors)

        return RepositoryMetrics(
            platform="github",
            url=repo["html_url"],
            repo=repo["full_name"],
            default_branch=repo["default_branch"],
            stars=repo["stargazers_count"],
            forks=repo["forks_count"],
            open_issues=repo["open_issues_count"],
            avg_time_to_close_days=avg_time_to_close,
            default_branch_is_protected=default_branch_protected,
            languages=languages,
            has_license=has_license,
            contributors=contributors,
            has_workflow_integration=has_workflow_integration,
            has_distribution_support=has_distribution_support,
            has_security_policy=has_security_policy,
            has_security_scanning=has_security_scanning,
            last_commit_date=repo.get("pushed_at"),
            inverse_simpson_index=inverse_simpson_index,
        )

    @staticmethod
    def _transform_contributors(
        contributors_raw: list[dict[str, Any]] | None,
    ) -> list[Contributor]:
        if not contributors_raw:
            return []
        return [
            Contributor(login=c["login"], total_commits=c["contributions"])
            for c in contributors_raw
        ]

    @staticmethod
    def _extract_languages(languages: dict[str, Any] | None) -> list[str]:
        if not languages:
            return []
        return list(languages.keys())
