"""
Adapter for transforming GitLab collector data into core models.
"""

import logging
from datetime import datetime
from typing import Any

from multi_modal_maturity_model.core.models import Contributor, RepositoryMetrics

logger = logging.getLogger(__name__)

LICENSE_FILENAMES = {
    "license",
    "license.md",
    "license.txt",
    "copying",
    "copying.md",
    "copying.txt",
}


class GitLabAdapter:
    """
    Transform raw GitLab API data into RepositoryMetrics domain model.

    This adapter takes the dictionary returned by GitLabClient.fetch()
    and converts it into a structured RepositoryMetrics object.
    """

    @staticmethod
    def to_repository_metrics(raw_data: dict[str, Any]) -> RepositoryMetrics:
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

        contributors = transform_contributors(raw_data.get("contributors"))
        languages = extract_languages(raw_data.get("languages"))
        avg_time_to_close = calculate_avg_time_to_close(raw_data.get("closed_issues"))
        has_license = detect_license(raw_data.get("repository_tree", []))

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
        )


def transform_contributors(contributors_raw: list[dict[str, Any]]) -> list[Contributor]:
    if not contributors_raw:
        return []
    return [
        Contributor(login=c.get("name", "unknown"), total_commits=c.get("commits", 0))
        for c in contributors_raw
    ]


def extract_languages(languages: dict[str, Any]) -> list[str]:
    if not languages:
        return []
    return list(languages.keys())


def parse_gitlab_iso_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def calculate_avg_time_to_close(closed_issues: list[Any] | None) -> float | None:
    """
    Calculate average time to close issues in days.
    Parameters
    ----------
    closed_issues : list[Any] | None
        List of closed issue objects from GitLab API.
    Returns
    -------
    float | None
        Average days to close, or None if no data available.
    """
    if not closed_issues:
        return None

    total_days = 0
    count = 0

    for issue in closed_issues:
        created_at = parse_gitlab_iso_datetime(getattr(issue, "created_at", None))
        closed_at = parse_gitlab_iso_datetime(getattr(issue, "closed_at", None))

        if created_at and closed_at:
            total_days += (closed_at - created_at).total_seconds() / 86400
            count += 1

    if count == 0:
        return None

    return round(total_days / count, 2)


def detect_license(repository_tree: list[dict[str, Any]]) -> bool:
    """
    Check if repository tree has a license file.
    Parameters
    ----------
    repository_tree : list[dict[str, Any]]
        Repository tree data from GitLab API.
    Returns
    -------
    bool
        True if license exists, False otherwise.
    """
    for file in repository_tree:
        if file["type"] == "blob" and file["name"].lower() in LICENSE_FILENAMES:
            return True
    return False
