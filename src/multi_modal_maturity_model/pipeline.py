"""High-level pipeline for maturity analysis of research software."""

import asyncio
import logging
from typing import TYPE_CHECKING

from .analyzers import HowfairisAnalyzer, LizardAnalyzer
from .clients import (
    AltmetricClient,
    BioToolsClient,
    EuropePMCClient,
    GitHubClient,
    GitLabClient,
    OpenAlexClient,
)
from .extraction import extract_all_metrics
from .git_utils import detect_platform, temporary_clone
from .normalization import normalize_metrics
from .models import MaturityProfile
from .scoring import DimensionScorer, OverallScorer

if TYPE_CHECKING:
    from .config import AppConfig

logger = logging.getLogger(__name__)


class MaturityPipeline:
    """
    High-level pipeline for maturity analysis of research software.

    Parameters
    ----------
    config : AppConfig
        Application configuration object.
    """

    def __init__(
        self,
        config: AppConfig,
    ):
        if config:
            self.config = config
            self.github_token = config.api.github_token
            self.gitlab_token = config.api.gitlab_token
            self.altmetric_api_key = config.api.altmetric_api_key

            self.dimension_scorer = DimensionScorer(config.weights)
            self.overall_scorer = OverallScorer(config.weights)

    async def run(
        self,
        repo_url: str,
        repo_path: str | None = None,
        biotools_id: str | None = None,
        dois: list[str] | None = None,
    ) -> dict[str, dict]:
        """
        Run the maturity analysis pipeline.

        Returns
        -------
        dict[str, dict]
            Dictionary containing:
            - 'raw_results': Raw data from all sources
            - 'extracted_metrics': Extracted metrics by metric name and source
            - 'normalized_metrics': Normalized metrics in [0, 1] scale
        """

        results_by_source = await self._fetch_all(repo_url, biotools_id, dois)

        # Only run analyzers if we have valid repo data
        repo_is_valid = "github" in results_by_source or "gitlab" in results_by_source

        if repo_is_valid:
            analysis_results = self._analyze_all(repo_url, repo_path)
            results_by_source.update(analysis_results)

        # Extract metrics using configuration
        publication_sources = ["openalex", "europepmc", "altmetric"]
        publication_results = {
            source: results_by_source.get(source, [])
            for source in publication_sources
            if source in results_by_source
        }

        # Convert patterns config to dict format
        patterns_dict = {
            "workflow_files": self.config.patterns.workflow_files,
            "distribution_files": self.config.patterns.distribution_files,
            "security_policy_files": self.config.patterns.security_policy_files,
            "security_scanning_files": self.config.patterns.security_scanning_files,
        }

        extracted_metrics = extract_all_metrics(
            metrics_cfg=self.config.metrics.metrics,
            results=results_by_source,
            patterns=patterns_dict,
            publication_results=publication_results if publication_results else None,
        )

        # Normalize extracted metrics to [0, 1] scale
        normalized_metrics = normalize_metrics(
            extracted_metrics=extracted_metrics,
            metrics_cfg=self.config.metrics.metrics,
        )

        dim_scores = self.dimension_scorer.score(normalized_metrics)
        overall_score = self.overall_scorer.aggregate(dim_scores)

        return {
            "raw_results": results_by_source,
            "extracted_metrics": extracted_metrics,
            "normalized_metrics": normalized_metrics,
            "maturity_profile": MaturityProfile(
                overall_score=overall_score,
                dimensions=dim_scores,
                metrics=normalized_metrics,
            ),
        }

    async def _fetch_all(
        self,
        repo_url: str,
        biotools_id: str | None = None,
        dois: list[str] | None = None,
    ) -> dict[str, dict]:
        """Collect data from all sources in parallel."""
        tasks = {}

        try:
            platform = detect_platform(repo_url)

            if platform == "github" and self.github_token:
                github_client = GitHubClient(repo_url, self.github_token)
                tasks["github"] = github_client.fetch()

            elif platform == "gitlab" and self.gitlab_token:
                gitlab_client = GitLabClient(repo_url, self.gitlab_token)
                tasks["gitlab"] = gitlab_client.fetch()
        except ValueError as e:
            logger.warning(f"Could not detect platform for {repo_url}: {e}")

        if biotools_id:
            biotools_client = BioToolsClient(biotools_id=biotools_id)
            tasks["biotools"] = biotools_client.fetch()

        if dois:
            openalex_client = OpenAlexClient(dois=dois)
            tasks["openalex"] = openalex_client.fetch()

            europepmc_client = EuropePMCClient(dois=dois)
            tasks["europepmc"] = europepmc_client.fetch()

            if self.altmetric_api_key:
                altmetric_client = AltmetricClient(
                    dois=dois, api_key=self.altmetric_api_key
                )
                tasks["altmetric"] = altmetric_client.fetch()

        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        return {
            source: result
            for source, result in zip(tasks.keys(), results)
            if not isinstance(result, Exception)
        }

    def _analyze_all(
        self, repo_url: str, repo_path: str | None = None
    ) -> dict[str, dict]:
        """Run all analyzers on the repository."""
        results = {}

        howfairis_analyzer = HowfairisAnalyzer(
            repo_url, self.github_token, self.gitlab_token
        )
        results["howfairis"] = howfairis_analyzer.analyze()

        if not repo_path:
            with temporary_clone(repo_url) as temp_path:
                lizard_analyzer = LizardAnalyzer(temp_path)
                results["lizard"] = lizard_analyzer.analyze()
        else:
            lizard_analyzer = LizardAnalyzer(repo_path)
            results["lizard"] = lizard_analyzer.analyze()

        return {key: value for key, value in results.items() if value is not None}
