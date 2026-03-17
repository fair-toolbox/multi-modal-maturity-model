"""
High-level pipeline for end-to-end maturity assessment.
"""

import logging
from typing import Any

from .adapters import BioToolsAdapter, GitHubAdapter, GitLabAdapter, LizardAdapter
from .collectors import (
    BioToolsClient,
    EuropePMCClient,
    GitHubClient,
    GitLabClient,
    HowfairisCollector,
    LizardCollector,
)
from .core.models import MaturityProfile
from .git_utils import resolve_repo_path
from .scoring import MaturityMapper

logger = logging.getLogger(__name__)


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
    >>> print(f"Overall score: {profile.overall_score:.2f}")
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
        platform: str | None = None,
        collect_code_quality: bool = True,
        collect_fair: bool = True,
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
        platform : str | None
            Explicit platform specification: "github" or "gitlab"
            Required when using short format (owner/repo)
            Ignored when repo_url is a full URL
        collect_code_quality : bool
            Whether to collect code quality metrics (requires cloning, default: True)
        collect_fair : bool
            Whether to collect FAIR compliance metrics (default: True)

        Returns
        -------
        MaturityProfile
            Complete maturity profile with all dimensions

        Raises
        ------
        ValueError
            If no data sources are provided
        """
        if not any([biotools_id, repo_url, repo_path, pmid]):
            raise ValueError(
                "At least one data source must be provided "
                "(biotools_id, repo_url, repo_path, or pmid)"
            )

        logger.info("Starting maturity assessment...")

        # Initialize collectors
        biotools_client = BioToolsClient() if biotools_id else None
        howfairis_collector = HowfairisCollector() if collect_fair else None
        europepmc_client = EuropePMCClient() if pmid else None

        # Determine repository platform and initialize client
        repo_client = None
        repo_platform = None
        if repo_url or repo_path:
            repo_platform = self._detect_platform(repo_url or repo_path, platform)

            if repo_platform == "github":
                if self.github_token:
                    repo_client = GitHubClient(token=self.github_token)
                else:
                    logger.warning(
                        "GitHub token not provided. Repository metrics will be limited. "
                        "Set GITHUB_TOKEN environment variable for full access."
                    )
            elif repo_platform == "gitlab":
                if self.gitlab_token:
                    repo_client = GitLabClient(token=self.gitlab_token)
                else:
                    logger.warning(
                        "GitLab token not provided. Repository metrics will be limited."
                    )

        # Track if we need to cleanup
        cleanup_path = None
        analysis_path = None

        try:
            # ====== Collect bio.tools data ======
            tool_model = None
            if biotools_client:
                logger.info(f"Collecting bio.tools data for {biotools_id}...")
                try:
                    biotools_raw = biotools_client.fetch(biotools_id)
                    tool_model = BioToolsAdapter.to_tool_model(biotools_raw)
                except Exception as e:
                    logger.warning(f"Failed to collect bio.tools data: {e}")

            # ====== Collect repository data ======
            repository_metrics = None
            if repo_client and repo_url:
                # Extract repo identifier from URL
                repo_identifier = self._extract_repo_identifier(repo_url, repo_platform)
                logger.info(f"Collecting {repo_platform} data for {repo_identifier}...")
                try:
                    if repo_platform == "github":
                        repo_raw = repo_client.fetch(repo_identifier)
                        repository_metrics = GitHubAdapter.to_repository_metrics(
                            repo_raw
                        )
                    elif repo_platform == "gitlab":
                        repo_raw = repo_client.fetch(repo_identifier)
                        repository_metrics = GitLabAdapter.to_repository_metrics(
                            repo_raw
                        )
                except Exception as e:
                    logger.warning(f"Failed to collect repository data: {e}")

            # ====== Resolve repository path for code analysis ======
            if collect_code_quality and (repo_url or repo_path):
                if repo_path:
                    # Use provided local path
                    analysis_path = repo_path
                    logger.info(f"Using local repository at {repo_path}")
                elif repo_url:
                    # Clone repository
                    logger.info(f"Cloning repository from {repo_url}...")
                    try:
                        # Convert short GitHub format to full URL if needed
                        full_url = self._normalize_repo_url(repo_url, repo_platform)
                        analysis_path, should_cleanup = resolve_repo_path(full_url)
                        if should_cleanup:
                            cleanup_path = analysis_path
                            logger.debug(
                                f"Repository cloned to temporary directory: {analysis_path}"
                            )
                    except Exception as e:
                        logger.warning(f"Failed to clone repository: {e}")
                        analysis_path = None

            # ====== Collect code quality metrics ======
            code_quality_metrics = None
            if collect_code_quality and analysis_path:
                logger.info(f"Analyzing code quality at {analysis_path}...")
                try:
                    lizard_collector = LizardCollector()
                    lizard_raw = lizard_collector.fetch(analysis_path)
                    code_quality_metrics = LizardAdapter.to_code_quality_metrics(
                        lizard_raw
                    )
                except Exception as e:
                    logger.warning(f"Failed to collect code quality metrics: {e}")

            # ====== Collect FAIR compliance ======
            fair_metrics = None
            if collect_fair and (
                repo_url or (repository_metrics and repository_metrics.url)
            ):
                fair_url = repo_url or repository_metrics.url
                # Normalize to full URL for howfairis
                fair_url = self._normalize_repo_url(fair_url, repo_platform)
                logger.info(f"Assessing FAIR compliance for {fair_url}...")
                try:
                    fair_metrics = howfairis_collector.fetch(fair_url)
                except Exception as e:
                    logger.warning(f"Failed to collect FAIR metrics: {e}")

            # ====== Collect citation metrics ======
            citation_metrics = None
            if europepmc_client:
                logger.info(f"Collecting citation data for PMID {pmid}...")
                try:
                    citation_metrics = europepmc_client.fetch(pmid)
                except Exception as e:
                    logger.warning(f"Failed to collect citation metrics: {e}")

            # ====== Map to maturity profile ======
            logger.info("Mapping collected data to maturity dimensions...")
            maturity_profile = self.mapper.map_to_maturity_profile(
                tool_model=tool_model,
                repository_metrics=repository_metrics,
                code_quality_metrics=code_quality_metrics,
                fair_metrics=fair_metrics,
                citation_metrics=citation_metrics,
            )

            logger.info(
                f"Assessment complete. Overall score: {maturity_profile.overall_score:.2f}"
            )
            return maturity_profile

        finally:
            # Cleanup temporary clone if needed
            if cleanup_path:
                logger.debug(f"Cleaning up temporary clone at {cleanup_path}")
                import shutil

                try:
                    shutil.rmtree(cleanup_path)
                except Exception as e:
                    logger.warning(f"Failed to cleanup temporary directory: {e}")

    def _detect_platform(
        self, url_or_path: str, explicit_platform: str | None = None
    ) -> str | None:
        """Detect repository platform from URL, path, or explicit specification.

        Parameters
        ----------
        url_or_path : str
            Repository URL, identifier, or local path
        explicit_platform : str | None
            Explicitly specified platform ("github" or "gitlab")
            Takes precedence for short format identifiers

        Returns
        -------
        str | None
            Detected platform ("github" or "gitlab") or None if cannot detect
        """
        if url_or_path.startswith(("http://", "https://", "git@")):
            url_lower = url_or_path.lower()
            if "github.com" in url_lower:
                return "github"
            elif "gitlab" in url_lower:
                return "gitlab"
            return None

        if explicit_platform:
            return explicit_platform

        return None

    def _extract_repo_identifier(self, repo_url: str, platform: str | None) -> str:
        """
        Extract repository identifier from URL.

        Examples:
        - "https://github.com/owner/repo" -> "owner/repo"
        - "owner/repo" -> "owner/repo"
        - "https://gitlab.com/owner/project" -> "owner/project"
        """
        # If already in short format (owner/repo), return as-is
        if "/" in repo_url and not repo_url.startswith(("http://", "https://", "git@")):
            return repo_url

        # Parse URL
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

    def _normalize_repo_url(self, repo_url: str, platform: str | None) -> str:
        """
        Normalize repository URL to full HTTPS format.

        Examples:
        - "owner/repo" -> "https://github.com/owner/repo"
        - "https://github.com/owner/repo" -> "https://github.com/owner/repo"
        """
        if repo_url.startswith(("http://", "https://", "git@")):
            return repo_url

        if platform == "github":
            return f"https://github.com/{repo_url}"
        elif platform == "gitlab":
            return f"https://gitlab.com/{repo_url}"

        return repo_url
