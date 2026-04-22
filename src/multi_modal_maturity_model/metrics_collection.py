import logging

from typing import Any

from .adapters import BioToolsAdapter, GitHubAdapter, GitLabAdapter
from .analyzers import HowfairisAnalyzer, LizardAnalyzer
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
)
from .utils import temporary_clone


logger = logging.getLogger(__name__)


def collect_biotools(
    client: BioToolsClient, adapter: BioToolsAdapter, biotools_id: str
) -> ToolModel | None:
    """Collect and normalize tool metrics for given platform."""
    try:
        raw_data = client.fetch(biotools_id)
        tool_model = adapter.to_tool_model(raw_data)
        return tool_model
    except Exception as e:
        logger.warning(f"Failed to collect metrics for biotoolsID {biotools_id}: {e}")
        return None


def collect_code_quality(
    client: LizardAnalyzer, repo_url: str | None, repo_path: str | None
) -> CodeQualityMetrics | None:
    """Collect and normalize code quality metrics."""
    try:
        if not repo_path:
            with temporary_clone(repo_url) as temp_path:
                raw_data = client.analyze(temp_path)
        else:
            raw_data = client.analyze(repo_path)

        code_quality_metrics = CodeQualityMetrics(
            total_nloc=raw_data.get("total_nloc"),
            total_ccn=raw_data.get("total_ccn"),
            avg_ccn=raw_data.get("avg_ccn"),
            duplicate_rate=raw_data.get("duplicate_rate"),
        )
        return code_quality_metrics
    except Exception as e:
        logger.error(f"Failed to collect code quality metrics: {e}")
        return None


def collect_howfairis(
    client: HowfairisAnalyzer, repo_url: str
) -> HowfairisMetrics | None:
    """Collect fairnessmetrics."""
    try:
        fair_metrics = client.analyze(repo_url)
        return HowfairisMetrics(
            license=fair_metrics.get("license"),
            repository=fair_metrics.get("repository"),
            registry=fair_metrics.get("registry"),
            citation=fair_metrics.get("citation"),
            checklist=fair_metrics.get("checklist"),
        )
    except Exception as e:
        logger.error(f"Failed to collect FAIR metrics for {repo_url}: {e}")
        return None


def collect_publications(
    epmc_client: EuropePMCClient,
    openalex_client: OpenAlexClient,
    ss_client: SemanticScholarClient,
    pmid: str | None = None,
    doi: str | None = None,
) -> PublicationMetrics | None:
    """Collect and normalize publication metrics."""
    try:
        epmc_data = epmc_client.fetch(pmid=pmid, doi=doi)
        ss_data = ss_client.fetch(doi)
        openalex_data = openalex_client.fetch(pmid=pmid, doi=doi)

        publication_metrics = _merge_publication_metrics(
            epmc=epmc_data,
            openalex=openalex_data,
            semantic_scholar=ss_data,
        )

        return publication_metrics
    except Exception as e:
        logger.warning(
            f"Failed to collect publication metrics for PMID {pmid} and DOI {doi}: {e}"
        )
        return None


def collect_repository(
    client: GitHubClient | GitLabClient,
    adapter: GitHubAdapter | GitLabAdapter,
    repo_identifier: str,
) -> RepositoryMetrics | None:
    """Collect and normalize repository metrics."""
    try:
        raw_data = client.fetch(repo_identifier)
        repo_model = adapter.to_repository_metrics(raw_data)
        return repo_model
    except Exception as e:
        logger.error(f"Failed to collect repository metrics for {repo_identifier}: {e}")
        return None


def _merge_publication_metrics(
    epmc: dict[str, Any] | None = None,
    openalex: dict[str, Any] | None = None,
    semantic_scholar: dict[str, Any] | None = None,
) -> PublicationMetrics | None:
    """Merge publication metrics from multiple sources."""

    if not epmc and not openalex and not semantic_scholar:
        return None

    merged_metrics = PublicationMetrics(
        doi=(
            semantic_scholar.get("externalIds", {}).get("DOI")
            if semantic_scholar
            else epmc.get("doi") if epmc else openalex.get("doi")
        ),
        pmid=epmc.get("pmid") if epmc else openalex.get("pmid") if openalex else None,
        citation_count=(
            semantic_scholar.get("citationCount")
            if semantic_scholar
            else epmc.get("citation_count") if epmc else openalex.get("citation_count")
        ),
        fwci=openalex.get("fwci") if openalex else None,
        influential_citation_count=(
            semantic_scholar.get("influentialCitationCount")
            if semantic_scholar
            else None
        ),
        altmetric_score=None,
        is_open_access=(
            semantic_scholar.get("isOpenAccess")
            if semantic_scholar
            else openalex.get("is_oa") if openalex else None
        ),
    )

    return merged_metrics
