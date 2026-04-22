"""
High-level pipeline for end-to-end maturity assessment.
"""

import logging
from dataclasses import dataclass
from functools import cached_property
from typing import Any

from .adapters import (
    BioToolsAdapter,
    GitHubAdapter,
    GitLabAdapter,
)

from .analyzers import (
    HowfairisAnalyzer,
    LizardAnalyzer,
)

from .clients import (
    BioToolsClient,
    EuropePMCClient,
    GitHubClient,
    GitLabClient,
    OpenAlexClient,
    SemanticScholarClient,
)

from .models import (
    CodeQualityMetrics,
    HowfairisMetrics,
    PublicationMetrics,
    RepositoryMetrics,
    ToolModel,
    MaturityProfile,
)
from .mapper import MaturityMapper

from .metrics_collection import (
    collect_biotools,
    collect_code_quality,
    collect_howfairis,
    collect_publications,
    collect_repository,
)

from .utils import detect_platform, extract_repo_identifier

logger = logging.getLogger(__name__)


@dataclass
class CollectedMetricsBundle:
    tool_model: ToolModel | None
    repository_metrics: RepositoryMetrics | None
    code_quality_metrics: CodeQualityMetrics | None
    fair_metrics: HowfairisMetrics | None
    publication_metrics: PublicationMetrics | None


class MaturityAssessor:
    """
    High-level orchestrator for complete maturity assessment.

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
        weights: dict[str, dict[str, float]] | None = None,
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
        weights : dict[str, dict[str, float]] | None
            Custom weights for dimensions and overall score.
            If None, uses defaults from weights.py.
            Example:
            {
                "compatibility": {"input_formats": 0.3, "output_formats": 0.3, ...},
                "overall": {"fairness": 0.3, "sustainability": 0.3, ...},
            }
        """

        if not github_token and not gitlab_token:
            raise ValueError(
                "At least one API token (GitHub or GitLab) must be provided."
            )

        self.github_token = github_token
        self.gitlab_token = gitlab_token
        self.max_citations_corpus = max_citations_corpus

        self.mapper = MaturityMapper(
            max_citations_corpus=max_citations_corpus, weights=weights
        )

        self.howfairis_analyzer = HowfairisAnalyzer(
            github_token=github_token, gitlab_token=gitlab_token
        )
        self.lizard_analyzer = LizardAnalyzer()

    @cached_property
    def github_client(self) -> GitHubClient:
        return GitHubClient(token=self.github_token)

    @cached_property
    def gitlab_client(self) -> GitLabClient:
        return GitLabClient(token=self.gitlab_token)

    @cached_property
    def biotools_client(self) -> BioToolsClient:
        return BioToolsClient()

    @cached_property
    def europepmc_client(self) -> EuropePMCClient:
        return EuropePMCClient()

    @cached_property
    def openalex_client(self) -> OpenAlexClient:
        return OpenAlexClient()

    @cached_property
    def semantic_scholar_client(self) -> SemanticScholarClient:
        return SemanticScholarClient()

    @cached_property
    def github_adapter(self) -> GitHubAdapter:
        return GitHubAdapter()

    @cached_property
    def gitlab_adapter(self) -> GitLabAdapter:
        return GitLabAdapter()

    @cached_property
    def biotools_adapter(self) -> BioToolsAdapter:
        return BioToolsAdapter()

    def assess(
        self,
        biotools_id: str | None = None,
        repo_url: str | None = None,
        repo_path: str | None = None,
        pmid: str | None = None,
        doi: str | None = None,
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
        repo_path : str | None
            Local path to repository (takes precedence over repo_url)
        pmid : str | None
            PubMed ID for citation metrics
        doi : str | None
            DOI for Semantic Scholar citation metrics
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
            include_code_quality=include_code_quality,
        )

        logger.info("Mapping collected data to maturity dimensions...")
        maturity_profile = self.mapper.map_to_maturity_profile(
            tool_model=bundle.tool_model,
            repository_metrics=bundle.repository_metrics,
            code_quality_metrics=bundle.code_quality_metrics,
            fair_metrics=bundle.fair_metrics,
            publication_metrics=bundle.publication_metrics,
        )

        logger.info("Assessment complete.")
        return maturity_profile

    def assess_batch(
        self,
        tools: list[dict[str, Any]],
        include_code_quality: bool = True,
    ) -> list[MaturityProfile | None]:
        """Batch assessment for multiple tools."""
        profiles = []
        for tool_spec in tools:
            try:
                profile = self.assess(
                    **tool_spec, include_code_quality=include_code_quality
                )
                profiles.append(profile)
            except Exception as e:
                logger.error(
                    f"Failed to assess tool {tool_spec.get('biotools_id', 'repo_url')}: {e}"
                )
                profiles.append(None)

        return profiles

    def _get_repository_client_and_adapter(self, platform: str):
        if platform == "github":
            return self.github_client, self.github_adapter
        elif platform == "gitlab":
            return self.gitlab_client, self.gitlab_adapter
        return None, None

    def _run_collection(
        self,
        biotools_id: str | None,
        repo_url: str | None,
        repo_path: str | None,
        pmid: str | None,
        doi: str | None,
        include_code_quality: bool,
    ) -> CollectedMetricsBundle:
        """
        Run the data collection pipeline.

        Returns a dictionary with all collected data.
        """
        platform = detect_platform(repo_url)

        repo_identifier = (
            extract_repo_identifier(repo_url, platform) if repo_url else None
        )

        repo_client, repo_adapter = self._get_repository_client_and_adapter(platform)

        repository_metrics = (
            collect_repository(repo_client, repo_adapter, repo_identifier)
            if repo_client and repo_identifier
            else None
        )

        tool_model = (
            collect_biotools(self.biotools_client, self.biotools_adapter, biotools_id)
            if biotools_id
            else None
        )

        code_quality_metrics = (
            collect_code_quality(self.lizard_analyzer, repo_url, repo_path)
            if include_code_quality and repo_url
            else None
        )

        fair_metrics = collect_howfairis(self.howfairis_analyzer, repo_url)

        publication_metrics = (
            collect_publications(
                self.europepmc_client,
                self.openalex_client,
                self.semantic_scholar_client,
                pmid,
                doi,
            )
            if pmid or doi
            else None
        )

        return CollectedMetricsBundle(
            tool_model=tool_model,
            repository_metrics=repository_metrics,
            code_quality_metrics=code_quality_metrics,
            fair_metrics=fair_metrics,
            publication_metrics=publication_metrics,
        )
