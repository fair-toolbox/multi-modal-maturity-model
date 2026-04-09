from .adapters import BioToolsAdapter, GitHubAdapter, GitLabAdapter
from .collectors import (
    BioToolsClient,
    EuropePMCClient,
    GitHubClient,
    GitLabClient,
    HowfairisCollector,
    LizardCollector,
    SemanticScholarClient,
)
from .core.models import CodeQualityMetrics, RepositoryMetrics, ToolModel
from .git_utils import temporary_clone

import logging

logger = logging.getLogger(__name__)


def collect_biotools(biotools_id: str) -> ToolModel | None:
    """Collect and normalize tool metrics for given platform."""
    try:
        raw_data = BioToolsClient().fetch(biotools_id)
        tool_model = BioToolsAdapter().to_tool_model(raw_data)
        return tool_model
    except Exception as e:
        logger.warning(f"Failed to collect metrics for biotoolsID {biotools_id}: {e}")
        return None


def collect_code_quality(
    repo_url: str | None, repo_path: str | None
) -> CodeQualityMetrics | None:
    """Collect and normalize code quality metrics."""
    client = LizardCollector()
    try:
        if not repo_path:
            with temporary_clone(repo_url) as temp_path:
                raw_data = client.fetch(temp_path)
        else:
            raw_data = client.fetch(repo_path)

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


def collect_howfairis(repo_url: str) -> dict | None:
    client = HowfairisCollector()
    try:
        fair_metrics = client.fetch(repo_url)
        return fair_metrics
    except Exception as e:
        logger.warning(f"Failed to collect HowFairis metrics for {repo_url}: {e}")
        return None


def collect_publications(pmid: str, doi: str) -> dict | None:
    epmc_client = EuropePMCClient()
    ss_client = SemanticScholarClient()

    try:
        epmc_data = epmc_client.fetch(pmid)
        ss_data = ss_client.fetch(doi)
        # TODO Process and combine data as needed

        return {"epmc": epmc_data, "semantic_scholar": ss_data}
    except Exception as e:
        logger.warning(
            f"Failed to collect publication metrics for PMID {pmid} and DOI {doi}: {e}"
        )
        return None


def collect_repository(
    repo_identifier: str,
    platform: str,
    github_token: str | None,
    gitlab_token: str | None,
) -> RepositoryMetrics | None:
    if platform == "github":
        client = GitHubClient(token=github_token)
        adapter = GitHubAdapter()

    elif platform == "gitlab":
        client = GitLabClient(token=gitlab_token)
        adapter = GitLabAdapter()

    try:
        raw_data = client.fetch(repo_identifier)
        repo_model = adapter.to_repository_metrics(raw_data)
        return repo_model
    except Exception as e:
        logger.warning(
            f"Failed to collect repository metrics for {repo_identifier} on {platform}: {e}"
        )
        return None

    # def _merge_citation_metrics(
    #    self,
    #    europepmc_metrics: dict[str, Any] | None,
    #    semantic_scholar_metrics: dict[str, Any] | None,
    # ) -> dict[str, Any] | None:
    #    """Merge citation metrics from Europe PMC and Semantic Scholar."""
    #    if not europepmc_metrics and not semantic_scholar_metrics:
    #        return None
    #    merged_metrics: dict[str, Any] = dict(europepmc_metrics or {})
    #    if semantic_scholar_metrics:
    #        merged_metrics.update(
    #            {
    #                "doi": semantic_scholar_metrics.get("externalIds", {}).get("DOI"),
    #                "title": semantic_scholar_metrics.get("title"),
    #                "citation_count": merged_metrics.get(
    #                    "citation_count",
    #                    semantic_scholar_metrics.get("citationCount"),
    #                ),
    #                "reference_count": semantic_scholar_metrics.get("referenceCount"),
    #                "year": semantic_scholar_metrics.get("year"),
    #                "authors": semantic_scholar_metrics.get("authors"),
    #                "influential_citation_count": semantic_scholar_metrics.get(
    #                    "influentialCitationCount"
    #                ),
    #            }
    #        )
    #    return merged_metrics
