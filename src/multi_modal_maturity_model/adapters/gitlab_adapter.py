"""
Adapter for transforming GitLab client data into core models.
"""

import logging
from typing import Any

from ..models import Contributor, RepositoryMetrics
from .base_repo_adapter import BaseRepositoryAdapter

logger = logging.getLogger(__name__)

LICENSE_FILENAMES = {
    "license",
    "license.md",
    "license.txt",
    "copying",
    "copying.md",
    "copying.txt",
}


class GitLabAdapter(BaseRepositoryAdapter):
    """
    Transform raw GitLab API data into RepositoryMetrics domain model.
    """

    def to_repository_metrics(self, raw_data: dict[str, Any]) -> RepositoryMetrics:
        """
        Convert raw GitLab data to RepositoryMetrics model.

        Parameters
        ----------
        raw_data : dict[str, Any]
            Raw data dictionary from GitLabClient.fetch()

        Returns
        -------
        RepositoryMetrics
            Structured repository metrics model.
        """
        repo = raw_data["repo"]
        open_issues_count = raw_data.get("open_issues_count", 0)
        default_branch_protected = raw_data.get("default_branch_protected")

        contributors = self._transform_contributors(raw_data.get("contributors"))
        languages = self._extract_languages(raw_data.get("languages"))
        repository_tree = raw_data.get("repository_tree")
        has_license = self._detect_license(repository_tree or [])

        has_workflow_integration = self.detect_workflow_support(repository_tree)
        has_distribution_support = self.detect_distribution_support(repository_tree)
        has_security_policy = self.detect_security_policy(repository_tree)
        has_security_scanning = self.detect_security_scanning(repository_tree)
        avg_time_to_close = self.calculate_avg_time_to_close(
            raw_data.get("closed_issues")
        )
        inverse_simpson_index = self.calculate_inverse_simpson_index(contributors)

        return RepositoryMetrics(
            platform="gitlab",
            url=repo.get("web_url"),
            repo=repo.get("path_with_namespace"),
            default_branch=repo.get("default_branch"),
            stars=repo.get("star_count", 0),
            forks=repo.get("forks_count", 0),
            open_issues=open_issues_count,
            avg_time_to_close_days=avg_time_to_close,
            default_branch_is_protected=default_branch_protected,
            languages=languages,
            has_license=has_license,
            contributors=contributors,
            has_workflow_integration=has_workflow_integration,
            has_distribution_support=has_distribution_support,
            has_security_policy=has_security_policy,
            has_security_scanning=has_security_scanning,
            last_commit_date=repo.get("last_activity_at"),
            inverse_simpson_index=inverse_simpson_index,
        )

    @staticmethod
    def _transform_contributors(
        contributors_raw: list[dict[str, Any]] | None,
    ) -> list[Contributor]:
        if not contributors_raw:
            return []
        return [
            Contributor(
                login=c.get("name", "unknown"), total_commits=c.get("commits", 0)
            )
            for c in contributors_raw
        ]

    @staticmethod
    def _extract_languages(languages: dict[str, Any] | None) -> list[str]:
        if not languages:
            return []
        return list(languages.keys())

    @staticmethod
    def _detect_license(repository_tree: list[dict[str, Any]]) -> bool:
        """
        Check if repository tree has a license file. GitLab does not provide license info in the main repo metadata.
        """
        for file in repository_tree:
            if file["type"] == "blob" and file["name"].lower() in LICENSE_FILENAMES:
                return True
        return False
