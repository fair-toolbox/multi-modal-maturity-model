"""High-level pipeline for maturity analysis."""

import asyncio
import logging

from .analyzers import HowfairisAnalyzer, LizardAnalyzer
from .clients import (
    AltmetricClient,
    BioToolsClient,
    EuropePMCClient,
    GitHubClient,
    GitLabClient,
    OpenAlexClient,
)
from .config import Settings, load_config
from .extraction import MetricExtractor
from .git_utils import detect_platform, temporary_clone
from .normalization import normalize_all
from .scoring import score_all

logger = logging.getLogger(__name__)


class MaturityPipeline:
    """
    High-level pipeline for maturity analysis of research software.

    Parameters
    ----------
    settings : Settings
        Application API settings.
    weights_path : str | None
        Path to weights.yaml file. If None, default weights are used.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        weights_path: str | None = None,
    ):
        self.settings = settings or Settings()

        self.weights_cfg, self.metrics_cfg, self.patterns_cfg = load_config(
            weights_path=weights_path,
        )

        self.extractor = MetricExtractor(self.metrics_cfg, self.patterns_cfg)

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
        logger.info(f"Starting maturity analysis for {repo_url}")

        results_by_source = await self._fetch_all(repo_url, biotools_id, dois)

        # Only run analyzers if we have valid repo data
        repo_is_valid = "github" in results_by_source or "gitlab" in results_by_source

        if repo_is_valid:
            logger.info(f"Running analyzers for {repo_url}")
            analysis_results = self._analyze_all(repo_url, repo_path)
            results_by_source.update(analysis_results)
        else:
            logger.warning(
                f"No valid repository data found for {repo_url}. Skipping analyzers."
            )

        extracted_metrics = (
            self.extractor.extract_all(
                results=results_by_source,
            )
            if results_by_source
            else {}
        )
        normalized_metrics = normalize_all(
            extracted_metrics=extracted_metrics, metrics_cfg=self.metrics_cfg
        )
        scores = score_all(
            extracted_metrics=extracted_metrics,
            normalized_metrics=normalized_metrics,
            weights_cfg=self.weights_cfg,
        )

        return scores.model_dump()

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
            self.settings.token_for_host(platform)

            if platform == "github" and self.settings.github_token:
                github_client = GitHubClient(repo_url, self.settings.github_token)
                tasks["github"] = github_client.fetch()

            elif platform == "gitlab" and self.settings.gitlab_token:
                gitlab_client = GitLabClient(repo_url, self.settings.gitlab_token)
                tasks["gitlab"] = gitlab_client.fetch()
        except ValueError as e:
            logger.error(f"Repository: {e}")

        if biotools_id:
            biotools_client = BioToolsClient(biotools_id=biotools_id)
            tasks["biotools"] = biotools_client.fetch()

        if dois:
            openalex_client = OpenAlexClient(dois=dois)
            tasks["openalex"] = openalex_client.fetch()

            europepmc_client = EuropePMCClient(dois=dois)
            tasks["europepmc"] = europepmc_client.fetch()

            if self.settings.altmetric_token:
                altmetric_client = AltmetricClient(
                    dois=dois, api_key=self.settings.altmetric_token
                )
                tasks["altmetric"] = altmetric_client.fetch()

        logger.info(f"Fetching data from sources: {list(tasks.keys())}")

        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        successful_results = {}
        for source, result in zip(tasks.keys(), results):
            if isinstance(result, Exception):
                logger.warning(f"Error fetching data from {source}: {result}")
                continue

            successful_results[source] = result

        return successful_results

    def _analyze_all(
        self, repo_url: str, repo_path: str | None = None
    ) -> dict[str, dict]:
        """Run all analyzers on the repository."""
        results = {}

        howfairis_analyzer = HowfairisAnalyzer(
            repo_url, self.settings.github_token, self.settings.gitlab_token
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
