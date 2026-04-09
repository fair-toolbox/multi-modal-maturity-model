"""
High-level pipeline for end-to-end maturity assessment.
"""

import logging
from dataclasses import dataclass
from typing import Any

from .core.models import (
    CodeQualityMetrics,
    MaturityProfile,
    RepositoryMetrics,
    ToolModel,
)
from .scoring import MaturityMapper

from .collect import (
    collect_biotools,
    collect_code_quality,
    collect_howfairis,
    collect_publications,
    collect_repository,
)

logger = logging.getLogger(__name__)


@dataclass
class CollectedMetricsBundle:
    tool_model: ToolModel | None
    repository_metrics: RepositoryMetrics | None
    code_quality_metrics: CodeQualityMetrics | None
    fair_metrics: dict[str, Any] | None
    publication_metrics: dict[str, Any] | None


class MaturityAssessor:
    """
    High-level orchestrator for complete maturity assessment.

    This class handles the entire pipeline:
    1. Automatic repository cloning (if URL provided)
    2. Data collection from all available sources
    3. Mapping to maturity dimensions
    4. Cleanup of temporary resources

    Example
    -------
    >>> assessor = MaturityAssessor(github_token="your_token")
    >>> profile = assessor.assess(
    ...     biotools_id="blast",
    ...     repo_url="https://github.com/ncbi/blast",
    ...     pmid="20003500"
    ... )
    >>> print(f"Overall score: {profile.overall_score.score:.2f}")
    """

    def __init__(
        self,
        github_token: str | None = None,
        gitlab_token: str | None = None,
        max_citations_corpus: int = 1000,
    ):
        """
        Initialize the maturity assessor.

        Parameters
        ----------
        github_token : str | None
            GitHub API token for authenticated requests
        gitlab_token : str | None
            GitLab API token for authenticated requests
        max_citations_corpus : int
            Maximum citations in reference corpus for normalizing
            scientific impact (default: 1000)
        """
        self.github_token = github_token
        self.gitlab_token = gitlab_token
        self.max_citations_corpus = max_citations_corpus

        # Initialize mapper
        self.mapper = MaturityMapper(max_citations_corpus=max_citations_corpus)

    def assess(
        self,
        biotools_id: str | None = None,
        repo_url: str | None = None,
        repo_path: str | None = None,
        pmid: str | None = None,
        doi: str | None = None,
        platform: str | None = None,
        include_code_quality: bool = True,
    ) -> MaturityProfile:
        """
        Assess maturity of a research software tool.

        This method orchestrates the entire assessment pipeline:
        - Clones repository if URL provided (and no local path)
        - Collects data from all available sources
        - Maps to maturity dimensions
        - Cleans up temporary clones

        Parameters
        ----------
        biotools_id : str | None
            bio.tools identifier (e.g., "blast")
        repo_url : str | None
            Repository URL or identifier
            - Full URL: https://github.com/owner/repo or https://gitlab.com/group/project
            - Short format: owner/repo (requires platform parameter)
        repo_path : str | None
            Local path to repository (takes precedence over repo_url)
        pmid : str | None
            PubMed ID for citation metrics
        doi : str | None
            DOI for Semantic Scholar citation metrics
        platform : str | None
            Explicit platform specification: "github" or "gitlab"
            Required when using short format (owner/repo)
            Ignored when repo_url is a full URL
        include_code_quality : bool
            Whether to include code quality metrics (requires cloning, default: True)

        Returns
        -------
        MaturityProfile
            Complete maturity profile with all dimensions

        Raises
        ------
        ValueError
            If repo_url is not provided or invalid.
        """
        if not repo_url:
            raise ValueError("Repository URL is required.")

        bundle = self._run_collection(
            biotools_id=biotools_id,
            repo_url=repo_url,
            repo_path=repo_path,
            pmid=pmid,
            doi=doi,
            platform=platform,
            include_code_quality=include_code_quality,
        )

        logger.info("Mapping collected data to maturity dimensions...")
        maturity_profile = self.mapper.map_to_maturity_profile(
            tool_model=bundle.tool_model,
            repository_metrics=bundle.repository_metrics,
            code_quality_metrics=bundle.code_quality_metrics,
            fair_metrics=bundle.fair_metrics,
            citation_metrics=bundle.publication_metrics,
        )

        logger.info(
            f"Assessment complete. Overall score: {maturity_profile.overall_score.score:.2f}"
        )
        return maturity_profile

    def _detect_platform(self, url: str) -> str | None:
        """Detect repository platform from URL."""
        if url.startswith(("http://", "https://", "git@")):
            url_lower = url.lower()
            if "github.com" in url_lower:
                return "github"
            elif "gitlab" in url_lower:
                return "gitlab"

        raise ValueError(f"Could not detect supported platform from URL: {url}")

    def _extract_repo_identifier(self, repo_url: str, platform: str | None) -> str:
        """
        Extract repository identifier from URL.

        Examples:
        - "https://github.com/owner/repo" -> "owner/repo"
        - "https://gitlab.com/owner/project" -> "owner/project"
        """
        if platform == "github":
            if "github.com/" in repo_url:
                parts = repo_url.split("github.com/")[1].split("/")
                repo = parts[1]
                if repo.endswith(".git"):
                    repo = repo[:-4]
                return f"{parts[0]}/{repo}"
        elif platform == "gitlab":
            if "gitlab.com/" in repo_url:
                # GitLab supports nested groups (e.g., group/subgroup/project)
                path = repo_url.split("gitlab.com/")[1]
                if path.endswith(".git"):
                    path = path[:-4]
                return path.rstrip("/")

        return repo_url

    def _run_collection(
        self,
        biotools_id: str | None,
        repo_url: str | None,
        repo_path: str | None,
        pmid: str | None,
        doi: str | None,
        platform: str | None,
        include_code_quality: bool,
    ) -> dict[str, Any]:
        """
        Run the data collection pipeline.

        Returns a dictionary with all collected data.
        """
        # Determine platform if not provided
        if repo_url and not platform:
            platform = self._detect_platform(repo_url)

        # Extract repository identifier for API calls
        repo_identifier = (
            self._extract_repo_identifier(repo_url, platform) if repo_url else None
        )

        # Collect data from all sources
        tool_model = collect_biotools(biotools_id) if biotools_id else None
        repository_metrics = (
            collect_repository(
                repo_identifier, platform, self.github_token, self.gitlab_token
            )
            if repo_identifier
            else None
        )
        code_quality_metrics = (
            collect_code_quality(repo_url, repo_path)
            if include_code_quality and repo_url
            else None
        )
        fair_metrics = collect_howfairis(repo_url)
        publication_metrics = collect_publications(pmid, doi) if pmid or doi else None

        return CollectedMetricsBundle(
            tool_model=tool_model,
            repository_metrics=repository_metrics,
            code_quality_metrics=code_quality_metrics,
            fair_metrics=fair_metrics,
            publication_metrics=publication_metrics,
        )
