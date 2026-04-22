"""
Base adapter for repository platform adapters.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from fnmatch import fnmatch
from pathlib import PurePosixPath
from typing import Any

from ..models import Contributor, RepositoryMetrics

logger = logging.getLogger(__name__)


WORKFLOW_FILE_PATTERNS = {
    "cwl": ("*.cwl",),
    "nextflow": ("main.nf", "nextflow.config", "*.nf"),
    "snakemake": ("Snakefile", "*.smk"),
    "wdl": ("*.wdl",),
}

DISTRIBUTION_FILE_PATTERNS = {
    "container": ("Dockerfile", "Containerfile", "apptainer.def", "Singularity"),
    "python-package": ("pyproject.toml", "setup.py", "requirements.txt"),
    "conda": (
        "environment.yml",
        "environment.yaml",
        "conda/meta.yaml",
        "meta.yaml",
    ),
}

SECURITY_POLICY_FILE_PATTERNS = (
    "SECURITY.md",
    "SECURITY.rst",
    "SECURITY.txt",
    ".github/SECURITY.md",
    ".github/SECURITY.rst",
    ".github/SECURITY.txt",
    "docs/SECURITY.md",
    "docs/SECURITY.rst",
    "docs/SECURITY.txt",
)

SECURITY_SCANNING_FILE_PATTERNS = (
    ".github/dependabot.yml",
    ".github/dependabot.yaml",
    ".github/workflows/*codeql*.yml",
    ".github/workflows/*codeql*.yaml",
    ".github/workflows/*security*.yml",
    ".github/workflows/*security*.yaml",
    ".github/workflows/*scorecards*.yml",
    ".github/workflows/*scorecards*.yaml",
    "*sast*.gitlab-ci.yml",
    "*dependency-scanning*.gitlab-ci.yml",
    "*secret-detection*.gitlab-ci.yml",
    "*container-scanning*.gitlab-ci.yml",
    ".gitlab/*sast*.yml",
    ".gitlab/*dependency-scanning*.yml",
    ".gitlab/*secret-detection*.yml",
    "ci/*sast*.yml",
    "ci/*dependency-scanning*.yml",
    "ci/*secret-detection*.yml",
)


class BaseRepositoryAdapter(ABC):
    """
    Abstract base class for repository platform adapters.

    Provides shared functionality for analyzing repository structure
    and calculating metrics from repository data.
    """

    @abstractmethod
    def to_repository_metrics(self, raw_data: dict[str, Any]) -> RepositoryMetrics:
        """
        Convert platform-specific raw data to RepositoryMetrics model.

        Parameters
        ----------
        raw_data : dict[str, Any]
            Raw data from platform client

        Returns
        -------
        RepositoryMetrics
            Standardized repository metrics
        """
        pass

    # Shared utility methods

    @staticmethod
    def parse_iso_datetime(value: str) -> datetime:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))

    @staticmethod
    def get_datetime_field(item: Any, field_name: str) -> str | None:
        if isinstance(item, dict):
            return item.get(field_name)
        else:
            return getattr(item, field_name, None)

    @classmethod
    def calculate_avg_time_to_close(
        cls, closed_issues: list[Any] | None
    ) -> float | None:
        """
        Calculate average time to close issues in days.
        """
        if not closed_issues:
            return None

        total_days = 0
        count = 0

        for issue in closed_issues:
            created_at = cls.get_datetime_field(issue, "created_at")
            closed_at = cls.get_datetime_field(issue, "closed_at")

            if created_at and closed_at:
                try:
                    created = cls.parse_iso_datetime(created_at)
                    closed = cls.parse_iso_datetime(closed_at)
                    days = (closed - created).total_seconds() / 86400
                    total_days += days
                    count += 1
                except (ValueError, AttributeError) as e:
                    logger.debug(f"Could not parse issue dates: {e}")
                    continue

        return round(total_days / count, 2) if count > 0 else None

    @staticmethod
    def calculate_inverse_simpson_index(
        contributors: list[Contributor] | None,
    ) -> float | None:
        """
        Calculate inverse Simpson index for contributor diversity.
        """
        if not contributors:
            return None

        total_commits = sum(
            c.total_commits for c in contributors if c.total_commits > 0
        )
        if total_commits == 0:
            return None

        shares = [
            c.total_commits / total_commits for c in contributors if c.total_commits > 0
        ]
        hhi = sum(s**2 for s in shares)

        return round(1 / hhi, 2) if hhi else None

    @staticmethod
    def extract_repository_file_paths(
        repository_items: list[dict[str, Any]] | None,
    ) -> list[str]:
        """
        Extract normalized file paths from repository tree entries.
        """
        if not repository_items:
            return []

        paths: list[str] = []
        for item in repository_items:
            item_type = item.get("type")
            if item_type not in {"blob", "file"}:
                continue

            path = item.get("path") or item.get("name")
            if path:
                paths.append(PurePosixPath(path).as_posix())

        return paths

    @classmethod
    def detect_workflow_support(
        cls, repository_items: list[dict[str, Any]] | None
    ) -> bool | None:
        """
        Detect whether repository files indicate workflow integration support.
        """
        if repository_items is None:
            return None

        file_paths = cls.extract_repository_file_paths(repository_items)
        return any(
            cls._path_matches_patterns(path, patterns)
            for path in file_paths
            for patterns in WORKFLOW_FILE_PATTERNS.values()
        )

    @classmethod
    def detect_distribution_support(
        cls, repository_items: list[dict[str, Any]] | None
    ) -> bool | None:
        """
        Detect whether repository files indicate standard distribution support.
        """
        if repository_items is None:
            return None

        file_paths = cls.extract_repository_file_paths(repository_items)
        has_container = any(
            cls._path_matches_patterns(path, DISTRIBUTION_FILE_PATTERNS["container"])
            for path in file_paths
        )
        has_packaging = any(
            cls._path_matches_patterns(
                path, DISTRIBUTION_FILE_PATTERNS["python-package"]
            )
            or cls._path_matches_patterns(path, DISTRIBUTION_FILE_PATTERNS["conda"])
            for path in file_paths
        )
        return has_container or has_packaging

    @classmethod
    def detect_security_policy(
        cls, repository_items: list[dict[str, Any]] | None
    ) -> bool | None:
        """
        Detect whether repository files include a security policy.
        """
        if repository_items is None:
            return None

        file_paths = cls.extract_repository_file_paths(repository_items)
        return any(
            cls._path_matches_patterns(path, SECURITY_POLICY_FILE_PATTERNS)
            for path in file_paths
        )

    @classmethod
    def detect_security_scanning(
        cls, repository_items: list[dict[str, Any]] | None
    ) -> bool | None:
        """
        Detect whether repository files indicate automated security scanning.
        """
        if repository_items is None:
            return None

        file_paths = cls.extract_repository_file_paths(repository_items)
        return any(
            cls._path_matches_patterns(path, SECURITY_SCANNING_FILE_PATTERNS)
            for path in file_paths
        )

    @staticmethod
    def _path_matches_patterns(path: str, patterns: tuple[str, ...]) -> bool:
        """
        Check if a file path matches any of the given glob patterns.
        """
        file_name = PurePosixPath(path).name
        return any(
            fnmatch(path, pattern) or fnmatch(file_name, pattern)
            for pattern in patterns
        )
