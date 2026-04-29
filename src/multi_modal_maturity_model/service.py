import logging
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
    PublicationRecord,
    RepositoryMetrics,
    ToolModel,
    MaturityProfile,
)
from .mapper import MaturityMapper

from .utils import detect_platform, extract_repo_identifier, temporary_clone

logger = logging.getLogger(__name__)


class MaturityService:
    """
    High-level orchestrator for complete maturity evaluation.

    Example
    -------
    >>> service = MaturityService(github_token="your_token")
    >>> profile = service.evaluate(
    ...     biotools_id="tool",
    ...     repo_url="https://github.com/owner/repo",
    ...     doi="10.1093/test/paper",
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
        Initialize the maturity service.

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

        self.github_client = GitHubClient(token=github_token)
        self.gitlab_client = GitLabClient(token=gitlab_token)
        self.biotools_client = BioToolsClient()
        self.europepmc_client = EuropePMCClient()
        self.openalex_client = OpenAlexClient()
        self.semantic_scholar_client = SemanticScholarClient()

        self.biotools_adapter = BioToolsAdapter()
        self.github_adapter = GitHubAdapter()
        self.gitlab_adapter = GitLabAdapter()

    def evaluate(
        self,
        biotools_id: str | None = None,
        repo_url: str | None = None,
        repo_path: str | None = None,
        dois: list[str] | None = None,
        include_code_quality: bool = True,
    ) -> MaturityProfile:
        """
         maturity of a research software tool.

        This method orchestrates the entire evaluation pipeline:
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
            Local path to repository (takes precedence over repo_url for code quality analysis)
        dois : list[str] | None
            List of DOIs for Semantic Scholar citation metrics
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

        platform = detect_platform(repo_url)
        repo_identifier = extract_repo_identifier(repo_url, platform)
        repo_client, repo_adapter = self._get_repository_client_and_adapter(platform)

        tool_model = self._collect_biotools(biotools_id) if biotools_id else None
        repository_metrics = (
            self._collect_repository(repo_client, repo_adapter, repo_identifier)
            if repo_client and repo_identifier
            else None
        )
        code_quality_metrics = (
            self._collect_code_quality(repo_url, repo_path)
            if include_code_quality and repo_url
            else None
        )
        fair_metrics = self._collect_howfairis(repo_url)
        publication_metrics = self._collect_publications(dois=dois) if dois else None

        logger.info("Mapping collected data to maturity dimensions...")

        maturity_profile = self.mapper.map_to_maturity_profile(
            tool_model=tool_model,
            repository_metrics=repository_metrics,
            code_quality_metrics=code_quality_metrics,
            fair_metrics=fair_metrics,
            publication_metrics=publication_metrics,
        )

        logger.info("Evaluation complete.")
        return maturity_profile

    def _get_repository_client_and_adapter(self, platform: str):
        if platform == "github":
            return self.github_client, self.github_adapter
        elif platform == "gitlab":
            return self.gitlab_client, self.gitlab_adapter
        return None, None

    def _collect_biotools(self, biotools_id: str) -> ToolModel | None:
        try:
            raw_data = self.biotools_client.fetch(biotools_id)
            tool_model = self.biotools_adapter.to_tool_model(raw_data)
            return tool_model
        except Exception as e:
            logger.error(
                f"Error occurred while collecting biotools data for ID {biotools_id}: {e}"
            )
            return None

    def _collect_repository(
        self, client, adapter, repo_identifier
    ) -> RepositoryMetrics | None:
        try:
            raw_data = client.fetch(repo_identifier)
            repository_metrics = adapter.to_repository_metrics(raw_data)
            return repository_metrics
        except Exception as e:
            logger.error(
                f"Error occurred while collecting repository data for {repo_identifier}: {e}"
            )
            return None

    def _collect_code_quality(
        self, repo_url: str, repo_path: str | None
    ) -> CodeQualityMetrics | None:
        try:
            if not repo_path:
                with temporary_clone(repo_url) as temp_path:
                    raw_data = self.lizard_analyzer.analyze(temp_path)
            else:
                raw_data = self.lizard_analyzer.analyze(repo_path)

            return CodeQualityMetrics(
                total_nloc=raw_data.get("total_nloc"),
                total_ccn=raw_data.get("total_ccn"),
                avg_ccn=raw_data.get("avg_ccn"),
                duplicate_rate=raw_data.get("duplicate_rate"),
            )
        except Exception as e:
            logger.error(
                f"Error occurred while collecting code quality metrics for {repo_url}: {e}"
            )
            return None

    def _collect_howfairis(self, repo_url: str) -> HowfairisMetrics | None:
        try:
            raw = self.howfairis_analyzer.analyze(repo_url)
            return HowfairisMetrics(
                license=raw.get("license"),
                repository=raw.get("repository"),
                registry=raw.get("registry"),
                citation=raw.get("citation"),
                checklist=raw.get("checklist"),
            )
        except Exception as e:
            logger.error(
                f"Error occurred while collecting howfairis metrics for {repo_url}: {e}"
            )
            return None

    def _collect_publications(
        self, dois: list[str] | None
    ) -> PublicationMetrics | None:

        records: list[PublicationRecord] = []

        for doi in dois:
            try:
                epmc = self.europepmc_client.fetch(doi=doi)
                openalex = self.openalex_client.fetch(doi=doi)
                semantic_scholar = self.semantic_scholar_client.fetch(doi=doi)

                record = _merge_publication_record(
                    epmc=epmc,
                    openalex=openalex,
                    semantic_scholar=semantic_scholar,
                    doi=doi,
                )
                if record:
                    records.append(record)

            except Exception as e:
                logger.error(
                    f"Error occurred while collecting publication metrics for DOI {doi}: {e}"
                )

        return _aggregate_publication_metrics(records)


def _merge_publication_record(
    epmc: dict[str, Any] | None = None,
    openalex: dict[str, Any] | None = None,
    semantic_scholar: dict[str, Any] | None = None,
    doi: str | None = None,
) -> PublicationRecord:
    """Merge publication metrics from multiple sources."""
    if not epmc and not openalex and not semantic_scholar:
        return None

    doi = (
        semantic_scholar.get("externalIds", {}).get("DOI")
        if semantic_scholar
        else epmc.get("doi") if epmc else openalex.get("doi")
    )

    pmid = epmc.get("pmid") if epmc else openalex.get("pmid") if openalex else None

    fwci = openalex.get("fwci") if openalex else None

    influential_citation_count = (
        semantic_scholar.get("influentialCitationCount") if semantic_scholar else None
    )

    altmetric_score = None  # Placeholder for future integration

    is_open_access = (
        semantic_scholar.get("isOpenAccess")
        if semantic_scholar
        else openalex.get("is_oa") if openalex else None
    )

    # Simple heuristic: take the maximum citation count across sources
    citation_count = max(
        filter(
            None,
            [
                epmc.get("citation_count") if epmc else None,
                openalex.get("cited_by_count") if openalex else None,
                semantic_scholar.get("citationCount") if semantic_scholar else None,
            ],
        ),
        default=None,
    )

    return PublicationRecord(
        doi=doi,
        pmid=pmid,
        citation_count=citation_count,
        fwci=fwci,
        influential_citation_count=influential_citation_count,
        altmetric_score=altmetric_score,
        is_open_access=is_open_access,
    )


def _aggregate_publication_metrics(
    records: list[PublicationRecord],
) -> PublicationMetrics | None:
    """Aggregate publication records into overall metrics."""
    if not records:
        return None

    total_citation_count = sum(r.citation_count for r in records if r.citation_count)
    total_influential_citation_count = sum(
        r.influential_citation_count for r in records if r.influential_citation_count
    )
    total_fwci = sum(r.fwci for r in records if r.fwci)
    altmetric_score = (
        max(r.altmetric_score for r in records if r.altmetric_score)
        if any(r.altmetric_score for r in records)
        else None
    )
    any_open_access = any(
        r.is_open_access for r in records if r.is_open_access is not None
    )
    all_open_access = all(
        r.is_open_access for r in records if r.is_open_access is not None
    )

    return PublicationMetrics(
        records=records,
        publication_count=len(records),
        total_citation_count=total_citation_count,
        total_influential_citation_count=total_influential_citation_count,
        total_fwci=total_fwci,
        altmetric_score=altmetric_score,
        any_open_access=any_open_access,
        all_open_access=all_open_access,
    )
